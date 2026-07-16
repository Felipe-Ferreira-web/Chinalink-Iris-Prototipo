# Bot WeCom Windows

> Segunda tentativa de automação de mensageria do WeChat/WeCom — via
> **UI Automation do Windows**, rodando num Windows Server (RDP), usando a
> lib `wxauto4` (versão gratuita). Pasta separada da antiga `Bot WeCom`
> (Linux, AT-SPI/OCR, descartada — ver `README.md` de lá para o histórico
> completo da investigação).

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

## Stack

| Item | Detalhe |
|---|---|
| Lib | [`wxauto4`](https://pypi.org/project/wxauto4/) — versão **gratuita**, sem licença comercial. Este módulo é só para testar até onde ela dá conta antes de considerar a `wxautox4` (Plus, paga, com restrição de uso comercial a checar). |
| Onde roda | Windows Server da empresa, sessão de desktop interativa real via RDP — **não** funciona em Docker/headless (precisa de sessão de UI de verdade). |
| App automatizado | WeChat desktop (ou WeCom, se confirmado que a lib também cobre o cliente corporativo) já logado na sessão. |
| Fluxo de dev | Editar aqui no Linux → `git push` → `git pull` no servidor Windows (ou VS Code Remote SSH, se configurado) → rodar `python explore.py` na sessão RDP. |

## ⚠️ Pré-requisito: versão exata do WeChat

A `wxauto4` (confirmado na documentação oficial, não só no changelog) só
funciona com o **cliente WeChat 4.0.5** especificamente — não "4.0 ou
mais recente". Antes de instalar a lib:

1. Confirmar qual versão do WeChat está instalada no Windows Server.
2. Se não for a 4.0.5, baixar essa versão específica em
   [`SiverKing/wechat4.0-windows-versions`](https://github.com/SiverKing/wechat4.0-windows-versions/releases)
   (não clicar direto no link de download da release — abrir a versão
   certa, expandir "Assets" e baixar o `.exe` de lá).
3. **Desativar o auto-update do WeChat** — uma atualização automática
   quebra a automação silenciosamente (a UI Automation passa a não achar
   mais os controles esperados).

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
python explore.py             # diagnóstico: conecta, lista sessões, lê histórico — sem enviar nada
python main.py                # escuta TARGET_CHAT_NAME por LISTEN_DURATION_SECONDS, imprime mensagens novas
python main.py --test-reply   # além de escutar, manda TEST_MESSAGE pra TARGET_CHAT_NAME uma vez no início
```

Rodar `explore.py` primeiro — não tem efeito colateral, só confirma que a
lib enxerga a janela do WeChat já aberta (`WeChat()`), lista as conversas
da sidebar (`GetSession()`) e lê o histórico da conversa alvo
(`ChatWith()` + `GetAllMessage()`). Cada passo imprime o resultado antes
de seguir pro próximo, pra facilitar ver exatamente onde algo quebra — não
temos como rodar/depurar isso a partir do Linux, todo teste real acontece
na sessão RDP.

`main.py` testa o mecanismo de "ler mensagem nova em tempo real"
(`AddListenChat` + callback), que é o ponto em aberto mais importante
desta etapa — ler mensagens hoje (na pasta antiga) dependia de OCR
comparando linhas de texto, sem saber o remetente de verdade.

## API confirmada na documentação (`wxauto4.WeChat`)

Lido direto do código-fonte (`wx.py`, `param.py`, `msgs/`), não só do
README do pacote:

| Método/atributo | O que faz |
|---|---|
| `WeChat(start_listener=False, debug=False)` | Conecta na instância já aberta. `.nickname`, `.path`, `.dir` disponíveis depois. |
| `GetSession()` | Lista as conversas da sidebar (`.name`, `.unread_count`). |
| `ChatWith(who, exact=False)` | Navega até a conversa. |
| `SendMsg(msg, who=None, at=None, exact=False)` | Envia texto; aceita `@` de outros usuários. |
| `SendFiles(filepath, who=None)` | Envia arquivo(s), aceita lista. |
| `GetAllMessage()` / `GetNewMessage()` | Lista de `Message` — `.attr` (`self`/`friend`/`system`), `.sender`, `.content`, `.type` (`text`/`image`/`file`/`voice`/`video`/`quote`/`other`). |
| `AddListenChat(who, callback)` | Registra `callback(msg, chat)`, disparado por um thread pool interno a cada `WxParam.LISTEN_INTERVAL` (padrão 1s) — é o jeito certo de monitorar chat, não polling manual. |
| `StopListening()` / `KeepRunning()` | Encerra o listener / bloqueia a thread principal enquanto ele roda. |
| `WxResponse` | Retorno de toda ação (`SendMsg`, `SendFiles`, `ChatWith`) — dict-like com `.is_success`, nunca lança exceção em falha esperada (contato não encontrado etc). Sempre checar `.is_success`, não assumir sucesso. |

## Pendências desta etapa

- [ ] Confirmar se `wxauto4` cobre só WeChat pessoal ou também WeCom
      (`WeCom()` é uma classe separada na lib — testar).
- [ ] Testar estabilidade do RDP durante uso prolongado (risco já
      identificado no relatório do módulo — causa ainda não confirmada:
      timeout de sessão ociosa, limite de sessões simultâneas, ou rede/VPN).
- [ ] Avaliar risco de detecção de login por região/IP (servidor fora da
      China) antes de qualquer teste com conta real de produção.
- [ ] **Licença**: mesmo a versão gratuita não tem licença formal (o
      repositório não declara nenhuma) — só um aviso de "uso exclusivo
      para fins de estudo e pesquisa", responsabilidade do usuário. Checar
      se isso é aceitável pra uso comercial no Iris antes de ir pra
      produção (mesma pendência já levantada pra `wxautox4`, só que ali
      pelo menos existe um tier pago pra negociar — aqui não).
- [ ] Só depois de validar o básico aqui: decidir se compensa migrar para
      `wxautox4` (Plus) e checar se a licença dela conflita com uso
      comercial no Iris.
