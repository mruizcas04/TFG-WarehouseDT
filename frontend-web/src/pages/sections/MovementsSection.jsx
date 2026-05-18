import { useState, useMemo, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getMovements } from '../../api/movements'
import { getUsers } from '../../api/users'
import { getProducts } from '../../api/products'
import { getWarehouses, getWarehouseFull, flattenLocations } from '../../api/warehouses'

const TYPE_CFG = {
  entrada:  { bg: '#EAF3DE', color: '#3B6D11', label: 'Entrada'  },
  salida:   { bg: '#FAEEDA', color: '#854F0B', label: 'Salida'   },
  traslado: { bg: '#EEEDFE', color: '#534AB7', label: 'Traslado' },
}

function TypeIcon({ type }) {
  const cfg = TYPE_CFG[type] || { bg: '#F1EFE8', color: '#888780' }
  return (
    <div style={{ width: 32, height: 32, borderRadius: '50%', background: cfg.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
      {type === 'entrada' && (
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M7 2v8M3.5 7l3.5 3.5 3.5-3.5" stroke={cfg.color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      )}
      {type === 'salida' && (
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M7 12V4M3.5 7L7 3.5 10.5 7" stroke={cfg.color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      )}
      {type === 'traslado' && (
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M2 7h10M8.5 4.5 11 7l-2.5 2.5M5.5 4.5 3 7l2.5 2.5" stroke={cfg.color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      )}
    </div>
  )
}

function compact(loc) {
  if (!loc) return null
  return `P${loc.aisle_number}·E${loc.shelf_number}·B${loc.level_number}·H${loc.position_number}`
}

function LocationLine({ movement, allLocations }) {
  const origin = allLocations.find(l => l.id === movement.origin_location_id)
  const dest   = allLocations.find(l => l.id === movement.destination_location_id)
  const qty    = movement.quantity

  const wrap = { display: 'flex', alignItems: 'center', gap: '6px', marginTop: '3px' }
  const txt  = { fontSize: '11px', color: '#888780' }

  if (movement.type === 'entrada') {
    return dest ? <div style={wrap}><span style={txt}>→ {compact(dest)}{qty ? ` · ${qty} ud.` : ''}</span></div> : null
  }
  if (movement.type === 'salida') {
    return origin ? <div style={wrap}><span style={txt}>← {compact(origin)}{qty ? ` · ${qty} ud.` : ''}</span></div> : null
  }
  if (movement.type === 'traslado') {
    const o = compact(origin)
    const d = compact(dest)
    return (o || d) ? <div style={wrap}><span style={txt}>{o || '—'} → {d || '—'}</span></div> : null
  }
  return null
}

function inRange(ts, range) {
  const d = new Date(ts)
  const now = new Date()
  if (range === '7d')   { const c = new Date(now); c.setDate(c.getDate() - 7);  return d >= c }
  if (range === '30d')  { const c = new Date(now); c.setDate(c.getDate() - 30); return d >= c }
  if (range === 'month') return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth()
  return true
}

export default function MovementsSection() {
  const { data: movements, isLoading } = useQuery({ queryKey: ['movements'], queryFn: getMovements })
  const { data: users }      = useQuery({ queryKey: ['users'],      queryFn: getUsers      })
  const { data: products }   = useQuery({ queryKey: ['products'],   queryFn: getProducts   })
  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const [allLocations, setAllLocations] = useState([])

  const [search,     setSearch]     = useState('')
  const [filterType, setFilterType] = useState('')
  const [filterUser, setFilterUser] = useState('')
  const [filterDate, setFilterDate] = useState('30d')
  const [visibleCount, setVisibleCount] = useState(10)

  useEffect(() => {
    if (!warehouses?.length) return
    Promise.all(warehouses.map(w => getWarehouseFull(w.id))).then(full => {
      setAllLocations(full.flatMap(flattenLocations))
    })
  }, [warehouses])

  useEffect(() => { setVisibleCount(10) }, [search, filterType, filterUser, filterDate])

  const getUserName    = id => users?.find(u => u.id === id)?.name    || '—'
  const getProductName = id => products?.find(p => p.id === id)?.name || '—'

  const uniqueUsers = useMemo(() => {
    if (!movements) return []
    const ids = [...new Set(movements.map(m => m.performed_by).filter(Boolean))]
    return ids.map(id => ({ id, name: users?.find(u => u.id === id)?.name || id }))
  }, [movements, users])

  const metrics = useMemo(() => {
    const all = movements || []
    return {
      total:     all.length,
      entradas:  all.filter(m => m.type === 'entrada').length,
      salidas:   all.filter(m => m.type === 'salida').length,
      traslados: all.filter(m => m.type === 'traslado').length,
    }
  }, [movements])

  const filtered = useMemo(() => {
    let list = [...(movements || [])].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    if (filterType) list = list.filter(m => m.type === filterType)
    if (filterUser) list = list.filter(m => m.performed_by === filterUser)
    list = list.filter(m => inRange(m.timestamp, filterDate))
    if (search) {
      const q = search.toLowerCase()
      list = list.filter(m =>
        getProductName(m.product_id).toLowerCase().includes(q) ||
        getUserName(m.performed_by).toLowerCase().includes(q)
      )
    }
    return list
  }, [movements, filterType, filterUser, filterDate, search, users, products])

  const displayed = filtered.slice(0, visibleCount)

  const fmtDate = ts => {
    const d = new Date(ts)
    return `${d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' })} · ${d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}`
  }

  const selectStyle = { border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '7px 10px', fontSize: '12px', color: '#1C1C1A', outline: 'none', background: 'white', cursor: 'pointer' }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <h2 style={{ fontSize: '20px', fontWeight: '500', color: '#1C1C1A', margin: 0 }}>Historial de movimientos</h2>

      {/* Métricas */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
        {[
          { label: 'Total movimientos', value: metrics.total,     bg: '#F8F8F6', numColor: '#1C1C1A', lblColor: '#888780' },
          { label: 'Entradas',          value: metrics.entradas,  bg: '#EAF3DE', numColor: '#3B6D11', lblColor: '#3B6D11' },
          { label: 'Salidas',           value: metrics.salidas,   bg: '#FAEEDA', numColor: '#854F0B', lblColor: '#854F0B' },
          { label: 'Traslados',         value: metrics.traslados, bg: '#EEEDFE', numColor: '#534AB7', lblColor: '#534AB7' },
        ].map(m => (
          <div key={m.label} style={{ background: m.bg, borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '18px 20px' }}>
            <div style={{ fontSize: '30px', fontWeight: '600', color: m.numColor, lineHeight: 1 }}>
              {isLoading ? '—' : m.value}
            </div>
            <div style={{ fontSize: '12px', color: m.lblColor, marginTop: '6px' }}>{m.label}</div>
          </div>
        ))}
      </div>

      {/* Filtros */}
      <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '10px 14px', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
        <input
          type="text"
          placeholder="Buscar producto, operario..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ flex: 1, minWidth: '160px', border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '7px 10px', fontSize: '12px', color: '#1C1C1A', outline: 'none' }}
        />
        <select value={filterType} onChange={e => setFilterType(e.target.value)} style={selectStyle}>
          <option value="">Todos</option>
          <option value="entrada">Entrada</option>
          <option value="salida">Salida</option>
          <option value="traslado">Traslado</option>
        </select>
        <select value={filterUser} onChange={e => setFilterUser(e.target.value)} style={selectStyle}>
          <option value="">Todos los operarios</option>
          {uniqueUsers.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
        </select>
        <select value={filterDate} onChange={e => setFilterDate(e.target.value)} style={selectStyle}>
          <option value="7d">Últimos 7 días</option>
          <option value="30d">Últimos 30 días</option>
          <option value="month">Este mes</option>
          <option value="all">Todo</option>
        </select>
      </div>

      {/* Lista */}
      {isLoading ? (
        <p style={{ color: '#888780', fontSize: '13px' }}>Cargando...</p>
      ) : filtered.length === 0 ? (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '40px', textAlign: 'center', color: '#888780', fontSize: '13px' }}>
          No hay movimientos con los filtros seleccionados
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', overflow: 'hidden' }}>
            {displayed.map((m, i) => {
              const cfg = TYPE_CFG[m.type] || { bg: '#F1EFE8', color: '#888780', label: m.type }
              return (
                <div
                  key={m.id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '40px auto 1fr auto auto auto',
                    alignItems: 'center',
                    gap: '14px',
                    padding: '14px 20px',
                    borderTop: i === 0 ? 'none' : '0.5px solid #F1EFE8',
                  }}
                >
                  <TypeIcon type={m.type} />

                  <span style={{ background: cfg.bg, color: cfg.color, padding: '2px 8px', borderRadius: '20px', fontSize: '11px', fontWeight: '500', whiteSpace: 'nowrap' }}>
                    {cfg.label}
                  </span>

                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: '13px', fontWeight: '500', color: '#1C1C1A' }}>
                      {m.product_id ? getProductName(m.product_id) : '—'}
                    </div>
                    <LocationLine movement={m} allLocations={allLocations} />
                  </div>

                  <span style={{ fontSize: '13px', color: '#5F5E5A', whiteSpace: 'nowrap' }}>
                    {getUserName(m.performed_by)}
                  </span>

                  <span style={{ fontSize: '12px', color: '#888780', whiteSpace: 'nowrap' }}>
                    {fmtDate(m.timestamp)}
                  </span>

                  <a
                    href="#"
                    onClick={e => e.preventDefault()}
                    style={{ fontSize: '12px', color: '#185FA5', whiteSpace: 'nowrap', textDecoration: 'none', fontWeight: '500' }}
                  >
                    Ver tarea
                  </a>
                </div>
              )
            })}
          </div>

          {visibleCount < filtered.length && (
            <div style={{ textAlign: 'center' }}>
              <button
                onClick={() => setVisibleCount(v => v + 10)}
                style={{ background: 'white', color: '#5F5E5A', border: '0.5px solid #D3D1C7', padding: '9px 24px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer', fontWeight: '500' }}
              >
                Ver más movimientos
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
