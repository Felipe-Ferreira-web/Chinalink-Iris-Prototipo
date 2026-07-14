// Seletores/heurísticas para navegar da página de produto até a página de
// contato do fornecedor, e para localizar o link "Ver detalhe" do celular e
// o CAPTCHA nela. A estrutura real do DOM do Alibaba muda com frequência e
// varia por layout — ajuste estes valores inspecionando a página alvo
// (DevTools > Elements) se algo parar de funcionar.
export const SELETORES = {
  // Texto do link/aba que leva à página de contatos do fornecedor.
  textoAbaContatos: ['contatos', 'contact', 'contact us'],

  // Link/span que revela o número (ex.: "Ver detalhe" ao lado de "Celular:").
  // A classe varia entre layouts ("view-details", "view-detail", etc.), mas o
  // texto é sempre esse — a interface do Alibaba usada aqui é sempre pt-BR —
  // então busca só pelo texto, escopado à linha do Celular/Telefone.
  textoVerDetalhe: ['ver detalhe'],
  // Rótulos que identificam a linha de "Celular" (para diferenciar de Telefone/Fax).
  textosLabelCelular: ['celular', 'mobile'],

  // Modal "Obter informações" que aparece depois de clicar em "Ver detalhe"
  // do celular, pedindo pra enviar o cartão de visita em troca do contato —
  // faz parte do fluxo normal (não é engano de clique), clicar automaticamente.
  textoModalCartao: ['obter informações', 'business card', 'get information'],
  textoBotaoEnviarCartao: ['enviar', 'send'],

  // Módulo "Informações de contato": o número vem como <img class="value-image">
  // (PNG base64) dentro de um .msg-item rotulado por .msg-title ("Celular:",
  // "Telefone:"). O texto real fica escondido (.value com display:none), então
  // a extração pega o src (data URI) da imagem e o server faz OCR.
  contato: {
    container: '.module-contactPersonNew',
    item: '.msg-item',
    titulo: '.msg-title',
    imagemValor: 'img.value-image',
    rotuloCelular: ['celular', 'mobile'],
    rotuloTelefone: ['telefone', 'phone', 'tel', 'fone'],
    // Último recurso, só quando não há celular nem telefone: o link do site
    // da empresa, que fica no mesmo módulo e nunca é obscurecido por imagem.
    rotuloSiteEmpresa: ['site da empresa', 'company website', 'website'],
  },

  // Seletores conhecidos dos widgets de CAPTCHA da Aliyun/Alibaba. Sempre
  // resolvido manualmente pelo colaborador (sem 2Captcha) — a extensão só
  // detecta que apareceu e espera ele sair do DOM.
  captchaSeletores: [
    '#nocaptcha',
    '.puzzle-captcha-container',
    '.puzzle-captcha-slider',
    '#puzzle-captcha-btn',
    '.scratch-captcha-container',
    '#baxia-dialog-content',
    '.baxia-dialog',
    '#nc_1_wrapper',
    '.nc_wrapper',
    'iframe[src*="captcha"]',
    'iframe[id*="baxia"]',
  ],
}
