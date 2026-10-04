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
export const signUp = async (email: string, password: string, name: string) => {
  console.log('Mock sign up:', email, name)
  if (typeof window !== 'undefined') window.localStorage.setItem('mock_auth', 'true')
  return { user: { id: 'mock-user-1', email, name } }
}
export const signIn = async (email: string, password: string) => {
  console.log('Mock sign in:', email)
  if (typeof window !== 'undefined') window.localStorage.setItem('mock_auth', 'true')
  return { user: { id: 'mock-user-1', email } }
}

export const signOut = async () => {
  console.log('Mock sign out')
  if (typeof window !== 'undefined') window.localStorage.removeItem('mock_auth')
  return true
}

export async function getCurrentUser() {
  // Try to simulate a logged-in session based on a flag or local storage, 
  // but for now, just return null so the login screen shows initially.
  // We can return a mock user if they have a 'mock_auth' token in local storage.
  if (typeof window !== 'undefined' && window.localStorage.getItem('mock_auth') === 'true') {
    return { id: 'mock-user-1', email: 'mock@example.com', name: 'Alex Learner' } as any
  }
  return null
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
