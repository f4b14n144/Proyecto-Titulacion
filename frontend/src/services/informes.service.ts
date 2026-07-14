import api from './api'

/** Obtiene el .docx del informe como Blob (para previsualizar o descargar). */
export async function obtenerDocxBlob(informeId: number): Promise<Blob> {
  // Cache-busting: el navegador cacheaba /descargar y mostraba versiones viejas
  const res = await api.get(`/informes/${informeId}/descargar`, {
    responseType: 'blob',
    params: { _t: Date.now() },
    headers: { 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
  })
  return new Blob([res.data], {
    type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  })
}

/**
 * Obtiene un gráfico del informe como object URL para usarlo en un <img>.
 * Un <img src> normal no envía el header Authorization, por eso se baja como blob.
 */
export async function obtenerGraficoUrl(informeId: number, nombre: string): Promise<string> {
  const res = await api.get(`/informes/${informeId}/grafico/${nombre}`, { responseType: 'blob' })
  return URL.createObjectURL(new Blob([res.data], { type: 'image/png' }))
}

/**
 * Descarga el .docx de un informe usando axios (con el token JWT del interceptor).
 * Un <a href> normal no envía el header Authorization, por eso daba 401.
 */
export async function descargarInforme(informeId: number, nombreSugerido?: string): Promise<void> {
  // Mismo cache-busting que la previsualización: sin esto el navegador devolvía
  // el .docx de una versión anterior del informe.
  const res = await api.get(`/informes/${informeId}/descargar`, {
    responseType: 'blob',
    params: { _t: Date.now() },
    headers: { 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
  })

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
