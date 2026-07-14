import { useState, useEffect, createContext, useContext } from 'react'
import type { AuthUser } from '../types'
import { authService } from '../services/auth.service'

interface AuthContext {
  user: AuthUser | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  /** Relee /auth/me. Se llama tras editar el perfil para que la barra superior
   *  muestre el nombre y la foto nuevos sin recargar la página. */
  refrescar: () => Promise<void>
}

export const AuthCtx = createContext<AuthContext>({
  user: null,
  loading: true,
  login: async () => {},
  logout: () => {},
  refrescar: async () => {},
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

  const refrescar = async () => {
    setUser(await authService.me())
  }

  return { user, loading, login, logout, refrescar }
}

export function useAuth() {
  return useContext(AuthCtx)
}
