import api from './api'
import type { TokenResponse, AuthUser, ApiResponse } from '../types'

export const authService = {
  async login(email: string, password: string): Promise<TokenResponse> {
    const { data } = await api.post<TokenResponse>('/auth/login', { email, password })
    return data
  },

  async me(): Promise<AuthUser> {
    const { data } = await api.get<ApiResponse<AuthUser>>('/auth/me')
    return data.data
  },

  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },
}
