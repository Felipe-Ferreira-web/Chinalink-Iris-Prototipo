# Status — Bot WeChat (2026-07-20)

Registro do que foi feito, decidido e descoberto, pra continuar depois
sem perder contexto. Não substitui o `README.md` (seletores/fluxos
confirmados) — aqui é o resumo de sessão: o que mudou, o que falta, e
por quê.

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
tests/manual/    rotinas dos flags --test-*/--watch-reply do main.py
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
| `start_group_chat` | Implementada, testada só com 1 nome (WeChat abre conversa individual, não forma grupo — esperado). **Não testada com 2+ nomes.** |
| `send_file` | Implementada. **Não testada ao vivo.** |
| `list_unread_sessions` / `--watch-reply` | Implementada. **Não testada ao vivo.** |
| `download_last_document` | Implementada. Só testado o caminho "já baixado" (Save as…); **"Download to…" nunca testado.** |

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
**A confirmação por Enter é suposição** (não foi possível capturar dump
do estado de edição — o clique no terminal pra rodar `inspect_ui.py`
tira o foco do campo) — validar ao vivo com `--test-set-remark`.

## Refactor: rotinas de teste manual viraram scripts standalone

`main.py` não tem mais flags — ficou só o comportamento padrão (achar
janela + ler/imprimir mensagens de `TARGET_CHAT_NAME`), reservado pro
que rodar de verdade em produção mais pra frente. Cada teste manual
(antes um `--test-*` do `main.py`) agora é um script standalone em
`tests/manual/`, rodado direto (`python tests/manual/add_contact.py
<telefone>`, etc.): `add_contact.py`, `start_chat.py`, `start_group.py`,
`send_file.py`, `download_last_file.py`, `set_remark.py`,
`watch_reply.py`, `read_messages.py`, `echo_last.py`,
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

## Próximos passos concretos

1. Validar `set_remark.py` ao vivo (a confirmação por Enter é suposição).
2. Continuar o ciclo teste-ao-vivo → pytest pras funções que faltam:
   `start_group.py` (2+ nomes), `send_file.py`, `watch_reply.py`,
   `download_last_file.py` (testar especificamente um arquivo AINDA NÃO
   baixado).

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
  `project_bot_wechat_decoupled_from_suppliers`, `project_wecom_windows_wxauto4_abandoned`.
