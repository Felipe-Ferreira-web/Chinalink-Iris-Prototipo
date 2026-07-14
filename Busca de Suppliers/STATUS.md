# Iris — Status do Módulo 1 (Busca e Painel de Fornecedores)

> Ver `ARCHITECTURE.md` para a arquitetura completa (stack, modelagem de dados, contratos de API). Este documento é o retrato do que já foi construído, o que está funcionando, e o que falta.

## O que já foi feito

### Estrutura e infraestrutura
- Repositório com três componentes: `server/` (Django), `client/` (React + Vite), `extension/` (WXT + TypeScript) — sem git inicializado ainda (decisão explícita, ainda não pedida).
- `docker-compose.yml` + `Dockerfile` em cada componente. Serviços: `redis`, `server`, `celery` (worker, configurado mas sem tasks reais ainda), `client`, `extension` (container "one-shot" que só builda e escreve em `.output/`).
- `run.sh` (Linux/macOS) e `run.bat` (Windows): derrubam containers/portas anteriores automaticamente, buildam com saída silenciosa (só mostram erro se o build falhar), sobem `redis`/`celery`/`extension` em segundo plano sem poluir o terminal, e deixam só os logs de `server`+`client` visíveis. Containers rodam com usuário não-root (uid 1000) para não gerar arquivos `root`-owned nos bind mounts.
- SQLite em dev (fallback padrão do `server/config/settings.py`); Postgres fica pronto pra produção só setando as env vars `DATABASE_*` — não precisa mudar código.

### Server (Django + DRF)
- Apps `sourcing` (`SourcingRequest`, `Supplier`, `ProductListing`) e `contacts` (`ContactExtraction`), com migrações aplicadas (inclui `ContactExtraction.company_website`).
- **Busca real via Apify**: `sourcing/services.py` chama o actor `alibaba-listings-scraper` (`piotrv1001`, ID `8EM2KQP90np87iSY5`), popula `Supplier`+`ProductListing` a partir do resultado. **Síncrono** — a requisição HTTP do `POST /api/sourcing-requests/` fica bloqueada até o actor terminar (~10-15s). Celery/Redis já estão configurados na infra mas essa chamada ainda não foi movida para lá.
  - **Retry automático**: o actor às vezes reporta sucesso mas devolve 0 itens (bloqueio silencioso do Alibaba pra aquela busca específica — confirmado testando o actor direto pela API do Apify). `run_alibaba_search` tenta até 3x antes de desistir, registrando `filters.retries` no `SourcingRequest`. Não elimina o bloqueio (é do lado do Alibaba/Apify), só mitiga picos pontuais.
- **Extração de contato**, bem mais completa que a versão inicial:
  - OCR real (`contacts/services.py`, Tesseract) quando o número vem como `<img class="value-image">` base64.
  - Caminho sem OCR (`phone_text`) quando o número já vem como texto visível no DOM — a extensão manda o texto direto.
  - Fallback pro **site da empresa** (`company_website`) quando o fornecedor não tem celular nem telefone cadastrado — só usado como último recurso, e só depois de confirmar que os dois campos estão de fato vazios (ver bug corrigido abaixo).
  - Prioridade de extração: **Celular > Telefone > Site da empresa**.
  - Atualiza `Supplier.status → contato_extraido` nos três caminhos (helper único `mark_supplier_contato_extraido`).
  - **Bug corrigido**: `company_website` era `URLField`, que exige esquema (`http://`/`https://`) — texto extraído sem protocolo (ex.: `www.foo.com`) causava `400 Enter a valid URL.` na extensão. Trocado pra `CharField` (é só exibido como texto no client, não usado como link real, não precisa de validação estrita).
- `ProductListingSerializer` expõe `contact_phone` e `contact_website` (busca a última `ContactExtraction` com `status=extraido` do produto) — é o que o client usa pra mostrar o contato já extraído ao lado do produto.
- Endpoints ativos: `GET /api/health/`, `POST /api/sourcing-requests/` (retorna já com `products` aninhados), `GET /api/sourcing-requests/{id}/products/`, `GET /api/products/{id}/`, `GET /api/suppliers/{id}/`, `POST/PATCH /api/contacts/extractions/`.
- Sem autenticação real ainda: todos os endpoints usam `AllowAny`; `SourcingRequest.requested_by` é sempre um usuário fixo `dev` criado automaticamente (`get_or_create`). Decisão explícita — login de verdade fica para depois.
- CORS liberado para `chrome-extension://`, `moz-extension://` e `http://localhost:5173`.

### Client (React + Vite + Tailwind v4)
- Form de busca (produto + quantidade, 1–50) que chama `POST /api/sourcing-requests/` de verdade e renderiza os produtos retornados: imagem, título (limpo de HTML cru que a Apify retorna), preço (com promocional riscado quando existe), MOQ, nota.
- Cada card mostra também (novo): badge do status do fornecedor (Novo / Contato extraído / Aprovado / Reprovado) e o contato extraído — telefone (📱) quando disponível, ou o site da empresa (🌐) como fallback quando não há telefone.
- Polling automático (a cada 5s) em `GET /api/sourcing-requests/{id}/products/` enquanto algum produto ainda não tem contato extraído — a extração roda de forma assíncrona na extensão (depende do colaborador navegar/resolver captcha), então o card atualiza sozinho sem precisar recarregar a página.
- Cada card linka para a URL real do Alibaba com `?iris_product_id={id}` embutido — é assim que a extensão sabe qual produto está associado à aba aberta.

### Extensão (WXT + TypeScript, builda para Chrome MV3 e Firefox MV2)
- `background.ts`: ponte HTTP genérica (contorna bloqueio de mixed content HTTPS→HTTP).
- `content.ts`: máquina de estados persistida em `browser.storage.local` (sobrevive a navegação/reload entre páginas). Fluxo atual:
  1. Lê `iris_product_id` da URL do produto, busca no server o nome exato do fornecedor (`GET /api/products/{id}/`).
  2. **Atalho direto**: em vez de clicar no link do fornecedor e depois procurar a aba "Contatos" (2 navegações), monta a URL `{origem-do-fornecedor}/contactinfo.html` e navega direto pra lá.
  3. **Validação do atalho**: confirma que a página que chegou é de fato o painel de contato (procura o módulo, o botão "Ver detalhe" ou um captcha). Se não for válido pra aquele fornecedor, cai automaticamente pro fluxo antigo (clicar no link do fornecedor → clicar na aba "Contatos"). Só validado contra **um** fornecedor até agora.
  4. Encontra e clica em "Ver detalhe" — busca escopada estritamente dentro do módulo de contato (`.module-contactPersonNew`), tentando primeiro a linha do **Celular** e caindo pra linha do **Telefone** se a do Celular estiver vazia (`-`). Busca só pelo texto "ver detalhe" (interface sempre em pt-BR nesse fluxo — simplificado depois de descobrir que a classe CSS variava entre fornecedores: `view-details`, `view-detail`, etc., causando cliques inconsistentes).
  5. Modal "Obter informações" (pede cartão de visita em troca do contato, parte normal do fluxo): detectado e o botão "Enviar" é clicado automaticamente.
  6. Se aparecer CAPTCHA: só espera — **sempre resolução manual pelo colaborador**, sem 2Captcha (decisão de arquitetura).
  7. Extrai o contato revelado (imagem base64 com OCR, texto puro sem OCR, ou site da empresa como último recurso) e envia pro server.
  - **Delay anti-bot**: 2s de espera antes de cada clique (link do fornecedor, aba Contatos, "Ver detalhe", "Enviar" do modal), pra não disparar detecção por cliques instantâneos.
  - **Bug corrigido — clique no elemento errado**: a busca genérica por texto podia acabar clicando em "Contato agora"/"Enviar consulta" da barra lateral (fluxo errado, pede troca de cartão de visita) em vez do "Ver detalhe" do Celular. Corrigido escopando a busca estritamente à linha certa dentro do módulo de contato.
  - **Bug corrigido — extração de texto lixo**: a extração de texto podia capturar o próprio texto do gatilho "Ver detalhe" como se fosse o valor revelado (antes do captcha ser resolvido), gravando lixo no banco com `status=extraido` — parecia ter funcionado mas não tinha. Corrigido ignorando explicitamente esse gatilho ao procurar o valor.
  - **Bug corrigido — extração prematura do site da empresa**: a extensão não distinguia "campo vazio" (`-`, de fato sem esse contato) de "campo ainda não revelado" (só mostra o gatilho "Ver detalhe"). Como o site da empresa costuma vir visível sem precisar de clique, ela caía pro site **antes mesmo de tentar revelar** celular/telefone, marcando `contato_extraido` prematuramente e mostrando só o link da página no client em vez do telefone. Corrigido com uma análise de 3 estados (`valor`/`vazio`/`pendente`) — site só é tentado quando os dois campos de telefone estão confirmadamente vazios.
  - **Recuperação de estado travado**: se uma tentativa anterior parou em `erro` ou `extraindo_contato` (estados sem tratamento no switch principal) e o colaborador reabre/recarrega uma página que já é o painel de contato, a extensão tenta de novo automaticamente em vez de ficar parada.
  - Dados corrompidos gerados por esses bugs durante os testes foram limpos do banco (`status→falha` + fornecedores resetados pra `novo`) em duas rodadas.
- Popup mostra o status em tempo real de cada etapa do fluxo (rótulos atualizados com os novos estados, incluindo `validando_atalho`).

### Distribuição da extensão (em discussão, nada implementado ainda)
- Objetivo: disponibilizar a extensão pra equipe interna sem exigir reinstalação manual a cada atualização, e sem publicar como extensão pública.
- **Investigado e descartado**: não existe API de navegador que permita instalação automática/via popup a partir de uma página web pra extensões não publicadas — isso foi removido dos navegadores há anos por segurança (`chrome.webstore.install()` inline e `InstallTrigger.install()` do Firefox, ambos descontinuados).
- **Caminho decidido a seguir** (ainda não implementado): publicar no Chrome Web Store com visibilidade **Privada/restrita à organização** (Google Workspace `chinalinktrading.com`) — não aparece pra fora da empresa, ganha o botão nativo "Adicionar ao Chrome" e atualização automática pra sempre. Alternativa mais forte se a empresa tiver Chrome gerenciado centralmente (Chrome Browser Cloud Management/GPO): política `ExtensionInstallForcelist` pra instalação e atualização 100% silenciosas — ainda não confirmado se a empresa tem esse gerenciamento.
- Pré-requisitos identificados, pendentes: ícones da extensão em vários tamanhos (**ainda não existem — nenhum arquivo de ícone no projeto**), conta de desenvolvedor Chrome Web Store (taxa única de US$5), política de privacidade curta (a extensão lê dados da página do Alibaba e manda pro nosso servidor — precisa de divulgação), screenshots pra ficha da loja.
- Descoberto durante essa investigação (sem relação com o trabalho atual): existe um projeto separado e não relacionado em `Iris - Testes/Teste Busca/bot/`, um bot em Node.js/Playwright que abre seu próprio Chromium (perfil persistente) e resolve captcha automaticamente — não usa nossa extensão nem nosso servidor Django (fala com `localhost:3000`, contrato de API diferente). Causou confusão em um teste porque abria "uma nova instância de navegador" sem relação com o que estávamos testando.

## Em aberto / não confirmado

- **Fluxo completo ainda não confirmado ponta a ponta pelo usuário** no Alibaba real após todos os fixes desta sessão (clique certo, delay, atalho, extração prematura do site, recuperação de estado). Vários bugs sucessivos já foram encontrados e corrigidos nos testes; falta uma passada completa e limpa confirmando captcha → revelação → extração → aparecendo certo no client.
- Taxa de acerto do atalho `contactinfo.html` só validada contra 1 fornecedor — o fallback pro fluxo antigo cobre o caso de falhar, mas vale observar quantos fornecedores realmente usam esse padrão de URL.
- O bloqueio do actor da Apify (0 resultados pra buscas específicas) é do lado do Alibaba/scraping, não do nosso código — o retry automático mitiga picos pontuais mas não é garantia (ex.: "phone case" continuou vazio mesmo após 3 tentativas em teste anterior).
- Decisão pendente com o usuário: confirmar se a empresa tem Chrome gerenciado centralmente (pra decidir entre Chrome Web Store privado vs. policy de instalação silenciosa).

## O que falta fazer

- [ ] Confirmar o fluxo completo da extensão contra o Alibaba real, ponta a ponta, após os fixes desta sessão
- [ ] Validar o atalho `contactinfo.html` contra mais fornecedores (hoje só testado em 1)
- [ ] Preparar distribuição da extensão pra equipe: ícones, política de privacidade, conta de desenvolvedor, publicação privada/restrita (ou policy de instalação silenciosa, a depender da infra da empresa)
- [ ] Mover a chamada à Apify para uma task Celery assíncrona (hoje bloqueia a requisição HTTP); implementar polling ou notificação no client pra saber quando terminou
- [ ] Autenticação real do colaborador no client (hoje é tudo `AllowAny` + usuário `dev` fixo)
- [ ] Lidar com o caso de a página do fornecedor abrir em nova aba (não tratado — a máquina de estados assume mesma aba)
- [ ] Filtros de qualidade/MOQ/avaliação mínima no client (ainda não decidido quais critérios usar)
- [ ] `git init` do repositório (deliberadamente não feito ainda)
- [ ] Módulo 2 (agente Iris no WeChat) e Módulo 3 (integrações internas) — fora do escopo até agora, arquitetura só descrita no escopo geral do projeto
