# Iris — Arquitetura (Módulo 1: Busca e Painel de Fornecedores)

## 1. Visão geral

Fluxo do Módulo 1:

```
Client (React) → colaborador insere produto
   → Server (Django) chama Apify → retorna produtos/fornecedores
   → colaborador abre link de cada fornecedor
   → Extensão (WXT) navega na página, revela contato
   → se captcha aparecer: colaborador resolve manualmente
   → Extensão extrai imagem/texto do contato → envia pro Server
   → Server roda OCR, normaliza e persiste o contato
   → Fornecedor marcado como "contato extraído" → dispara Módulo 2 (Iris no WeCom, fora de escopo aqui)
```

Decisões-base:
- Fluxo **semi-automático**: sem 2Captcha, sem resolução automática de captcha — o colaborador resolve manualmente na aba aberta quando aparece.
- Referência de padrão validado: `Iris - Testes/Teste Busca` (Node/Express + extensão WXT/TS) — aqui trocamos o servidor Node por Django.

## 2. Stack por componente

| Componente | Tecnologia |
|---|---|
| Server (backend) | Python / Django + Django REST Framework |
| Filas | Celery + Redis |
| OCR | Tesseract (`pytesseract`) |
| Busca de produtos | Apify — actor [Alibaba Listings Scraper](https://apify.com/piotrv1001/alibaba-listings-scraper) (`8EM2KQP90np87iSY5`) |
| Client web | React + TypeScript (Vite) |
| Extensão | WXT + TypeScript (Manifest V3) |
| Banco de dados | SQLite em dev/protótipo (fallback padrão do server); PostgreSQL quando for para produção (troca só via env vars `DATABASE_*`) |

## 3. Estrutura de pastas (monorepo)

```
Chinalink - Iris/
├── ARCHITECTURE.md
├── README.md
├── server/                 # Django project (usa a venv já existente na raiz)
│   ├── manage.py
│   ├── config/          # settings, urls, celery.py
│   ├── sourcing/        # app: SourcingRequest, Product, Supplier
│   ├── contacts/        # app: ContactExtraction (OCR)
│   └── requirements.txt
├── client/               # React + TS (Vite)
└── extension/           # WXT + TypeScript
```

## 4. Divisão de responsabilidades

**Extensão (WXT + TS)** — só DOM, zero lógica de negócio:
- `content.ts`: observa a página do fornecedor, clica para revelar contato, confirma dialogs, detecta captcha (se aparecer, só sinaliza status "aguardando resolução manual" — colaborador resolve na própria aba), extrai a imagem/texto do contato revelado.
- `background.ts`: ponte HTTP — faz o `fetch` para o server (evita bloqueio de mixed content HTTPS→HTTP), sem lógica além disso.
- `popup/`: status da extração atual.

**Server (Django)** — toda a lógica de negócio:
- Recebe contato extraído da extensão, roda OCR, normaliza, persiste.
- Chama a API Apify para buscar produtos/fornecedores a partir do que o colaborador inseriu no client.
- Orquestra jobs assíncronos (Celery) para busca e OCR.
- Serve a API REST consumida pelo client.

**Client (React)**:
- Form de busca de produto, listagem de resultados (produtos + fornecedores), status de extração de contato por fornecedor.

## 5. Apps Django e modelagem de dados

O actor Apify usado (`alibaba-listings-scraper`) só aceita `search` (string) e `limit` (integer) como input, e devolve por item: `title`, `price`, `promotionPrice`, `discount`, `moq` (string livre, ex. `"Min. order: 1 unit"`), `companyName`, `countryCode`, `productUrl`, `mainImage`, `reviewScore`, `reviewCount`, `deliveryEstimate` — **não** retorna uma URL de perfil do fornecedor separada, só `productUrl` (página do produto) e `companyName`. Por isso `ContactExtraction` está amarrada a `ProductListing` (não a `Supplier` diretamente): é o `productUrl` que o colaborador abre e onde a extensão atua; não existe outro link do fornecedor para navegar.

### App `sourcing`

**SourcingRequest** — cada busca que o colaborador dispara no client
- `id`
- `query` (CharField) — produto buscado, vai direto no `search` do actor
- `limit` (IntegerField, nullable) — repassado ao actor
- `filters` (JSONField) — filtros aplicados no client *após* o retorno do actor (MOQ, avaliação mínima etc. — critérios ainda em aberto, ver seção 7; o actor não filtra nativamente, então isso é feito no server em cima do resultado bruto)
- `requested_by` (FK → User)
- `status` (choices: `pending`, `running`, `done`, `failed`)
- `created_at`, `updated_at`

**Supplier** (Fornecedor)
- `id`
- `name` (CharField) ← `companyName`
- `platform` (CharField, ex: `alibaba`)
- `country_code` (CharField, nullable) ← `countryCode`
- `raw_data` (JSONField) — dump bruto do item retornado pela Apify
- `status` (choices: `novo`, `contato_extraido`, `aprovado`, `reprovado`)
- `created_at`, `updated_at`
- Sem `profile_url`/`external_id` únicos disponíveis na origem — dedup feito por `(platform, name, country_code)` como chave best-effort (não é garantidamente único; se o actor futuramente expuser um id estável, migrar para ele)

**ProductListing** (resultado de uma busca)
- `id`
- `sourcing_request` (FK → SourcingRequest)
- `supplier` (FK → Supplier)
- `title` (CharField) ← `title`
- `url` (URLField) ← `productUrl` — é esse link que o colaborador abre e a extensão navega
- `price` (CharField) ← `price` (ex. `"$119.60"` — mantido como string na ingestão bruta; normalização numérica fica para quando decidirmos critérios de filtro, ver seção 7)
- `promotion_price` (CharField, nullable) ← `promotionPrice`
- `discount` (CharField, nullable) ← `discount`
- `moq` (CharField, nullable) ← `moq` (string livre do actor, ex. `"Min. order: 1 unit"`)
- `main_image` (URLField, nullable) ← `mainImage`
- `review_score` (DecimalField, nullable) ← `reviewScore`
- `review_count` (IntegerField, nullable) ← `reviewCount`
- `delivery_estimate` (CharField, nullable) ← `deliveryEstimate`
- `raw_data` (JSONField) — item bruto completo retornado pela Apify
- `created_at`

### App `contacts`

**ContactExtraction**
- `id`
- `product` (FK → ProductListing) — a extração acontece a partir do link de um produto específico; o fornecedor é acessado via `product.supplier`
- `status` (choices: `pendente`, `aguardando_captcha`, `extraido`, `falha`)
- `raw_image` (ImageField, nullable) — imagem enviada pela extensão
- `phone_raw_text` (TextField, nullable) — saída crua do OCR
- `phone` (CharField, nullable) — normalizado
- `wechat` (CharField, nullable)
- `extracted_by` (FK → User, nullable) — colaborador que resolveu o captcha manualmente
- `error_message` (TextField, nullable)
- `created_at`, `updated_at`

## 6. Contratos de API (implementado)

**Client → Server**
- `POST /api/sourcing-requests/` `{query, limit}` → cria `SourcingRequest`, chama o actor Apify **de forma síncrona** (bloqueia a resposta HTTP até terminar — ok para protótipo; migrar para Celery é um próximo passo) e retorna o objeto já com `products` aninhados
- `GET /api/sourcing-requests/{id}/products/` → lista `ProductListing` resultantes
- `GET /api/products/{id}/` → detalhe de um produto (com `supplier` aninhado) — usado pela extensão pra saber o nome exato do fornecedor sem precisar adivinhar pelo DOM
- `GET /api/suppliers/{id}/` → detalhe do fornecedor + status de contato

**Extensão → Server**
- `POST /api/contacts/extractions/` `{product, status, image_data?, wechat?}` → cria/atualiza `ContactExtraction` vinculada ao `ProductListing` aberto. `image_data` é a `data:image/...;base64,...` do `<img class="value-image">` revelado na página (Alibaba renderiza o número como imagem anti-scraping) — o server decodifica e roda OCR (Tesseract) na hora, síncrono. Ao concluir com sucesso, atualiza `product.supplier.status = contato_extraido`.
- O client passa `?iris_product_id={id}` na URL do produto ao abrir o link (`client/src/App.tsx`); a extensão lê esse parâmetro na aba e guarda o estado da máquina de navegação (`extension/utils/status.ts`, via `browser.storage.local`) pra sobreviver a cada navegação (produto → fornecedor → aba de contatos → captcha → extração).

## 7. Decisões em aberto (herdadas do escopo geral, não bloqueiam o esqueleto)

- Critérios de qualidade da cota de fornecedores
- Estratégia de atualização de preços
- Filtros de MOQ e avaliações mínimas
- Verificação formal da empresa no WeCom (Módulo 2, pré-requisito de produção)
- Checkpoints obrigatórios durante conversa com fornecedor (Módulo 2)

## 8. Próximos passos (fora desta etapa)

1. Scaffold do Django project (`server/`) com as apps `sourcing` e `contacts` e os models acima.
2. Scaffold da extensão (WXT) com `content.ts`/`background.ts` placeholders.
3. Scaffold do client (Vite + React + TS).
4. Endpoint "hello world" de ponta a ponta (extensão → server) para validar a comunicação.
