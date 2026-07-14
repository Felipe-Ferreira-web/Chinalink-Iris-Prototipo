import { SELETORES } from '../utils/constantes'
import { definirStatus, lerStatus, type StatusAtual } from '../utils/status'

export default defineContentScript({
  matches: ['*://*.alibaba.com/*'],
  main() {
    console.log('[Iris] Content script carregado em', location.href)
    iniciarFluxo()
  },
})

// Resetam a cada injeção do content script (ou seja, a cada navegação de
// página) — é isso que permite tentar de novo depois de um reload causado
// pela resolução do captcha.
let jaClicouBotaoVerDetalhe = false
let jaClicouEnviarCartao = false
let jaEnviouContato = false
interface RespostaServidor {
  ok: boolean
  status?: number
  data?: any
  error?: string
}

async function chamarServidor(path: string, method: string, body?: unknown): Promise<RespostaServidor> {
  const resposta = (await browser.runtime.sendMessage({ type: 'iris:hub-request', path, method, body })) as
    | RespostaServidor
    | undefined
  if (!resposta) return { ok: false, error: 'Sem resposta do background (extensão recarregando?)' }
  return resposta
}

async function iniciarFluxo() {
  const url = new URL(location.href)
  const productIdParam = url.searchParams.get('iris_product_id')
  let status = await lerStatus()

  if (productIdParam) {
    const productId = Number(productIdParam)
    const flowTerminado = status?.estado === 'contato_enviado' || status?.estado === 'erro' || !status
    if (status?.productId !== productId || flowTerminado) {
      status = {
        estado: 'navegando_fornecedor',
        productId,
        mensagem: 'Localizando página do fornecedor...',
        atualizadoEm: new Date().toISOString(),
      }
      await definirStatus(status)
    }
  }

  if (!status?.productId) return

  // Se uma tentativa anterior travou num estado sem tratamento no switch
  // abaixo (erro, ou uma extração que ficou pela metade por causa de reload/
  // falha de rede) e o colaborador reabre/recarrega uma página que já é
  // claramente o painel de contato, tenta de novo em vez de ficar parado.
  const estadosRetomaveis: StatusAtual['estado'][] = ['erro', 'extraindo_contato']
  if (estadosRetomaveis.includes(status.estado) && encontrarPainelContato()) {
    console.log(`[Iris] Estado anterior era "${status.estado}" mas esta página já é o painel de contato — tentando de novo.`)
    status = { ...status, estado: 'aguardando_botao', mensagem: 'Tentando novamente após estado anterior incompleto.' }
    await definirStatus(status)
  }

  await processarEtapa(status)
}

async function processarEtapa(status: StatusAtual) {
  switch (status.estado) {
    case 'navegando_fornecedor':
      await etapaNavegarFornecedor(status)
      break
    case 'validando_atalho':
      await etapaValidarAtalho(status)
      break
    case 'navegando_contatos':
      await etapaNavegarContatos(status)
      break
    case 'aguardando_botao':
    case 'aguardando_captcha':
      await etapaRevelarContato(status)
      break
  }
}

// Etapa 1: na página do produto, encontra o link para a página do fornecedor
// (usando o nome exato que já temos no banco, via product_id). Em vez de
// clicar e depois procurar a aba "Contatos" (2 navegações), monta direto a
// URL "{origem-do-fornecedor}/contactinfo.html" e navega pra lá — se esse
// atalho não for válido pra esse fornecedor, etapaValidarAtalho cai pro
// fluxo antigo (clicar na aba "Contatos").
async function etapaNavegarFornecedor(status: StatusAtual) {
  const resposta = await chamarServidor(`/api/products/${status.productId}/`, 'GET')
  if (!resposta.ok) {
    await definirStatus({ ...status, estado: 'erro', mensagem: `Falha ao buscar produto: ${resposta.error ?? resposta.status}` })
    return
  }

  const nomeFornecedor: string = resposta.data.supplier.name
  const link = await esperarPor(() => encontrarLinkPorTexto([nomeFornecedor]), 15000)
  if (!link) {
    await definirStatus({ ...status, estado: 'erro', mensagem: `Link do fornecedor "${nomeFornecedor}" não encontrado na página.` })
    return
  }

  const fornecedorHref = link.href
  const urlAtalho = `${new URL(fornecedorHref).origin}/contactinfo.html`

  await definirStatus({
    ...status,
    estado: 'validando_atalho',
    fornecedor: nomeFornecedor,
    fornecedorHref,
    mensagem: `Abrindo contatos de ${nomeFornecedor} (atalho)...`,
  })
  await atraso()
  location.href = urlAtalho
}

// Etapa 1.5: chegamos direto em {origem}/contactinfo.html — confirma que
// essa página realmente é o painel de contato (senão pode ser 404 ou layout
// diferente) antes de seguir. Se não achar em alguns segundos, volta pro
// fluxo antigo: navega pra home do fornecedor e clica na aba "Contatos".
async function etapaValidarAtalho(status: StatusAtual) {
  const valido = await esperarPor(
    () => (encontrarPainelContato() || encontrarBotaoVerDetalheCelular() || encontrarCaptcha() ? true : null),
    5000
  )

  if (valido) {
    await definirStatus({ ...status, estado: 'aguardando_botao', mensagem: 'Painel de contato encontrado (atalho funcionou).' })
    await processarEtapa({ ...status, estado: 'aguardando_botao' })
    return
  }

  if (status.atalhoTentado || !status.fornecedorHref) {
    await definirStatus({ ...status, estado: 'erro', mensagem: 'Atalho pra contactinfo.html falhou e não há fallback disponível.' })
    return
  }

  console.log('[Iris] Atalho direto pra contactinfo.html não funcionou pra este fornecedor, voltando ao fluxo por clique.')
  await definirStatus({
    ...status,
    estado: 'navegando_contatos',
    atalhoTentado: true,
    mensagem: `Abrindo página de ${status.fornecedor}...`,
  })
  await atraso()
  location.href = status.fornecedorHref
}

// Etapa 2 (fallback): na página do fornecedor, encontra e clica na aba "Contatos".
async function etapaNavegarContatos(status: StatusAtual) {
  const link = await esperarPor(() => encontrarLinkPorTexto(SELETORES.textoAbaContatos), 15000)
  if (!link) {
    await definirStatus({ ...status, estado: 'erro', mensagem: 'Aba "Contatos" não encontrada na página do fornecedor.' })
    return
  }

  await definirStatus({ ...status, estado: 'aguardando_botao', mensagem: 'Abrindo aba de contatos...' })
  await atraso()
  link.click()
}

function encontrarPainelContato(): Element | null {
  return document.querySelector(SELETORES.contato.container)
}

// Etapa 3: na página de contatos, clica em "Ver detalhe" do celular, trata o
// CAPTCHA (sempre manual — o colaborador resolve na própria aba) e extrai o
// número revelado. Fica observando mudanças na tela até terminar.
async function etapaRevelarContato(status: StatusAtual) {
  observarMudancasDeTela(status)
  if (await processarTelaDeContato(status)) return

  const botao = await esperarPor(encontrarBotaoVerDetalheCelular, 15000)
  if (botao && !jaClicouBotaoVerDetalhe) {
    jaClicouBotaoVerDetalhe = true
    console.log('[Iris] Clicando em "Ver detalhe" do celular:', botao)
    await atraso()
    botao.click()
    return
  }
  if (!botao) {
    await definirStatus({ ...status, estado: 'erro', mensagem: '"Ver detalhe" do celular não encontrado nesta página.' })
  }
}

function observarMudancasDeTela(status: StatusAtual) {
  const observer = new MutationObserver(async () => {
    if (await processarTelaDeContato(status)) observer.disconnect()
  })
  observer.observe(document.body, { childList: true, subtree: true })
}

// Retorna true quando o fluxo terminou (contato enviado) e não é mais
// preciso observar a tela.
async function processarTelaDeContato(status: StatusAtual): Promise<boolean> {
  if (jaEnviouContato) return true

  const botaoCartao = encontrarBotaoEnviarCartao()
  if (botaoCartao && !jaClicouEnviarCartao) {
    jaClicouEnviarCartao = true
    console.log('[Iris] Clicando em "Enviar" no modal de cartão de visita:', botaoCartao)
    await atraso()
    botaoCartao.click()
    return false
  }

  const captcha = encontrarCaptcha()
  if (captcha) {
    const atual = await lerStatus()
    if (atual?.estado !== 'aguardando_captcha') {
      console.log('[Iris] CAPTCHA detectado, aguardando resolução manual:', captcha)
      await definirStatus({ ...status, estado: 'aguardando_captcha', mensagem: 'CAPTCHA detectado — resolva manualmente para continuar.' })
    }
    return false
  }

  return tentarExtrairEEnviar(status)
}

async function tentarExtrairEEnviar(status: StatusAtual): Promise<boolean> {
  if (jaEnviouContato) return true

  const contato = extrairContato()
  if (!contato) return false

  jaEnviouContato = true
  await definirStatus({ ...status, estado: 'extraindo_contato', mensagem: 'Contato encontrado, extraindo número...' })

  const resposta = await chamarServidor('/api/contacts/extractions/', 'POST', {
    product: status.productId,
    status: 'extraido',
    ...(contato.campo === 'site'
      ? { company_website: contato.valor }
      : contato.tipo === 'imagem'
        ? { image_data: contato.valor }
        : { phone_text: contato.valor }),
  })

  if (!resposta.ok) {
    jaEnviouContato = false
    await definirStatus({ ...status, estado: 'erro', mensagem: `Falha ao enviar contato ao server: ${resposta.error ?? resposta.status}` })
    return true
  }

  await definirStatus({ ...status, estado: 'contato_enviado', mensagem: 'Contato extraído e enviado ao server com sucesso.' })
  return true
}

type ContatoExtraido =
  | { campo: 'telefone'; tipo: 'imagem' | 'texto'; valor: string }
  | { campo: 'site'; valor: string }

// Placeholder que o Alibaba mostra quando o campo existe mas está vazio
// (ex.: "Celular: -") — não conta como valor encontrado.
const VALOR_VAZIO = '-'

// O texto visível do "Site da empresa" às vezes vem sem esquema (ex.:
// "www.foo.com"), diferente do href de um <a> (sempre absoluto). Não é
// obrigatório pro server aceitar (company_website virou CharField), mas
// deixa o valor mais útil caso vire link algum dia.
function normalizarUrl(valor: string): string {
  return /^https?:\/\//i.test(valor) ? valor : `http://${valor}`
}

function ehGatilhoVerDetalhe(el: Element): boolean {
  const texto = el.textContent?.trim().toLowerCase() ?? ''
  return SELETORES.textoVerDetalhe.includes(texto)
}

// Pega só o texto entre este rótulo e o próximo — em alguns layouts o
// Alibaba agrupa dois campos (ex.: Celular e Site da empresa) no mesmo
// .msg-item, e pegar o texto do item inteiro vazava o campo errado.
// Pula o próprio gatilho "Ver detalhe" (span/link que abre o captcha): antes
// do valor ser revelado, ele é o único irmão não-vazio ali, e sem esse skip
// a extração mandava "Ver detalhe" pro server como se fosse o número.
function valorTextoAposRotulo(tituloEl: Element | null): string {
  let texto = ''
  let proximo: Element | null = tituloEl?.nextElementSibling ?? null
  while (proximo) {
    if (proximo.matches(SELETORES.contato.titulo)) break
    if (ehGatilhoVerDetalhe(proximo)) {
      proximo = proximo.nextElementSibling
      continue
    }
    texto = proximo.textContent?.trim() ?? ''
    if (texto) break
    proximo = proximo.nextElementSibling
  }
  return texto
}

function itemTemGatilhoVerDetalhe(item: HTMLElement): boolean {
  return Array.from(item.querySelectorAll<HTMLElement>('*')).some((el) => {
    if (el.children.length !== 0) return false
    return ehGatilhoVerDetalhe(el)
  })
}

type ResultadoCampoTelefone =
  | { estado: 'valor'; contato: ContatoExtraido }
  | { estado: 'vazio' | 'pendente' }

// O número do fornecedor às vezes vem como <img class="value-image"> (PNG
// base64, pra dificultar scraping) e às vezes já como texto visível direto no
// DOM — depende do layout/fluxo. Tenta a imagem primeiro (precisa de OCR no
// server) e cai pro texto puro (já pronto, sem OCR) quando não há imagem.
//
// Distingue "campo vazio" (mostra "-", de fato não tem esse contato) de
// "campo pendente" (ainda mostra só o gatilho "Ver detalhe", não revelado
// ainda) — sem essa distinção, a extensão caía direto pro site da empresa
// (que costuma vir visível, sem precisar de clique) antes mesmo de tentar
// revelar o celular/telefone, marcando o fornecedor como "contato extraído"
// prematuramente.
function analisarCampoTelefone(itens: HTMLElement[], rotulos: string[]): ResultadoCampoTelefone {
  for (const item of itens) {
    const tituloEl = item.querySelector(SELETORES.contato.titulo)
    const titulo = tituloEl?.textContent?.trim().toLowerCase() ?? ''
    if (!rotulos.some((r) => titulo.includes(r))) continue

    const img = item.querySelector<HTMLImageElement>(SELETORES.contato.imagemValor)
    const src = img?.getAttribute('src') ?? ''
    if (src.startsWith('data:image')) {
      return { estado: 'valor', contato: { campo: 'telefone', tipo: 'imagem', valor: src } }
    }

    if (itemTemGatilhoVerDetalhe(item)) return { estado: 'pendente' }

    const texto = valorTextoAposRotulo(tituloEl)
    if (texto && texto !== VALOR_VAZIO) {
      return { estado: 'valor', contato: { campo: 'telefone', tipo: 'texto', valor: texto } }
    }
    return { estado: 'vazio' }
  }
  return { estado: 'vazio' }
}

// Prioridade: Celular > Telefone > Site da empresa (só como último recurso,
// quando o fornecedor não tem nenhum telefone/celular cadastrado — nunca
// enquanto algum dos dois ainda estiver "pendente" de revelação).
function extrairContato(): ContatoExtraido | null {
  const container = document.querySelector(SELETORES.contato.container)
  if (!container) return null

  const itens = Array.from(container.querySelectorAll<HTMLElement>(SELETORES.contato.item))

  const celular = analisarCampoTelefone(itens, SELETORES.contato.rotuloCelular)
  if (celular.estado === 'valor') return celular.contato
  if (celular.estado === 'pendente') return null

  const telefone = analisarCampoTelefone(itens, SELETORES.contato.rotuloTelefone)
  if (telefone.estado === 'valor') return telefone.contato
  if (telefone.estado === 'pendente') return null

  for (const item of itens) {
    const tituloEl = item.querySelector(SELETORES.contato.titulo)
    const titulo = tituloEl?.textContent?.trim().toLowerCase() ?? ''
    if (!SELETORES.contato.rotuloSiteEmpresa.some((r) => titulo.includes(r))) continue

    const link = item.querySelector<HTMLAnchorElement>('a[href]')
    if (link?.href) return { campo: 'site', valor: link.href }

    const texto = valorTextoAposRotulo(tituloEl)
    if (texto && texto !== VALOR_VAZIO) return { campo: 'site', valor: normalizarUrl(texto) }
  }
  return null
}

function encontrarLinkPorTexto(textos: string[]): HTMLAnchorElement | null {
  const alvo = textos.map((t) => t.trim().toLowerCase())
  const links = Array.from(document.querySelectorAll<HTMLAnchorElement>('a'))
  return (
    links.find((a) => alvo.includes(a.textContent?.trim().toLowerCase() ?? '')) ??
    links.find((a) => alvo.some((t) => (a.textContent?.trim().toLowerCase() ?? '').includes(t))) ??
    null
  )
}

// Escopado só dentro do módulo de contato (mesmo container usado pra extrair
// a imagem do número) — nunca considera botões de fora dele, como o "Contato
// agora"/"Enviar consulta" da barra lateral, que abrem um fluxo totalmente
// diferente (pedido de contato via mensagem, exige troca de cartão de visita)
// em vez de revelar o número diretamente.
function encontrarBotaoVerDetalhePorRotulo(rotulos: string[]): HTMLElement | null {
  const container = document.querySelector(SELETORES.contato.container)
  if (!container) return null

  const itens = Array.from(container.querySelectorAll<HTMLElement>(SELETORES.contato.item))
  for (const item of itens) {
    const titulo = item.querySelector(SELETORES.contato.titulo)?.textContent?.trim().toLowerCase() ?? ''
    if (!rotulos.some((t) => titulo.includes(t))) continue

    const botao = Array.from(item.querySelectorAll<HTMLElement>('*')).find((el) => {
      if (el.children.length !== 0) return false
      return ehGatilhoVerDetalhe(el)
    })
    if (botao) return botao
  }
  return null
}

// Celular primeiro; se a linha do Celular estiver vazia ("-", sem gatilho
// "Ver detalhe" nenhum), tenta a do Telefone — mesma prioridade usada na
// extração, senão o fluxo travava em fornecedores sem celular cadastrado.
function encontrarBotaoVerDetalheCelular(): HTMLElement | null {
  return (
    encontrarBotaoVerDetalhePorRotulo(SELETORES.textosLabelCelular) ??
    encontrarBotaoVerDetalhePorRotulo(SELETORES.contato.rotuloTelefone)
  )
}

// Localiza o botão "Enviar" do modal "Obter informações" (pede pra trocar o
// cartão de visita pelo contato do fornecedor, aberto pelo "Ver detalhe"):
// procura botões/links com esse texto exato dentro de um contêiner cujo
// texto bate com o cabeçalho/corpo do modal.
function encontrarBotaoEnviarCartao(): HTMLElement | null {
  const candidatos = Array.from(document.querySelectorAll<HTMLElement>('button, a, [role="button"]')).filter((el) => {
    const texto = el.textContent?.trim().toLowerCase() ?? ''
    return SELETORES.textoBotaoEnviarCartao.includes(texto)
  })

  for (const el of candidatos) {
    if (!estaVisivel(el)) continue
    let atual: HTMLElement | null = el
    for (let i = 0; i < 6 && atual; i++) {
      const texto = atual.textContent?.toLowerCase() ?? ''
      if (SELETORES.textoModalCartao.some((t) => texto.includes(t))) {
        return el
      }
      atual = atual.parentElement
    }
  }
  return null
}

function estaVisivel(el: Element): boolean {
  const estilo = getComputedStyle(el as HTMLElement)
  if (estilo.display === 'none' || estilo.visibility === 'hidden' || estilo.opacity === '0') return false
  const rect = (el as HTMLElement).getBoundingClientRect()
  return rect.width > 1 && rect.height > 1
}

function encontrarCaptcha(): Element | null {
  // Só considera visível: a baxia costuma só esconder (display:none) o widget
  // depois de resolvido, em vez de remover do DOM — sem essa checagem o
  // fluxo acharia que o captcha nunca sai.
  for (const seletor of SELETORES.captchaSeletores) {
    for (const el of Array.from(document.querySelectorAll(seletor))) {
      if (estaVisivel(el)) return el
    }
  }
  return null
}

const DELAY_ANTI_BOT_MS = 2000

// Espera antes de cada clique/ação pra não disparar detecção anti-bot por
// cliques instantâneos demais assim que o elemento aparece na tela.
function atraso(ms = DELAY_ANTI_BOT_MS): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function esperarPor<T>(fn: () => T | null, timeoutMs: number, intervaloMs = 300): Promise<T | null> {
  return new Promise((resolve) => {
    const inicio = Date.now()
    const tick = () => {
      const resultado = fn()
      if (resultado) return resolve(resultado)
      if (Date.now() - inicio >= timeoutMs) return resolve(null)
      setTimeout(tick, intervaloMs)
    }
    tick()
  })
}
