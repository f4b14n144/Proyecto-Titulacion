import { useState, useEffect } from 'react'
import api from '../../services/api'
import type { Area, ApiResponse } from '../../types'

interface Usuario { id: number; nombre_completo: string; email_institucional: string; rol_id: number }
interface Asignatura { id: number; area_id: number; nombre: string; codigo: string; activa: boolean }
interface PeriodoAcademico { id: number; nombre: string; activo: boolean }
interface Jefatura { id: number; usuario_id: number; area_id: number; periodo_id: number }
interface Asignacion { id: number; usuario_id: number; asignatura_id: number; periodo_id: number; grupo: string }

type Tab = 'jefaturas' | 'docentes'

export default function Asignaciones() {
  const [tab, setTab] = useState<Tab>('jefaturas')
  const [periodos, setPeriodos] = useState<PeriodoAcademico[]>([])
  const [areas, setAreas] = useState<Area[]>([])
  const [asignaturas, setAsignaturas] = useState<Asignatura[]>([])
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [jefaturas, setJefaturas] = useState<Jefatura[]>([])
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [filtroPeriodo, setFiltroPeriodo] = useState('')
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  // Formulario jefatura
  const [fJef, setFJef] = useState({ usuario_id: '', area_id: '', periodo_id: '' })
  const [errJef, setErrJef] = useState('')
  const [guardandoJef, setGuardandoJef] = useState(false)

  // Formulario asignación
  const [fAsig, setFAsig] = useState({ usuario_id: '', asignatura_id: '', periodo_id: '', grupo: '' })
  const [errAsig, setErrAsig] = useState('')
  const [guardandoAsig, setGuardandoAsig] = useState(false)

  const cargarBase = async () => {
    const [pRes, aRes, asRes, uRes] = await Promise.all([
      api.get<ApiResponse<PeriodoAcademico[]>>('/periodos/'),
      api.get<ApiResponse<Area[]>>('/areas/'),
      // Todas (incluidas inactivas) para poder mostrar el nombre en el histórico;
      // el selector del formulario filtra solo las activas.
      api.get<ApiResponse<Asignatura[]>>('/asignaturas/', { params: { incluir_inactivas: true } }),
      api.get<ApiResponse<Usuario[]>>('/usuarios/'),
    ])
    setPeriodos(pRes.data.data)
    setAreas(aRes.data.data)
    setAsignaturas(asRes.data.data)
    setUsuarios(uRes.data.data)
    // Seleccionar el período activo por defecto
    const activo = pRes.data.data.find((p) => p.activo)
    if (activo && !filtroPeriodo) setFiltroPeriodo(activo.id.toString())
  }

  const cargarAsignaciones = async () => {
    if (!filtroPeriodo) return
    const params = { periodo_id: filtroPeriodo }
    const [jRes, asigRes] = await Promise.all([
      api.get<ApiResponse<Jefatura[]>>('/jefaturas/', { params }),
      api.get<ApiResponse<Asignacion[]>>('/asignaciones/', { params }),
    ])
    setJefaturas(jRes.data.data)
    setAsignaciones(asigRes.data.data)
  }

  useEffect(() => {
    setCargando(true)
    setError('')
    cargarBase()
      .then(() => cargarAsignaciones())
      .catch(() => setError('Error al cargar datos.'))
      .finally(() => setCargando(false))
  }, [])

  useEffect(() => {
    if (filtroPeriodo) cargarAsignaciones()
  }, [filtroPeriodo])

  const nombreUsuario = (id: number) => usuarios.find((u) => u.id === id)?.nombre_completo ?? `#${id}`
  const nombreArea = (id: number) => areas.find((a) => a.id === id)?.nombre ?? `#${id}`
  const nombreAsignatura = (id: number) => {
    const a = asignaturas.find((a) => a.id === id)
    return a ? `${a.codigo} — ${a.nombre}` : `#${id}`
  }

  const asignarJefatura = async () => {
    const periodoEfectivo = fJef.periodo_id || filtroPeriodo
    if (!fJef.usuario_id || !fJef.area_id || !periodoEfectivo) {
      setErrJef('Todos los campos son obligatorios.')
      return
    }
    setGuardandoJef(true)
    setErrJef('')
    try {
      await api.post('/jefaturas/', {
        usuario_id: Number(fJef.usuario_id),
        area_id: Number(fJef.area_id),
        periodo_id: Number(periodoEfectivo),
      })
      setFJef({ usuario_id: '', area_id: '', periodo_id: filtroPeriodo })
      await cargarAsignaciones()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErrJef(msg ?? 'Error al asignar jefatura.')
    } finally {
      setGuardandoJef(false)
    }
  }

  const eliminarJefatura = async (id: number) => {
    if (!confirm('¿Eliminar esta jefatura?')) return
    try { await api.delete(`/jefaturas/${id}`); await cargarAsignaciones() }
    catch { alert('No se pudo eliminar.') }
  }

  const [copiando, setCopiando] = useState(false)

  const copiarDePeriodo = async () => {
    if (!filtroPeriodo) { alert('Selecciona primero el período destino (arriba a la derecha).'); return }
    const destino = Number(filtroPeriodo)
    const otros = periodos.filter((p) => p.id !== destino)
    if (otros.length === 0) { alert('No hay otro período del cual copiar.'); return }

    // Sugerir el período distinto más reciente como origen
    const lista = otros.map((p) => `${p.id}: ${p.nombre}`).join('\n')
    const resp = prompt(
      `Traer asignaciones y jefaturas AL período seleccionado.\n\n` +
      `Escribe el ID del período de ORIGEN:\n${lista}`,
      String(otros[0].id),
    )
    if (!resp) return
    const origen = Number(resp)
    if (!otros.some((p) => p.id === origen)) { alert('ID de período no válido.'); return }

    setCopiando(true)
    try {
      const { data } = await api.post<ApiResponse<{ asignaciones: number; jefaturas: number }>>(
        '/asignaciones/copiar-periodo',
        { periodo_origen: origen, periodo_destino: destino },
      )
      await cargarAsignaciones()
      alert(data.message)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(msg ?? 'No se pudo copiar del período anterior.')
    } finally {
      setCopiando(false)
    }
  }

  const crearAsignacion = async () => {
    const periodoEfectivo = fAsig.periodo_id || filtroPeriodo
    if (!fAsig.usuario_id || !fAsig.asignatura_id || !periodoEfectivo || !fAsig.grupo.trim()) {
      setErrAsig('Todos los campos son obligatorios.')
      return
    }
    setGuardandoAsig(true)
    setErrAsig('')
    try {
      await api.post('/asignaciones/', {
        usuario_id: Number(fAsig.usuario_id),
        asignatura_id: Number(fAsig.asignatura_id),
        periodo_id: Number(periodoEfectivo),
        grupo: fAsig.grupo.trim(),
      })
      setFAsig({ usuario_id: '', asignatura_id: '', periodo_id: filtroPeriodo, grupo: '' })
      await cargarAsignaciones()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErrAsig(msg ?? 'Error al crear asignación.')
    } finally {
      setGuardandoAsig(false)
    }
  }

  const eliminarAsignacion = async (id: number) => {
    if (!confirm('¿Eliminar esta asignación?')) return
    try { await api.delete(`/asignaciones/${id}`); await cargarAsignaciones() }
    catch { alert('No se pudo eliminar.') }
  }

  const tabClass = (t: Tab) =>
    `px-4 py-2 text-sm font-medium border-b-2 transition ${
      tab === t ? 'border-ups-blue text-ups-blue' : 'border-transparent text-gray-500 hover:text-gray-700'
    }`

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Asignaciones del Período</h1>
          <p className="text-sm text-gray-500 mt-0.5">Jefaturas de área y asignaciones docente-asignatura</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={copiarDePeriodo}
            disabled={copiando}
            className="border border-ups-blue text-ups-blue px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-ups-blue hover:text-white transition disabled:opacity-60"
            title="Copia las asignaciones y jefaturas de otro período al período seleccionado"
          >
            {copiando ? 'Copiando...' : '↧ Traer de otro período'}
          </button>
          <label className="text-sm text-gray-600">Período:</label>
          <select
            value={filtroPeriodo}
            onChange={(e) => setFiltroPeriodo(e.target.value)}
            className="border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue"
          >
            <option value="">Seleccionar</option>
            {periodos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
          </select>
        </div>
      </div>

      {error && <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}

      {/* Tabs */}
      <div className="flex border-b mb-6">
        <button className={tabClass('jefaturas')} onClick={() => setTab('jefaturas')}>Jefaturas de Área</button>
        <button className={tabClass('docentes')} onClick={() => setTab('docentes')}>Asignaciones Docente</button>
      </div>

      {cargando ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ups-blue" />
        </div>
      ) : tab === 'jefaturas' ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Formulario */}
          <div className="bg-white rounded-xl border p-5">
            <h2 className="font-semibold text-gray-700 mb-1">Asignar jefe de área</h2>
            <p className="text-xs text-gray-500 mb-4">
              Un área puede tener hasta <strong>2 jefes</strong> (las áreas grandes lo
              necesitan). Para asignar el segundo, vuelve a elegir la misma área con otro docente.
            </p>
            <div className="flex flex-col gap-3">
              <select value={fJef.periodo_id || filtroPeriodo}
                onChange={(e) => setFJef({ ...fJef, periodo_id: e.target.value })}
                className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-ups-blue focus:outline-none">
                <option value="">Período</option>
                {periodos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
              </select>
              <select value={fJef.area_id}
                onChange={(e) => setFJef({ ...fJef, area_id: e.target.value })}
                className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-ups-blue focus:outline-none">
                <option value="">Área</option>
                {areas.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
              </select>
              <select value={fJef.usuario_id}
                onChange={(e) => setFJef({ ...fJef, usuario_id: e.target.value })}
                className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-ups-blue focus:outline-none">
                <option value="">Docente</option>
                {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre_completo}</option>)}
              </select>
              {errJef && <p className="text-sm text-red-600">{errJef}</p>}
              <button onClick={asignarJefatura} disabled={guardandoJef}
                className="bg-ups-blue text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-60">
                {guardandoJef ? 'Asignando...' : 'Asignar jefatura'}
              </button>
            </div>
          </div>
          {/* Lista */}
          <div className="bg-white rounded-xl border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Área</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Jefe</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {jefaturas.length === 0
                  ? <tr><td colSpan={3} className="text-center text-gray-400 text-sm py-8">Sin jefaturas asignadas</td></tr>
                  : jefaturas.filter((j) => !filtroPeriodo || j.periodo_id === Number(filtroPeriodo)).map((j) => (
                    <tr key={j.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-800">{nombreArea(j.area_id)}</td>
                      <td className="px-4 py-3 text-gray-600">{nombreUsuario(j.usuario_id)}</td>
                      <td className="px-4 py-3 text-right">
                        <button onClick={() => eliminarJefatura(j.id)} className="text-red-500 hover:underline text-xs">Eliminar</button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Formulario */}
          <div className="bg-white rounded-xl border p-5">
            <h2 className="font-semibold text-gray-700 mb-4">Asignar docente a asignatura</h2>
            <div className="flex flex-col gap-3">
              <select value={fAsig.periodo_id || filtroPeriodo}
                onChange={(e) => setFAsig({ ...fAsig, periodo_id: e.target.value })}
                className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-ups-blue focus:outline-none">
                <option value="">Período</option>
                {periodos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
              </select>
              <select value={fAsig.usuario_id}
                onChange={(e) => setFAsig({ ...fAsig, usuario_id: e.target.value })}
                className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-ups-blue focus:outline-none">
                <option value="">Docente</option>
                {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre_completo}</option>)}
              </select>
              <select value={fAsig.asignatura_id}
                onChange={(e) => setFAsig({ ...fAsig, asignatura_id: e.target.value })}
                className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-ups-blue focus:outline-none">
                <option value="">Asignatura</option>
                {asignaturas.filter((a) => a.activa).map((a) => <option key={a.id} value={a.id}>{a.codigo} — {a.nombre}</option>)}
              </select>
              <input type="text" value={fAsig.grupo}
                onChange={(e) => setFAsig({ ...fAsig, grupo: e.target.value.toUpperCase() })}
                placeholder="Grupo (ej: A1)"
                className="border rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-ups-blue focus:outline-none" />
              {errAsig && <p className="text-sm text-red-600">{errAsig}</p>}
              <button onClick={crearAsignacion} disabled={guardandoAsig}
                className="bg-ups-blue text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-60">
                {guardandoAsig ? 'Asignando...' : 'Crear asignación'}
              </button>
            </div>
          </div>
          {/* Lista */}
          <div className="bg-white rounded-xl border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Docente</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Asignatura</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Grupo</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {asignaciones.length === 0
                  ? <tr><td colSpan={4} className="text-center text-gray-400 text-sm py-8">Sin asignaciones</td></tr>
                  : asignaciones.filter((a) => !filtroPeriodo || a.periodo_id === Number(filtroPeriodo)).map((a) => (
                    <tr key={a.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-800 text-xs">{nombreUsuario(a.usuario_id)}</td>
                      <td className="px-4 py-3 text-gray-600 text-xs">{nombreAsignatura(a.asignatura_id)}</td>
                      <td className="px-4 py-3 font-mono text-gray-600">{a.grupo}</td>
                      <td className="px-4 py-3 text-right">
                        <button onClick={() => eliminarAsignacion(a.id)} className="text-red-500 hover:underline text-xs">Eliminar</button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
