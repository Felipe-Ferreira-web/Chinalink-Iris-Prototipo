import { useEffect, useState } from 'react'

const SERVER_URL = 'http://localhost:8000'

type Supplier = {
  id: number
  name: string
  country_code: string | null
  status: string
}

type ProductListing = {
  id: number
  title: string
  url: string
  price: string | null
  promotion_price: string | null
  discount: string | null
  moq: string | null
  main_image: string | null
  review_score: string | null
  review_count: number | null
  delivery_estimate: string | null
  supplier: Supplier
  contact_phone: string | null
  contact_website: string | null
}

const ROTULO_STATUS_FORNECEDOR: Record<string, string> = {
  novo: 'Novo',
  contato_extraido: 'Contato extraído',
  aprovado: 'Aprovado',
  reprovado: 'Reprovado',
}

type SourcingResult = {
  id: number
  query: string
  status: string
  products: ProductListing[]
}

function stripTags(html: string) {
  return html.replace(/<[^>]*>/g, '')
}

// A extensão lê esse parâmetro na aba aberta pra saber qual product_id
// associar à extração de contato que ela vai iniciar naquela página.
function withProductParam(url: string, productId: number) {
  const separator = url.includes('?') ? '&' : '?'
  return `${url}${separator}iris_product_id=${productId}`
}

const MIN_LIMIT = 1
const MAX_LIMIT = 50

function App() {
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(10)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SourcingResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch(`${SERVER_URL}/api/sourcing-requests/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, limit }),
      })

      if (!response.ok) {
        throw new Error(`Server respondeu ${response.status}`)
      }

      setResult(await response.json())
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  // A extração de contato roda na extensão, de forma assíncrona (o
  // colaborador precisa navegar pelo Alibaba) — fica reconsultando os
  // produtos enquanto algum ainda não tiver contact_phone/status atualizado.
  useEffect(() => {
    if (!result) return
    const faltaContato = result.products.some(
      (p) => !p.contact_phone && !p.contact_website && p.supplier.status === 'novo'
    )
    if (!faltaContato) return

    const intervalId = setInterval(async () => {
      try {
        const response = await fetch(`${SERVER_URL}/api/sourcing-requests/${result.id}/products/`)
        if (!response.ok) return
        const products: ProductListing[] = await response.json()
        setResult((atual) => (atual ? { ...atual, products } : atual))
      } catch {
        // Falha pontual de rede não interrompe o polling.
      }
    }, 5000)

    return () => clearInterval(intervalId)
  }, [result?.id, result?.products])

  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="text-2xl font-semibold mb-6">Iris — Busca de Fornecedores</h1>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Produto a buscar"
          className="flex-1 rounded border border-slate-300 px-3 py-2"
        />
        <input
          type="number"
          value={limit}
          onChange={(event) =>
            setLimit(Math.min(MAX_LIMIT, Math.max(MIN_LIMIT, Number(event.target.value) || MIN_LIMIT)))
          }
          min={MIN_LIMIT}
          max={MAX_LIMIT}
          title="Quantidade de produtos"
          className="w-20 rounded border border-slate-300 px-3 py-2"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-slate-800 px-4 py-2 text-white hover:bg-slate-700 disabled:opacity-50"
        >
          {loading ? 'Buscando...' : 'Buscar'}
        </button>
      </form>

      {result && (
        <p className="mt-4 text-sm text-slate-500">
          Sourcing request #{result.id} — status: {result.status} — {result.products.length} produtos
        </p>
      )}
      {error && <p className="mt-4 text-sm text-red-600">Erro: {error}</p>}

      {result && result.products.length > 0 && (
        <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {result.products.map((product) => (
            <a
              key={product.id}
              href={withProductParam(product.url, product.id)}
              target="_blank"
              rel="noreferrer"
              className="block rounded border border-slate-200 p-3 hover:shadow-md transition-shadow"
            >
              {product.main_image && (
                <img
                  src={product.main_image}
                  alt=""
                  className="w-full h-36 object-contain mb-2"
                />
              )}
              <p className="text-sm font-medium line-clamp-2">{stripTags(product.title)}</p>
              <div className="flex items-center gap-2 mt-1">
                <p className="text-xs text-slate-500">{product.supplier.name}</p>
                <span className="text-[10px] uppercase tracking-wide rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">
                  {ROTULO_STATUS_FORNECEDOR[product.supplier.status] ?? product.supplier.status}
                </span>
              </div>
              {product.contact_phone ? (
                <p className="text-xs font-medium text-emerald-700 mt-1">📱 {product.contact_phone}</p>
              ) : (
                product.contact_website && (
                  // Texto puro (não <a>): o card inteiro já é um link pro
                  // produto, aninhar outro <a> aqui seria HTML inválido.
                  <p className="text-xs font-medium text-slate-600 mt-1">🌐 {product.contact_website}</p>
                )
              )}
              <div className="flex items-baseline gap-2 mt-2">
                {product.promotion_price ? (
                  <>
                    <span className="text-sm font-semibold text-red-600">{product.promotion_price}</span>
                    <span className="text-xs text-slate-400 line-through">{product.price}</span>
                  </>
                ) : (
                  <span className="text-sm font-semibold">{product.price}</span>
                )}
              </div>
              {product.moq && <p className="text-xs text-slate-500">{product.moq}</p>}
              {product.review_score && (
                <p className="text-xs text-slate-500">
                  ★ {product.review_score} ({product.review_count})
                </p>
              )}
            </a>
          ))}
        </div>
      )}
    </div>
  )
}

export default App
