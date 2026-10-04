import { createAuthClient } from '@neondatabase/auth'

const authEnv = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
const authUrl = authEnv?.VITE_NEON_AUTH_URL
export const authClient = authUrl ? createAuthClient(authUrl) : null

function requireAuthClient() {
  if (!authClient) throw new Error('VITE_NEON_AUTH_URL is not configured.')
  return authClient
}

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
  unwrap(requireAuthClient().signUp.email({ email, password, name }))

export const signIn = (email: string, password: string) =>
  unwrap(requireAuthClient().signIn.email({ email, password }))

export const signOut = () => unwrap(requireAuthClient().signOut())

export async function getCurrentUser() {
  const result = await requireAuthClient().getSession()
  if (result.error) throw new Error(getErrorMessage(result.error))
  return result.data?.user ?? null
}

export type AuthSession = { userId: string }
export type AuthStateListener = (session: AuthSession | null) => void
export const AUTH_STATE_EVENT = 'relearn:auth-state'

let currentSession: AuthSession | null = null
const listeners = new Set<AuthStateListener>()

function updateAuthState(session: AuthSession | null) {
  currentSession = session
  listeners.forEach(listener => listener(session))
}

if (typeof window !== 'undefined') {
  window.addEventListener(AUTH_STATE_EVENT, event => {
    updateAuthState((event as CustomEvent<AuthSession | null>).detail)
  })
}

export function announceAuthState(session: AuthSession | null) {
  if (typeof window === 'undefined') {
    updateAuthState(session)
    return
  }
  window.dispatchEvent(new CustomEvent(AUTH_STATE_EVENT, { detail: session }))
}

export function subscribeToAuthState(listener: AuthStateListener) {
  listeners.add(listener)
  listener(currentSession)
  return () => {
    listeners.delete(listener)
  }
}

export function journeyTourStorageKey(userId: string) {
  return `relearn.journey-tour.seen:${encodeURIComponent(userId)}`
}
