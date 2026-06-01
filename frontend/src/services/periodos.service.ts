import api from './api'
import type { PeriodoAcademico, ApiResponse } from '../types'

export const periodosService = {
  async listar(activo?: boolean): Promise<PeriodoAcademico[]> {
    const params = activo !== undefined ? { activo } : {}
    const { data } = await api.get<ApiResponse<PeriodoAcademico[]>>('/periodos/', { params })
    return data.data
  },

  async crear(payload: Omit<PeriodoAcademico, 'id'>): Promise<PeriodoAcademico> {
    const { data } = await api.post<ApiResponse<PeriodoAcademico>>('/periodos/', payload)
    return data.data
  },

  async actualizar(id: number, payload: Partial<Omit<PeriodoAcademico, 'id'>>): Promise<PeriodoAcademico> {
    const { data } = await api.put<ApiResponse<PeriodoAcademico>>(`/periodos/${id}`, payload)
    return data.data
  },

  async eliminar(id: number): Promise<void> {
    await api.delete(`/periodos/${id}`)
  },
}
