import { createInternalNeonAuth } from '@neondatabase/auth'

export type AuthenticatedUser = {
  id: number
  name: string
  email: string
  role: 'student' | 'teacher' | 'admin'
}

const authEnv = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
const authUrl = authEnv?.VITE_NEON_AUTH_URL
const backend = authEnv?.VITE_API_URL || 'http://localhost:8000/api'
const auth = authUrl ? createInternalNeonAuth(authUrl) : null

function getAuth() {
  if (!auth) throw new Error('Neon Auth is not configured. Set VITE_NEON_AUTH_URL in the frontend environment.')
  return auth
}

function throwAuthError(result: { error?: { message?: string } | null }) {
  if (result.error) throw new Error(result.error.message || 'Authentication failed.')
}

export async function signUp(email: string, password: string, name: string) {
  const result = await getAuth().adapter.signUp.email({ email, password, name })
  throwAuthError(result)
  return result.data
}

export async function signIn(email: string, password: string) {
  const result = await getAuth().adapter.signIn.email({ email, password })
  throwAuthError(result)
  return result.data
}

export async function signOut() {
  const result = await getAuth().adapter.signOut()
  throwAuthError(result)
  return true
}

export async function getAccessToken() {
  return auth?.getJWTToken() ?? null
}

export async function getCurrentUser(): Promise<AuthenticatedUser | null> {
  if (!auth) return null
  const session = await auth.adapter.getSession()
  throwAuthError(session)
  if (!session.data?.session) return null

  const token = await auth.getJWTToken()
  if (!token) return null
  let response: Response
  try {
    response = await fetch(`${backend}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
  } catch (cause) {
    if (cause instanceof TypeError) {
      throw new Error(
        `Your Neon sign-in succeeded, but the Re:Learn API could not be reached at ${backend}. Start the FastAPI backend or set VITE_API_URL to the deployed API URL.`,
      )
    }
    throw cause
  }
  if (!response.ok) {
    const message = (await response.json().catch(() => null))?.detail
    throw new Error(message || 'Unable to verify the authenticated session.')
  }
  return response.json()
}

export function journeyTourStorageKey(userId: string) {
  return `relearn.journey-tour.seen:${encodeURIComponent(userId)}`
}
