# Status — Bot WeChat (2026-07-17)

Registro do que foi feito, decidido e descoberto na sessão de hoje, pra
continuar depois sem perder contexto. Não substitui o `README.md`
(que documenta os seletores/fluxos confirmados) — aqui é o resumo da
sessão: o que mudou, o que falta, e por quê.

## Contexto de ambiente (sempre válido, não só hoje)

O WeChat só existe no servidor Windows (RDP) — este ambiente de trabalho
(Linux) nunca executa nada contra o WeChat real. O ciclo é sempre:
escrevo código + digo o que inspecionar → você roda no servidor e cola
o dump/resultado aqui → eu implemento/ajusto → você testa de novo.

## Mudanças estruturais feitas hoje

- Pasta `Bot WeCom` (tentativa antiga em Linux, AT-SPI/OCR) **apagada**
  do repo — nunca confirmada de ponta a ponta, substituída pela
  automação via `pywinauto` no Windows.
- Pasta `Bot WeCom Windows` **renomeada para `Bot WeChat`** (`git mv`,
  histórico preservado).
- Integração com o server Django "Busca de Suppliers" (`server_client.py`,
  `sync_suppliers.py`, campos de config relacionados) **removida de
  propósito** — aquele módulo vai pra outro repositório, o bot virou um
  projeto independente. Não é esquecimento; não reconectar sem
  confirmar de novo com o usuário.
- `wxauto4` (fork `AngeCoo/wxauto-4.0`) **reinvestigado como possível
  "base de referência"** pra evitar mapear tudo na mão — descartado de
  novo: 16 dos 19 commits do fork são gerados por IA (branches
  `codex/...`), a função de add-contact nem é pública na lib (código
  morto, nunca ligado à classe `WeChat`), textos hardcoded em chinês, e
  reusa o mesmo `Menu.select('粘贴')` do deadlock já visto antes. Não
  vale reabrir essa investigação sem motivo novo.

## Funções mapeadas e implementadas hoje

Todas em `wechat.py`, com seletores reais confirmados via
`inspect_ui.py` (nunca adivinhados) — ver `README.md` pras tabelas
completas.

| Função | Status |
|---|---|
| `find_or_start_chat(main_window, contact_name)` | Implementada (aba Contacts + botão "Messages"). **Não testada ao vivo ainda.** |
| `start_group_chat(main_window, contact_names)` | Implementada. Testada com 1 nome só: confirmado que 1 pessoa não forma grupo de verdade (abre conversa individual) — **ainda não testada com 2+ nomes**. |
| `send_file(window, chat_name, filepath)` | Implementada (botão "Send File" → diálogo nativo `#32770` "Select File" → cola caminho, clica "Open"). **Não testada ao vivo ainda.** |
| `list_unread_sessions(window)` | Implementada (lê marcador `[N]` embutido no texto do `session_item_`). **Não testada ao vivo ainda.** Usada pelo novo `main.py --watch-reply` (loop, vigia sidebar inteira, responde mensagem nova, Ctrl+C sai). |
| `download_last_document(window, chat_name, save_dir)` | Implementada — clica direito na bolha (`class='mmui::ChatBubbleItemView'`), decide entre "Download to…"/"Save as…" lendo o estado direto do texto da bolha (`Not Downloaded` presente ou não), preenche o mesmo tipo de diálogo nativo do `send_file` em modo salvar. **Só testado ao vivo o caminho "já baixado" (Save as…); "Download to…" ainda não foi exercitado.** |
| `add_contact_by_phone` | Já existia antes de hoje, implementada. **Ainda não testada ao vivo** (item pendente de antes). |
| `send_message`/`read_messages`/`open_chat`/`list_sessions` | Já confirmadas funcionando ao vivo em sessão anterior. |

**Todas as 6 funções pedidas no início da sessão (adicionar contato,
iniciar conversa, enviar mensagem, responder mensagem nova, enviar
documento, baixar documento) estão implementadas.** O que falta agora é
só rodar os testes ao vivo — nenhuma delas foi exercitada de ponta a
ponta contra o WeChat real ainda, exceto `send_message`/`read_messages`/
`open_chat` (de sessão anterior) e a metade "já baixado" do
`download_last_document`.

Novos flags de teste em `main.py`: `--test-start-chat NOME`,
`--test-start-group NOME1 NOME2 ...`, `--test-send-file NOME CAMINHO`,
`--watch-reply [texto]`, `--test-download-last-file NOME PASTA` (além
dos já existentes `--test-add-contact`, `--test-reply`, `--echo-last`).

## Próximos passos concretos

Só falta testar ao vivo, não tem mais nada pra mapear/implementar por
enquanto:
1. `--test-add-contact <telefone>`
2. `--test-start-chat <nome>`
3. `--test-start-group <nome1> <nome2>` (2+ nomes — só testado com 1)
4. `--test-send-file <nome> <caminho>`
5. `--watch-reply`
6. `--test-download-last-file <nome> <pasta>` — testar especificamente
   com um arquivo **ainda não baixado** (o caminho "Download to…" nunca
   foi exercitado; se falhar, o diálogo resultante pode ter
   título/seletor diferente do assumido — ver README).

## Onde mais olhar

- `README.md` (mesma pasta) — tabelas de seletores confirmados, seção
  "Pendências" com checklist mais granular.
- Plano ativo: `~/.claude/plans/primeiro-planeje-e-leia-humble-sonnet.md`.
- Memória entre sessões: `project_bot_wechat_decoupled_from_suppliers.md`
  e `project_wecom_windows_wxauto4_abandoned.md` (no sistema de memória
  do Claude Code), ambas atualizadas hoje.
