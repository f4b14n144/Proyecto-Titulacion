import { useState, useEffect, createContext, useContext } from 'react'
import type { AuthUser } from '../types'
import { authService } from '../services/auth.service'

interface AuthContext {
  user: AuthUser | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

export const AuthCtx = createContext<AuthContext>({
  user: null,
  loading: true,
  login: async () => {},
  logout: () => {},
})

export function useAuthProvider(): AuthContext {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      authService
        .me()
        .then(setUser)
        .catch(() => {
          localStorage.clear()
          setUser(null)
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (email: string, password: string) => {
    const tokens = await authService.login(email, password)
    localStorage.setItem('access_token', tokens.access_token)
    localStorage.setItem('refresh_token', tokens.refresh_token)
    const me = await authService.me()
    setUser(me)
  }

  const logout = () => {
    authService.logout()
    setUser(null)
  }

  return { user, loading, login, logout }
}

export function useAuth() {
  return useContext(AuthCtx)
}
