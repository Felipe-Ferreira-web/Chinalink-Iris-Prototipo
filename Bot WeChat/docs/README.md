# Bot WeChat

> Automação de mensageria do WeChat via **UI Automation do Windows**,
> rodando num Windows Server (RDP). Sucessora de uma primeira tentativa em
> Linux (AT-SPI/OCR — abandonada, pasta `Bot WeCom` removida do repo; ver
> `git log --diff-filter=D --summary -- "Bot WeCom"` se precisar do
> histórico completo da investigação).
>
> A lib `wxauto4` (via fork `AngeCoo/wxauto-4.0`) foi **testada e
> abandonada duas vezes** — ver seção "Tentativas abandonadas: wxauto4"
> abaixo. Abordagem atual: automação própria com `pywinauto`, em cima da
> árvore de controles real do WeChat (inspecionada, não adivinhada).

## Objetivo

Mapear o máximo possível das funções básicas do WeChat (ler/enviar
mensagem, adicionar contato por telefone, e o que mais for surgindo) pra
automatizar o fluxo padrão de uso — por etapas, testando cada função
contra o WeChat real antes de seguir pra próxima. Nunca adivinhar
seletor: sempre a partir de dump real da UI (`ui_mapping/inspect_ui.py`).

## Por que Windows + UI Automation

- Não existe "WeCom Web" pra chat (`work.weixin.qq.com` é só Admin Console).
- Não existe cliente WeCom nativo pra Linux.
- **Windows UI Automation funciona de verdade** para o WeChat/WeCom —
  automação por elemento (nome/controle), não por coordenada de tela ou
  OCR. Por isso o bot roda num Windows Server (RDP), não em Linux.

## Tentativas abandonadas: `wxauto4`

### Primeira tentativa: usar a lib direto

Testamos `wxauto4` via fork [`AngeCoo/wxauto-4.0`](https://github.com/AngeCoo/wxauto-4.0)
(o pacote `wxauto4` do PyPI não tem wheel pra Python 3.13, e o repo do
autor original `cluic/wxauto4` foi esvaziado — issue da comunidade aponta
ameaça jurídica recebida, mesmo motivo de outro projeto similar
(`PyWxDump`) ter sumido). Resultado:

- `WeChat()`, `.nickname`, `.path`, `.dir` funcionavam (chamadas Win32
  triviais, só leem a janela).
- `GetSession()` sempre voltava vazio, e `ChatWith()`/busca de contato
  travava ou dava timeout num `ListControl` — em **duas versões
  diferentes do WeChat** (4.1.11.52 e a 4.0.5.26, a build especificamente
  recomendada pela comunidade pra essa lib), o que descartou versão do
  WeChat como causa.
- Rodando com terminal elevado (Administrator, igual ao WeChat), o erro
  mudou: travou num deadlock real dentro de `menu.select('粘贴')` —
  `LockManager.process_lock` (um `multiprocessing.Lock()`, não
  reentrante) sendo readquirido numa chamada aninhada, dentro do mesmo
  thread. Um bug de concorrência que só aparece rodando de verdade.
- **Causa raiz**: o histórico de commits do fork tem branches chamadas
  `codex/complete-unimplemented-features-from-documentation`,
  `codex/complete-unimplemented-features-in-chat-class` etc — sinal de
  que o código foi gerado por um agente de IA (Codex) "completando" a API
  a partir só do README, sem nunca ter rodado contra um WeChat de
  verdade. Isso explica os sintomas: o que é chamada Win32 rasa funciona,
  o que depende da árvore real de UI (nomes de classe, itens de menu,
  fluxo de busca) foi adivinhado e não bate com o app real. O outro fork
  encontrado (`moguangjian/wxauto-4.0`) é cópia idêntica do mesmo
  histórico — não é alternativa independente.

### Segunda tentativa: usar como referência/base, testando função por função

Ideia revisitada depois: em vez de mapear tudo na mão, usar o código do
fork como ponto de partida, testar e só fazer manual o que não
funcionasse. Antes de tentar, fomos direto na fonte real (não só o
README):

- Confirmado via `gh api repos/AngeCoo/wxauto-4.0/commits`: 16 dos 19
  commits vêm de branches `codex/...`, todos mergeados num intervalo de
  ~45 minutos em 2025-09-19 — a mesma causa raiz da primeira tentativa,
  agora com evidência direta de código-fonte, não só da memória do
  episódio anterior.
- A função que precisaríamos (add contact por telefone) **não é
  pública**: existe uma classe `SearchNewFriendWnd` em
  `wxauto4/ui/component.py`, mas nunca é chamada em lugar nenhum do
  repo — nunca foi ligada à classe `WeChat` pública. Usá-la exigiria
  importar um internal não exposto, e mesmo assim os textos são todos
  hardcoded em chinês (`Name="添加朋友"`, `"搜索"`, `"添加到通讯录"` —
  nosso WeChat roda em inglês) e ela reusa exatamente
  `Menu.select('粘贴')` — o mesmo caminho de código do deadlock acima.

Decisão (as duas vezes): não adotar `wxauto4` em nenhuma parte do fluxo.
`wechat/` já cobre mais do que o fork oferece pra essas funções, feito
a partir de dumps reais desta instalação (inglês), sem os riscos acima.

## Abordagem atual: automação própria com `pywinauto`

[`pywinauto`](https://github.com/pywinauto/pywinauto) é uma lib de UI
Automation madura, real e ativamente mantida — não um wrapper de
procedência duvidosa. Em vez de replicar a API inteira de um "wxauto"
(moments, grupos, arquivos, tudo), escrevemos só o que precisamos, função
por função.

**Primeiro passo pra cada função nova**: `ui_mapping/inspect_ui.py` dumpa a árvore
real de controles do WeChat já aberto, sem clicar em nada, pra descobrir
de verdade os nomes/classes dos elementos envolvidos — em vez de
adivinhar.

**Seletores confirmados** no dump real (interface em **inglês**, não
chinês — o cliente do servidor está assim, e é por isso que o fork
abandonado, com textos de menu em chinês tipo `'粘贴'`, nunca funcionava):

| Elemento | Seletor real |
|---|---|
| Item de conversa na sidebar | `auto_id='session_item_<Nome>'`, dentro da lista `auto_id='session_list'` — dá pra clicar direto, sem busca/colar/menu nenhum |
| Campo de digitar mensagem | `auto_id='chat_input_field'` (Edit) |
| Botão de enviar | `text='Send'` (classe `mmui::XOutlineButton`) |
| Lista de mensagens | `auto_id='chat_message_list'`; itens de texto são `class='mmui::ChatTextItemView'` (outros tipos, ex. `ChatItemView`, são só separador de horário) |

Implementado em `wechat/`: `find_wechat_window()`, `list_sessions()`,
`list_unread_sessions()`, `open_chat()`, `send_message()`, `read_messages()`,
`add_contact_by_phone()`, `find_or_start_chat()`, `start_group_chat()`,
`send_file()`, `download_last_document()`.
`explore.py` e `main.py` foram reescritos em cima disso (a versão antiga,
baseada no `wxauto4` abandonado, saiu — não tinha por que manter código
morto).

**Detalhe de implementação**: a versão instalada do `pywinauto` (0.6.9)
não aceita `auto_id=` como filtro direto em `.descendants()`/`.children()`
(só `class_name`/`title`/`control_type` chegam até a condição UIA) —
`wechat/` filtra por `auto_id` na mão em Python depois de buscar os
descendentes, em vez de passar isso como kwarg (que daria `TypeError`).

## Fluxo de adicionar contato novo (`add_contact_by_phone`)

Um número de telefone que ainda não é contato do WeChat precisa passar
pelo diálogo "Add Contacts": buscar o telefone e enviar pedido de
amizade. Confirmado nos dumps reais (`ui_mapping/inspect_ui.py --title "Add
Contact"` / `--title "Send Friend Request"`):

| Elemento | Seletor real |
|---|---|
| Diálogo "Add Contacts" | janela separada de verdade, `class='mmui::AddFriendWindow'` |
| Campo de busca | único `Edit` da janela |
| Botão de busca | `text='Search'` (diferente da busca da sidebar, que usa Enter — aqui tem botão de verdade) |
| Resultado "não encontrado" | `Text` contendo `"User not found"` |
| Resultado encontrado | botão `text='Add to Contacts'`; apelido (nickname) real fica num `Text` cujo `auto_id` termina em `display_name_text` |
| Diálogo "Send Friend Request" | janela separada, `class='mmui::VerifyFriendWindow'` |
| Mensagem de verificação | `Edit` pré-preenchido, editável (dá pra customizar) |
| Botão de confirmar | `text='OK'` (existe também `text='Cancel'` — sempre desambiguar pelo texto) |

**Detalhe importante**: o apelido do WeChat da pessoa (ex. "Summer")
quase nunca bate com o nome que você tinha associado ao número — é esse
apelido que fica na sidebar depois (`session_item_<apelido>`). Por isso
`add_contact_by_phone()` retorna o apelido (ou `None` se o telefone não
corresponder a ninguém), e é ele que deve ser usado depois em
`send_message()`/`open_chat()` — ver `main.py --test-add-contact`.

**Aviso — não é bug, é como o WeChat funciona**: depois do pedido de
amizade, a outra pessoa precisa **ACEITAR** antes de existir conversa pra
mandar mensagem. Testando logo em seguida com `send_message`, é esperado
falhar até lá (contato ainda não aparece na sidebar) — combine com quem
for aceitar antes de testar.

## Fluxo de iniciar conversa com contato existente (`find_or_start_chat`)

Um contato que já existe no WeChat mas ainda não tem sessão na sidebar
(ex.: pedido de amizade recém-aceito, ou qualquer contato antigo sem
histórico recente) não é achado por `open_chat` (que só procura
`session_item_<Nome>`). Confirmado no dump real da aba "Contacts":

| Elemento | Seletor real |
|---|---|
| Aba "Contacts" | `text='Contacts'` (classe `mmui::XTabBarItem`), na barra de navegação principal |
| Campo de busca de contatos | `Edit` classe `mmui::XValidatorTextEdit` (mesma classe usada no diálogo Add Contacts) — filtra a lista ao colar/digitar |
| Lista de contatos | `auto_id='primary_table_.contact_list'`, classe `mmui::StickyHeaderRecyclerListView` — é um Recycler, itens fora da tela podem não existir na árvore UIA sem filtrar antes |
| Item de contato | `ListItem` classe `mmui::ContactsCellItemView`, `text=<Nome>` (sem `auto_id` próprio, diferente da sidebar) |
| Botão "Messages" no perfil | `text='Messages'` — abre/troca pra conversa com esse contato |

`find_or_start_chat()` tenta a sidebar primeiro (`open_chat`, caminho
rápido pra quem já tem sessão) e só usa esse fluxo da aba Contacts como
fallback. Retorna o nome da conversa aberta, ou `None` se o nome não
corresponder a nenhum contato.

## Fluxo de criar grupo (`start_group_chat`)

Confirmado no dump real do diálogo "Start Group Chat" (aberto pelo mesmo
botão "Shortcuts" usado em "Add Contacts", item de menu "Start Group
Chat"):

| Elemento | Seletor real |
|---|---|
| Diálogo | janela separada, `class='mmui::SessionPickerWindow'`, título contendo `"Start Group Chat"` |
| Campo de busca de contatos | `Edit` classe `mmui::XValidatorTextEdit` (mesmo padrão de sempre) |
| Item de contato selecionável | `CheckBox` classe `mmui::SPSelectionContactRow`, `text=<Nome>` — clicar marca/desmarca |
| Contador de selecionados | `auto_id='sp_choice_contact_list'`, texto tipo `"N contact(s) selected"` |
| Botão de confirmar | `auto_id='confirm_btn'`, `text='Finish'` |
| Botão de cancelar | `auto_id='cancel_btn'`, `text='Cancel'` |

**Confirmado ao vivo, não é bug**: selecionar só 1 nome e confirmar não
cria grupo de verdade — o WeChat abre a conversa individual com essa
pessoa (grupo de verdade parece exigir 2+ nomes). `start_group_chat()`
não valida quantidade mínima — deixa o próprio WeChat decidir, e
`get_current_chat_name()` sempre reflete o que realmente abriu.

**Ainda não confirmado ao vivo**: se buscar/selecionar um segundo nome
reseta a busca mantendo a primeira seleção marcada, ou se precisa de
outro passo entre cada seleção — só testado com 1 nome até agora. Testar
com 2+ antes de confiar nisso pra grupos maiores.

## Fluxo de enviar documento (`send_file`)

O botão "Send File" (barra de ferramentas ao lado de `chat_input_field`,
junto com Sticker/Favorites/Screenshot/Voice) abre um diálogo **nativo
do Windows**, não uma janela do WeChat:

| Elemento | Seletor real |
|---|---|
| Botão "Send File" | `text='Send File'` (classe `mmui::XButton`), na toolbar `auto_id='tool_bar_accessible'` |
| Diálogo | `class='#32770'`, título `"Select File"` — diálogo padrão do Windows (Explorer embutido) |
| Campo de nome de arquivo | `Edit`, `title='File name:'` — aceita colar o caminho completo direto, sem precisar navegar visualmente |
| Botão de confirmar | `auto_id='1'`, `text='Open'` |
| Botão de cancelar | `auto_id='2'`, `text='Cancel'` |

`send_file()` cola o caminho completo (clipboard, mesmo padrão de
sempre) no campo de nome de arquivo e clica "Open" — não navega pela
árvore de pastas do diálogo. `auto_id='1'`/`title='File name:'` foram
escolhidos por serem estáveis entre esse diálogo e o de salvar (ver
seção seguinte) — o `auto_id` do campo de nome muda entre os dois
(`1148` no de abrir, `1001` no de salvar), mas o rótulo não. Depois de
"Open", o arquivo só fica anexado no compositor — `send_file()` ainda
clica no botão "Send" (mesmo da mensagem de texto) pra mandar de fato.

**Diálogo nativo é aninhado, não é janela de topo**: `Select File`
(e o `Save as…`/`Download to…` do download) aparecem só como
descendentes da janela principal na árvore UIA — `Desktop().windows()`
nunca os encontra. `_find_nested_window_by_title()` busca dentro da
janela principal em vez do desktop inteiro (diferente dos diálogos Qt
do próprio WeChat — Add Contacts, Start Group Chat — que são janelas de
topo de verdade).

## Fluxo de mensagem não lida em qualquer conversa (`list_unread_sessions`)

O WeChat embute a contagem de não lidas como uma **linha própria no
texto** do item da sidebar (`session_item_<Nome>`), logo após o nome —
não é um badge/elemento visual separado. Confirmado no dump real:

| Estado do item | `window_text()` |
|---|---|
| Sem pendência | `'Felipe\n\n\n'` |
| Com 1 mensagem não lida | `'Felipe\n[1]\nAoba\n13:48\n'` (linha 2 = `[N]`, linha 3 = preview, linha 4 = horário) |
| Mensagem tipo arquivo (preview) | `'Felipe\n[File] arquivo.txt\n15:56\n'` |

`list_unread_sessions()` casa a 2ª linha contra `UNREAD_MARKER_RE`
(`^\[(\d+)\]$`) — mesmo princípio já usado pro prefixo `[File]`, só que
aqui é um número entre colchetes. `tests/manual/watch_messages.py` usa
isso pra vigiar a sidebar inteira em loop (10s, a cada 5s — sem
persistir em arquivo, começa do zero a cada execução) e **só imprime**
o que chegou de novo (nome da conversa + texto) — não responde nada
sozinho, decisão consciente: sem uma IA de verdade decidindo o
conteúdo, auto-responder não faz sentido (ver `docs/STATUS.md`).

## Fluxo de achar documento recebido (`download_last_document`)

Abaixo do limite de "Auto download" do WeChat (Settings > My Account,
padrão 20 MB), o arquivo já baixa sozinho, sem clicar em nada — então
`download_last_document()` não clica em nada, só localiza o arquivo:

| Elemento | Seletor real |
|---|---|
| Bolha de mensagem tipo arquivo | `ListItem` classe `mmui::ChatBubbleItemView`, dentro de `chat_message_list` |
| Texto da bolha, arquivo **não baixado** (> 20MB) | `"File\n<nome>\n<tamanho>\nNot Downloaded\n微信电脑版"` |
| Texto da bolha, **já baixado** | `"File\n<nome>\n<tamanho>"` (sem a linha `Not Downloaded`) |
| Storage location (Settings > My Account) | raiz configurável (`WECHAT_STORAGE_ROOT` no `.env`) |
| Estrutura real em disco | `<storage_root>\wxid_<id>_<sufixo opaco>\msg\file\<AAAA-MM>\<nome>` |

`download_last_document(window, chat_name, storage_root)`: lê o nome do
arquivo na bolha (2ª linha) e, se não estiver "Not Downloaded", busca
recursivamente (`storage_root.rglob(f"{stem}*{suffix}")` — por padrão,
não nome exato) e devolve o mais recente por data de modificação.
Arquivo **acima de 20MB** ("Not Downloaded") ainda não é suportado —
levanta erro (nunca precisamos disso na prática até agora).

**Pegadinhas resolvidas**:
- O sufixo depois do `wxid` na pasta de storage é opaco/imprevisível —
  nunca montar esse caminho na mão, sempre `rglob` na raiz toda.
- O nome do arquivo em disco pode ter sufixo próprio do WeChat (ex.:
  bolha mostra "arquivo.txt", arquivo real é "arquivo(2).txt" se já
  existia um com esse nome) — por isso a busca é por padrão, não exata.
- Trocar o "Storage location" no WeChat não achata a estrutura — ela
  continua aninhada (`wxid.../msg/file/mês/`), só muda a raiz.

`WECHAT_STORAGE_ROOT` é **específico de máquina/conta** — reconfirmar
se migrar de servidor Windows, de conta WeChat, ou for pra produção.

## Histórico: integração com o server Django (Busca de Suppliers)

Chegamos a implementar uma integração completa com o server Django do
módulo "Busca de Suppliers" (`GET /api/suppliers/?status=contato_extraido`,
`PATCH` pra `contato_wechat_enviado`, via `server_client.py` +
`sync_suppliers.py`) — depois descontinuada: aquele módulo vai ser
movido pra outro repositório, e este bot passou a ser um projeto
independente, focado só em mapear as funções do WeChat em si. Os
arquivos de integração foram removidos; se precisar reconectar algo
parecido no futuro, o histórico do git tem a implementação completa de
referência (`git log --all --diff-filter=D -- "*/server_client.py"`).

## Setup (no Windows Server)

```powershell
cd "Bot WeChat"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Preencha `.env` com um `TARGET_CHAT_NAME` seguro para teste (ex.: `File
Transfer` / `文件传输助手` — conversa de notas pessoais do próprio WeChat,
não um contato real). Preencha também `WECHAT_STORAGE_ROOT` com o valor
de Settings > My Account > Storage location do WeChat — **específico de
máquina/conta**, reconfirmar se migrar de servidor ou de conta.

## Uso

Nome/caminho com espaço precisa de aspas (senão o Windows quebra em
argumentos separados) — nunca terminar um argumento quotado com `\`
antes da aspas de fechamento (`\"` vira aspas literal, não fecha a
string).

```powershell
python ui_mapping/inspect_ui.py                          # dump da janela principal em ui_mapping/dumps/ — sem clicar em nada
python ui_mapping/inspect_ui.py --title "Add Contact"     # dump de qualquer outra janela aberta (diálogos)
python explore.py                             # diagnóstico: lista sessões, lê histórico de TARGET_CHAT_NAME
python main.py                                  # só lê e imprime as mensagens de TARGET_CHAT_NAME

# Testes manuais (tests/manual/) — cada um chama uma função de wechat/ isolada
python tests/manual/send_test_message.py                    # manda TEST_MESSAGE (ou "texto") pra TARGET_CHAT_NAME
python tests/manual/echo_last.py                             # lê a última mensagem de TARGET_CHAT_NAME e reenvia ela mesma
python tests/manual/add_contact.py <telefone>                # testa add_contact_by_phone isolado, usa TEST_MESSAGE
python tests/manual/add_contact.py <telefone> "texto"        # idem, com mensagem específica
python tests/manual/start_chat.py <nome>                     # testa find_or_start_chat com um contato já existente
python tests/manual/start_group.py <nome1> <nome2> ...       # testa start_group_chat com 2+ contatos já existentes
python tests/manual/send_file.py <nome> <caminho>            # testa send_file com um arquivo local
python tests/manual/watch_messages.py                        # vigia todas as conversas, imprime mensagem nova
python tests/manual/download_last_file.py <nome>             # testa download_last_document
python tests/manual/set_remark.py <nome> <apelido>           # testa set_contact_remark
```

## Pendências

**Confirmadas funcionando ao vivo, com teste pytest** (ver
`docs/STATUS.md` pro histórico/detalhes de cada uma):
`add_contact_by_phone`, `find_or_start_chat`, `send_file`,
`set_contact_remark`, `download_last_document` (só arquivo ≤20MB).

**Ainda não confirmado ao vivo**:
- [ ] `tests/manual/watch_messages.py` (`list_unread_sessions`) — código
      pronto, nunca rodado contra o WeChat real ainda.
- [ ] `tests/manual/start_group.py` com **2+ nomes** (`start_group_chat`
      — só testado com 1 nome, que corretamente não formou grupo).
      Bloqueado: precisa de um segundo celular disponível pra testar.

Outros itens, sem prazo definido:
- [ ] Confirmar se a automação também cobre WeCom (cliente corporativo)
      ou só WeChat pessoal.
- [ ] Testar estabilidade do RDP durante uso prolongado (risco já
      identificado no relatório do módulo — causa ainda não confirmada:
      timeout de sessão ociosa, limite de sessões simultâneas, ou rede/VPN).
      Sessão desconectada (não deslogada) parece manter o processo rodando
      — vale confirmar se isso é suficiente antes de investir num driver
      de monitor virtual.
- [ ] Avaliar risco de detecção de login por região/IP (servidor fora da
      China) antes de qualquer teste com conta real de produção.
