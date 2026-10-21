const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8001'

export function setToken(token: string | null): void {
  if (token) localStorage.setItem('learning-support-token', token)
  else localStorage.removeItem('learning-support-token')
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('learning-support-token')
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    throw new Error(detail?.detail ?? `Error ${response.status}`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function downloadPdf(path: string): Promise<void> {
  const token = localStorage.getItem('learning-support-token')
  const response = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new Error('No se pudo descargar el informe.')
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = 'informe-familiar.pdf'
  link.click()
  URL.revokeObjectURL(url)
}
