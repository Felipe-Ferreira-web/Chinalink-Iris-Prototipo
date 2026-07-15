# Bot WeCom

> Documento único deste módulo — o que é, como funciona, o que foi
> integrado com o server Django (Busca de Suppliers), bugs descobertos e
> corrigidos (incluindo a investigação completa de AT-SPI), e o que ainda
> está pendente.

## O que é

Automatiza o **WeChat desktop nativo para Linux** (pacote AUR `wechat` →
`wechat-bin`, sandboxed via bwrap pelo wrapper "portable" da Kraftland).
Não é WeCom, não é navegador — é o cliente oficial da Tencent (Qt, cliente
X11 via XWayland), sandboxed.

**Instalação** (Arch/AUR):
```bash
paru -S wechat-bin       # ou wechat-universal-bwrap — ver seção AT-SPI abaixo pra diferença
```

Repositórios: sandbox `wechat` (Kraftland) — https://github.com/Kraftland/portable;
cliente real `wechat-bin` (binário proprietário Tencent) — https://weixin.qq.com/

## Por que automação por pixel, não semântica

O jeito ideal de automatizar um app desktop é via **AT-SPI** — a árvore de
acessibilidade que leitores de tela (ex. Orca) usam pra navegar a UI sem
"ver" a tela: pergunta programaticamente "que elementos existem aqui",
sem depender de onde as coisas estão desenhadas.

**Testado exaustivamente e descartado**, em 3 configurações diferentes:

**1ª rodada — `wechat-universal-bwrap`** (`paru -S wechat-universal-bwrap`):
consultada a árvore de apps no barramento AT-SPI via `gi.repository.Atspi`
(`Atspi.get_desktop(0)`), mesmo mecanismo do `explore_ui.py`. Resultado: só
5 apps do sistema aparecem registrados (`ksmserver`, `gmenudbusmenuproxy`,
`xembedsniproxy`, `kaccess`, `xdg-desktop-portal-gtk`) — o WeChat não
aparece. Causa provável, inspecionando o script de sandbox
(`/usr/lib/wechat-universal/start.sh`, bubblewrap): faz bind do socket do
D-Bus de sessão, mas **não** faz bind do socket separado do AT-SPI
(tipicamente `$XDG_RUNTIME_DIR/at-spi/bus`). Sem esse socket dentro do
sandbox, o app não consegue se conectar ao barramento de acessibilidade
mesmo linkando `at-spi2-core`.

**2ª rodada — pacote `wechat` 1:11 (sandbox "Portable", Kraftland)**:
diferente do `wechat-universal-bwrap`, esse sandbox **já faz bind do
socket AT-SPI por padrão** e monta um proxy D-Bus dedicado só pra chamadas
`org.a11y.atspi.*` (confirmado na própria linha de comando do `bwrap` em
execução). Mesmo assim, o WeChat não aparece na lista AT-SPI.

**3ª tentativa — forçar `QT_ACCESSIBILITY=1`**: fechado o WeChat
(`portable --actions quit`) e relançado com essa variável antes do
`portable`. Mesmo resultado — e nem é garantido que a variável chegou de
fato dentro do sandbox (o lançamento passa por `systemd-run`, que não
herda o ambiente do shell automaticamente).

**Conclusão**: testado em 3 configurações diferentes (universal sem bind
do socket, sandbox padrão com bind do socket, sandbox com
`QT_ACCESSIBILITY=1` forçado) — todas negativas. Não é problema de
sandbox/configuração: mesmo com o canal de comunicação disponível e
configurado corretamente pelo empacotador, o binário do WeChat em si não
implementa/emite nada na árvore de acessibilidade nesta plataforma, mesmo
linkando `at-spi2-core`.

Também foi investigado se existe algum **endpoint/API alternativo** antes
de aceitar essa conclusão: `WeChatAppEx` (runtime de mini-programas,
baseado em Chromium — confirmado via `strings` no binário, que lista a
flag `--remote-debugging-port`) até suporta debug remoto de verdade, mas é
um processo separado que só hospeda mini-programas, não a UI nativa de
contatos/conversas. O binário principal (`wechat`) não expõe D-Bus próprio
nem porta de debug (`strings` só acha um genérico `--debug`, sem API por
trás). Uma porta HTTP local encontrada aberta (127.0.0.1:34331) foi
testada via `curl` e não é um protocolo CDP nem nada documentado — só
retorna 404, provavelmente um servidor de recursos internos do runtime de
mini-programas. **Automação por tela é o único caminho viável aqui.**

Por isso a automação é "por pixel": screenshot + OCR (Tesseract via
`pytesseract`) pra ler texto e achar posições, `ydotool`/`xdotool` pra
mover o mouse e clicar, `xclip` + Ctrl+V pra colar texto.

## Como a janela é encontrada

`_NET_CLIENT_LIST` da raiz (não `xdotool search --class`/`--name` — ambos
casam com sub-janelas erradas: o título muda entre sessões, "Weixin" numa e
"WeChat" noutra, e buscas por nome/classe livre casam com janelas auxiliares
menores como tooltips ou o ícone de bandeja). Ver `utils.py::buscar_janela`.

**Mas nem toda janela do WeChat é "top-level" nesse sentido.** Os diálogos
"Add Contacts" e "Send Friend Request" (ver seção de integração abaixo) são
janelas reais, com geometria e título próprios, mas **não aparecem em
`_NET_CLIENT_LIST`** — só são encontráveis via `xdotool search --name`
(`utils.py::buscar_janela_por_nome`). Uma versão anterior desta automação
assumia (errado) que o WeChat só tinha uma janela, e por isso capturava/
clicava sempre na janela base enquanto o diálogo de verdade estava por cima.

## Como a tela é capturada

`spectacle -f` (tela **toda**, todos os monitores) + recorte pela geometria
conhecida da janela alvo — não `spectacle -a` (janela ativa) nem
`import`/ImageMagick.

- ImageMagick (`import -window <id>`) não funciona: captura X11 legada de
  janela específica é bloqueada pelo compositor Wayland/KWin neste setup.
  `spectacle` passa pelo portal oficial e funciona.
- `spectacle -a` (janela ativa) **foi trocado por `-f` (tela toda)** depois
  de um bug confirmado ao vivo: se o usuário estivesse com o foco em outra
  janela (IDE, terminal) no instante exato da captura, `-a` fotografava
  aquilo em vez do WeChat, produzindo OCR de conteúdo completamente errado
  (ex.: capturou o próprio texto do terminal, achando que era um botão do
  WeChat). Capturar a tela toda e recortar por geometria conhecida não
  depende de foco nenhum — só de a janela estar visível (não coberta).
- Esse mesmo motivo (reativar janela = perder foco de popups transitórios)
  também tinha outro efeito colateral: `focar_janela` (windowactivate)
  antes de cada screenshot estava **fechando os próprios menus/diálogos**
  que a automação acabara de abrir. Com a captura por `-f`, não precisamos
  mais reativar nada só pra fotografar.

## OCR: texto por conteúdo, não coordenada fixa

A maioria dos elementos clicáveis tem rótulo de texto visível — pra esses,
a automação localiza o texto por OCR TODA VEZ que roda (`_localizar_texto_em_area`),
em vez de decorar uma coordenada de pixel. Isso elimina a necessidade de
recalibrar quando a janela muda de tamanho/posição — só é preciso
recalibrar se o TEXTO do botão mudar de verdade (nova versão do app, outro
idioma).

Só botões **ícone-only** (sem texto, ex. o "+" de atalhos) não têm como ser
achados assim — pra esses, guardamos posição + legenda (tooltip, que
aparece ao passar o mouse) e, se a posição salva não bater mais com a
legenda esperada, o bot varre a janela sozinho procurando de novo
(`_localizar_icone_por_tooltip`).

**Achado curioso**: nem todo texto visível é um botão. No diálogo "Add
Contacts", o texto "Search" faz parte do PLACEHOLDER do campo ("Search
WeChat ID or mobile number", uma frase só) — não existe botão separado de
busca. A busca dispara com **Enter** depois de colar o número, não com
clique num botão.

## Envio de mensagem (`send_message`) — bug do toggle da sidebar

Clicar na conversa da sidebar quando ela **já está aberta** a FECHA (é um
toggle, não "abrir garantido") — causou uma falha silenciosa difícil de
depurar (clique/colagem indo pro painel vazio, sem erro nenhum). Por isso
`send_message` confere o título do chat atualmente aberto via OCR antes de
decidir se precisa clicar na sidebar. Vale pra qualquer automação futura
que alterne entre conversas: nunca assumir qual está aberta, sempre
confirmar antes de agir.

Texto é colado via clipboard (`xclip` + Ctrl+V simulado), não digitado
tecla-por-tecla (`xdotool type` é bem menos confiável pra acentos/unicode).
A janela é refocada antes de CADA ação (clique/colagem), não só uma vez no
início — reduz (sem eliminar) a corrida com o uso real do mouse/teclado do
colaborador, já que a automação roda no mesmo display X de verdade.

## Movimento do mouse — bugs de `xdotool`/`ydotool`

- `xdotool mousemove` **não move o ponteiro de verdade** neste setup —
  bloqueio do Wayland/KWin ao warp via XTest (confirmado ao vivo: posição
  não mudava, clique caía onde o mouse físico já estava). Resolvido
  trocando por `ydotool` (injeta via uinput, nível do kernel).
- `ydotool mousemove --absolute` também não é perfeito: mapeia pra um
  espaço de coordenadas que não bate com pixels reais em setup
  multi-monitor (confirmado ao vivo: pedir uma posição específica foi
  parar no canto errado da tela). Uma tentativa de corrigir por delta
  relativo em malha fechada foi testada e descartada — a leitura de
  posição via `xdotool getmouselocation` não é confiável o bastante pra
  fechar a malha, e o cursor chegou a sair da tela numa tentativa. Ficamos
  com `--absolute` simples mesmo, sabendo da limitação.
- **Pré-requisito pra rodar qualquer coisa que clique**: `ydotoold`
  rodando e o usuário no grupo `input`:
  ```bash
  sudo pacman -S --needed ydotool
  sudo usermod -aG input $USER   # nova sessão de shell pra aplicar
  systemctl --user enable --now ydotool.service
  ```

## Integração com o server Django (Busca de Suppliers)

Objetivo: quando um fornecedor tem `status=contato_extraido` no server,
buscar o telefone no WeChat, enviar pedido de amizade, marcar
`contato_wechat_enviado`.

**Server** (fora desta pasta): novo status `Supplier.Status.CONTATO_WECHAT_ENVIADO`;
`SupplierSerializer` expõe `contact_phone`/`contact_website` direto;
`SupplierViewSet` ganhou filtro `?status=` e `PATCH`.

**Bot WeCom**:
- `server_client.py` — cliente HTTP (`buscar_suppliers_aguardando_contato`,
  `marcar_contato_wechat_enviado`).
- `sync_suppliers.py` — loop de sincronização; `--test-phone` testa uma
  tentativa isolada contra um número fixo, sem precisar do server.
- `calibrate_add_contact.py` — calibração interativa (contagem regressiva
  de 5s por etapa: aperta Enter no terminal, troca pro WeChat, navega até
  a tela certa, deixa o mouse parado até a captura).
- `wechat_client.search_and_add_contact()` — a automação.

### Fluxo atual

```
1. Ícone de atalhos (shortcuts_button) — clique confirmado por legenda (tooltip)
2. "Add Contacts" no menu — clique por texto (OCR)
       ↓ abre janela separada "Add Contacts" (buscar_janela_por_nome)
3. Campo de busca — clique (sem verificação de mudança na tela)
4. Cola o telefone + Enter (não existe botão "Search" separado)
5. "Add to Contacts" no card de perfil — clique por texto
       ↓ abre janela separada "Send Friend Request" (buscar_janela_por_nome)
6. Botão de confirmar/enviar — clique por texto
```

### Pendências / não confirmado

- **`send_request_button` ainda não calibrado corretamente.** Última
  captura leu "Hide Their Posts" (item de menu de privacidade/momentos de
  outra tela, não um botão de confirmar) — a calibração desse passo
  específico ainda pega o elemento errado, ou a janela "Send Friend
  Request" não estava estável no momento da captura.
- Nunca confirmado ponta a ponta com um número real que exista no WeChat.
- Rótulos de texto genéricos (nomes curtos, comuns a outras telas) têm
  risco de match falso se aparecerem em mais de um lugar na mesma janela.
- Decisão em aberto: continuar debugando esse método, simplificar pra
  coordenada fixa sem OCR, ou deixar esse passo manual.

## Limitações conhecidas (gerais)

- Leitura de mensagens é comparação de linhas de texto via OCR do chat
  **atualmente aberto** — não sabe de qual remetente veio, não lê chats em
  segundo plano, pode confundir linhas se o OCR errar caracteres.
- Só `tesseract-data-eng`/`tesseract-data-por` instalados — mensagens em
  chinês saem como lixo no OCR (`tesseract-data-chi-sim` se precisar).
- Clique na sidebar só funciona se a conversa já estiver visível sem
  rolar.
- Automação roda no **mesmo display X que o colaborador usa de verdade** —
  cliques/colagem podem competir com o uso real do mouse/teclado. Mover
  pra um Xvfb isolado é mecanicamente viável mas exigiria encerrar a sessão
  real do WeChat (mesma conta usada como "mascote" por decisão temporária)
  — retomar quando houver conta separada.
- `python -u`/logging sem buffer é necessário pra ver `print()` em tempo
  real quando a saída não é um terminal interativo.

## Setup

```bash
cd "Bot WeCom"
sudo pacman -S --needed xdotool ydotool python-gobject xclip tesseract tesseract-data-eng tesseract-data-por
sudo usermod -aG input $USER   # necessário pro ydotool; nova sessão de shell pra aplicar
systemctl --user enable --now ydotool.service
python3 -m venv --system-site-packages venv   # --system-site-packages: PyGObject (gi/Atspi) não é instalável via pip
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Uso

```bash
python explore_ui.py                       # diagnóstico: localiza janela, tenta AT-SPI, salva screenshot
python main.py                             # loop de leitura (imprime mensagens novas do chat aberto)
python main.py --test-reply "teste"        # também testa envio pra TARGET_CHAT_NAME (use "File Transfer")
python calibrate_add_contact.py            # (re)calibra o fluxo de adicionar contato
python sync_suppliers.py --test-phone      # testa busca+adicionar contato isolado, sem server/loop
python sync_suppliers.py                   # loop real, consultando o server
```
