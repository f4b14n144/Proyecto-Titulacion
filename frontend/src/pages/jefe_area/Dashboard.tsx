import { useAuth } from '../../hooks/useAuth'

export default function JefeDashboard() {
  const { user } = useAuth()

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">
        Bienvenido, {user?.nombre_completo}
      </h1>
      <p className="text-gray-500 text-sm mb-6">Panel del Jefe de Área</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <InformeCard numero={2} titulo="Revisión AVAC" estado="Pendiente" />
        <InformeCard numero={3} titulo="Visitas Áulicas + Interciclo" estado="Pendiente" />
        <InformeCard numero={4} titulo="Análisis Final" estado="Pendiente" />
      </div>
    </div>
  )
}

function InformeCard({ numero, titulo, estado }: { numero: number; titulo: string; estado: string }) {
  return (
    <div className="bg-white rounded-xl border p-5">
      <div className="flex items-center gap-3 mb-2">
        <span className="bg-ups-blue text-white text-sm font-bold w-8 h-8 rounded-full flex items-center justify-center">
          {numero}
        </span>
        <span className="font-semibold text-gray-800">{titulo}</span>
      </div>
      <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded">{estado}</span>
    </div>
  )
}
