import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getTasks, createTask, deleteTask } from '../../api/tasks'
import { getRecommendation } from '../../api/stats'
import { getMovements } from '../../api/movements'
import { getUsers } from '../../api/users'
import { getProducts } from '../../api/products'
import { getBoxes } from '../../api/boxes'
import { getWarehouses, getWarehouseFull, flattenLocations } from '../../api/warehouses'

const labelStyle = { display: 'block', fontSize: '11px', fontWeight: '500', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }
const inputStyle = { width: '100%', border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '9px 12px', fontSize: '13px', color: '#1C1C1A', outline: 'none', boxSizing: 'border-box' }
const selectStyle = { ...inputStyle, background: 'white' }

function ProductSearch({ products, value, onChange }) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const selected = products?.find(p => p.id === value)
  const filtered = products?.filter(p =>
    p.name.toLowerCase().includes(query.toLowerCase()) ||
    (p.barcode && p.barcode.includes(query))
  ) || []

  useEffect(() => {
    const handleClick = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  if (selected) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '8px 12px', background: 'white' }}>
        <span style={{ fontSize: '13px', color: '#1C1C1A', flex: 1, fontWeight: '500' }}>{selected.name}</span>
        {selected.barcode && <span style={{ fontSize: '11px', color: '#888780' }}>{selected.barcode}</span>}
        <button type="button" onClick={() => onChange('')} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#888780', fontSize: '14px', padding: '0', lineHeight: 1 }}>✕</button>
      </div>
    )
  }

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <div style={{ position: 'relative' }}>
        <input
          type="text"
          placeholder="Busca por nombre o código de barras..."
          value={query}
          onChange={e => { setQuery(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          style={{ ...inputStyle, paddingRight: '90px' }}
        />
        <span style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', fontSize: '10px', color: '#B4B2A9', pointerEvents: 'none' }}>nombre / EAN</span>
      </div>
      {open && filtered.length > 0 && (
        <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100, background: 'white', border: '0.5px solid #D3D1C7', borderRadius: '8px', marginTop: '4px', maxHeight: '200px', overflowY: 'auto', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}>
          {filtered.map(p => (
            <div
              key={p.id}
              onMouseDown={() => { onChange(p.id); setQuery(''); setOpen(false) }}
              style={{ padding: '8px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '0.5px solid #F1EFE8' }}
              onMouseEnter={e => e.currentTarget.style.background = '#F8F8F6'}
              onMouseLeave={e => e.currentTarget.style.background = ''}
            >
              <span style={{ fontSize: '13px', color: '#1C1C1A', fontWeight: '500', flex: 1 }}>{p.name}</span>
              {p.barcode && <span style={{ fontSize: '11px', color: '#888780' }}>{p.barcode}</span>}
            </div>
          ))}
        </div>
      )}
      {open && query && filtered.length === 0 && (
        <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100, background: 'white', border: '0.5px solid #D3D1C7', borderRadius: '8px', marginTop: '4px', padding: '10px 12px', fontSize: '13px', color: '#888780' }}>
          Sin resultados
        </div>
      )}
    </div>
  )
}

function LocationPicker({ allLocations, value, onChange, label }) {
  const shelves = [...new Set(allLocations.map(l => l.aisle_number))].sort((a, b) => a - b)
  const [aisle, setAisle] = useState('')
  const [shelf, setShelf] = useState('')
  const [level, setLevel] = useState('')
  const [pos, setPos] = useState('')

  const shelfNumbers = aisle ? [...new Set(allLocations.filter(l => l.aisle_number === Number(aisle)).map(l => l.shelf_number))].sort((a,b)=>a-b) : []
  const levelNumbers = (aisle && shelf) ? [...new Set(allLocations.filter(l => l.aisle_number === Number(aisle) && l.shelf_number === Number(shelf)).map(l => l.level_number))].sort((a,b)=>a-b) : []
  const posNumbers = (aisle && shelf && level) ? [...new Set(allLocations.filter(l => l.aisle_number === Number(aisle) && l.shelf_number === Number(shelf) && l.level_number === Number(level)).map(l => l.position_number))].sort((a,b)=>a-b) : []

  useEffect(() => {
    if (aisle && shelf && level && pos) {
      const loc = allLocations.find(l =>
        l.aisle_number === Number(aisle) && l.shelf_number === Number(shelf) &&
        l.level_number === Number(level) && l.position_number === Number(pos)
      )
      onChange(loc?.id || '', loc || null)
    } else {
      onChange('', null)
    }
  }, [aisle, shelf, level, pos])

  useEffect(() => {
    if (!value) { setAisle(''); setShelf(''); setLevel(''); setPos(''); return }
    const loc = allLocations.find(l => l.id === value)
    if (loc) {
      setAisle(String(loc.aisle_number))
      setShelf(String(loc.shelf_number))
      setLevel(String(loc.level_number))
      setPos(String(loc.position_number))
    }
  }, [value, allLocations])

  const preview = (aisle && shelf && level && pos) ? `F${aisle} · Est. ${shelf} · Balda ${level} · Hueco ${pos}` : null

  return (
    <div>
      {label && <label style={labelStyle}>{label}</label>}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '8px' }}>
        {[
          { label: 'Fila', value: aisle, options: shelves, onChange: v => { setAisle(v); setShelf(''); setLevel(''); setPos('') }, disabled: false },
          { label: 'Estantería', value: shelf, options: shelfNumbers, onChange: v => { setShelf(v); setLevel(''); setPos('') }, disabled: !aisle },
          { label: 'Balda', value: level, options: levelNumbers, onChange: v => { setLevel(v); setPos('') }, disabled: !shelf },
          { label: 'Hueco', value: pos, options: posNumbers, onChange: v => setPos(v), disabled: !level },
        ].map(col => (
          <div key={col.label}>
            <label style={{ fontSize: '10px', color: '#B4B2A9', marginBottom: '4px', display: 'block' }}>{col.label}</label>
            <select value={col.value} onChange={e => col.onChange(e.target.value)} style={selectStyle} disabled={col.disabled}>
              <option value="">—</option>
              {col.options.map(o => <option key={o} value={o}>{o}</option>)}
            </select>
          </div>
        ))}
      </div>
      {preview && <p style={{ fontSize: '11px', color: '#888780', margin: '4px 0 0' }}>→ {preview}</p>}
    </div>
  )
}


function LocationInventoryInfo({ inventory, products, boxes }) {
  if (!inventory) return <span style={{ fontSize: '12px', color: '#B4B2A9' }}>Vacía</span>

  if (inventory.box_id) {
    const box = boxes?.find(b => b.id === inventory.box_id)
    const qty = inventory.box_current_quantity ?? box?.current_quantity
    const max = inventory.box_max_capacity ?? box?.max_capacity
    const productName = products?.find(p => p.id === box?.product_id)?.name || '—'
    return (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: '#E8EEFF', color: '#2244AA', padding: '3px 8px', borderRadius: '6px', fontSize: '12px', fontWeight: '500' }}>
        <span style={{ width: '7px', height: '7px', borderRadius: '2px', background: '#3366CC', flexShrink: 0 }} />
        {productName} · {qty}/{max} ud.
      </span>
    )
  }

  if (inventory.product_id) {
    const productName = products?.find(p => p.id === inventory.product_id)?.name || '—'
    return (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: '#EAF3DE', color: '#3B6D11', padding: '3px 8px', borderRadius: '6px', fontSize: '12px', fontWeight: '500' }}>
        Producto · {productName} · {inventory.quantity} ud.
      </span>
    )
  }

  return <span style={{ fontSize: '12px', color: '#B4B2A9' }}>Vacía</span>
}

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M1.5 3.5h11M5.5 3.5V2.5a1 1 0 0 1 1-1h1a1 1 0 0 1 1 1v1M2.5 3.5l.75 8a1 1 0 0 0 1 .916h5.5a1 1 0 0 0 1-.916l.75-8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function BoxIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 11 11" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M5.5 1.5L9.5 3.5v4L5.5 9.5l-4-2v-4L5.5 1.5z" stroke="currentColor" strokeWidth="1.1" strokeLinejoin="round"/>
      <path d="M1.5 3.5l4 2 4-2M5.5 5.5v4" stroke="currentColor" strokeWidth="1.1" strokeLinejoin="round"/>
    </svg>
  )
}

function PersonIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="6" cy="4" r="2.2" stroke="currentColor" strokeWidth="1.1"/>
      <path d="M1.5 10.5c0-2.485 2.015-4 4.5-4s4.5 1.515 4.5 4" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round"/>
    </svg>
  )
}

function TypeArrow({ type }) {
  if (type === 'salida') return (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2 8L8 2M8 2H4.5M8 2v3.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
  if (type === 'entrada') return (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 2L2 8M2 8h3.5M2 8V4.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2 5h6M6 3l2 2-2 2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

const twinButtonStyle = {
  background: '#F1EFE8', color: '#185FA5', border: '0.5px solid #D3D1C7',
  borderRadius: '8px', padding: '7px 12px', fontSize: '12px', cursor: 'pointer',
  marginTop: '8px', display: 'inline-flex', alignItems: 'center', gap: '6px',
}

export default function TasksSection({ onRequestLocationSelection }) {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [timeFilter, setTimeFilter] = useState('all') // 'all' | 'month' | 'week' | 'today'
  const [form, setForm] = useState({
    assigned_to: '',
    type: 'entrada',
    product_id: '',
    quantity: '',
    origin_location_id: '',
    destination_location_id: '',
  })
  const [originLocation, setOriginLocation] = useState(null)
  const [allLocations, setAllLocations] = useState([])
  const [formError, setFormError] = useState(null)
  const [quantityError, setQuantityError] = useState(false)

  const [filterType, setFilterType] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [visibleCount, setVisibleCount] = useState(10)
  const [productPopup, setProductPopup] = useState(null)
  const [deleteModal, setDeleteModal] = useState(null)
  const popupRef = useRef(null)

  const updateForm = (patch) => {
    setFormError(null)
    if ('quantity' in patch) setQuantityError(false)
    setForm(prev => ({ ...prev, ...patch }))
  }

  const { data: tasks, isLoading } = useQuery({ queryKey: ['tasks'], queryFn: getTasks })
  const { data: users } = useQuery({ queryKey: ['users'], queryFn: getUsers })
  const { data: products } = useQuery({ queryKey: ['products'], queryFn: getProducts })
  const { data: boxes } = useQuery({ queryKey: ['boxes'], queryFn: getBoxes })
  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const { data: recommendation } = useQuery({
    queryKey: ['recommendation'],
    queryFn: getRecommendation,
    enabled: showForm,
    staleTime: 30_000,
  })
  const { data: movements } = useQuery({ queryKey: ['movements'], queryFn: getMovements })

  useEffect(() => {
    if (!warehouses?.length) return
    Promise.all(warehouses.map(w => getWarehouseFull(w.id))).then(full => {
      setAllLocations(full.flatMap(flattenLocations))
    })
  }, [warehouses])

  useEffect(() => {
    setVisibleCount(10)
  }, [filterType, filterStatus, searchQuery])

  // Preseleccionar el trabajador recomendado cuando se abre el formulario
  useEffect(() => {
    if (showForm && recommendation?.length > 0 && !form.assigned_to) {
      const recommended = recommendation.find(r => r.is_recommended)
      if (recommended) updateForm({ assigned_to: recommended.user_id })
    }
  }, [showForm, recommendation])

  useEffect(() => {
    if (!productPopup) return
    const handleClick = (e) => {
      if (popupRef.current && !popupRef.current.contains(e.target)) setProductPopup(null)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [productPopup])

  const handleOriginChange = (locationId, locationObj) => {
    setOriginLocation(locationObj)
    let patch = { origin_location_id: locationId, product_id: '', quantity: '' }

    const inv = locationObj?.inventory
    if (inv?.box_id) {
      const box = boxes?.find(b => b.id === inv.box_id)
      if (box) patch.product_id = box.product_id
    } else if (inv?.product_id) {
      patch.product_id = inv.product_id
    }
    updateForm(patch)
  }

  const needsOrigin = form.type === 'salida' || form.type === 'traslado'
  const needsDestination = form.type === 'entrada' || form.type === 'traslado'
  const needsQuantity = form.type === 'entrada' || form.type === 'salida' || form.type === 'traslado'

  const originInv = originLocation?.inventory
  const originMaxQty = originInv?.box_id
    ? (originInv.box_current_quantity ?? boxes?.find(b => b.id === originInv.box_id)?.current_quantity)
    : originInv?.product_id
    ? originInv.quantity
    : null

  const quantity = Number(form.quantity) || 0

  const validateDestination = (locationId) => {
    if (form.type === 'entrada') return null
    const loc = allLocations.find(l => l.id === locationId)
    if (!loc) return 'Ubicación no encontrada'
    if (loc.inventory) return 'Esta ubicación ya está ocupada'
    const hasTask = tasks?.some(t =>
      t.status !== 'completada' &&
      (t.destination_location_id === locationId || t.origin_location_id === locationId)
    )
    if (hasTask) return 'Esta ubicación ya tiene una tarea activa asignada'
    return null
  }

  const validateOrigin = (locationId) => {
    const loc = allLocations.find(l => l.id === locationId)
    if (!loc) return 'Ubicación no encontrada'
    const hasTask = tasks?.some(t =>
      t.status !== 'completada' &&
      (t.destination_location_id === locationId || t.origin_location_id === locationId)
    )
    if (hasTask) return 'Esta ubicación ya tiene una tarea activa asignada'
    return null
  }

  const createMutation = useMutation({
    mutationFn: createTask,
    onSuccess: () => {
      queryClient.invalidateQueries(['tasks'])
      setShowForm(false)
      setFormError(null)
      setQuantityError(false)
      setOriginLocation(null)
      setForm({ assigned_to: '', type: 'entrada', product_id: '', quantity: '', origin_location_id: '', destination_location_id: '' })
      queryClient.invalidateQueries(['recommendation'])
    },
    onError: (err) => setFormError(err?.response?.data?.detail || 'Error al crear la tarea'),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteTask,
    onSuccess: () => queryClient.invalidateQueries(['tasks']),
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    if (needsQuantity && (!form.quantity || Number(form.quantity) < 1)) {
      setQuantityError(true)
      return
    }
    createMutation.mutate({
      assigned_to: form.assigned_to,
      type: form.type,
      product_id: form.product_id || null,
      quantity: form.quantity ? Number(form.quantity) : null,
      origin_location_id: needsOrigin ? form.origin_location_id || null : null,
      destination_location_id: needsDestination ? form.destination_location_id || null : null,
    })
  }

  const resetForm = () => { setShowForm(false); setOriginLocation(null); setFormError(null); setQuantityError(false) }

  const statusLabel = s => ({ pendiente: 'Pendiente', en_curso: 'En curso', completada: 'Completada' })[s] || s
  const statusBadge = s => ({ pendiente: { bg: '#FAEEDA', color: '#854F0B' }, en_curso: { bg: '#E6F1FB', color: '#185FA5' }, completada: { bg: '#EAF3DE', color: '#3B6D11' } })[s] || { bg: '#F1EFE8', color: '#888780' }
  const typeLabel = t => ({ entrada: 'Entrada', salida: 'Salida', traslado: 'Traslado' })[t] || t
  const typeBadge = t => ({ entrada: { bg: '#EAF3DE', color: '#3B6D11' }, salida: { bg: '#FAEEDA', color: '#854F0B' }, traslado: { bg: '#EEEDFE', color: '#534AB7' } })[t] || { bg: '#F1EFE8', color: '#888780' }
  const getUserName = id => users?.find(u => u.id === id)?.name || '—'
  const getProductName = id => products?.find(p => p.id === id)?.name || '—'
  const getLocationLabel = id => allLocations.find(l => l.id === id)?.label || '—'
  const getInitials = name => {
    const parts = name.trim().split(/\s+/)
    return parts.length >= 2 ? (parts[0][0] + parts[1][0]).toUpperCase() : name.slice(0, 2).toUpperCase()
  }
  const hexToRgba = (hex, alpha) => {
    if (!hex || hex.length < 7) return `rgba(136,135,128,${alpha})`
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    return `rgba(${r},${g},${b},${alpha})`
  }

  const monthsShort = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
  const formatDate = dateStr => {
    const d = new Date(dateStr)
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    return `${d.getDate()} ${monthsShort[d.getMonth()]} ${d.getFullYear()} · ${hh}:${mm}`
  }

  const handleDeleteTask = (task) => {
    const name = task.product_id ? getProductName(task.product_id) : null
    setDeleteModal({ taskId: task.id, name })
  }

  const handleProductClick = (e, product) => {
    e.stopPropagation()
    const rect = e.currentTarget.getBoundingClientRect()
    const popupWidth = 280
    const rightX = rect.right + 8
    const x = rightX + popupWidth > window.innerWidth ? rect.left - popupWidth - 8 : rightX
    setProductPopup({ product, x, y: rect.top })
  }

  const filteredTasks = tasks?.filter(task => {
    if (filterType !== 'all' && task.type !== filterType) return false
    if (filterStatus !== 'all' && task.status !== filterStatus) return false
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      const productName = task.product_id ? getProductName(task.product_id).toLowerCase() : ''
      const workerName = getUserName(task.assigned_to).toLowerCase()
      if (!productName.includes(q) && !workerName.includes(q)) return false
    }
    return true
  }) || []

  const displayedTasks = filteredTasks.slice(0, visibleCount)

  const pillActive = { background: '#185FA5', color: 'white', border: 'none', padding: '5px 12px', borderRadius: '20px', fontSize: '12px', fontWeight: '500', cursor: 'pointer' }
  const pillInactive = { background: 'white', color: '#5F5E5A', border: '0.5px solid #D3D1C7', padding: '5px 12px', borderRadius: '20px', fontSize: '12px', cursor: 'pointer' }

  const movMetrics = {
    total:     movements?.length ?? 0,
    entradas:  movements?.filter(m => m.type === 'entrada').length  ?? 0,
    salidas:   movements?.filter(m => m.type === 'salida').length   ?? 0,
    traslados: movements?.filter(m => m.type === 'traslado').length ?? 0,
  }

  // ── Filtro de tiempo para métricas (total / mes / semana / hoy) ───────────
  const TIME_FILTERS = [
    { key: 'all',   label: 'Total' },
    { key: 'month', label: 'Este mes' },
    { key: 'week',  label: 'Esta semana' },
    { key: 'today', label: 'Hoy' },
  ]
  const movMetricsFiltered = (() => {
    if (!movements) return { total: 0, entradas: 0, salidas: 0, traslados: 0 }
    const now = new Date()
    let cutoff = null
    if (timeFilter === 'today') {
      cutoff = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    } else if (timeFilter === 'week') {
      const day = now.getDay() // 0 = domingo, 1 = lunes
      const daysToMonday = (day + 6) % 7
      cutoff = new Date(now.getFullYear(), now.getMonth(), now.getDate() - daysToMonday)
    } else if (timeFilter === 'month') {
      cutoff = new Date(now.getFullYear(), now.getMonth(), 1)
    }
    const filtered = cutoff
      ? movements.filter(m => new Date(m.timestamp) >= cutoff)
      : movements
    return {
      total:     filtered.length,
      entradas:  filtered.filter(m => m.type === 'entrada').length,
      salidas:   filtered.filter(m => m.type === 'salida').length,
      traslados: filtered.filter(m => m.type === 'traslado').length,
    }
  })()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '500', color: '#1C1C1A' }}>Tareas</h2>
        <button onClick={() => setShowForm(!showForm)} style={{ background: '#185FA5', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}>
          + Nueva tarea
        </button>
      </div>

      {/* Filtro de tiempo para métricas */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {TIME_FILTERS.map(({ key, label }) => (
          <button key={key} onClick={() => setTimeFilter(key)}
            style={{
              padding: '5px 14px', borderRadius: '20px',
              border: timeFilter === key ? 'none' : '0.5px solid #D3D1C7',
              background: timeFilter === key ? '#185FA5' : '#F1EFE8',
              color: timeFilter === key ? 'white' : '#5F5E5A',
              fontSize: '12px', fontWeight: timeFilter === key ? '500' : '400',
              cursor: 'pointer',
            }}>
            {label}
          </button>
        ))}
      </div>

      {/* Panel de métricas de movimientos (filtrados por tiempo) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
        {[
          { label: 'Total movimientos', value: movMetricsFiltered.total,     bg: '#F8F8F6', numColor: '#1C1C1A', lblColor: '#888780' },
          { label: 'Entradas',          value: movMetricsFiltered.entradas,  bg: '#EAF3DE', numColor: '#3B6D11', lblColor: '#3B6D11' },
          { label: 'Salidas',           value: movMetricsFiltered.salidas,   bg: '#FAEEDA', numColor: '#854F0B', lblColor: '#854F0B' },
          { label: 'Traslados',         value: movMetricsFiltered.traslados, bg: '#EEEDFE', numColor: '#534AB7', lblColor: '#534AB7' },
        ].map(m => (
          <div key={m.label} style={{ background: m.bg, borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '18px 20px' }}>
            <div style={{ fontSize: '30px', fontWeight: '600', color: m.numColor, lineHeight: 1 }}>
              {movements == null ? '—' : m.value}
            </div>
            <div style={{ fontSize: '12px', color: m.lblColor, marginTop: '6px' }}>{m.label}</div>
          </div>
        ))}
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#1C1C1A', margin: 0 }}>Nueva tarea</h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={labelStyle}>Asignar a</label>
              <select
                value={form.assigned_to}
                onChange={e => updateForm({ assigned_to: e.target.value })}
                style={selectStyle}
                required
              >
                <option value="">Selecciona un usuario</option>
                {recommendation
                  ? <>
                      {recommendation.map(r => (
                        <option key={r.user_id} value={r.user_id}>
                          {r.is_recommended ? `⭐ ${r.name}` : r.name}
                        </option>
                      ))}
                      {users?.filter(u => u.role === 'admin').map(a => (
                        <option key={a.id} value={a.id}>{a.name}</option>
                      ))}
                    </>
                  : users?.map(u => <option key={u.id} value={u.id}>{u.name}</option>)
                }
              </select>
              {(() => {
                const selectedRec = recommendation?.find(r => r.user_id === form.assigned_to)
                if (!selectedRec) return null
                const totalLoad = selectedRec.pending_today + selectedRec.pending_old
                const totalForRate = selectedRec.total_completed + totalLoad
                const rate = totalForRate > 0
                  ? Math.round(selectedRec.total_completed / totalForRate * 100)
                  : 100
                return (
                  <div style={{ marginTop: '6px', display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                    {selectedRec.is_recommended && (
                      <span style={{ background: '#EAF3DE', color: '#3B6D11', fontSize: '10px', fontWeight: '600', padding: '2px 7px', borderRadius: '20px', letterSpacing: '0.02em' }}>
                        Recomendado
                      </span>
                    )}
                    <span style={{ fontSize: '11px', color: '#888780' }}>
                      {selectedRec.pending_today} {selectedRec.pending_today === 1 ? 'tarea pendiente hoy' : 'tareas pendientes hoy'}
                      {' · '}
                      {selectedRec.pending_old} {selectedRec.pending_old === 1 ? 'atrasada' : 'atrasadas'}
                      {' · '}
                      tasa completado: {rate}%
                    </span>
                  </div>
                )
              })()}
            </div>
            <div>
              <label style={labelStyle}>Tipo de operación</label>
              <select
                value={form.type}
                onChange={e => {
                  updateForm({ type: e.target.value, product_id: '', quantity: '', origin_location_id: '', destination_location_id: '' })
                  setOriginLocation(null)
                }}
                style={selectStyle}
              >
                <option value="entrada">Entrada</option>
                <option value="salida">Salida</option>
                <option value="traslado">Traslado</option>
              </select>
            </div>
          </div>

          {needsOrigin && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <label style={{ ...labelStyle, marginBottom: 0 }}>Ubicación origen</label>
                <button
                  type="button"
                  style={{ ...twinButtonStyle, marginTop: 0 }}
                  onClick={() => {
                    onRequestLocationSelection?.('origin', { type: 'all' }, (locationId) => {
                      const loc = allLocations.find(l => l.id === locationId)
                      handleOriginChange(locationId, loc || null)
                    }, validateOrigin)
                  }}
                >
                  <svg width="11" height="11" viewBox="0 0 11 11" fill="none"><rect x="1" y="1" width="9" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.1"/><path d="M3.5 5.5h4M5.5 3.5v4" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round"/></svg>
                  Seleccionar en almacén 3D
                </button>
              </div>
              <LocationPicker
                allLocations={allLocations}
                value={form.origin_location_id}
                onChange={handleOriginChange}
              />
              {form.origin_location_id && (
                <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '11px', color: '#888780' }}>Contenido actual:</span>
                  <LocationInventoryInfo inventory={originInv} products={products} boxes={boxes} />
                </div>
              )}
              {form.origin_location_id && !originInv && (
                <p style={{ fontSize: '12px', color: '#A32D2D', margin: '6px 0 0' }}>La ubicación seleccionada está vacía</p>
              )}
            </div>
          )}

          <div>
            <label style={labelStyle}>
              Producto
              {needsOrigin && form.origin_location_id && <span style={{ color: '#B4B2A9', fontWeight: '400', marginLeft: '6px' }}>(detectado automáticamente)</span>}
            </label>
            <ProductSearch
              products={products}
              value={form.product_id}
              onChange={v => updateForm({ product_id: v })}
            />
          </div>

          {needsQuantity && (
            <div>
              <label style={labelStyle}>
                {form.type === 'entrada' ? 'Cantidad a introducir' : form.type === 'traslado' ? 'Unidades a trasladar' : 'Unidades a extraer'}
                {originMaxQty != null && (form.type === 'salida' || form.type === 'traslado') && (
                  <span style={{ color: '#B4B2A9', fontWeight: '400', marginLeft: '6px' }}>máx. {originMaxQty}</span>
                )}
              </label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <input
                  type="number"
                  min="1"
                  max={(form.type === 'salida' || form.type === 'traslado') && originMaxQty != null ? originMaxQty : undefined}
                  value={form.quantity}
                  onChange={e => updateForm({ quantity: e.target.value })}
                  placeholder="1"
                  style={{ ...inputStyle, width: '120px', border: quantityError ? '1px solid #A32D2D' : '0.5px solid #D3D1C7' }}
                />
                {quantityError && <span style={{ fontSize: '12px', color: '#A32D2D' }}>Introduce al menos 1 unidad</span>}
              </div>
            </div>
          )}

          {needsDestination && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <label style={{ ...labelStyle, marginBottom: 0 }}>Ubicación destino</label>
                <button
                  type="button"
                  style={{ ...twinButtonStyle, marginTop: 0 }}
                  onClick={() => {
                    onRequestLocationSelection?.('destination', { type: 'all' }, (locationId) => {
                      updateForm({ destination_location_id: locationId })
                    }, validateDestination)
                  }}
                >
                  <svg width="11" height="11" viewBox="0 0 11 11" fill="none"><rect x="1" y="1" width="9" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.1"/><path d="M3.5 5.5h4M5.5 3.5v4" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round"/></svg>
                  Seleccionar en almacén 3D
                </button>
              </div>
              <LocationPicker
                allLocations={allLocations}
                value={form.destination_location_id}
                onChange={v => updateForm({ destination_location_id: v })}
              />
            </div>
          )}

          {formError && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#FCEBEB', border: '0.5px solid #F5C6C6', borderRadius: '8px', padding: '9px 12px' }}>
              <span style={{ color: '#A32D2D', fontSize: '12px', flex: 1 }}>{formError}</span>
              <button type="button" onClick={() => setFormError(null)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#A32D2D', fontSize: '14px', padding: '0', lineHeight: 1, flexShrink: 0 }}>✕</button>
            </div>
          )}

          <div style={{ display: 'flex', gap: '10px' }}>
            <button type="submit" disabled={createMutation.isLoading} style={{ background: '#185FA5', color: 'white', border: 'none', padding: '9px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}>
              {createMutation.isLoading ? 'Creando...' : 'Crear tarea'}
            </button>
            <button type="button" onClick={resetForm} style={{ background: '#F1EFE8', color: '#5F5E5A', border: 'none', padding: '9px 16px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer' }}>
              Cancelar
            </button>
          </div>
        </form>
      )}

      {!isLoading && tasks?.length > 0 && (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          {[['all', 'Todos'], ['entrada', 'Entrada'], ['salida', 'Salida'], ['traslado', 'Traslado']].map(([val, label]) => (
            <button key={val} onClick={() => setFilterType(val)} style={filterType === val ? pillActive : pillInactive}>{label}</button>
          ))}
          <div style={{ width: '1px', height: '20px', background: '#E5E4E0', flexShrink: 0, margin: '0 4px' }} />
          {[['all', 'Todos'], ['pendiente', 'Pendiente'], ['en_curso', 'En curso'], ['completada', 'Completada']].map(([val, label]) => (
            <button key={val} onClick={() => setFilterStatus(val)} style={filterStatus === val ? pillActive : pillInactive}>{label}</button>
          ))}
          <div style={{ width: '1px', height: '20px', background: '#E5E4E0', flexShrink: 0, margin: '0 4px' }} />
          <input
            type="text"
            placeholder="Buscar por producto o operario..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{ flex: 1, minWidth: '160px', border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '6px 10px', fontSize: '12px', color: '#1C1C1A', outline: 'none' }}
          />
        </div>
      )}

      {isLoading ? (
        <p style={{ color: '#888780', fontSize: '13px' }}>Cargando...</p>
      ) : tasks?.length === 0 ? (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '40px', textAlign: 'center', color: '#888780', fontSize: '13px' }}>
          No hay tareas creadas
        </div>
      ) : filteredTasks.length === 0 ? (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '40px', textAlign: 'center', color: '#888780', fontSize: '13px' }}>
          No hay tareas que coincidan con los filtros
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: '#FAFAFA' }}>
                  {['Tipo', 'Producto', 'Ubicación', 'Asignado a', 'Estado', 'Fecha', ''].map((h, i) => (
                    <th key={i} style={{ textAlign: 'left', padding: '10px 16px', color: '#888780', fontWeight: '500', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '0.5px solid #E5E4E0', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {displayedTasks.map(task => {
                  const sb = statusBadge(task.status)
                  const tb = typeBadge(task.type)
                  const product = task.product_id ? products?.find(p => p.id === task.product_id) : null
                  const assignedUser = users?.find(u => u.id === task.assigned_to)
                  return (
                    <tr key={task.id} style={{ borderTop: '0.5px solid #F1EFE8' }}>
                      <td style={{ padding: '12px 16px', verticalAlign: 'middle' }}>
                        <span style={{ background: tb.bg, color: tb.color, padding: '3px 8px', borderRadius: '20px', fontSize: '11px', fontWeight: '500', whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <TypeArrow type={task.type} />
                          {typeLabel(task.type)}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px', verticalAlign: 'middle' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          <span
                            onClick={(e) => product && handleProductClick(e, product)}
                            style={{ fontSize: '13px', fontWeight: '500', color: '#1C1C1A', cursor: product ? 'pointer' : 'default' }}
                          >
                            {product?.name || '—'}
                          </span>
                          {product?.category && (
                            <span style={{
                              display: 'inline-flex', alignItems: 'center', gap: '4px',
                              background: hexToRgba(product.category.color, 0.12),
                              color: product.category.color,
                              padding: '2px 7px', borderRadius: '20px', fontSize: '11px', fontWeight: '500', width: 'fit-content',
                            }}>
                              <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: product.category.color, flexShrink: 0 }} />
                              {product.category.name}
                            </span>
                          )}
                          {task.quantity != null && (
                            <span style={{ fontSize: '12px', color: '#888780' }}>
                              {task.quantity} {task.quantity === 1 ? 'unidad' : 'unidades'}
                            </span>
                          )}
                        </div>
                      </td>
                      <td style={{ padding: '12px 16px', verticalAlign: 'middle' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '12px' }}>
                          <div style={{ display: 'flex', gap: '5px', alignItems: 'baseline' }}>
                            <span style={{ fontSize: '10px', fontWeight: '600', color: '#B4B2A9', textTransform: 'uppercase', letterSpacing: '0.04em', flexShrink: 0 }}>Desde</span>
                            <span style={{ color: '#5F5E5A' }}>{task.origin_location_id ? getLocationLabel(task.origin_location_id) : 'Exterior'}</span>
                          </div>
                          <div style={{ display: 'flex', gap: '5px', alignItems: 'baseline' }}>
                            <span style={{ fontSize: '10px', fontWeight: '600', color: '#B4B2A9', textTransform: 'uppercase', letterSpacing: '0.04em', flexShrink: 0 }}>Hasta</span>
                            <span style={{ color: '#5F5E5A' }}>{task.destination_location_id ? getLocationLabel(task.destination_location_id) : 'Exterior'}</span>
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: '12px 16px', verticalAlign: 'middle' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {assignedUser ? (
                            <>
                              <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: '#E6F1FB', color: '#185FA5', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: '600', flexShrink: 0, letterSpacing: '0.03em' }}>
                                {getInitials(assignedUser.name)}
                              </div>
                              <span style={{ fontSize: '13px', color: '#1C1C1A' }}>{assignedUser.name}</span>
                            </>
                          ) : (
                            <>
                              <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: '#F1EFE8', color: '#B4B2A9', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                                <PersonIcon />
                              </div>
                              <span style={{ fontSize: '13px', color: '#B4B2A9', fontStyle: 'italic' }}>Sin asignar</span>
                            </>
                          )}
                        </div>
                      </td>
                      <td style={{ padding: '12px 16px', verticalAlign: 'middle' }}>
                        <span style={{ background: sb.bg, color: sb.color, padding: '3px 10px', borderRadius: '20px', fontSize: '12px', fontWeight: '500', whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: sb.color, flexShrink: 0 }} />
                          {statusLabel(task.status)}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px', color: '#888780', verticalAlign: 'middle', whiteSpace: 'nowrap', fontSize: '12px' }}>
                        {formatDate(task.created_at)}
                      </td>
                      <td style={{ padding: '12px 16px', verticalAlign: 'middle' }}>
                        {task.status !== 'en_curso' && (
                          <button
                            onClick={() => handleDeleteTask(task)}
                            disabled={deleteMutation.isLoading}
                            title="Eliminar tarea"
                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#B4B2A9', padding: '4px', borderRadius: '4px', lineHeight: 1, display: 'flex', alignItems: 'center' }}
                            onMouseEnter={e => e.currentTarget.style.color = '#A32D2D'}
                            onMouseLeave={e => e.currentTarget.style.color = '#B4B2A9'}
                          >
                            <TrashIcon />
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {visibleCount < filteredTasks.length && (
            <div style={{ textAlign: 'center' }}>
              <button
                onClick={() => setVisibleCount(v => v + 10)}
                style={{ background: 'white', color: '#185FA5', border: '0.5px solid #185FA5', padding: '8px 20px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer', fontWeight: '500' }}
              >
                Ver más ({filteredTasks.length - visibleCount} restantes)
              </button>
            </div>
          )}
        </div>
      )}

      {deleteModal && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 1100, background: 'rgba(28,28,26,0.18)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={() => setDeleteModal(null)}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{ background: 'white', borderRadius: '14px', border: '0.5px solid #E5E4E0', padding: '28px 28px 24px', boxShadow: '0 8px 32px rgba(0,0,0,0.10)', width: '360px', display: 'flex', flexDirection: 'column', gap: '20px' }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontSize: '15px', fontWeight: '600', color: '#1C1C1A' }}>Eliminar tarea</span>
              <span style={{ fontSize: '13px', color: '#5F5E5A', lineHeight: '1.55' }}>
                {deleteModal.name
                  ? <>¿Seguro que quieres eliminar <strong style={{ color: '#1C1C1A' }}>{deleteModal.name}</strong>?</>
                  : '¿Seguro que quieres eliminar esta tarea?'
                }
                {' '}Esta acción no se puede deshacer.
              </span>
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setDeleteModal(null)}
                style={{ background: '#F1EFE8', color: '#5F5E5A', border: 'none', padding: '8px 18px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer', fontWeight: '500' }}
              >
                Cancelar
              </button>
              <button
                onClick={() => { deleteMutation.mutate(deleteModal.taskId); setDeleteModal(null) }}
                disabled={deleteMutation.isLoading}
                style={{ background: '#A32D2D', color: 'white', border: 'none', padding: '8px 18px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}
              >
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}

      {productPopup && (
        <div
          ref={popupRef}
          style={{
            position: 'fixed',
            top: productPopup.y,
            left: productPopup.x,
            zIndex: 1000,
            background: 'white',
            border: '0.5px solid #E5E4E0',
            borderRadius: '10px',
            padding: '14px 16px',
            boxShadow: '0 4px 16px rgba(0,0,0,0.1)',
            minWidth: '200px',
            maxWidth: '300px',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
              <span style={{ fontWeight: '600', fontSize: '13px', color: '#1C1C1A' }}>{productPopup.product.name}</span>
              <button onClick={() => setProductPopup(null)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#888780', fontSize: '14px', padding: '0', lineHeight: 1, flexShrink: 0 }}>✕</button>
            </div>
            {productPopup.product.barcode && (
              <div style={{ fontSize: '12px', color: '#5F5E5A' }}>
                <span style={{ color: '#888780' }}>Código de barras: </span>{productPopup.product.barcode}
              </div>
            )}
            {productPopup.product.category && (
              <div style={{ fontSize: '12px', color: '#5F5E5A', display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                <span style={{ color: '#888780' }}>Categoría:</span>
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: '4px',
                  background: hexToRgba(productPopup.product.category.color, 0.12),
                  color: productPopup.product.category.color,
                  padding: '2px 8px', borderRadius: '20px', fontSize: '11px', fontWeight: '500',
                }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: productPopup.product.category.color, flexShrink: 0 }} />
                  {productPopup.product.category.name}
                </span>
              </div>
            )}
            {productPopup.product.description && (
              <div style={{ fontSize: '12px', color: '#5F5E5A' }}>
                <span style={{ color: '#888780' }}>Descripción: </span>{productPopup.product.description}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
