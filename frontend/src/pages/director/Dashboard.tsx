import { useAuth } from '../../hooks/useAuth'

export default function DirectorDashboard() {
  const { user } = useAuth()

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">
        Bienvenido, {user?.nombre_completo}
      </h1>
      <p className="text-gray-500 text-sm mb-6">Panel de la Dirección de Carrera</p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Período activo" value="—" />
        <StatCard label="Informes generados" value="0" />
        <StatCard label="Informes pendientes" value="0" />
      </div>

      <div className="mt-8 bg-white rounded-xl border p-6">
        <h2 className="font-semibold text-gray-700 mb-2">Accesos rápidos</h2>
        <p className="text-sm text-gray-400">
          Usa el menú lateral para gestionar períodos, consejos, asignaciones y generar informes.
        </p>
      </div>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-xl border p-5 flex flex-col gap-1">
      <span className="text-3xl font-bold text-ups-blue">{value}</span>
      <span className="text-sm text-gray-500">{label}</span>
    </div>
  )
}
