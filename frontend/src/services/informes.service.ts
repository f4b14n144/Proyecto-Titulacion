import api from './api'

/**
 * Descarga el .docx de un informe usando axios (con el token JWT del interceptor).
 * Un <a href> normal no envía el header Authorization, por eso daba 401.
 */
export async function descargarInforme(informeId: number, nombreSugerido?: string): Promise<void> {
  const res = await api.get(`/informes/${informeId}/descargar`, { responseType: 'blob' })

  // Intentar tomar el nombre del header Content-Disposition
  let filename = nombreSugerido ?? `informe_${informeId}.docx`
  const cd = res.headers['content-disposition'] as string | undefined
  if (cd) {
    const m = cd.match(/filename="?([^"]+)"?/)
    if (m) filename = m[1]
  }

  const blob = new Blob([res.data], {
    type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
}
