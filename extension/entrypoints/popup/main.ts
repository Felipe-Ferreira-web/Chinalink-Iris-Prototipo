import './style.css'
import { lerStatus, observarStatus, type StatusAtual } from '../../utils/status'

const rotulos: Record<StatusAtual['estado'], string> = {
  ocioso: 'Ocioso',
  navegando_fornecedor: 'Abrindo página do fornecedor',
  validando_atalho: 'Testando atalho direto pra contatos',
  navegando_contatos: 'Abrindo aba de contatos',
  aguardando_botao: 'Procurando "Ver detalhe"',
  aguardando_captcha: 'Aguardando CAPTCHA (manual)',
  extraindo_contato: 'Extraindo contato',
  contato_enviado: 'Contato enviado',
  erro: 'Erro',
}

function renderizarStatus(status: StatusAtual | null) {
  const badge = document.getElementById('status-badge')!
  const mensagem = document.getElementById('status-mensagem')!

  if (!status) {
    badge.textContent = 'Ocioso'
    mensagem.textContent = 'Aguardando atividade numa página do Alibaba...'
    return
  }

  badge.textContent = rotulos[status.estado] ?? status.estado
  mensagem.textContent = status.fornecedor ? `${status.mensagem} (${status.fornecedor})` : status.mensagem
}

lerStatus().then(renderizarStatus)
observarStatus(renderizarStatus)

const botao = document.getElementById('testar-conexao')!
const resultado = document.getElementById('resultado')!

botao.addEventListener('click', async () => {
  resultado.textContent = 'Testando...'

  const resposta = await browser.runtime.sendMessage({
    type: 'iris:hub-request',
    path: '/api/health/',
    method: 'GET',
  })

  resultado.textContent = resposta?.ok
    ? `Server respondeu: ${JSON.stringify(resposta.data)}`
    : `Falha: ${resposta?.error ?? resposta?.status}`
})
