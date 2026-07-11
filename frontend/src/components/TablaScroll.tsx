interface Props {
  children: React.ReactNode
  /** Ancho mínimo de la tabla; por debajo de eso aparece scroll horizontal. */
  anchoMinimo?: string
}

/**
 * Envoltura de tablas anchas.
 *
 * En monitores de baja resolución una tabla de muchas columnas se comprime y
 * parte las celdas en varias líneas. Aquí se le da un ancho mínimo y se deja
 * que la tabla haga scroll horizontal dentro de su tarjeta, en lugar de
 * deformarse. La página nunca hace scroll lateral.
 */
export default function TablaScroll({ children, anchoMinimo = '56rem' }: Props) {
  return (
    <div className="bg-white rounded-xl border overflow-hidden">
      <div className="overflow-x-auto">
        <div style={{ minWidth: anchoMinimo }}>{children}</div>
      </div>
    </div>
  )
}
