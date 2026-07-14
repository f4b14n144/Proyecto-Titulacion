export interface Usuario {
  id: number
  nombre_completo: string
  email_institucional: string
  rol_id: number
  activo: boolean
}

export interface AuthUser {
  id: number
  nombre_completo: string
  email_institucional: string
  rol: 'DIRECTOR_CARRERA' | 'JEFE_AREA' | 'DOCENTE'
  activo: boolean
  titulo?: string | null
  /** Foto de perfil como data URI; null si no ha subido ninguna */
  foto?: string | null
  /** Área que dirige, si es jefe de área */
  area_id?: number | null
  area_nombre?: string | null
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface ApiResponse<T> {
  data: T
  message: string
  success: boolean
}

export interface PeriodoAcademico {
  id: number
  nombre: string
  fecha_inicio: string
  fecha_fin: string
  activo: boolean
}

export interface Area {
  id: number
  nombre: string
}

export interface Rol {
  id: number
  nombre: string
}
