# Bot WeCom Windows

> Segunda tentativa de automação de mensageria do WeChat/WeCom — via
> **UI Automation do Windows**, rodando num Windows Server (RDP). Pasta
> separada da antiga `Bot WeCom` (Linux, AT-SPI/OCR, descartada — ver
> `README.md` de lá para o histórico completo da investigação).
>
> A lib `wxauto4` (via fork `AngeCoo/wxauto-4.0`) foi **testada e
> abandonada** — ver seção "Tentativa abandonada" abaixo. Abordagem atual:
> automação própria com `pywinauto`, em cima da árvore de controles real
> do WeChat (inspecionada, não adivinhada).

## Por que uma pasta separada

A abordagem em `Bot WeCom` automatizava o **WeChat nativo para Linux** por
pixel (screenshot + OCR + `ydotool`), porque o binário não expõe árvore
AT-SPI nesta plataforma (testado exaustivamente, 3 configurações — ver
relatório do módulo). Essa investigação seguinte concluiu que:

- Não existe "WeCom Web" para chat (`work.weixin.qq.com` é só Admin Console).
- Não existe cliente WeCom nativo para Linux.
- **Windows UI Automation funciona de verdade** para o WeChat/WeCom via
  `wxauto`/`wxautox` — automação por elemento (nome/controle), não por
  coordenada de tela ou OCR.

Como o ambiente de execução (Windows Server) e o mecanismo de automação
(UI Automation do Windows, não AT-SPI/X11) são completamente diferentes,
faz mais sentido desenvolver isso numa pasta própria em vez de misturar
com o código Linux antigo.

## Tentativa abandonada: `wxauto4`

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

Decisão: abandonar qualquer wrapper "wxauto*" sem primeiro checar se o
histórico de commits é genuíno, e construir automação própria mínima em
cima da árvore de controles real (ver abaixo).

## Abordagem atual: automação própria com `pywinauto`

[`pywinauto`](https://github.com/pywinauto/pywinauto) é uma lib de UI
Automation madura, real e ativamente mantida — não um wrapper de
procedência duvidosa. Em vez de replicar a API inteira de um "wxauto"
(moments, grupos, arquivos, tudo), escrevemos só o que o Iris precisa:
enviar mensagem e ler mensagem nova.

**Primeiro passo — sem versão travada do WeChat** (essa trava era só do
fork abandonado): `inspect_ui.py` dumpa a árvore real de controles do
WeChat já aberto, sem clicar em nada, pra descobrir de verdade os
nomes/classes da caixa de busca, lista de conversas, campo de mensagem e
botão de enviar — em vez de adivinhar.

**Seletores confirmados** no dump real (interface em **inglês**, não
chinês — o cliente do servidor está assim, e é por isso que o fork
abandonado, com textos de menu em chinês tipo `'粘贴'`, nunca funcionava):

| Elemento | Seletor real |
|---|---|
| Item de conversa na sidebar | `auto_id='session_item_<Nome>'`, dentro da lista `auto_id='session_list'` — dá pra clicar direto, sem busca/colar/menu nenhum |
| Campo de digitar mensagem | `auto_id='chat_input_field'` (Edit) |
| Botão de enviar | `text='Send'` (classe `mmui::XOutlineButton`) |
| Lista de mensagens | `auto_id='chat_message_list'`; itens de texto são `class='mmui::ChatTextItemView'` (outros tipos, ex. `ChatItemView`, são só separador de horário) |

Implementado em `wechat.py`: `find_wechat_window()`, `list_sessions()`,
`open_chat()`, `send_message()`, `read_messages()`. `explore.py` e
`main.py` foram reescritos em cima disso (a versão antiga, baseada no
`wxauto4` abandonado, saiu — não tinha por que manter código morto).

**Detalhe de implementação**: a versão instalada do `pywinauto` (0.6.9)
não aceita `auto_id=` como filtro direto em `.descendants()`/`.children()`
(só `class_name`/`title`/`control_type` chegam até a condição UIA) —
`wechat.py` filtra por `auto_id` na mão em Python depois de buscar os
descendentes, em vez de passar isso como kwarg (que daria `TypeError`).

## Fluxo de adicionar contato novo (`add_contact_by_phone`)

Fornecedores extraídos do Alibaba (status `contato_extraido` no server)
**não são contatos do WeChat ainda** — só temos o telefone. Antes de
mandar mensagem é preciso abrir o diálogo "Add Contacts", buscar o
telefone e enviar pedido de amizade. Confirmado nos dumps reais
(`inspect_ui.py --title "Add Contact"` / `--title "Send Friend Request"`):

| Elemento | Seletor real |
|---|---|
| Diálogo "Add Contacts" | janela separada de verdade, `class='mmui::AddFriendWindow'` |
| Campo de busca | único `Edit` da janela |
| Botão de busca | `text='Search'` (diferente da busca da sidebar, que usa Enter — aqui tem botão de verdade) |
| Resultado "não encontrado" | `Text` contendo `"User not found"` |
| Resultado encontrado | botão `text='Add to Contacts'`; apelido (nickname) real fica num `Text` cujo `auto_id` termina em `display_name_text` |
| Diálogo "Send Friend Request" | janela separada, `class='mmui::VerifyFriendWindow'` |
| Mensagem de verificação | `Edit` pré-preenchido, editável (dá pra customizar, diferente do que a versão Linux antiga assumia) |
| Botão de confirmar | `text='OK'` (existe também `text='Cancel'` — sempre desambiguar pelo texto) |

**Detalhe importante**: o apelido do WeChat da pessoa (ex. "Summer")
quase nunca bate com o nome do fornecedor no Django nem com o telefone
buscado — é esse apelido que fica na sidebar depois
(`session_item_<apelido>`). Por isso `add_contact_by_phone()` retorna o
apelido (ou `None` se o telefone não corresponder a ninguém), e é ele —
não o nome do fornecedor — que devem ser usados depois em
`send_message()`/`open_chat()`. Ver `sync_suppliers.py::_contatar`.

**Aviso — não é bug, é como o WeChat funciona**: depois do pedido de
amizade, a outra pessoa precisa **ACEITAR** antes de existir conversa pra
mandar mensagem. Um fornecedor recém-adicionado pode falhar em
`send_message` por um tempo (contato ainda não aparece na sidebar) — o
loop trata isso como "tenta de novo no próximo tick", não marca
`contato_wechat_enviado` até a mensagem sair de verdade.

## Integração com o server Django (Busca de Suppliers)

Confirmado direto no código do server
(`server/sourcing/{models,views,serializers}.py`, projeto irmão
`Busca de Suppliers/`):

- `Supplier.Status`: `novo` → `contato_extraido` → `contato_wechat_enviado`
  → `aprovado`/`reprovado`.
- `GET /api/suppliers/?status=contato_extraido` — lista quem ainda precisa
  de contato (serializer expõe `contact_phone`/`contact_website`).
- `PATCH /api/suppliers/{id}/` com `{"status": "contato_wechat_enviado"}`
  — marca como contatado, pra não repetir.
- **Sem autenticação** (`AllowAny` em todos os ViewSets) — não precisa de
  token/login no client.
- Nesta etapa, server Django e este bot rodam **na mesma máquina**
  (Windows Server) — `SOURCING_SERVER_URL=http://localhost:8000`, sem
  CORS/rede entre servidores pra ajustar.

`server_client.py` (porta quase direta do `Bot WeCom/server_client.py`
antigo, Linux) implementa `buscar_suppliers_aguardando_contato()` e
`marcar_contato_wechat_enviado()`. `sync_suppliers.py` fecha o loop:
acha a janela do WeChat **uma vez só** (fora do loop — é o passo mais
lento confirmado ao vivo, chegou a levar 1 minuto), depois por fornecedor
tenta `add_contact_by_phone` → `send_message` → PATCH, com try/except
por fornecedor (um falhar não derruba o loop).

**Execução**: por ora é um script Python normal, rodado manualmente e
deixado aberto (mesmo padrão de "rodar o server") — não uma Tarefa
Agendada/serviço ainda. Um Windows Service de verdade roda na Session 0 e
**não consegue** interagir com a UI, então não é opção pra automação de
tela; se precisar rodar sem terminal aberto na tela, a alternativa é
desconectar (não fazer logoff) a sessão RDP — o processo continua rodando
no servidor.

## Setup (no Windows Server)

```powershell
cd "Bot WeCom Windows"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Preencha `.env` com um `TARGET_CHAT_NAME` seguro para teste (ex.: `File
Transfer` / `文件传输助手` — conversa de notas pessoais do próprio WeChat,
não um contato real).

## Uso

```powershell
python inspect_ui.py                     # dump da janela principal em ui_dump.txt — sem clicar em nada
python inspect_ui.py --title "Add Contact"    # dump de qualquer outra janela aberta (diálogos)
python explore.py                        # diagnóstico: lista sessões, lê histórico de TARGET_CHAT_NAME
python main.py                           # só lê e imprime as mensagens de TARGET_CHAT_NAME
python main.py --test-reply              # além de ler, manda TEST_MESSAGE pra TARGET_CHAT_NAME antes
python main.py --echo-last               # lê a última mensagem de TARGET_CHAT_NAME e reenvia ela mesma
python sync_suppliers.py --test-phone    # testa add_contact_by_phone isolado, contra TEST_PHONE, sem server
python sync_suppliers.py --once          # 1 passada real (server + WeChat) e sai — bom pro demo, sem loop
python sync_suppliers.py                 # loop real: consulta o server, adiciona contato, manda mensagem, marca enviado
```

## Pendências desta etapa

- [ ] Testar `sync_suppliers.py --test-phone` ponta a ponta contra o
      WeChat real (`add_contact_by_phone` ainda não foi exercitado de
      verdade, só os seletores foram confirmados via dump).
- [ ] Testar o loop completo (`sync_suppliers.py`) com um `Supplier` real
      no Django com `status=contato_extraido`.
- [ ] Combinar antes do demo: o `TEST_PHONE`/primeiro fornecedor testado
      precisa ser um número que alguém vá **aceitar** o pedido de amizade
      rápido (colega avisado, ou segundo dispositivo próprio).
- [ ] Implementar leitura de mensagem **nova** em tempo real (hoje
      `read_messages` lê tudo que já está na tela; falta decidir entre
      polling comparando com o que já foi visto, ou investigar se dá pra
      usar `UIA_StructureChangedEventId`/`AutomationEventHandler` do
      pywinauto pra reagir a mensagem nova sem polling).
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
