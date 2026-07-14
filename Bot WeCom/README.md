# Bot WeChat — leitura e envio via automação de UI nativa (protótipo, sem IA)

Automatiza o **WeChat desktop nativo para Linux** (pacote AUR `wechat` →
`wechat-bin`, sandboxed via bwrap pelo wrapper "portable" da Kraftland).
Não é WeCom, não é navegador — é um app desktop nativo (Qt, cliente X11 via
XWayland).

**Instalação** (Arch/AUR):

```bash
paru -S wechat-universal-bwrap
```

(ou `wechat-bwrap`/`wechat-bin` — todos resolvem pro mesmo pacote `wechat`).

**Repositórios:**
- `wechat` (wrapper de sandbox, o que o AUR instala): https://github.com/Kraftland/portable
- `wechat-bin` (cliente real, binário proprietário da Tencent): https://weixin.qq.com/

Escopo desta etapa: **só o loop de leitura + envio**. Sem GPT-4o-mini, sem
histórico de conversa, sem integração com o server Django do Módulo 1.

## Como funciona (Caminho B — coordenadas de tela + OCR)

Testamos primeiro se dava pra automatizar via AT-SPI (árvore de
acessibilidade — mais robusto, não depende de coordenada de pixel). Não deu:
o WeChat não registra nada no barramento AT-SPI deste sistema (confirmado
com `explore_ui.py` — a lista de apps do barramento nem lista o WeChat).

Por isso a automação aqui é "por pixel":
1. Encontra a janela principal via `_NET_CLIENT_LIST` da raiz (não
   `xdotool search --class`/`--name` — ambos casam com sub-janelas erradas
   ou título ambíguo; o título da janela varia entre sessões, "Weixin" numa
   e "WeChat" noutra — veja comentário em `utils.py::buscar_janela`).
2. Foca a janela e tira um screenshot via `spectacle -a` (não `import`/
   ImageMagick — captura X11 legada de janela específica é bloqueada pelo
   compositor Wayland/KWin neste setup; `spectacle` passa pelo portal e
   funciona).
3. Usa OCR (Tesseract via `pytesseract`) pra achar o nome da conversa na
   sidebar e clicar nela, e pra ler o texto do painel de mensagens.
4. Envia texto colando no clipboard (`xclip`) + Ctrl+V, mais confiável que
   `xdotool type` pra acentos/unicode.

Coordenadas de clique (caixa de texto, botão "Send(S)") estão calibradas
contra o layout real da janela (1309x650) em `wechat_client.py` — se o
WeChat mudar de versão/layout, ou a janela for redimensionada, recalibrar
rodando `explore_ui.py` de novo e ajustando as constantes `*_REL`.

**Importante — checar estado antes de agir**: clicar na conversa da sidebar
quando ela **já está aberta** a FECHA (é um toggle, não um "abrir
garantido") — isso causou uma falha silenciosa bem difícil de depurar
(clique/colagem indo pro painel vazio, sem erro nenhum). `send_message` por
isso confere o título do chat atualmente aberto via OCR antes de decidir se
precisa clicar na sidebar. Esse princípio vale pra qualquer automação futura
que alterne entre várias conversas: nunca assumir qual está aberta, sempre
confirmar antes.

## Limitações conhecidas

- Leitura é uma comparação de linhas de texto via OCR do chat **atualmente
  aberto** — não sabe de qual remetente veio, não lê chats em segundo
  plano, e pode confundir linhas se o OCR errar caracteres.
- Só `tesseract-data-eng` e `tesseract-data-por` instalados — mensagens em
  chinês vão sair como lixo no OCR. Instalar `tesseract-data-chi-sim` se for
  preciso.
- Clique na conversa da sidebar só funciona se ela já estiver visível sem
  precisar rolar a lista.
- Sujeito a falso-negativo/positivo do OCR (nomes parecidos, texto cortado).
- Automação roda no **mesmo display X que o colaborador usa de verdade** —
  cliques/colagem podem competir com o uso real do mouse/teclado durante os
  testes (mitigado parcialmente refocando a janela antes de cada ação em
  `send_message`, mas não elimina 100% a corrida). Considerado mover pra um
  display X virtual (Xvfb) isolado — mecanicamente viável (ver histórico do
  plano da sessão), mas abandonado por ora porque exigiria encerrar a
  sessão do WeChat na tela real enquanto o bot rodar (mesma conta sendo
  usada como "mascote" por decisão temporária). Retomar essa opção quando
  houver conta separada pra automação.
- `python -u`/logging sem buffer é necessário pra ver o `print()` de
  mensagens em tempo real quando a saída não é um terminal interativo
  (ex.: `timeout ... | tee log.txt`) — sem isso, o stdout fica bufferizado
  e só aparece no fim do processo.

## Setup

```bash
cd "Bot WeCom"
sudo pacman -S --needed xdotool python-gobject xclip tesseract tesseract-data-eng tesseract-data-por
python3 -m venv --system-site-packages venv   # --system-site-packages é necessário: PyGObject (gi/Atspi) não é instalável via pip
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Passo 1 — diagnóstico (rodar antes de confiar na automação)

```bash
python explore_ui.py
```

Localiza a janela, tenta dumpar AT-SPI (`ui_dump/atspi_dump.txt`) e sempre
salva um screenshot (`ui_dump/screenshot.png`). Se o WeChat atualizar e a UI
mudar, é aqui que se começa a recalibrar.

## Passo 2 — rodar o loop

```bash
python main.py                             # só lê e imprime mensagens novas do chat aberto
python main.py --test-reply "teste"        # também envia essa mensagem pra TARGET_CHAT_NAME
```

Use `TARGET_CHAT_NAME=File Transfer` (padrão do `.env.example`) pra testar
envio sem mandar mensagem pra um contato real.
