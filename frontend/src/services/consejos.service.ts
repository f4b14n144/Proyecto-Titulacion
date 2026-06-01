import api from './api'
import type { ApiResponse } from '../types'

export interface Consejo {
  id: number
  periodo_id: number
  fecha_consejo: string
  fecha_limite_informe: string
  fecha_activacion: string | null
  flujo_estado: string
}

export type ConsejoCreate = Omit<Consejo, 'id' | 'flujo_estado'>
export type ConsejoUpdate = Partial<ConsejoCreate & { flujo_estado: string }>

export const consejosService = {
  async listar(periodo_id?: number): Promise<Consejo[]> {
    const params = periodo_id !== undefined ? { periodo_id } : {}
    const { data } = await api.get<ApiResponse<Consejo[]>>('/consejos/', { params })
    return data.data
  },

  async crear(payload: ConsejoCreate): Promise<Consejo> {
    const { data } = await api.post<ApiResponse<Consejo>>('/consejos/', payload)
    return data.data
  },

  async actualizar(id: number, payload: ConsejoUpdate): Promise<Consejo> {
    const { data } = await api.put<ApiResponse<Consejo>>(`/consejos/${id}`, payload)
    return data.data
  },

  async eliminar(id: number): Promise<void> {
    await api.delete(`/consejos/${id}`)
  },
}
