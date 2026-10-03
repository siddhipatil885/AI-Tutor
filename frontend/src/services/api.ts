const base = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${base}${path}`)
  if (!response.ok) {
    throw new Error((await response.json().catch(() => null))?.detail || 'Backend request failed')
  }
  return response.json()
}

export const getBackendHealth = () => get<{ status: string }>('/health')
export const getDatabaseHealth = () => get<{ status: string }>('/health/db')
