import { useState, useEffect } from 'react'
import { obtenerGraficoUrl } from '../services/informes.service'

interface Props {
  informeId: number
  nombre: string
  alt: string
}

/**
 * Muestra un gráfico del informe. Se descarga como blob porque un <img src>
 * normal no envía el header Authorization.
 */
export default function GraficoInforme({ informeId, nombre, alt }: Props) {
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelado = false

    obtenerGraficoUrl(informeId, nombre)
      .then((u) => {
        if (cancelado) { URL.revokeObjectURL(u); return }
        objectUrl = u
        setUrl(u)
      })
      .catch(() => { if (!cancelado) setError(true) })

    return () => {
      cancelado = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [informeId, nombre])

  if (error) return null
  if (!url) {
    return <div className="h-40 bg-gray-50 rounded animate-pulse" aria-hidden />
  }
  return <img src={url} alt={alt} className="max-w-full mx-auto" />
}
