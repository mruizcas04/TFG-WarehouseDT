import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getMovements } from '../../api/movements'
import { getUsers } from '../../api/users'

export default function MovementsSection() {
  const { data: movements, isLoading } = useQuery({ queryKey: ['movements'], queryFn: getMovements })
  const { data: users } = useQuery({ queryKey: ['users'], queryFn: getUsers })

  const [filterType, setFilterType] = useState('')
  const [filterUser, setFilterUser] = useState('')
  const [filterDate, setFilterDate] = useState('')

  const getUserName = (id) => users?.find((u) => u.id === id)?.name || '—'
  const typeLabel = (t) => ({ entrada: 'Entrada', salida: 'Salida', traslado: 'Traslado' })[t] || t
  const typeBadge = (t) => ({ entrada: { bg: '#EAF3DE', color: '#3B6D11' }, salida: { bg: '#FAEEDA', color: '#854F0B' }, traslado: { bg: '#EEEDFE', color: '#534AB7' } })[t] || { bg: '#F1EFE8', color: '#888780' }

  const filtered = useMemo(() => {
    let result = [...(movements || [])].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    if (filterType) result = result.filter(m => m.type === filterType)
    if (filterUser) result = result.filter(m => m.performed_by === filterUser)
    if (filterDate) result = result.filter(m => new Date(m.timestamp).toISOString().slice(0, 10) === filterDate)
    return result
  }, [movements, filterType, filterUser, filterDate])

  const hasFilters = filterType || filterUser || filterDate
  const selectStyle = { border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '7px 12px', fontSize: '12px', color: '#1C1C1A', outline: 'none', background: 'white', cursor: 'pointer' }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '500', color: '#1C1C1A' }}>Historial de movimientos</h2>
        <span style={{ fontSize: '13px', color: '#888780' }}>{filtered.length} de {movements?.length ?? 0} registros</span>
      </div>

      {/* Filtros */}
      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
        <select value={filterType} onChange={(e) => setFilterType(e.target.value)} style={selectStyle}>
          <option value="">Todos los tipos</option>
          <option value="entrada">Entrada</option>
          <option value="salida">Salida</option>
          <option value="traslado">Traslado</option>
        </select>

        <select value={filterUser} onChange={(e) => setFilterUser(e.target.value)} style={selectStyle}>
          <option value="">Todos los empleados</option>
          {users?.map((u) => (
            <option key={u.id} value={u.id}>{u.name}</option>
          ))}
        </select>

        <input
          type="date"
          value={filterDate}
          onChange={(e) => setFilterDate(e.target.value)}
          style={selectStyle}
        />

        {hasFilters && (
          <button
            onClick={() => { setFilterType(''); setFilterUser(''); setFilterDate('') }}
            style={{ background: 'none', border: 'none', fontSize: '12px', color: '#A32D2D', cursor: 'pointer', fontWeight: '500' }}
          >
            Limpiar filtros
          </button>
        )}
      </div>

      {isLoading ? (
        <p style={{ color: '#888780', fontSize: '13px' }}>Cargando...</p>
      ) : filtered.length === 0 ? (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '40px', textAlign: 'center', color: '#888780', fontSize: '13px' }}>
          No hay movimientos con los filtros seleccionados
        </div>
      ) : (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ background: '#FAFAFA' }}>
                {['Tipo', 'Realizado por', 'Origen', 'Destino', 'Fecha y hora'].map((h) => (
                  <th key={h} style={{ textAlign: 'left', padding: '10px 20px', color: '#888780', fontWeight: '500', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '0.5px solid #E5E4E0' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((movement) => {
                const tb = typeBadge(movement.type)
                return (
                  <tr key={movement.id} style={{ borderTop: '0.5px solid #F1EFE8' }}>
                    <td style={{ padding: '12px 20px' }}>
                      <span style={{ background: tb.bg, color: tb.color, padding: '2px 8px', borderRadius: '20px', fontSize: '11px', fontWeight: '500' }}>
                        {typeLabel(movement.type)}
                      </span>
                    </td>
                    <td style={{ padding: '12px 20px', color: '#1C1C1A', fontWeight: '500' }}>{getUserName(movement.performed_by)}</td>
                    <td style={{ padding: '12px 20px', color: '#888780', fontSize: '12px', fontFamily: 'monospace' }}>
                      {movement.origin_location_id ? movement.origin_location_id.slice(0, 8) + '...' : '—'}
                    </td>
                    <td style={{ padding: '12px 20px', color: '#888780', fontSize: '12px', fontFamily: 'monospace' }}>
                      {movement.destination_location_id ? movement.destination_location_id.slice(0, 8) + '...' : '—'}
                    </td>
                    <td style={{ padding: '12px 20px', color: '#888780' }}>
                      {new Date(movement.timestamp).toLocaleString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}