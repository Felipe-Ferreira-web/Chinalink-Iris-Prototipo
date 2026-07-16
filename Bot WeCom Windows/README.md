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
python inspect_ui.py   # dump da árvore real de controles em ui_dump.txt — sem clicar em nada
```

Abra `ui_dump.txt` depois de rodar e procure pelos elementos: caixa de
busca, lista de conversas na sidebar, campo de digitar mensagem, botão de
enviar. É a partir desses nomes/classes reais que a automação de
`SendMsg`/leitura de mensagem vai ser escrita — os scripts antigos
`explore.py`/`main.py` (que dependiam do `wxauto4` abandonado) ainda
estão na pasta como referência, mas não rodam mais sem reinstalar aquela
dependência.

## Pendências desta etapa

- [ ] Rodar `inspect_ui.py` no servidor e mapear os seletores reais da
      caixa de busca, lista de conversas, campo de mensagem e botão de
      enviar.
- [ ] Escrever `send_message`/`read_new_messages` próprios com
      `pywinauto`, testados contra o WeChat de verdade (não adivinhados).
- [ ] Confirmar se a automação também cobre WeCom (cliente corporativo)
      ou só WeChat pessoal.
- [ ] Testar estabilidade do RDP durante uso prolongado (risco já
      identificado no relatório do módulo — causa ainda não confirmada:
      timeout de sessão ociosa, limite de sessões simultâneas, ou rede/VPN).
- [ ] Avaliar risco de detecção de login por região/IP (servidor fora da
      China) antes de qualquer teste com conta real de produção.
