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
| `add_contact_by_phone` | Já existia antes de hoje, implementada. **Ainda não testada ao vivo** (item pendente de antes). |
| `send_message`/`read_messages`/`open_chat`/`list_sessions` | Já confirmadas funcionando ao vivo em sessão anterior. |

Novos flags de teste em `main.py`: `--test-start-chat NOME`,
`--test-start-group NOME1 NOME2 ...` (além dos já existentes
`--test-add-contact`, `--test-reply`, `--echo-last`).

## Em andamento: enviar e baixar documento

**Enviar documento (`send_file`, ainda não implementada)**: o botão
existe e foi confirmado — `text='Send File'`, na barra ao lado de
`chat_input_field`. Falta descobrir o que abre ao clicar (diálogo nativo
de arquivo? aceita paste de `CF_HDROP`?) — ninguém clicou nele ainda
pra ver.

**Baixar documento (`download_last_document`, ainda não implementada)**
— bastante descoberto hoje, quase pronto:
- Bolha de mensagem tipo arquivo: `class='mmui::ChatBubbleItemView'`,
  texto no formato `"File\n<nome_do_arquivo>\n<tamanho>\n微信电脑版"` —
  dá pra extrair o nome do arquivo direto do texto (linha 2), sem
  precisar abrir nada.
- **Clique simples na bolha já baixa E abre no app padrão do sistema**
  (ex. Notepad) — comportamento real, mas ruim pra automação (não
  queremos abrir apps aleatórios). Evitar clique simples.
- Clique direito abre menu de contexto que **muda conforme o estado**:
  - Arquivo **já baixado**: `Copy`, `Edit`, `Forward...`,
    `Add to Favorites`, `Select...`, `Reminder`, `Quote`, `Summary`,
    **`Show in folder`**, **`Save as...`**, `Open With...`, `Recall`.
  - Arquivo **ainda não baixado**: `Download`, `Forward...`,
    `Add to Favorites`, `Select...`, `Reminder`, `Quote`,
    **`Download to...`**, `Delete`.
  - Imagem ainda não baixada (menu ainda mais reduzido):
    `Forward...`, `Add to Favorites`, `Select...`, `Reminder`, `Quote`,
    `Open in new window`, `Delete` — **sem opção de download visível**
    (precisa investigar melhor esse caso separadamente).
- **Decisão**: preferir `"Download to..."`/`"Save as..."` (deixam a
  gente escolher o destino explicitamente) em vez de `"Show in folder"`
  (que exigiria ler o caminho de volta da barra de endereço do
  Explorer — mais frágil).
- **Não confirmado ainda**: ao clicar `"Download to..."`, abre um
  diálogo de verdade pra escolher pasta, ou vai direto pro Documents
  padrão sem perguntar nada? Última mensagem do usuário («está baixando
  em documents padrão do user») sugere que pode ir direto, mas não
  ficou claro se apareceu diálogo no meio. Precisa confirmar isso (e o
  padrão exato de pasta/nome dentro de Documents) antes de escrever
  `download_last_document`.

## Ainda não iniciado

- **Responder mensagem nova em qualquer conversa** (`list_unread_sessions`
  + flag `--watch-reply`) — precisa mapear o indicador de "não lida" num
  `session_item_<Nome>` da sidebar. Só vimos `mmui::XBadge` nos botões da
  barra de navegação principal (abas Weixin/Contacts/etc.), ainda não
  num item de conversa individual — dump ainda pendente (mandar mensagem
  de teste sem abrir a conversa, depois `inspect_ui.py` padrão).

## Próximos passos concretos (nesta ordem)

1. Confirmar o comportamento de `"Download to..."` (diálogo real ou
   destino fixo?) e terminar `download_last_document`.
2. Clicar em `"Send File"` e mapear o que abre, pra implementar
   `send_file`.
3. Mapear o indicador de "não lida" na sidebar, pra implementar
   `list_unread_sessions` + `--watch-reply`.
4. Rodar os testes ao vivo ainda pendentes: `--test-add-contact`,
   `--test-start-chat`, `--test-start-group` (com 2+ nomes).

## Onde mais olhar

- `README.md` (mesma pasta) — tabelas de seletores confirmados, seção
  "Pendências" com checklist mais granular.
- Plano ativo: `~/.claude/plans/primeiro-planeje-e-leia-humble-sonnet.md`.
- Memória entre sessões: `project_bot_wechat_decoupled_from_suppliers.md`
  e `project_wecom_windows_wxauto4_abandoned.md` (no sistema de memória
  do Claude Code), ambas atualizadas hoje.
