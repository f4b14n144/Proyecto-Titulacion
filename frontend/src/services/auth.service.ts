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

  /** Edita el nombre y el título del propio usuario. */
  async actualizarPerfil(nombre_completo: string, titulo: string | null): Promise<void> {
    await api.put('/auth/perfil', { nombre_completo, titulo })
  },

  /** Sube la foto de perfil. El backend la recorta y la devuelve como data URI. */
  async subirFoto(archivo: File): Promise<string> {
    const form = new FormData()
    form.append('archivo', archivo)
    const { data } = await api.post('/auth/foto', form)
    return data.data.foto as string
  },

  async quitarFoto(): Promise<void> {
    await api.delete('/auth/foto')
  },

  async cambiarPassword(password_actual: string, password_nueva: string): Promise<void> {
    await api.post('/auth/cambiar-password', { password_actual, password_nueva })
  },

  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },
}
