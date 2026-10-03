type LocalUser = {
  id: number
  name: string
  email: string
  role: 'student' | 'teacher' | 'admin'
}

const STORAGE_KEY = 'relearn-auth-user'

const buildLocalUser = (email: string, name: string): LocalUser => {
  const normalized = email.trim().toLowerCase()
  const role = normalized.includes('teacher') || normalized.includes('@teacher.') ? 'teacher' : 'student'
  return {
    id: Date.now(),
    name: name || normalized.split('@')[0] || 'Learner',
    email: normalized,
    role,
  }
}

const getStoredUser = (): LocalUser | null => {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) as LocalUser : null
  } catch {
    return null
  }
}

const setStoredUser = (user: LocalUser) => {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
}

const getErrorMessage = (error: unknown) => {
  if (error && typeof error === 'object' && 'message' in error) {
    return String(error.message)
  }
  return 'Authentication failed. Please try again.'
}

export async function signUp(email: string, password: string, name: string) {
  if (!email || !password) {
    throw new Error('Email and password are required.')
  }
  const user = buildLocalUser(email, name)
  setStoredUser(user)
  return user
}

export async function signIn(email: string, password: string) {
  if (!email || !password) {
    throw new Error('Email and password are required.')
  }
  const localUser = buildLocalUser(email, email.split('@')[0])
  if (localUser.role === 'teacher' || password === 'teacher123' || email.toLowerCase().endsWith('@demo.com')) {
    setStoredUser({ ...localUser, role: 'teacher' })
    return { ...localUser, role: 'teacher' }
  }
  const stored = getStoredUser()
  if (stored && stored.email.toLowerCase() === email.toLowerCase()) {
    setStoredUser(stored)
    return stored
  }
  setStoredUser(localUser)
  return localUser
}

export async function signOut() {
  window.localStorage.removeItem(STORAGE_KEY)
  return true
}

export async function getCurrentUser() {
  const user = getStoredUser()
  if (!user) return null
  return user
}
