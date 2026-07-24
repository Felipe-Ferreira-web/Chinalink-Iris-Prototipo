# Status — Bot WeChat (atualizado 2026-07-23)

Registro do que foi feito, decidido e descoberto, pra continuar depois
sem perder contexto. Não substitui o `README.md` (seletores/fluxos
confirmados) — aqui é o resumo de sessão: o que mudou, o que falta, e
por quê.

## Resumo rápido (leia isto primeiro)

**Confirmado funcionando ao vivo, com pytest**: `add_contact_by_phone`,
`find_or_start_chat`, `send_message`/`read_messages`/`open_chat`/
`list_sessions`, `send_file`, `set_contact_remark`,
`download_last_document` (só arquivo ≤20MB — ver tabela abaixo),
`list_unread_sessions`/`watch_messages.py` (redesign completo, ver seção
própria abaixo).

**Próximo passo concreto**: `start_group.py` com 2+ nomes — falta um
segundo celular disponível pra testar (único item bloqueado, não é bug).

**Antes de mexer em `download_last_document`/`send_file`**: leia
"Redesign concluído" e "Bug corrigido: diálogo nativo não encontrado"
mais abaixo — tem 2 pegadinhas de UIA (diálogo nativo aninhado vs. menu
de contexto que é janela de topo) fáceis de reverter por engano.

## Contexto de ambiente (sempre válido)

O WeChat só existe no servidor Windows (RDP) — este ambiente de trabalho
(Linux) nunca executa nada contra o WeChat real. Ciclo sempre: escrevo
código → você testa no servidor e cola o resultado/dump aqui → ajusto →
você testa de novo.

## Fluxo de trabalho atual (novo, 2026-07-20)

Testar cada função 1 por 1 no servidor; quando confirmar que está
funcionando, escrevo um teste pytest de caracterização (pywinauto
mockado, não fala com o WeChat de verdade — só trava o comportamento
atual como referência pra não quebrar sem perceber depois). Framework:
pytest (`requirements.txt`).

## Estrutura de pastas (reorganizada hoje)

```
docs/            README.md, STATUS.md
tests/pytests/   conftest.py (stub de libs Windows-only), test_*.py
tests/manual/    rotinas standalone de teste ao vivo (add_contact.py etc.)
ui_mapping/      inspect_ui.py, dumps/*.txt
```

`pytest.ini` fica na raiz de propósito (pytest não acha config dentro de
subpasta quando rodado da raiz). Rodar tudo: `pytest` (da raiz, venv
ativo). `ui_mapping/inspect_ui.py` sempre grava em `ui_mapping/dumps/`,
não importa de onde for chamado.

## Funções testadas ao vivo e status atual

| Função | Status |
|---|---|
| `add_contact_by_phone` | **Confirmado funcionando ao vivo.** Bug corrigido: campo de busca do diálogo "Add Contacts" não aceitava paste via Ctrl+V/clipboard — trocado pra digitar o telefone direto via keystrokes. Teste pytest: `tests/pytests/test_add_contact_by_phone.py` (3 casos, passando). |
| `find_or_start_chat` | Testado ao vivo: **funcionou na 2ª tentativa, falhou na 1ª** (achava que tinha travado no botão "Messages"). Teste pytest escrito: `tests/pytests/test_find_or_start_chat.py` (3 casos, passando) — mas caracteriza o código ATUAL, que ainda tem o bug de tab abaixo. |
| `send_message`/`read_messages`/`open_chat`/`list_sessions` | Confirmadas funcionando ao vivo em sessão anterior. Sem teste pytest ainda. |
| `start_group_chat` | Implementada, testada só com 1 nome (WeChat abre conversa individual, não forma grupo — esperado). **Não testada com 2+ nomes** — bug de parâmetro com espaço em investigação (ver abaixo). |
| `send_file` | **Confirmado funcionando ao vivo (2026-07-21)**, depois de 2 fixes: diálogo nativo aninhado + clique em Send faltando (ver abaixo). Teste pytest: `tests/pytests/test_send_file.py`. |
| `list_unread_sessions` / `watch_messages.py` | **Confirmado funcionando ao vivo (2026-07-23)**, depois do redesign completo (ver seção própria abaixo). Só detecta e imprime (não responde mais). Teste pytest: `tests/pytests/test_watch_messages.py` (5 casos, passando). |
| `download_last_document` | **Confirmado funcionando ao vivo (2026-07-22)**, com a abordagem nova (ver seção própria abaixo) — sem clique, busca recursiva na pasta de storage. Teste pytest: `tests/pytests/test_download_last_document.py` (3 casos). |
| `set_contact_remark` | **Confirmado funcionando ao vivo (2026-07-21)** — Enter realmente confirma a edição do remark. Teste pytest: `tests/pytests/test_set_contact_remark.py` (2 casos, passando). |

## Bug corrigido: assumir a aba ativa

**Diagnóstico do usuário** (explica a flakiness do `find_or_start_chat`):
funções que dependem da aba "Weixin" (lista de conversas, `session_item_*`)
ou da aba "Contacts" não garantem que essa aba está ativa antes de agir —
só assumem. Se uma chamada anterior deixou o WeChat em outra aba, a
árvore UIA esperada nem existe ainda, e a função falha silenciosamente
ou trava esperando um elemento que nunca aparece. Mesmo padrão de
[[feedback-ui-automation-check-state-before-acting]], em nível de aba.
Detalhes salvos na memória: `feedback_wechat_ensure_tab_before_acting`.

**Fix implementado**: novo helper `_switch_to_tab(main_window, tab_text)`
que clica explicitamente na aba antes de agir. Aplicado em `list_sessions`,
`list_unread_sessions` e `open_chat` (aba "Weixin" — cobre por chamada
`send_message`, `read_messages`, `send_file`, `download_last_document`,
e o caminho rápido do `find_or_start_chat`). `find_or_start_chat`
(fallback pra Contacts) refatorado pra usar o mesmo helper. **Re-testado
ao vivo, confirmado funcionando.**

## Identificação única de contato: WeChat ID + Remark

Discussão: nickname não é único (WeChat não garante isso), então dá pra
ter colisão entre dois contatos com o mesmo nome exibido — problema real
conforme a base de contatos crescer. Investigado via dump real do card
de perfil (aba Contacts):

- **WeChat ID** (ex.: `wxid_b9zdqyk5a0dv22`): único e imutável, exposto
  no perfil como campo `ProfileTextView` (path estável, mesmo pra
  qualquer contato). Bom pra guardar/comparar, mas a sidebar continua
  indexada por nome (`session_item_<Nome>`) — não resolve colisão de
  clique sozinho.
- **Remark** (apelido privado, só o dono da conta vê): quando setado,
  passa a ser exibido em TODA a UI no lugar do nickname (sidebar,
  Contacts, chat) — usuário confirmou ao vivo que funciona como alias
  de verdade, buscável pelos dois (nome original E remark). **Essa é a
  solução real pro problema de nome duplicado**: definir um remark
  único no contato resolve a colisão na raiz.

**Implementado**: `set_contact_remark(main_window, contact_name, remark)`
— acha o contato na aba Contacts, clica no botão do remark (vira campo
editável, confirmado ao vivo), cola o novo valor, confirma com Enter.
**Confirmado ao vivo (2026-07-21)**: Enter realmente salva o remark.
Teste pytest: `tests/pytests/test_set_contact_remark.py`.

**Descoberta confirmada por dump real (2026-07-21)**: depois que um
contato tem alias, a sidebar passa a indexar por ele — dump mostrou
`auto_id='session_item_Bobão'` (o alias), não mais o nome original.
O nome original ainda funciona como termo de busca (localiza o contato),
mas deixa de ser a chave exibida/gravada. **Regra de uso daqui pra
frente**: qualquer chamada que referencie um contato já aliasado
(`open_chat`, `send_message`, `find_or_start_chat`, comparações com
`list_sessions`) precisa usar o **alias**, não o nome original — não é
bug do `wechat.py` (as funções só usam a string recebida), é disciplina
de chamada. Nome original só serve pra achar o contato a primeira vez /
setar o alias.

## Refactor: rotinas de teste manual viraram scripts standalone

`main.py` não tem mais flags — ficou só o comportamento padrão (achar
janela + ler/imprimir mensagens de `TARGET_CHAT_NAME`), reservado pro
que rodar de verdade em produção mais pra frente. Cada teste manual
(antes um `--test-*` do `main.py`) agora é um script standalone em
`tests/manual/`, rodado direto (`python tests/manual/add_contact.py
<telefone>`, etc.): `add_contact.py`, `start_chat.py`, `start_group.py`,
`send_file.py`, `download_last_file.py`, `set_remark.py`,
`watch_messages.py`, `read_messages.py`, `echo_last.py`,
`send_test_message.py`.

Cada script só faz parsing de args + chama `wechat/` direto (nenhuma
lógica própria, sem camada de indireção tipo `run()`) — `wechat/`
continua sendo a única fonte de lógica de verdade; os scripts manuais
só existem pra facilitar chamar uma função individual pra teste, sem
precisar de REPL. `_tests_setup.py` (mesma pasta) centraliza o setup
repetido (achar janela, config, log, fix de `sys.path` pra achar
`wechat/`/`config.py` dois níveis acima). Nomes sem prefixo `test_`
de propósito, pra não colidir com a descoberta automática do pytest
(que roda os testes de verdade em `tests/pytests/`).

## Refactor: wechat.py virou pacote wechat/

`wechat.py` (~600 linhas, tudo junto) virou a pasta `wechat/`:
`wechat/wechat.py` (todas as funções, sem mudança de lógica) e
`wechat/setup_wechat.py` (só as constantes/seletores, com descrição
curta ao lado de cada uma quando não óbvia pelo nome). **Sem
`__init__.py`** (pacote namespace implícito, decisão explícita do
usuário — evita a camada extra de reexport) — todo arquivo que usa
o módulo faz `from wechat import wechat` (não `import wechat` puro,
que só pegaria o pacote vazio) e chama `wechat.X(...)` normalmente
depois disso. Decisão consciente: **não** foi pra um arquivo por
função — as funções se chamam entre si o tempo todo e compartilham
os mesmos helpers, então isso só criaria risco de import circular
sem ganho real, num código ainda pequeno (~20 funções).

Pegadinha resolvida: os testes pytest faziam `patch("wechat.X")` —
como as funções agora são definidas em `wechat.wechat`, não em
`wechat/__init__.py`, o patch precisa mirar `wechat.wechat.X` (onde o
nome é resolvido em tempo de chamada), senão o mock não afeta nada de
verdade. Os dois arquivos de teste foram corrigidos, 6 continuam
passando.

## Solicitação de amizade recebida: aceite automático, sem tela

Testado ao vivo (2026-07-21): contato removido do Iris de propósito,
depois pedido de amizade mandado de outro celular pro Iris. **Nenhuma
ação manual no lado do Iris** — a sessão já apareceu direto na sidebar
(`session_item_Felipe`, `[1]` não lida, mensagem de saudação padrão),
sem nenhuma tela de "Accept"/"Decline" pra automatizar. Conclusão: essa
conta tem a confirmação de amizade desativada (config de privacidade do
WeChat) — quem manda pedido já vira sessão ativa direto.

**Implicação**: não precisa de função nova pra "aceitar solicitação" —
o loop que já existe (`list_unread_sessions`/`watch_messages.py`) já
cobre esse caso, contato novo chega como qualquer sessão não lida. **Risco
conhecido, não resolvido**: se o nome exibido do novo contato colidir
com o de um contato já existente (mesmo problema de
[[identificação única de contato]] de sempre), não tem telefone
disponível pra usar de remark (diferente do fluxo `add_contact_by_phone`,
que já sai com o telefone em mãos) — precisaria do WeChat ID via aba
Contacts como identificador de fallback. Não resolver agora, só
registrado.

**Confirmado o espelho** (dump `ui_dump_request_accepted.txt`, mesmo
dia): quando é o Iris que manda o pedido (via `add_contact_by_phone`) e
a outra pessoa aceita, aparece exatamente igual — sessão nova com `[1]`
e mensagem de sistema genérica ("Aceitei sua solicitação de amizade.
Vamos conversar!"). Mesma conclusão: nenhuma detecção especial
necessária, o loop de não lidas já cobre os dois sentidos. **Aberto,
não resolvido**: essa frase é mensagem de sistema, não sabemos ainda se
`read_messages`/`MESSAGE_TEXT_CLASS` captura ela como mensagem normal
(faltaria dump do `chat_message_list` dessa conversa) — hoje isso só
apareceria logado por `watch_messages.py` (que não responde mais nada
sozinho, ver seção abaixo), não é mais um risco de ação indevida.

## Bug corrigido: diálogo nativo não encontrado (send_file / download_last_document)

**Sintoma** (`send_file.py` ao vivo, 2026-07-21): diálogo "Select File"
abria e respondia normal a clique manual, mas o script nunca avançava —
`find_window_by_title` estourava os 15s e lançava `RuntimeError`
("Nenhuma janela... encontrada"), sem travar de fato (só parecia, pelo
tempo de espera).

**Causa confirmada por dump real**: `find_window_by_title` só enumera
`Desktop(backend="uia").windows()` (janelas de nível superior). Os
dumps `ui_dump_select_file.txt` e `ui_dump_save.txt` mostram que os
diálogos nativos do Windows (`#32770`, "Select File" e "Save as…")
aparecem só como **descendentes da janela principal** na árvore UIA,
não como janela irmã dela no desktop — `Desktop().windows()` nunca os
enxerga. Diferente dos diálogos Qt próprios do WeChat (Add Contacts,
Send Friend Request, Start Group Chat), que são janelas de topo de
verdade e continuam achados normalmente por `find_window_by_title`.

**Fix**: novo helper `_find_nested_window_by_title(parent_window,
title_needles)` — busca em `parent_window.descendants(control_type=
"Window")` em vez do desktop inteiro. Usado em `send_file` e
`download_last_document` no lugar de `find_window_by_title` pros
diálogos nativos "Select File"/"Save as…"/"Download to…".

**`send_file`: re-testado ao vivo, confirmado funcionando** — faltava
também um clique em "Send" depois de anexar (o WeChat só anexa, não
manda sozinho). Teste pytest: `tests/pytests/test_send_file.py`.

**`_click_menu_item_by_prefix` (menu de contexto, botão direito na
bolha do arquivo): continua usando `Desktop().windows()`, não o helper
aninhado** — dump real (`ui_dump_download.txt`, clique manual)
confirmou que esse menu (`mmui::XMenu`) É janela de nível superior de
verdade (ao contrário dos diálogos "Select File"/"Save as…", que são
aninhados). Cheguei a "corrigir" isso pra busca aninhada por engano
(mesmo padrão dos diálogos) e tive que reverter — o menu de contexto
é o caso oposto.

## Histórico: abordagem antiga de diálogo nativo (abandonada)

As duas seções abaixo (coordenada de clique + sobrescrita) descrevem a
abordagem por diálogo nativo "Save as…", **substituída** pela busca
recursiva (ver "Redesign" mais abaixo). Código removido do `wechat.py`.
Fica só de referência, útil se algum dia precisar suportar o caso de
arquivo >20MB ("Not Downloaded").

## Bug corrigido: coordenada de clique no balão de arquivo (download_last_document)

**Sintoma**: `bubble.right_click_input()` não abria menu nenhum —
WeChat vinha pro primeiro plano (foco ok), mas nada mais acontecia,
mesmo com o texto "Save as…" existindo de verdade no menu (confirmado
clicando manualmente).

**Causa confirmada por screenshot do usuário**: o retângulo da bolha
reportado pelo UIA é a **linha inteira** da mensagem (976px de largura,
quase o painel de chat todo) — bem mais largo que o balão visível de
verdade, que fica alinhado à esquerda (~277px). O clique automático
mirava o CENTRO desse retângulo largo, caindo em espaço vazio à
direita do balão — não em cima de nada.

**Fix**: `bubble.right_click_input(coords=(180, 40))` — mira um ponto
fixo dentro da área visível de verdade (perto do texto do nome do
arquivo), em vez do centro do retângulo. **Confirmado ao vivo,
funcionando** — o menu abre certo agora.

## Bug corrigido: sobrescrita silenciosa no download

Depois do fix de coordenada, o "Save as…" passou a funcionar, mas
salvar num arquivo já existente disparava o diálogo nativo "Confirm
Save As" (Yes/No) sem tratamento. Decisão do usuário: nunca sobrescrever
— gerar nome com sufixo tipo Windows (`arquivo (2).txt`) em vez de
perguntar/sobrescrever. Implementado: `_unique_save_path(save_dir,
filename)` — checa `Path.exists()` e incrementa sufixo `(2)`, `(3)`...
até achar um nome livre, ANTES de abrir o diálogo (nunca aciona a
confirmação de sobrescrita). Não testado ao vivo ainda (achado antes do
redesign abaixo).

## Redesign concluído: download_last_document via storage + busca recursiva

**Descoberta ao vivo (2026-07-21)**, via dump do menu de Settings
(`ui_dump_settings.txt`): o WeChat tem duas configs relevantes —
"Storage location" (raiz onde tudo é salvo, com botão "Change") e
"Auto download file less than" (20 MB, com toggle) — arquivos abaixo
desse tamanho baixam sozinhos, sem clique nenhum.

Usuário trocou a "Storage location" pra uma pasta fixa própria, mas a
estrutura interna do WeChat continua aninhada e "codificada" mesmo
assim — não vira uma pasta plana. Estrutura real confirmada:
`<pasta_raiz>\wxid_<id>_<sufixo opaco>\msg\file\<AAAA-MM>\<nome_arquivo>`
(ex.: `wxid_zfvkkeyczfw222_2bc1\msg\file\2026-07\`). O sufixo depois do
wxid não é previsível (não é só o wxid da conta) — **não vale tentar
montar esse caminho na mão**.

Usuário também descobriu um item de menu **"Download"** (diferente do
"Download to…" que já tínhamos) que resolve o download sozinho, sem
abrir diálogo nativo nenhum — clica e pronto, arquivo cai na estrutura
acima automaticamente.

**Plano** (ainda não implementado): trocar toda a automação de diálogo
nativo por: clique direito na bolha (já corrigido, `coords=(180,40)`) →
clicar no item de menu "Download" → localizar o arquivo com busca
recursiva (`Path(storage_root).rglob(filename)`, pegar o mais recente
por mtime) dentro da pasta de storage fixa, em vez de tentar prever o
caminho exato. Isso substitui TODA a lógica de `_find_nested_window_by_title`
+ `_unique_save_path` + diálogo "Save as…"/"Download to…" pra esse fluxo
(fica mais simples e robusto).

**Implementado e confirmado ao vivo (2026-07-22)**: `download_last_document(window,
chat_name, storage_root)` — só levanta erro se "Not Downloaded" (>20MB,
caso não suportado ainda); senão busca `storage_root.rglob(f"{stem}*{suffix}")`
(padrão, não nome exato) e devolve o mais recente por mtime. Não usa
mais diálogo nativo, `_click_menu_item_by_prefix` nem "Download"/"Download
to…" — todo esse código foi removido (morto). `_unique_save_path` também
removido (só fazia sentido pro fluxo de diálogo antigo).

**Pegadinha resolvida**: o nome do arquivo em disco pode ter sufixo
próprio do WeChat (ex.: bolha mostra "arquivo.txt", mas o arquivo real
é "arquivo(2).txt" se já existia outro com esse nome) — por isso a
busca é por padrão (`stem*sufixo`), não por nome exato.

**Config nova**: `WECHAT_STORAGE_ROOT` em `.env`/`config.py` — raiz de
storage do WeChat (Settings > Storage location). **Específico de
máquina/conta — precisa reconfirmar se migrar de servidor Windows, de
conta WeChat, ou for pra produção.** Não vale a pena mudar esse valor
no WeChat (testado): a estrutura aninhada (`wxid_..._sufixo/msg/file/
<ano-mês>/`) persiste não importa a raiz, só muda onde ela fica.

Teste pytest: `tests/pytests/test_download_last_document.py` (3 casos,
usa `tmp_path` real do pytest pra simular arquivos em disco — não
mocka `Path`, só as chamadas pywinauto).

## Redesign: watch_reply.py virou watch_messages.py (não responde mais)

**Motivo** (usuário, 2026-07-22): responder automaticamente com um
texto fixo pra qualquer mensagem nova não faz sentido sem entender o
conteúdo — isso só vai fazer sentido quando existir uma IA real
decidindo a resposta. Até lá, o script só serve pra confirmar que a
detecção de mensagem nova funciona.

**Mudança inicial**: renomeado `watch_reply.py` → `watch_messages.py`,
removido `wechat.send_message` e o argumento `texto`. Só imprime (via
log, que já tem horário): número sequencial da notificação, nome da
conversa e o texto da mensagem nova.

**Primeiro teste ao vivo (2026-07-22), 2 bugs achados e corrigidos**:
contagem errada na 1ª vez que uma conversa aparecia como não lida
(tratava todo o histórico como novo) e falta de timeout (rodava pra
sempre, só saía com Ctrl+C). Fixes de então: `seen_counts` como base na
1ª visão, `WATCH_DURATION_SECONDS = 10`.

## Redesign completo (2026-07-23): `[N]` da sidebar + fim de `seen_counts`

**Motivo** (usuário, ao usar o script pela 1ª vez após os fixes de
2026-07-22): o script continuava com comportamento estranho — mesmo
depois de ler as notificações pendentes, ficava rodando até o timeout
em vez de encerrar. Diagnosticado: `read_messages()` já chama
`open_chat()` internamente, então cada conversa não-lida já abria de
verdade — só que o loop continuava reabrindo/fechando abas até o
timeout global, mesmo sem nada novo pra processar.

**Discussão sobre concorrência** (usuário levantou 2 problemas reais):
1. Nova notificação pode chegar enquanto processamos a lista atual.
2. A mesma conversa pode receber mensagem nova entre montar a lista e
   efetivamente ler ela (lista "congelada" fica desatualizada).

**Decisão de design**: nunca guardar a lista de pendentes de uma vez —
reconsultar `list_unread_sessions()` a cada passo do loop, pegar só a
1ª pendente, processar (abre+lê, que já É a leitura real no momento em
que acontece), e voltar a consultar do zero. Cobre os dois problemas
sem precisar de lock nem timestamp.

**Risco de starvation identificado pelo usuário**: sem limite, uma
conversa muito ativa (ou várias) poderia monopolizar o loop pra sempre,
atrasando o resto do sistema. Fix: dois limites independentes, sai ao
bater qualquer um dos dois — `WATCH_DURATION_SECONDS` (tempo) e
`MAX_MESSAGES_PER_RUN = 10` (teto de mensagens por execução). O que
sobrar fica pendente pra próxima chamada do script (`[N]` da sidebar
não é resetado por quem não abriu a conversa).

**Melhoria adicional** (ideia do usuário): em vez de `seen_counts`
(dict em memória, contagem da última vez que o script viu aquela
conversa) pra decidir quantas mensagens são novas, usar diretamente o
`[N]` que já aparece na sidebar (`UNREAD_MARKER_RE`) — é o próprio
WeChat dizendo quantas são não lidas, não depende de estado local
sobrevivendo entre execuções. `list_unread_sessions` mudou de
`list[str]` pra `list[tuple[str, int]]` (nome, contagem não lida);
`watch_messages.py` usa `messages[-unread_count:]` em vez de comparar
com uma contagem anterior guardada em memória. Único chamador afetado
era o próprio `watch_messages.py` (confirmado por busca no repo).

**Encerramento imediato ao esvaziar** (ajuste fino depois do 1º teste
ao vivo bem-sucedido, 2026-07-23): o log mostrou 6s de atraso entre a
última notificação e o "Encerrando" — o loop, ao achar a lista vazia,
ainda dormia `WATCH_POLL_INTERVAL_SECONDS` antes de reavaliar o
timeout. Fix: `break` imediato quando `list_unread_sessions()` volta
vazia, em vez de dormir e continuar. Timeout/teto de mensagens
continuam como rede de segurança se as notificações não pararem de
chegar. `WATCH_POLL_INTERVAL_SECONDS` removido (ficou sem uso).

**Confirmado ao vivo (2026-07-23)**, 2 notificações simultâneas (Felipe
e Victor Silva), lidas e logadas corretamente, script encerrando sem
atraso perceptível depois da última. Teste pytest de caracterização:
`tests/pytests/test_watch_messages.py` (5 casos — lista vazia encerra
sem sleep, usa `[N]` em vez de histórico completo, múltiplas pendentes
processadas em ordem, teto de mensagens corta com pendente sobrando,
timeout corta com pendente sobrando). Precisou inserir `tests/manual/`
no `sys.path` dentro do próprio arquivo de teste (nenhum outro script
de `tests/manual/` tinha teste até agora, sem precedente no
`conftest.py` pra isso) — se mais scripts manuais ganharem teste,
considerar centralizar esse path-hack no `conftest.py`.

## Próximos passos concretos (ordem sugerida pra retomar)

1. `start_group.py` com 2+ nomes — bloqueado por enquanto, falta um
   segundo celular pra testar.
2. Bug de espaço em nome/caminho passado por linha de comando: **não é
   bug de código, é uso do cmd do Windows** — `\"` no fim de um argumento
   entre aspas vira aspas literal dentro do valor, não fecha a string.
   Nunca terminar um argumento quotado com `\` antes da aspas de
   fechamento (afetou `send_file.py`/`download_last_file.py` várias
   vezes na sessão de 2026-07-21).
3. Itens sem prazo definido (ver `docs/README.md` > "Pendências"):
   confirmar cobertura WeCom vs. WeChat pessoal, testar estabilidade do
   RDP em uso prolongado, avaliar risco de detecção de login por
   região/IP antes de qualquer teste com conta real de produção.

## Performance — não urgente, olhar no futuro

`find_window_by_title`/`_click_by_text`/`_click_menu_item_by_prefix`
chamam `Desktop(backend="uia").windows()`, que enumera TODAS as janelas
de nível superior abertas no desktop (não só o WeChat) — 2 chamadas UIA
por janela só pra filtrar. No servidor real, com várias janelas abertas
(RDP), isso pode ficar caro. Não mexer sem medir antes quanto tempo
cada chamada realmente leva nesse servidor — sem esse dado, ajustar
`FIND_TIMEOUT_SECONDS`/`FIND_POLL_INTERVAL_SECONDS` é chute.

## Onde mais olhar

- `docs/README.md` — tabelas de seletores confirmados.
- Memória entre sessões (Claude Code): `feedback_wechat_ensure_tab_before_acting`,
  `feedback_pywinauto_focus_before_click`, `feedback_docstrings_comments_max_10_words`,
  `feedback_push_back_when_unclear`, `project_bot_wechat_decoupled_from_suppliers`,
  `project_wecom_windows_wxauto4_abandoned`.
