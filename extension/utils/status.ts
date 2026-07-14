export type StatusEstado =
  | 'ocioso'
  | 'navegando_fornecedor'
  | 'validando_atalho'
  | 'navegando_contatos'
  | 'aguardando_botao'
  | 'aguardando_captcha'
  | 'extraindo_contato'
  | 'contato_enviado'
  | 'erro'

export interface StatusAtual {
  estado: StatusEstado
  mensagem: string
  fornecedor?: string
  // URL da home do fornecedor — guardada pra permitir o fallback pro fluxo
  // antigo (clicar na aba "Contatos") se o atalho direto pra contactinfo.html
  // não for válido pra esse fornecedor.
  fornecedorHref?: string
  // Evita retentar o atalho indefinidamente se ele falhar.
  atalhoTentado?: boolean
  productId?: number
  atualizadoEm: string
}

const STORAGE_KEY = 'iris_status'

export async function definirStatus(status: Omit<StatusAtual, 'atualizadoEm'>): Promise<void> {
  const completo: StatusAtual = { ...status, atualizadoEm: new Date().toISOString() }
  await browser.storage.local.set({ [STORAGE_KEY]: completo })
}

export async function lerStatus(): Promise<StatusAtual | null> {
  const dados = await browser.storage.local.get(STORAGE_KEY)
  return (dados[STORAGE_KEY] as StatusAtual) ?? null
}

export function observarStatus(callback: (status: StatusAtual) => void): () => void {
  const listener = (changes: Record<string, Browser.storage.StorageChange>) => {
    if (changes[STORAGE_KEY]) {
      callback(changes[STORAGE_KEY].newValue as StatusAtual)
    }
  }
  browser.storage.onChanged.addListener(listener)
  return () => browser.storage.onChanged.removeListener(listener)
}
