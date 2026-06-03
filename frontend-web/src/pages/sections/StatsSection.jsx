import { useQuery } from '@tanstack/react-query'
import { getStats } from '../../api/stats'

function getInitials(name) {
  const parts = name.trim().split(/\s+/)
  return parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase()
}

function StatCard({ label, value, sub }) {
  return (
    <div style={{
      background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0',
      padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '6px',
    }}>
      <span style={{ fontSize: '11px', fontWeight: '500', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        {label}
      </span>
      <span style={{ fontSize: '28px', fontWeight: '600', color: '#1C1C1A', lineHeight: 1 }}>
        {value}
      </span>
      {sub && <span style={{ fontSize: '12px', color: '#B4B2A9' }}>{sub}</span>}
    </div>
  )
}

function ProgressBar({ value, max = 100 }) {
  const pct = max > 0 ? Math.min(100, value) : 0
  const color = pct >= 80 ? '#3B6D11' : pct >= 50 ? '#185FA5' : '#854F0B'
  const bg = pct >= 80 ? '#EAF3DE' : pct >= 50 ? '#E6F1FB' : '#FAEEDA'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div style={{ flex: 1, height: '6px', borderRadius: '3px', background: '#F1EFE8', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', borderRadius: '3px', background: color, transition: 'width 0.4s' }} />
      </div>
      <span style={{ fontSize: '12px', fontWeight: '600', color, background: bg, padding: '1px 6px', borderRadius: '20px', whiteSpace: 'nowrap' }}>
        {pct.toFixed(1)}%
      </span>
    </div>
  )
}

export default function StatsSection() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
    staleTime: 60_000,
  })

  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '500', color: '#1C1C1A' }}>Estadísticas</h2>
        <p style={{ color: '#888780', fontSize: '13px' }}>Cargando...</p>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '500', color: '#1C1C1A' }}>Estadísticas</h2>
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '40px', textAlign: 'center', color: '#888780', fontSize: '13px' }}>
          No se pudieron cargar las estadísticas
        </div>
      </div>
    )
  }

  const mostActiveWorker = data.most_active_worker

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <h2 style={{ fontSize: '20px', fontWeight: '500', color: '#1C1C1A' }}>Estadísticas</h2>

      {/* Métricas globales */}
      <div>
        <h3 style={{ fontSize: '13px', fontWeight: '500', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '12px' }}>
          Métricas globales
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
          <StatCard
            label="Tareas completadas"
            value={data.global_total_tasks_completed.toLocaleString()}
          />
          <StatCard
            label="Tasa de completado"
            value={`${data.global_completion_rate.toFixed(1)}%`}
          />
          <StatCard
            label="Movimientos registrados"
            value={data.global_total_movements.toLocaleString()}
          />
          <StatCard
            label="Día más activo"
            value={data.busiest_day ?? '—'}
          />
        </div>
      </div>

      {/* Tabla de trabajadores */}
      <div>
        <h3 style={{ fontSize: '13px', fontWeight: '500', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '12px' }}>
          Rendimiento por operario
        </h3>

        {data.workers.length === 0 ? (
          <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '40px', textAlign: 'center', color: '#888780', fontSize: '13px' }}>
            No hay operarios activos
          </div>
        ) : (
          <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: '#FAFAFA' }}>
                  {['Operario', 'Completadas', 'Pendientes', 'Tasa de completado'].map((h, i) => (
                    <th
                      key={i}
                      style={{
                        textAlign: 'left', padding: '10px 16px',
                        color: '#888780', fontWeight: '500', fontSize: '11px',
                        textTransform: 'uppercase', letterSpacing: '0.04em',
                        borderBottom: '0.5px solid #E5E4E0', whiteSpace: 'nowrap',
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.workers.map((w) => {
                  const isMostActive = mostActiveWorker === w.name && w.total_completed > 0
                  return (
                    <tr key={String(w.user_id)} style={{ borderTop: '0.5px solid #F1EFE8' }}>
                      {/* Nombre + avatar */}
                      <td style={{ padding: '14px 16px', verticalAlign: 'middle' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <div style={{
                            width: '32px', height: '32px', borderRadius: '50%',
                            background: '#E6F1FB', color: '#185FA5',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: '11px', fontWeight: '600', flexShrink: 0, letterSpacing: '0.03em',
                          }}>
                            {getInitials(w.name)}
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                            <span style={{ fontWeight: '500', color: '#1C1C1A' }}>{w.name}</span>
                            {isMostActive && (
                              <span style={{ background: '#FAEEDA', color: '#854F0B', fontSize: '10px', fontWeight: '600', padding: '1px 6px', borderRadius: '20px', width: 'fit-content' }}>
                                Más activo
                              </span>
                            )}
                          </div>
                        </div>
                      </td>

                      {/* Completadas: total / semana / mes */}
                      <td style={{ padding: '14px 16px', verticalAlign: 'middle' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                          <span style={{ fontWeight: '600', color: '#1C1C1A', fontSize: '14px' }}>
                            {w.total_completed}
                          </span>
                          <span style={{ fontSize: '11px', color: '#888780' }}>
                            Esta semana: <strong style={{ color: '#5F5E5A' }}>{w.completed_this_week}</strong>
                            &nbsp;·&nbsp;
                            Este mes: <strong style={{ color: '#5F5E5A' }}>{w.completed_this_month}</strong>
                          </span>
                        </div>
                      </td>

                      {/* Pendientes */}
                      <td style={{ padding: '14px 16px', verticalAlign: 'middle' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ fontWeight: '500', color: '#1C1C1A' }}>{w.total_pending}</span>
                          {w.pending_old > 0 && (
                            <span style={{
                              background: '#FCEBEB', color: '#A32D2D',
                              fontSize: '10px', fontWeight: '600',
                              padding: '2px 7px', borderRadius: '20px',
                            }}>
                              {w.pending_old} atrasada{w.pending_old !== 1 ? 's' : ''}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Tasa de completado */}
                      <td style={{ padding: '14px 16px', verticalAlign: 'middle', minWidth: '180px' }}>
                        <ProgressBar value={w.completion_rate} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
