import api from './api'
import type { TokenResponse, AuthUser } from '../types'

export const authService = {
  async login(email: string, password: string): Promise<TokenResponse> {
    const { data } = await api.post<TokenResponse>('/auth/login', { email, password })
    return data
  },

  async me(): Promise<AuthUser> {
    // /auth/me devuelve el objeto directo (no envuelto en {data,...}), igual que login
    const { data } = await api.get<AuthUser>('/auth/me')
    return data
  },

  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },
}
