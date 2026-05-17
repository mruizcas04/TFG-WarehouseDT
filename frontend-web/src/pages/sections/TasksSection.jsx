import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getTasks, createTask } from '../../api/tasks'
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

  useEffect(() => { if (!value) { setAisle(''); setShelf(''); setLevel(''); setPos('') } }, [value])

  const preview = (aisle && shelf && level && pos) ? `P${aisle} · Est. ${shelf} · Balda ${level} · Hueco ${pos}` : null

  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '8px' }}>
        {[
          { label: 'Pasillo', value: aisle, options: shelves, onChange: v => { setAisle(v); setShelf(''); setLevel(''); setPos('') }, disabled: false },
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

// Badge que indica si la cantidad implica caja o producto suelto
function QuantityTypeBadge({ quantity }) {
  if (!quantity || quantity <= 1) return null
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '4px',
      background: '#E8EEFF', color: '#2244AA',
      padding: '2px 8px', borderRadius: '20px', fontSize: '11px', fontWeight: '500',
    }}>
      <span style={{ width: '7px', height: '7px', borderRadius: '2px', background: '#3366CC', flexShrink: 0 }} />
      Caja
    </span>
  )
}

// Muestra el contenido actual de una ubicación (para confirmar qué hay antes de una salida)
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
        Caja · {productName} · {qty}/{max} ud.
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

export default function TasksSection() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
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

  const updateForm = (patch) => { setFormError(null); setForm(prev => ({ ...prev, ...patch })) }

  const { data: tasks, isLoading } = useQuery({ queryKey: ['tasks'], queryFn: getTasks })
  const { data: users } = useQuery({ queryKey: ['users'], queryFn: getUsers })
  const { data: products } = useQuery({ queryKey: ['products'], queryFn: getProducts })
  const { data: boxes } = useQuery({ queryKey: ['boxes'], queryFn: getBoxes })
  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })

  useEffect(() => {
    if (!warehouses?.length) return
    Promise.all(warehouses.map(w => getWarehouseFull(w.id))).then(full => {
      setAllLocations(full.flatMap(flattenLocations))
    })
  }, [warehouses])

  // Al seleccionar ubicación de origen, auto-detectar producto y cantidad máxima
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

  const workers = users?.filter(u => u.role === 'worker')
  const needsOrigin = form.type === 'salida' || form.type === 'traslado'
  const needsDestination = form.type === 'entrada' || form.type === 'traslado'
  const needsQuantity = form.type === 'entrada' || form.type === 'salida'

  const originInv = originLocation?.inventory
  const originBoxMaxQty = originInv?.box_id
    ? (originInv.box_current_quantity ?? boxes?.find(b => b.id === originInv.box_id)?.current_quantity)
    : null

  const quantity = Number(form.quantity) || 0

  const createMutation = useMutation({
    mutationFn: createTask,
    onSuccess: () => {
      queryClient.invalidateQueries(['tasks'])
      setShowForm(false)
      setFormError(null)
      setOriginLocation(null)
      setForm({ assigned_to: '', type: 'entrada', product_id: '', quantity: '', origin_location_id: '', destination_location_id: '' })
    },
    onError: (err) => setFormError(err?.response?.data?.detail || 'Error al crear la tarea'),
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    createMutation.mutate({
      assigned_to: form.assigned_to,
      type: form.type,
      product_id: form.product_id || null,
      quantity: form.quantity ? Number(form.quantity) : null,
      origin_location_id: needsOrigin ? form.origin_location_id || null : null,
      destination_location_id: needsDestination ? form.destination_location_id || null : null,
    })
  }

  const resetForm = () => { setShowForm(false); setOriginLocation(null); setFormError(null) }

  const statusLabel = s => ({ pendiente: 'Pendiente', en_curso: 'En curso', completada: 'Completada' })[s] || s
  const statusBadge = s => ({ pendiente: { bg: '#FAEEDA', color: '#854F0B' }, en_curso: { bg: '#E6F1FB', color: '#185FA5' }, completada: { bg: '#EAF3DE', color: '#3B6D11' } })[s] || { bg: '#F1EFE8', color: '#888780' }
  const typeLabel = t => ({ entrada: 'Entrada', salida: 'Salida', traslado: 'Traslado' })[t] || t
  const typeBadge = t => ({ entrada: { bg: '#EAF3DE', color: '#3B6D11' }, salida: { bg: '#FAEEDA', color: '#854F0B' }, traslado: { bg: '#EEEDFE', color: '#534AB7' } })[t] || { bg: '#F1EFE8', color: '#888780' }
  const getUserName = id => users?.find(u => u.id === id)?.name || '—'
  const getProductName = id => products?.find(p => p.id === id)?.name || '—'
  const getLocationLabel = id => allLocations.find(l => l.id === id)?.label || '—'

  const getTaskContent = (task) => {
    if (!task.product_id) return '—'
    const name = getProductName(task.product_id)
    const qty = task.quantity
    if (!qty) return name
    if (qty > 1) return (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
        {name}
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px', background: '#E8EEFF', color: '#2244AA', padding: '1px 6px', borderRadius: '20px', fontSize: '10px', fontWeight: '500' }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '1px', background: '#3366CC', flexShrink: 0 }} />
          Caja
        </span>
        <span style={{ color: '#888780', fontSize: '12px' }}>{qty} ud.</span>
      </span>
    )
    return `${name} · ${qty} ud.`
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '500', color: '#1C1C1A' }}>Tareas</h2>
        <button onClick={() => setShowForm(!showForm)} style={{ background: '#185FA5', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}>
          + Nueva tarea
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#1C1C1A', margin: 0 }}>Nueva tarea</h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={labelStyle}>Asignar a</label>
              <select value={form.assigned_to} onChange={e => updateForm({ assigned_to: e.target.value })} style={selectStyle} required>
                <option value="">Selecciona un trabajador</option>
                {workers?.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
              </select>
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

          {/* Origen: salida y traslado */}
          {needsOrigin && (
            <div>
              <LocationPicker
                allLocations={allLocations}
                value={form.origin_location_id}
                onChange={handleOriginChange}
                label="Ubicación origen"
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

          {/* Producto: siempre visible (en salida/traslado se rellena automáticamente) */}
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

          {/* Cantidad + badge Caja */}
          {needsQuantity && (
            <div>
              <label style={labelStyle}>
                {form.type === 'entrada' ? 'Cantidad a introducir' : 'Unidades a extraer'}
                {originBoxMaxQty != null && form.type === 'salida' && (
                  <span style={{ color: '#B4B2A9', fontWeight: '400', marginLeft: '6px' }}>máx. {originBoxMaxQty}</span>
                )}
              </label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <input
                  type="number"
                  min="1"
                  max={form.type === 'salida' && originBoxMaxQty != null ? originBoxMaxQty : undefined}
                  value={form.quantity}
                  onChange={e => updateForm({ quantity: e.target.value })}
                  placeholder="1"
                  style={{ ...inputStyle, width: '120px' }}
                />
                <QuantityTypeBadge quantity={quantity} />
                {quantity > 1 && (
                  <span style={{ fontSize: '11px', color: '#888780' }}>
                    {form.type === 'entrada'
                      ? 'Se almacenará como caja en el gemelo digital'
                      : 'Extracción parcial de caja'}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Destino: entrada y traslado */}
          {needsDestination && (
            <LocationPicker
              allLocations={allLocations}
              value={form.destination_location_id}
              onChange={v => updateForm({ destination_location_id: v })}
              label="Ubicación destino"
            />
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

      {isLoading ? (
        <p style={{ color: '#888780', fontSize: '13px' }}>Cargando...</p>
      ) : tasks?.length === 0 ? (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '40px', textAlign: 'center', color: '#888780', fontSize: '13px' }}>
          No hay tareas creadas
        </div>
      ) : (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ background: '#FAFAFA' }}>
                {['Tipo', 'Producto', 'Origen', 'Destino', 'Asignado a', 'Creado por', 'Estado', 'Fecha'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '10px 16px', color: '#888780', fontWeight: '500', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '0.5px solid #E5E4E0', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tasks?.map(task => {
                const sb = statusBadge(task.status)
                const tb = typeBadge(task.type)
                return (
                  <tr key={task.id} style={{ borderTop: '0.5px solid #F1EFE8' }}>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{ background: tb.bg, color: tb.color, padding: '2px 8px', borderRadius: '20px', fontSize: '11px', fontWeight: '500', whiteSpace: 'nowrap' }}>{typeLabel(task.type)}</span>
                    </td>
                    <td style={{ padding: '12px 16px', color: '#5F5E5A' }}>{getTaskContent(task)}</td>
                    <td style={{ padding: '12px 16px', color: '#5F5E5A', fontSize: '12px' }}>{task.origin_location_id ? getLocationLabel(task.origin_location_id) : '—'}</td>
                    <td style={{ padding: '12px 16px', color: '#5F5E5A', fontSize: '12px' }}>{task.destination_location_id ? getLocationLabel(task.destination_location_id) : '—'}</td>
                    <td style={{ padding: '12px 16px', color: '#1C1C1A', fontWeight: '500' }}>{getUserName(task.assigned_to)}</td>
                    <td style={{ padding: '12px 16px', color: '#5F5E5A' }}>{getUserName(task.created_by)}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{ background: sb.bg, color: sb.color, padding: '2px 8px', borderRadius: '20px', fontSize: '11px', fontWeight: '500', whiteSpace: 'nowrap' }}>{statusLabel(task.status)}</span>
                    </td>
                    <td style={{ padding: '12px 16px', color: '#888780', whiteSpace: 'nowrap' }}>{new Date(task.created_at).toLocaleDateString('es-ES')}</td>
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
