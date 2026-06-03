import { useQuery } from '@tanstack/react-query'
import { getWarehouses } from '../../api/warehouses'
import { getProducts } from '../../api/products'
import { getTasks } from '../../api/tasks'
import { getMovements } from '../../api/movements'
import { getUsers } from '../../api/users'

const StatCard = ({ label, value, sub, accentColor }) => (
  <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '20px 22px' }}>
    <div style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '10px' }}>{label}</div>
    <div style={{ fontSize: '32px', fontWeight: '500', color: '#1C1C1A', lineHeight: 1 }}>{value}</div>
    {sub && (
      <div style={{ fontSize: '12px', color: '#888780', marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
        <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: accentColor, flexShrink: 0, display: 'inline-block' }}></span>
        {sub}
      </div>
    )}
  </div>
)

const statusLabel = (status) => ({ pendiente: 'Pendiente', en_curso: 'En curso', completada: 'Completada' })[status] || status
const statusColor = (status) => ({ pendiente: { bg: '#FAEEDA', color: '#854F0B' }, en_curso: { bg: '#E6F1FB', color: '#185FA5' }, completada: { bg: '#EAF3DE', color: '#3B6D11' } })[status] || { bg: '#F1EFE8', color: '#888780' }
const typeLabel = (type) => ({ entrada: 'Entrada', salida: 'Salida', traslado: 'Traslado' })[type] || type
const typeColor = (type) => ({ entrada: { bg: '#EAF3DE', color: '#3B6D11' }, salida: { bg: '#FAEEDA', color: '#854F0B' }, traslado: { bg: '#EEEDFE', color: '#534AB7' } })[type] || { bg: '#F1EFE8', color: '#888780' }

export default function HomeSection() {
  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const { data: products } = useQuery({ queryKey: ['products'], queryFn: getProducts })
  const { data: tasks } = useQuery({ queryKey: ['tasks'], queryFn: getTasks })
  const { data: movements } = useQuery({ queryKey: ['movements'], queryFn: getMovements })
  const { data: users } = useQuery({ queryKey: ['users'], queryFn: getUsers })

  const warehouse = warehouses?.[0]
  const totalLocations = warehouse?.total_locations ?? 0

  const pendingTasks = tasks?.filter(t => t.status === 'pendiente') || []
  const activeTasks = tasks?.filter(t => t.status === 'en_curso') || []

  const today = new Date().toDateString()
  const todayMovements = movements?.filter(m => new Date(m.timestamp).toDateString() === today) || []
  const todayEntradas = todayMovements.filter(m => m.type === 'entrada').length
  const todaySalidas = todayMovements.filter(m => m.type === 'salida').length

  const getUserName = (id) => users?.find(u => u.id === id)?.name || '—'
  const recentTasks = [...(tasks || [])].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 5)
  const recentMovements = [...(movements || [])].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 5)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
        <StatCard
        label="Ubicaciones"
        value={totalLocations}
         sub={`${warehouse?.name || 'Sin almacén'}`}
        accentColor="#185FA5"
        />
        <StatCard
          label="Productos"
          value={products?.length ?? '—'}
          sub={`${products?.length ?? 0} en catálogo`}
          accentColor="#639922"
        />
        <StatCard
          label="Tareas"
          value={pendingTasks.length}
          sub={`${activeTasks.length} en curso ahora`}
          accentColor="#EF9F27"
        />
        <StatCard
          label="Movimientos hoy"
          value={todayMovements.length}
          sub={`${todayEntradas} entradas · ${todaySalidas} salidas`}
          accentColor="#7F77DD"
        />
      </div>

      {/* Tables */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '12px' }}>

        {/* Tareas recientes */}
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '0.5px solid #E5E4E0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '13px', fontWeight: '500', color: '#1C1C1A' }}>Tareas recientes</span>
            <span style={{ fontSize: '12px', color: '#185FA5', cursor: 'pointer' }}>{tasks?.length ?? 0} total</span>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ background: '#FAFAFA' }}>
                <th style={{ textAlign: 'left', padding: '8px 20px', color: '#888780', fontWeight: '500', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Tipo</th>
                <th style={{ textAlign: 'left', padding: '8px 20px', color: '#888780', fontWeight: '500', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Asignado a</th>
                <th style={{ textAlign: 'left', padding: '8px 20px', color: '#888780', fontWeight: '500', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Estado</th>
              </tr>
            </thead>
            <tbody>
              {recentTasks.length === 0 ? (
                <tr><td colSpan={3} style={{ padding: '20px', color: '#888780', textAlign: 'center' }}>No hay tareas</td></tr>
              ) : recentTasks.map((task) => {
                const sc = statusColor(task.status)
                return (
                  <tr key={task.id} style={{ borderTop: '0.5px solid #F1EFE8' }}>
                    <td style={{ padding: '11px 20px', color: '#1C1C1A', fontWeight: '500' }}>{typeLabel(task.type)}</td>
                    <td style={{ padding: '11px 20px', color: '#5F5E5A' }}>{getUserName(task.assigned_to)}</td>
                    <td style={{ padding: '11px 20px' }}>
                      <span style={{ background: sc.bg, color: sc.color, padding: '2px 8px', borderRadius: '20px', fontSize: '11px', fontWeight: '500' }}>
                        {statusLabel(task.status)}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Movimientos recientes */}
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '0.5px solid #E5E4E0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '13px', fontWeight: '500', color: '#1C1C1A' }}>Últimos movimientos</span>
            <span style={{ fontSize: '12px', color: '#185FA5', cursor: 'pointer' }}>{movements?.length ?? 0} total</span>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ background: '#FAFAFA' }}>
                <th style={{ textAlign: 'left', padding: '8px 20px', color: '#888780', fontWeight: '500', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Tipo</th>
                <th style={{ textAlign: 'left', padding: '8px 20px', color: '#888780', fontWeight: '500', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Realizado por</th>
                <th style={{ textAlign: 'left', padding: '8px 20px', color: '#888780', fontWeight: '500', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Hora</th>
              </tr>
            </thead>
            <tbody>
              {recentMovements.length === 0 ? (
                <tr><td colSpan={3} style={{ padding: '20px', color: '#888780', textAlign: 'center' }}>No hay movimientos</td></tr>
              ) : recentMovements.map((movement) => {
                const tc = typeColor(movement.type)
                return (
                  <tr key={movement.id} style={{ borderTop: '0.5px solid #F1EFE8' }}>
                    <td style={{ padding: '11px 20px' }}>
                      <span style={{ background: tc.bg, color: tc.color, padding: '2px 8px', borderRadius: '20px', fontSize: '11px', fontWeight: '500' }}>
                        {typeLabel(movement.type)}
                      </span>
                    </td>
                    <td style={{ padding: '11px 20px', color: '#5F5E5A' }}>{getUserName(movement.performed_by)}</td>
                    <td style={{ padding: '11px 20px', color: '#888780' }}>
                      {new Date(movement.timestamp).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}