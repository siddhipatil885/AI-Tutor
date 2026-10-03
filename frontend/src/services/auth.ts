import { createAuthClient } from '@neondatabase/auth'

const authUrl = import.meta.env.VITE_NEON_AUTH_URL

if (!authUrl) {
  throw new Error('VITE_NEON_AUTH_URL is not configured.')
}

export const authClient = createAuthClient(authUrl)

function getErrorMessage(error: unknown) {
  if (error && typeof error === 'object' && 'message' in error) {
    return String(error.message)
  }
  return 'Authentication failed. Please try again.'
}

async function unwrap<T extends { data?: unknown; error?: unknown }>(request: Promise<T>) {
  const result = await request
  if (result.error) throw new Error(getErrorMessage(result.error))
  return result.data
}

export const signUp = (email: string, password: string, name: string) =>
  unwrap(authClient.signUp.email({ email, password, name }))

export const signIn = (email: string, password: string) =>
  unwrap(authClient.signIn.email({ email, password }))

export const signOut = () => unwrap(authClient.signOut())

export async function getCurrentUser() {
  const result = await authClient.getSession()
  if (result.error) throw new Error(getErrorMessage(result.error))
  return result.data?.user ?? null
}
