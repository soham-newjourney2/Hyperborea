// P15 admin session: JWT in sessionStorage (per tab; window.open copies it to the report tab). RBAC-ready role.
const KEY = 'hyperborea.token'
const ROLE = 'hyperborea.role'

export function getToken(): string | null {
  try {
    return sessionStorage.getItem(KEY)
  } catch {
    return null
  }
}

export function getRole(): string | null {
  try {
    return sessionStorage.getItem(ROLE)
  } catch {
    return null
  }
}

export function setSession(token: string, role: string) {
  try {
    sessionStorage.setItem(KEY, token)
    sessionStorage.setItem(ROLE, role)
  } catch {
    /* storage blocked: session lasts for this page only */
  }
  memToken = token
}

export function clearSession() {
  try {
    sessionStorage.removeItem(KEY)
    sessionStorage.removeItem(ROLE)
  } catch {
    /* ignore */
  }
  memToken = null
}

let memToken: string | null = null
export const currentToken = () => getToken() ?? memToken

export class AuthError extends Error {
  constructor(msg = 'Login required') {
    super(msg)
    this.name = 'AuthError'
  }
}

export const AUTH_EVENT = 'hyperborea:auth-required'
