import { useEffect, useRef, useState } from 'react'
import { Camera, Trash2, Save, KeyRound } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { authService } from '../../services/auth.service'
import Avatar from '../../components/Avatar'

/** Mensaje de resultado de una acción (verde si fue bien, rojo si falló). */
function Aviso({ texto, error }: { texto: string; error?: boolean }) {
  if (!texto) return null
  const clases = error
    ? 'text-red-700 bg-red-50 border-red-200'
    : 'text-green-700 bg-green-50 border-green-200'
  return <p className={`text-sm px-3 py-2 rounded-lg border ${clases}`}>{texto}</p>
}

/** El detalle de un error de la API, o un mensaje por defecto. */
function detalle(e: unknown, porDefecto: string): string {
  const m = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof m === 'string') return m
  return porDefecto
}

const TITULOS = ['Ing.', 'Mg.', 'PhD.', 'Lic.', 'Dr.', 'Msc.']

export default function MiCuenta() {
  const { user, refrescar } = useAuth()

  // ─── Datos personales ───
  const [nombre, setNombre] = useState('')
  const [titulo, setTitulo] = useState('')
  const [guardando, setGuardando] = useState(false)
  const [avisoDatos, setAvisoDatos] = useState('')
  const [errorDatos, setErrorDatos] = useState('')

  // ─── Foto ───
  const inputFoto = useRef<HTMLInputElement>(null)
  const [subiendo, setSubiendo] = useState(false)
  const [avisoFoto, setAvisoFoto] = useState('')
  const [errorFoto, setErrorFoto] = useState('')

  // ─── Contraseña ───
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [repite, setRepite] = useState('')
  const [cambiando, setCambiando] = useState(false)
  const [avisoPass, setAvisoPass] = useState('')
  const [errorPass, setErrorPass] = useState('')

  useEffect(() => {
    if (user) {
      setNombre(user.nombre_completo)
      setTitulo(user.titulo ?? '')
    }
  }, [user])

  if (!user) return null

  const guardarDatos = async () => {
    setAvisoDatos(''); setErrorDatos('')
    if (!nombre.trim()) { setErrorDatos('El nombre no puede estar vacío.'); return }
    setGuardando(true)
    try {
      await authService.actualizarPerfil(nombre.trim(), titulo.trim() || null)
      await refrescar()
      setAvisoDatos('Datos guardados.')
    } catch (e) {
      setErrorDatos(detalle(e, 'No se pudieron guardar los datos.'))
    } finally {
      setGuardando(false)
    }
  }

  const elegirFoto = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const archivo = e.target.files?.[0]
    if (!archivo) return
    setAvisoFoto(''); setErrorFoto(''); setSubiendo(true)
    try {
      await authService.subirFoto(archivo)
      await refrescar()
      setAvisoFoto('Foto actualizada.')
    } catch (err) {
      setErrorFoto(detalle(err, 'No se pudo subir la foto.'))
    } finally {
      setSubiendo(false)
      // Sin esto, volver a elegir el MISMO archivo no dispara el onChange
      if (inputFoto.current) inputFoto.current.value = ''
    }
  }

  const quitarFoto = async () => {
    setAvisoFoto(''); setErrorFoto(''); setSubiendo(true)
    try {
      await authService.quitarFoto()
      await refrescar()
      setAvisoFoto('Foto eliminada. Se muestran tus iniciales.')
    } catch (err) {
      setErrorFoto(detalle(err, 'No se pudo quitar la foto.'))
    } finally {
      setSubiendo(false)
    }
  }

  const cambiarPassword = async () => {
    setAvisoPass(''); setErrorPass('')
    if (!actual || !nueva) { setErrorPass('Completa todos los campos.'); return }
    if (nueva.length < 6) { setErrorPass('La nueva contraseña debe tener al menos 6 caracteres.'); return }
    if (nueva !== repite) { setErrorPass('La nueva contraseña y su confirmación no coinciden.'); return }
    setCambiando(true)
    try {
      await authService.cambiarPassword(actual, nueva)
      setActual(''); setNueva(''); setRepite('')
      setAvisoPass('Contraseña actualizada correctamente.')
    } catch (e) {
      setErrorPass(detalle(e, 'No se pudo cambiar la contraseña.'))
    } finally {
      setCambiando(false)
    }
  }

  const campo = 'w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ups-blue'
  const tarjeta = 'bg-white rounded-xl shadow-sm border border-gray-200 p-6'

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Editar mi cuenta</h1>
      <p className="text-sm text-gray-500 mb-6">
        Tus datos personales, tu foto y tu contraseña.
      </p>

      {/* ─── Foto ─── */}
      <section className={`${tarjeta} mb-5`}>
        <h2 className="font-semibold text-gray-800 mb-4">Foto de perfil</h2>
        <div className="flex items-center gap-6">
          <div className="bg-ups-blue rounded-full p-1 shrink-0">
            <Avatar nombre={user.nombre_completo} foto={user.foto} tamano={96} />
          </div>
          <div className="flex-1">
            <div className="flex flex-wrap gap-2 mb-2">
              <button
                onClick={() => inputFoto.current?.click()}
                disabled={subiendo}
                className="inline-flex items-center gap-2 bg-ups-blue text-white px-4 py-2 rounded-lg
                           text-sm font-medium hover:bg-blue-800 disabled:opacity-60"
              >
                <Camera size={16} />
                {subiendo ? 'Subiendo...' : user.foto ? 'Cambiar foto' : 'Subir foto'}
              </button>
              {user.foto && (
                <button
                  onClick={quitarFoto}
                  disabled={subiendo}
                  className="inline-flex items-center gap-2 text-red-600 border border-red-200 px-4 py-2
                             rounded-lg text-sm font-medium hover:bg-red-50 disabled:opacity-60"
                >
                  <Trash2 size={16} /> Quitar
                </button>
              )}
            </div>
            <p className="text-xs text-gray-500">
              JPG o PNG, hasta 5 MB. Se recorta a un cuadrado automáticamente.
            </p>
            <input
              ref={inputFoto}
              type="file"
              accept="image/*"
              onChange={elegirFoto}
              className="hidden"
            />
          </div>
        </div>
        <div className="mt-3">
          <Aviso texto={avisoFoto} />
          <Aviso texto={errorFoto} error />
        </div>
      </section>

      {/* ─── Datos personales ─── */}
      <section className={`${tarjeta} mb-5`}>
        <h2 className="font-semibold text-gray-800 mb-4">Datos personales</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Título</label>
            <input
              list="titulos-academicos"
              value={titulo}
              onChange={(e) => setTitulo(e.target.value)}
              placeholder="Ing."
              className={campo}
            />
            <datalist id="titulos-academicos">
              {TITULOS.map((t) => <option key={t} value={t} />)}
            </datalist>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Nombre completo</label>
            <input value={nombre} onChange={(e) => setNombre(e.target.value)} className={campo} />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Correo institucional</label>
            <input value={user.email_institucional} disabled
              className={`${campo} bg-gray-50 text-gray-500 cursor-not-allowed`} />
            <p className="text-xs text-gray-400 mt-1">Lo asigna la universidad; no se puede cambiar.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Rol</label>
            <input value={user.rol.replace('_', ' ')} disabled
              className={`${campo} bg-gray-50 text-gray-500 cursor-not-allowed`} />
            <p className="text-xs text-gray-400 mt-1">
              {user.area_nombre
                ? `Jefe de Área de ${user.area_nombre}. Lo asigna la Dirección de Carrera.`
                : 'Lo asigna la Dirección de Carrera.'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 mt-5">
          <button
            onClick={guardarDatos}
            disabled={guardando}
            className="inline-flex items-center gap-2 bg-ups-blue text-white px-4 py-2 rounded-lg
                       text-sm font-medium hover:bg-blue-800 disabled:opacity-60"
          >
            <Save size={16} /> {guardando ? 'Guardando...' : 'Guardar cambios'}
          </button>
          <Aviso texto={avisoDatos} />
          <Aviso texto={errorDatos} error />
        </div>
      </section>

      {/* ─── Contraseña ─── */}
      <section className={tarjeta}>
        <h2 className="font-semibold text-gray-800 mb-4">Cambiar contraseña</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Contraseña actual</label>
            <input type="password" value={actual} onChange={(e) => setActual(e.target.value)} className={campo} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nueva contraseña</label>
            <input type="password" value={nueva} onChange={(e) => setNueva(e.target.value)} className={campo} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Confirmar nueva</label>
            <input type="password" value={repite} onChange={(e) => setRepite(e.target.value)} className={campo} />
          </div>
        </div>
        <p className="text-xs text-gray-400 mt-2">Mínimo 6 caracteres.</p>

        <div className="flex items-center gap-3 mt-5">
          <button
            onClick={cambiarPassword}
            disabled={cambiando}
            className="inline-flex items-center gap-2 bg-ups-blue text-white px-4 py-2 rounded-lg
                       text-sm font-medium hover:bg-blue-800 disabled:opacity-60"
          >
            <KeyRound size={16} /> {cambiando ? 'Cambiando...' : 'Cambiar contraseña'}
          </button>
          <Aviso texto={avisoPass} />
          <Aviso texto={errorPass} error />
        </div>
      </section>
    </div>
  )
}
