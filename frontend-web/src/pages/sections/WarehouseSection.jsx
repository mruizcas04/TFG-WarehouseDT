import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getWarehouses, createWarehouse } from '../../api/warehouses'
import { getProducts } from '../../api/products'
import DigitalTwin from '../../components/DigitalTwin'
import { useAuthStore } from '../../store/authStore'

const DEFAULT_SHELF = { num_levels: 3, num_locations: 5 }
const DEFAULT_AISLE = () => ({ is_double: false, shelves: [{ ...DEFAULT_SHELF }] })

const labelStyle = {
  display: 'block', fontSize: '11px', fontWeight: '500', color: '#888780',
  textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px',
}
const inputStyle = {
  width: '100%', border: '0.5px solid #D3D1C7', borderRadius: '8px',
  padding: '9px 12px', fontSize: '13px', color: '#1C1C1A', outline: 'none',
}
const numInputStyle = { ...inputStyle, width: '80px' }

const FILTERS = [
  { key: 'all',     label: 'Todo' },
  { key: 'free',    label: 'Libre' },
  { key: 'product', label: 'Producto' },
  { key: 'box',     label: 'Caja' },
  { key: 'task',    label: 'Tarea activa' },
]

// Leyenda de colores para modo normal
const LEGEND_NORMAL = [
  { color: '#999',    label: 'Libre' },
  { color: '#33cc33', label: 'Producto / Caja' },
  { color: '#ffdd00', label: 'Tarea activa' },
]

// Leyenda compacta para modo selección
const LEGEND_SELECTION = [
  { color: '#999',    label: 'Libre' },
  { color: '#33cc33', label: 'Ocupada' },
  { color: '#ffdd00', label: 'Tarea activa' },
  { color: '#33AAFF', label: 'Seleccionada' },
]

export default function WarehouseSection({
  digitalTwinRef: externalRef,
  onLocationSelected,
  // Props de modo selección (llegan desde Dashboard cuando hay pendingLocationSelection)
  selectionModeConfig = null,
  selectedLocationPreview = null,
  onConfirmLocation,
  onDeselectLocation,
  onCancelSelection,
}) {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [aisles, setAisles] = useState([DEFAULT_AISLE()])
  const [activeFilter, setActiveFilter] = useState('all')
  const [selectedProduct, setSelectedProduct] = useState('')
  const internalRef = useRef(null)
  const digitalTwinRef = externalRef ?? internalRef
  const { token } = useAuthStore()

  const handleFilter = (key) => {
    setActiveFilter(key)
    setSelectedProduct('')
    digitalTwinRef.current?.setFilter(key)
  }

  const handleProductFilter = (e) => {
    const productId = e.target.value
    setSelectedProduct(productId)
    if (productId) {
      setActiveFilter('all')
      digitalTwinRef.current?.setProductFilter(productId)
    } else {
      digitalTwinRef.current?.setFilter('all')
    }
  }

  const { data: warehouses, isLoading } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const { data: products } = useQuery({ queryKey: ['products'], queryFn: getProducts })

  const mutation = useMutation({
    mutationFn: createWarehouse,
    onSuccess: () => {
      queryClient.invalidateQueries(['warehouses'])
      setShowForm(false)
      setName('')
      setAisles([DEFAULT_AISLE()])
    },
  })

  const addAisle = () => setAisles([...aisles, DEFAULT_AISLE()])
  const removeAisle = (ai) => setAisles(aisles.filter((_, i) => i !== ai))
  const toggleAisleDouble = (ai) => {
    setAisles(aisles.map((aisle, i) => i !== ai ? aisle : { ...aisle, is_double: !aisle.is_double }))
  }
  const addShelf = (ai) => {
    const updated = [...aisles]
    updated[ai] = { ...updated[ai], shelves: [...updated[ai].shelves, { ...DEFAULT_SHELF }] }
    setAisles(updated)
  }
  const removeShelf = (ai, si) => {
    const updated = [...aisles]
    updated[ai] = { ...updated[ai], shelves: updated[ai].shelves.filter((_, i) => i !== si) }
    setAisles(updated)
  }
  const updateShelf = (ai, si, field, value) => {
    const updated = aisles.map((aisle, i) => {
      if (i !== ai) return aisle
      return { ...aisle, shelves: aisle.shelves.map((shelf, j) => j !== si ? shelf : { ...shelf, [field]: Math.max(1, parseInt(value) || 1) }) }
    })
    setAisles(updated)
  }

  const totalLocations = aisles.reduce((acc, aisle) => acc + aisle.shelves.reduce((a, s) => a + (aisle.is_double ? 2 : 1) * s.num_levels * s.num_locations, 0), 0)
  const totalShelves = aisles.reduce((acc, aisle) => acc + aisle.shelves.length * (aisle.is_double ? 2 : 1), 0)
  const totalRows = aisles.reduce((acc, aisle) => acc + (aisle.is_double ? 2 : 1), 0)

  const handleSubmit = (e) => {
    e.preventDefault()
    mutation.mutate({ name, aisles: aisles.map(aisle => ({ shelves: aisle.shelves.map(s => ({ ...s, is_double: aisle.is_double })) })) })
  }

  const warehouse = warehouses?.[0]

  // ─── Estructura con posición estable para DigitalTwin ──────────────────────
  //
  // Para evitar que React desmonte Unity al cambiar entre modo normal y modo
  // selección, todos los bloques que preceden a DigitalTwin usan display:none
  // en vez de renderizado condicional (&&). Así el índice de DigitalTwin dentro
  // de su div padre es siempre el mismo y React no lo remonta.
  //
  // Árbol simplificado del div "gemelo-card":
  //   child 0: controles modo normal   (display:none en modo selección)
  //   child 1: leyenda modo selección  (display:none en modo normal)
  //   child 2: <DigitalTwin>           (siempre en índice 2 — nunca remonta)

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      ...(selectionModeConfig ? { height: '100%', gap: 0 } : { gap: '20px' }),
    }}>

      {/* ── Bloque 1: contenido modo normal (oculto en modo selección) ── */}
      <div style={{ display: selectionModeConfig ? 'none' : 'flex', flexDirection: 'column', gap: '20px' }}>

        {/* Cabecera */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h2 style={{ fontSize: '20px', fontWeight: '500', color: '#1C1C1A' }}>Almacén</h2>
          {!warehouse && (
            <button onClick={() => setShowForm(!showForm)}
              style={{ background: '#185FA5', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}>
              + Nuevo almacén
            </button>
          )}
        </div>

        {/* Formulario de creación */}
        {showForm && (
          <form onSubmit={handleSubmit} style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#1C1C1A' }}>Configurar almacén</h3>
            <div>
              <label style={labelStyle}>Nombre del almacén</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} style={{ ...inputStyle, maxWidth: '320px' }} required />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <label style={labelStyle}>Filas ({aisles.length})</label>
                <button type="button" onClick={addAisle}
                  style={{ background: '#F1EFE8', color: '#185FA5', border: 'none', padding: '5px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: '500', cursor: 'pointer' }}>
                  + Añadir fila
                </button>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {aisles.map((aisle, ai) => {
                  const rowStart = aisles.slice(0, ai).reduce((sum, a) => sum + (a.is_double ? 2 : 1), 1)
                  return (
                    <div key={ai} style={{ border: `0.5px solid ${aisle.is_double ? '#B5D4F4' : '#E5E4E0'}`, borderRadius: '10px', overflow: 'hidden' }}>
                      <div style={{ background: aisle.is_double ? '#EEF4FF' : '#F8F8F6', padding: '10px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{ fontSize: '12px', fontWeight: '500', color: '#5F5E5A' }}>
                            {aisle.is_double ? `Filas ${rowStart} y ${rowStart + 1}` : `Fila ${rowStart}`}
                          </span>
                          {aisle.is_double && <span style={{ fontSize: '11px', fontWeight: '500', color: '#185FA5', background: '#DAEAF9', padding: '2px 8px', borderRadius: '20px' }}>Doble</span>}
                        </div>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <label style={{ display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer', fontSize: '12px', color: '#5F5E5A', userSelect: 'none' }}>
                            <input type="checkbox" checked={aisle.is_double} onChange={() => toggleAisleDouble(ai)} style={{ cursor: 'pointer', width: '14px', height: '14px', accentColor: '#185FA5' }} />
                            Fila doble
                            <span title="Una fila doble crea dos estanterías back-to-back sin pasillo entre ellas, con sus propios identificadores."
                              style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '14px', height: '14px', borderRadius: '50%', background: '#D3D1C7', color: 'white', fontSize: '9px', fontWeight: '700', cursor: 'default', lineHeight: 1 }}>
                              i
                            </span>
                          </label>
                          <button type="button" onClick={() => addShelf(ai)}
                            style={{ background: 'none', border: '0.5px solid #D3D1C7', color: '#185FA5', padding: '3px 10px', borderRadius: '5px', fontSize: '11px', cursor: 'pointer' }}>
                            + Estantería
                          </button>
                          <button type="button" onClick={() => removeAisle(ai)} disabled={aisles.length === 1}
                            style={{ background: 'none', border: 'none', color: aisles.length === 1 ? '#D3D1C7' : '#C0392B', cursor: aisles.length === 1 ? 'default' : 'pointer', fontSize: '15px', lineHeight: 1, padding: '2px' }}>
                            ✕
                          </button>
                        </div>
                      </div>
                      <div style={{ padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '40px 1fr 100px 100px 36px', gap: '8px', padding: '0 4px' }}>
                          <span style={{ fontSize: '11px', color: '#B4B2A9' }}>#</span>
                          <span style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Estantería</span>
                          <span style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Niveles</span>
                          <span style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Ubic./nivel</span>
                          <span />
                        </div>
                        {aisle.shelves.map((shelf, si) => (
                          <div key={si} style={{ display: 'grid', gridTemplateColumns: '40px 1fr 100px 100px 36px', gap: '8px', alignItems: 'center', background: aisle.is_double ? '#EEF4FF' : '#FAFAF8', borderRadius: '8px', padding: '8px 10px' }}>
                            <span style={{ fontSize: '12px', color: '#888780', textAlign: 'center' }}>{si + 1}</span>
                            <span style={{ fontSize: '13px', color: aisle.is_double ? '#185FA5' : '#5F5E5A' }}>Estantería {si + 1}</span>
                            <input type="number" min="1" value={shelf.num_levels} onChange={(e) => updateShelf(ai, si, 'num_levels', e.target.value)} style={numInputStyle} />
                            <input type="number" min="1" value={shelf.num_locations} onChange={(e) => updateShelf(ai, si, 'num_locations', e.target.value)} style={numInputStyle} />
                            <button type="button" onClick={() => removeShelf(ai, si)} disabled={aisle.shelves.length === 1}
                              style={{ background: 'none', border: 'none', color: aisle.shelves.length === 1 ? '#D3D1C7' : '#C0392B', cursor: aisle.shelves.length === 1 ? 'default' : 'pointer', fontSize: '16px', lineHeight: 1, padding: '2px' }}>
                              ✕
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
              <div style={{ marginTop: '10px', fontSize: '12px', color: '#888780' }}>
                Total: <strong style={{ color: '#1C1C1A' }}>{totalLocations}</strong> ubicaciones en{' '}
                <strong style={{ color: '#1C1C1A' }}>{totalShelves}</strong> estantería{totalShelves !== 1 ? 's' : ''} y{' '}
                <strong style={{ color: '#1C1C1A' }}>{totalRows}</strong> fila{totalRows !== 1 ? 's' : ''}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button type="submit" disabled={mutation.isLoading}
                style={{ background: '#185FA5', color: 'white', border: 'none', padding: '9px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}>
                {mutation.isLoading ? 'Creando...' : 'Crear almacén'}
              </button>
              <button type="button" onClick={() => setShowForm(false)}
                style={{ background: '#F1EFE8', color: '#5F5E5A', border: 'none', padding: '9px 16px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer' }}>
                Cancelar
              </button>
            </div>
          </form>
        )}

        {/* Estado de carga */}
        {isLoading && <p style={{ color: '#888780', fontSize: '13px' }}>Cargando...</p>}

        {/* Sin almacén */}
        {!isLoading && !warehouse && (
          <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '40px', textAlign: 'center', color: '#888780', fontSize: '13px' }}>
            No hay ningún almacén configurado
          </div>
        )}

        {/* Métricas */}
        {!isLoading && warehouse && (
          <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: '500', color: '#1C1C1A', marginBottom: '8px' }}>{warehouse.name}</h3>
                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  {[{ label: 'Estanterías', value: warehouse.num_shelves }, { label: 'Total ubicaciones', value: warehouse.total_locations ?? '—' }].map((stat) => (
                    <div key={stat.label} style={{ padding: '12px 16px', background: '#F8F8F6', borderRadius: '8px', minWidth: '120px' }}>
                      <div style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>{stat.label}</div>
                      <div style={{ fontSize: '24px', fontWeight: '500', color: '#1C1C1A' }}>{stat.value}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ fontSize: '12px', color: '#B4B2A9' }}>{new Date(warehouse.created_at).toLocaleDateString('es-ES')}</div>
            </div>
          </div>
        )}

        {/* Cabecera del gemelo (sin el canvas — el canvas vive más abajo) */}
        {!isLoading && warehouse && (
          <div style={{ background: 'white', borderRadius: '12px 12px 0 0', border: '0.5px solid #E5E4E0', borderBottom: 'none', padding: '24px 24px 0' }}>
            <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#1C1C1A', marginBottom: '16px' }}>Gemelo Digital</h3>
            <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
              {LEGEND_NORMAL.map(({ color, label }) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: color }} />
                  <span style={{ fontSize: '12px', color: '#888780' }}>{label}</span>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
              {FILTERS.map(({ key, label }) => (
                <button key={key} onClick={() => handleFilter(key)}
                  style={{ padding: '5px 14px', borderRadius: '20px', border: activeFilter === key ? 'none' : '0.5px solid #D3D1C7', background: activeFilter === key ? '#185FA5' : '#F1EFE8', color: activeFilter === key ? 'white' : '#5F5E5A', fontSize: '12px', fontWeight: activeFilter === key ? '500' : '400', cursor: 'pointer' }}>
                  {label}
                </button>
              ))}
            </div>
            <div style={{ marginBottom: '12px' }}>
              <select value={selectedProduct} onChange={handleProductFilter}
                style={{ border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '6px 12px', fontSize: '12px', color: selectedProduct ? '#1C1C1A' : '#888780', background: 'white', outline: 'none', cursor: 'pointer', minWidth: '200px' }}>
                <option value="">Todos los productos</option>
                {products?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
          </div>
        )}
      </div>{/* fin bloque modo normal */}

      {/* ── Bloque 2: cabecera modo selección (oculta en modo normal) ── */}
      <div style={{
        display: selectionModeConfig ? 'flex' : 'none',
        alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 20px', borderBottom: '0.5px solid #E5E4E0', flexShrink: 0,
      }}>
        <div>
          <h3 style={{ fontSize: '15px', fontWeight: '500', color: '#1C1C1A', margin: '0 0 3px' }}>
            {selectionModeConfig?.field === 'origin' ? 'Seleccionar ubicación origen' : 'Seleccionar ubicación destino'}
          </h3>
          <p style={{ fontSize: '12px', color: '#888780', margin: 0 }}>
            {selectedLocationPreview ? 'Confirma la selección o elige otra ubicación' : 'Haz click en una ubicación del gemelo digital'}
          </p>
        </div>
        <button
          type="button"
          onClick={onCancelSelection}
          style={{ border: 'none', background: '#F1EFE8', color: '#5F5E5A', width: '32px', height: '32px', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}
        >
          <svg width="11" height="11" viewBox="0 0 11 11" fill="none"><path d="M1 1l9 9M10 1L1 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
        </button>
      </div>

      {/* ── Bloque 3: card del gemelo — SIEMPRE EN ESTA POSICIÓN DEL ÁRBOL ──
          En modo normal: card con borde y padding estándar (borde superior-redondeado
          si hay cabecera de sección encima, o totalmente redondeado si no hay almacén).
          En modo selección: rellena el espacio disponible del modal. */}
      <div style={
        selectionModeConfig
          ? { flex: '1 1 auto', padding: '12px 20px', minHeight: '300px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }
          : {
              background: 'white',
              borderRadius: (!isLoading && warehouse) ? '0 0 12px 12px' : '12px',
              border: '0.5px solid #E5E4E0',
              borderTop: (!isLoading && warehouse) ? 'none' : '0.5px solid #E5E4E0',
              padding: '24px',
              display: (!isLoading && warehouse) ? 'block' : 'none',
            }
      }>

        {/* Leyenda compacta — solo visible en modo selección (display:none no rompe posición de DigitalTwin) */}
        <div style={{ display: selectionModeConfig ? 'flex' : 'none', gap: '14px', marginBottom: '10px', flexShrink: 0, flexWrap: 'wrap' }}>
          {LEGEND_SELECTION.map(({ color, label }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div style={{ width: '10px', height: '10px', borderRadius: '2px', background: color, flexShrink: 0 }} />
              <span style={{ fontSize: '11px', color: '#888780' }}>{label}</span>
            </div>
          ))}
        </div>

        {/* DigitalTwin — posición FIJA: siempre el segundo hijo de este div.
            React nunca lo remonta porque index y tipo de componente son constantes. */}
        {warehouse
          ? <DigitalTwin ref={digitalTwinRef} warehouseId={warehouse.id} token={token} onLocationSelected={onLocationSelected} containerStyle={selectionModeConfig ? { flex: '1 1 0', height: undefined } : undefined} />
          : selectionModeConfig
            ? <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, color: '#888780', fontSize: '13px' }}>No hay almacén configurado</div>
            : null
        }
      </div>

      {/* ── Bloque 4: panel de confirmación / error (solo modo selección) ── */}
      <div style={{
        display: selectionModeConfig && selectedLocationPreview ? 'flex' : 'none',
        alignItems: 'center', gap: '12px',
        padding: '14px 20px', flexShrink: 0,
        borderTop: '0.5px solid #E5E4E0',
        background: selectedLocationPreview?.error ? '#FEF3F2' : '#F0F8EC',
      }}>
        {selectedLocationPreview?.error ? (
          <>
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none" style={{ flexShrink: 0 }}><circle cx="7.5" cy="7.5" r="6.5" stroke="#A32D2D" strokeWidth="1.2"/><path d="M7.5 4.5v3.5" stroke="#A32D2D" strokeWidth="1.3" strokeLinecap="round"/><circle cx="7.5" cy="10.5" r="0.8" fill="#A32D2D"/></svg>
              <span style={{ fontSize: '13px', color: '#A32D2D' }}>{selectedLocationPreview.error}</span>
            </div>
            <button type="button" onClick={onDeselectLocation}
              style={{ background: 'white', color: '#5F5E5A', border: '0.5px solid #D3D1C7', borderRadius: '7px', padding: '6px 14px', fontSize: '12px', fontWeight: '500', cursor: 'pointer', flexShrink: 0 }}>
              Seleccionar otra
            </button>
          </>
        ) : (
          <>
            <div style={{ flex: 1 }}>
              <span style={{ fontSize: '12px', color: '#5F5E5A' }}>Seleccionada: </span>
              <strong style={{ fontSize: '13px', color: '#1C1C1A' }}>{selectedLocationPreview?.locationLabel}</strong>
            </div>
            <button type="button" onClick={onDeselectLocation}
              style={{ background: 'white', color: '#5F5E5A', border: '0.5px solid #D3D1C7', borderRadius: '7px', padding: '6px 14px', fontSize: '12px', cursor: 'pointer', flexShrink: 0 }}>
              Otra
            </button>
            <button type="button" onClick={onConfirmLocation}
              style={{ background: '#185FA5', color: 'white', border: 'none', borderRadius: '7px', padding: '6px 18px', fontSize: '12px', fontWeight: '500', cursor: 'pointer', flexShrink: 0 }}>
              Confirmar
            </button>
          </>
        )}
      </div>

      {/* ── Bloque 5: hint bar cuando no hay selección aún (solo modo selección) ── */}
      <div style={{
        display: selectionModeConfig && !selectedLocationPreview ? 'flex' : 'none',
        justifyContent: 'center', padding: '10px 20px',
        borderTop: '0.5px solid #F1EFE8', flexShrink: 0,
      }}>
        <span style={{ fontSize: '11px', color: '#B4B2A9' }}>
          {selectionModeConfig?.filter?.type === 'free' ? 'Solo se pueden seleccionar ubicaciones libres' : 'Puedes seleccionar cualquier ubicación'}
        </span>
      </div>

    </div>
  )
}
