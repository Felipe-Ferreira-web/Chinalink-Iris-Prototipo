# Iris — Fluxo Resumido (estado atual)

> Ver `STATUS.md` para detalhes/bugs corrigidos e `ARCHITECTURE.md` para a arquitetura completa.

```
1. Colaborador digita um produto no CLIENT (React) e clica "Buscar"
       │
       ▼
2. SERVER (Django) chama o actor da Apify (alibaba-listings-scraper),
   com retry automático (até 3x) se vier 0 resultados
       │
       ▼
3. SERVER salva Supplier + ProductListing no banco e devolve pro CLIENT
       │
       ▼
4. CLIENT mostra os cards (imagem, preço, MOQ, nota) e começa a dar
   polling a cada 5s em cada produto, esperando o contato aparecer
       │
       ▼
5. Colaborador clica no card → abre a página real do Alibaba
   (?iris_product_id=N na URL)
       │
       ▼
6. EXTENSÃO detecta o parâmetro, pergunta pro SERVER o nome do
   fornecedor, acha o link dele na página
       │
       ▼
7. EXTENSÃO tenta o atalho {fornecedor}/contactinfo.html direto
   (pula a navegação manual pela aba "Contatos"); se não for válido
   pra esse fornecedor, cai pro fluxo antigo (clica na aba Contatos)
       │
       ▼
8. EXTENSÃO clica em "Ver detalhe" (Celular, ou Telefone se Celular
   estiver vazio) e confirma o modal "Enviar cartão de visita" se aparecer
       │
       ▼
9. Se aparecer CAPTCHA → extensão só espera. Colaborador resolve
   manualmente na aba (sem 2Captcha, decisão de arquitetura)
       │
       ▼
10. EXTENSÃO extrai o contato revelado — imagem (OCR no server),
    texto puro, ou site da empresa como último recurso — e manda
    pro SERVER
       │
       ▼
11. SERVER processa (OCR se for imagem), marca Supplier → contato_extraido
       │
       ▼
12. CLIENT (que estava dando polling) atualiza o card sozinho,
    mostrando telefone (📱) ou site (🌐)
```

## O que já funciona de ponta a ponta
- Passos 1–4 (busca real, Apify, salvar, mostrar no client, polling) — confirmado funcionando.
- Passos 5–11 (extensão) — implementados, com vários bugs já corrigidos nos testes (clique no elemento errado, extração de texto lixo, extração prematura do site), mas **ainda sem uma passada 100% limpa confirmada pelo usuário** contra o Alibaba real depois dos últimos fixes.

## Maior risco externo (fora do nosso código)
- O actor da Apify às vezes é bloqueado pelo Alibaba (anti-bot) e retorna 0 resultados mesmo pra buscas válidas. O retry mitiga picos pontuais, não elimina o problema.
