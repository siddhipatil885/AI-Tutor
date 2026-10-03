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
  if (typeof window === 'undefined') { updateAuthState(session); return }
  window.dispatchEvent(new CustomEvent(AUTH_STATE_EVENT, { detail: session }))
}

export function subscribeToAuthState(listener: AuthStateListener) {
  listeners.add(listener)
  listener(currentSession)
  return () => { listeners.delete(listener) }
}

export function journeyTourStorageKey(userId: string) {
  return `relearn.journey-tour.seen:${encodeURIComponent(userId)}`
}