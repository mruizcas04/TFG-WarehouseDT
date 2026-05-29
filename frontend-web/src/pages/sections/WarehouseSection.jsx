import { useState, useRef, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getWarehouses, createWarehouse, getWarehouseFull, expandWarehouse } from '../../api/warehouses'
import { getProducts } from '../../api/products'
import DigitalTwin from '../../components/DigitalTwin'
import { useAuthStore } from '../../store/authStore'

const DEFAULT_SHELF = { num_levels: 3, num_locations: 5 }
const DEFAULT_AISLE = () => ({ is_double: false, shelves: [{ ...DEFAULT_SHELF }] })

function buildLogicalAisles(shelves) {
  const byAisle = {}
  for (const s of shelves) {
    if (!byAisle[s.aisle_number]) byAisle[s.aisle_number] = []
    byAisle[s.aisle_number].push(s)
  }
  const nums = Object.keys(byAisle).map(Number).sort((a, b) => a - b)
  const result = []
  let i = 0
  while (i < nums.length) {
    const n = nums[i]
    const isDouble = byAisle[n].some(s => s.is_double)
    result.push({
      frontAisleNumber: n,
      backAisleNumber: isDouble && i + 1 < nums.length ? nums[i + 1] : null,
      isDouble,
      existingShelves: byAisle[n],
      addedShelves: [],
    })
    i += isDouble ? 2 : 1
  }
  return result
}

const labelStyle = {
  display: 'block', fontSize: '11px', fontWeight: '500', color: '#888780',
  textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px',
}
const inputStyle = {
  width: '100%', border: '0.5px solid #D3D1C7', borderRadius: '8px',
  padding: '9px 12px', fontSize: '13px', color: '#1C1C1A', outline: 'none',
}
const numInputStyle = { ...inputStyle, width: '80px' }

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
  const [showExpandForm, setShowExpandForm] = useState(false)
  const [expandState, setExpandState] = useState(null)
  const [selectedProduct, setSelectedProduct] = useState('')
  const internalRef = useRef(null)
  const digitalTwinRef = externalRef ?? internalRef
  const { token } = useAuthStore()

  const handleProductFilter = (e) => {
    const productId = e.target.value
    setSelectedProduct(productId)
    if (productId) {
      digitalTwinRef.current?.setProductFilter(productId)
    } else {
      digitalTwinRef.current?.clearFilter()
    }
  }

  const handleResetCamera = () => {
    digitalTwinRef.current?.resetCameraView()
  }

  const handleFullscreen = () => {
    digitalTwinRef.current?.requestFullscreen()
  }

  const { data: warehouses, isLoading } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const { data: products } = useQuery({ queryKey: ['products'], queryFn: getProducts })
  const firstWarehouse = warehouses?.[0]
  const { data: warehouseFull } = useQuery({
    queryKey: ['warehouse-full', firstWarehouse?.id],
    queryFn: () => getWarehouseFull(firstWarehouse.id),
    enabled: !!firstWarehouse?.id,
    // Polling: refetch cada 3s para que las estadísticas se actualicen ante movimientos / tareas.
    refetchInterval: 3000,
    // Para evitar parpadeo en cada refetch — react-query mantiene los datos previos hasta que llegan los nuevos.
    keepPreviousData: true,
  })

  const stats = useMemo(() => {
    if (!warehouseFull) return null
    const aisles = new Set()
    let total = 0, occupied = 0
    for (const shelf of warehouseFull.shelves || []) {
      aisles.add(shelf.aisle_number)
      for (const level of shelf.levels || []) {
        for (const loc of level.locations || []) {
          total++
          if (loc.inventory && (loc.inventory.product_id || loc.inventory.box_id)) occupied++
        }
      }
    }
    return {
      aisles: aisles.size,
      shelves: (warehouseFull.shelves || []).length,
      total,
      occupied,
      free: total - occupied,
      tasks: (warehouseFull.active_task_locations || []).length,
    }
  }, [warehouseFull])

  const mutation = useMutation({
    mutationFn: createWarehouse,
    onSuccess: () => {
      queryClient.invalidateQueries(['warehouses'])
      setShowForm(false)
      setName('')
      setAisles([DEFAULT_AISLE()])
    },
  })

  const expandMutation = useMutation({
    mutationFn: ({ id, data }) => expandWarehouse(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['warehouses'])
      queryClient.invalidateQueries(['warehouse-full'])
      setShowExpandForm(false)
      setExpandState(null)
      digitalTwinRef.current?.reload()
    },
  })

  const openExpandForm = () => {
    if (!warehouseFull) return
    setExpandState({ existingAisles: buildLogicalAisles(warehouseFull.shelves || []), newAisles: [] })
    setShowExpandForm(true)
  }

  const handleExpandSubmit = (e) => {
    e.preventDefault()
    const extend_aisles = expandState.existingAisles
      .filter(ea => ea.addedShelves.length > 0)
      .map(ea => ({ aisle_number: ea.frontAisleNumber, new_shelves: ea.addedShelves }))
    const new_aisles = expandState.newAisles.map(a => ({
      shelves: a.shelves.map(s => ({ ...s, is_double: a.is_double }))
    }))
    expandMutation.mutate({ id: firstWarehouse.id, data: { extend_aisles, new_aisles } })
  }

  const addShelfToExisting = (aisleIdx) => {
    setExpandState(prev => {
      const updated = prev.existingAisles.map((ea, i) =>
        i !== aisleIdx ? ea : { ...ea, addedShelves: [...ea.addedShelves, { ...DEFAULT_SHELF }] }
      )
      return { ...prev, existingAisles: updated }
    })
  }

  const updateExpandAddedShelf = (aisleIdx, shelfIdx, field, value) => {
    setExpandState(prev => {
      const updated = prev.existingAisles.map((ea, i) => {
        if (i !== aisleIdx) return ea
        return {
          ...ea,
          addedShelves: ea.addedShelves.map((s, j) =>
            j !== shelfIdx ? s : { ...s, [field]: Math.max(1, parseInt(value) || 1) }
          ),
        }
      })
      return { ...prev, existingAisles: updated }
    })
  }

  const removeExpandAddedShelf = (aisleIdx, shelfIdx) => {
    setExpandState(prev => {
      const updated = prev.existingAisles.map((ea, i) =>
        i !== aisleIdx ? ea : { ...ea, addedShelves: ea.addedShelves.filter((_, j) => j !== shelfIdx) }
      )
      return { ...prev, existingAisles: updated }
    })
  }

  const addNewAisle = () => setExpandState(prev => ({ ...prev, newAisles: [...prev.newAisles, DEFAULT_AISLE()] }))
  const removeNewAisle = (ai) => setExpandState(prev => ({ ...prev, newAisles: prev.newAisles.filter((_, i) => i !== ai) }))
  const toggleNewAisleDouble = (ai) => setExpandState(prev => ({
    ...prev,
    newAisles: prev.newAisles.map((a, i) => i !== ai ? a : { ...a, is_double: !a.is_double }),
  }))
  const addShelfToNewAisle = (ai) => setExpandState(prev => ({
    ...prev,
    newAisles: prev.newAisles.map((a, i) => i !== ai ? a : { ...a, shelves: [...a.shelves, { ...DEFAULT_SHELF }] }),
  }))
  const removeShelfFromNewAisle = (ai, si) => setExpandState(prev => ({
    ...prev,
    newAisles: prev.newAisles.map((a, i) => i !== ai ? a : { ...a, shelves: a.shelves.filter((_, j) => j !== si) }),
  }))
  const updateNewAisleShelf = (ai, si, field, value) => setExpandState(prev => ({
    ...prev,
    newAisles: prev.newAisles.map((a, i) => i !== ai ? a : {
      ...a,
      shelves: a.shelves.map((s, j) => j !== si ? s : { ...s, [field]: Math.max(1, parseInt(value) || 1) }),
    }),
  }))

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
          {warehouse && !showExpandForm && (
            <button onClick={openExpandForm}
              style={{ background: '#F1EFE8', color: '#185FA5', border: '0.5px solid #C5DEFA', padding: '8px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}>
              + Ampliar almacén
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

        {/* Formulario de expansión */}
        {showExpandForm && expandState && (
          <form onSubmit={handleExpandSubmit} style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#1C1C1A' }}>Ampliar almacén</h3>

            {/* Filas existentes */}
            <div>
              <label style={labelStyle}>Filas existentes</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {expandState.existingAisles.map((ea, ai) => {
                  const label = ea.isDouble
                    ? `Filas ${ea.frontAisleNumber} y ${ea.backAisleNumber}`
                    : `Fila ${ea.frontAisleNumber}`
                  return (
                    <div key={ai} style={{ border: '0.5px solid #E5E4E0', borderRadius: '10px', overflow: 'hidden' }}>
                      <div style={{ background: '#F8F8F6', padding: '10px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '12px', fontWeight: '500', color: '#5F5E5A' }}>{label}</span>
                          {ea.isDouble && <span style={{ fontSize: '11px', fontWeight: '500', color: '#185FA5', background: '#DAEAF9', padding: '2px 8px', borderRadius: '20px' }}>Doble</span>}
                          <span style={{ fontSize: '11px', color: '#888780' }}>{ea.existingShelves.length} estantería{ea.existingShelves.length !== 1 ? 's' : ''}</span>
                        </div>
                        <button type="button" onClick={() => addShelfToExisting(ai)}
                          style={{ background: 'none', border: '0.5px solid #D3D1C7', color: '#185FA5', padding: '3px 10px', borderRadius: '5px', fontSize: '11px', cursor: 'pointer' }}>
                          + Estantería
                        </button>
                      </div>
                      {ea.addedShelves.length > 0 && (
                        <div style={{ padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          <div style={{ display: 'grid', gridTemplateColumns: '40px 1fr 100px 100px 36px', gap: '8px', padding: '0 4px' }}>
                            <span style={{ fontSize: '11px', color: '#B4B2A9' }}>#</span>
                            <span style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Nueva</span>
                            <span style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Niveles</span>
                            <span style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Ubic./nivel</span>
                            <span />
                          </div>
                          {ea.addedShelves.map((s, si) => (
                            <div key={si} style={{ display: 'grid', gridTemplateColumns: '40px 1fr 100px 100px 36px', gap: '8px', alignItems: 'center', background: '#F1F8FF', borderRadius: '8px', padding: '8px 10px' }}>
                              <span style={{ fontSize: '12px', color: '#888780', textAlign: 'center' }}>{ea.existingShelves.length + si + 1}</span>
                              <span style={{ fontSize: '13px', color: '#185FA5' }}>Estantería {ea.existingShelves.length + si + 1}</span>
                              <input type="number" min="1" value={s.num_levels} onChange={e => updateExpandAddedShelf(ai, si, 'num_levels', e.target.value)} style={numInputStyle} />
                              <input type="number" min="1" value={s.num_locations} onChange={e => updateExpandAddedShelf(ai, si, 'num_locations', e.target.value)} style={numInputStyle} />
                              <button type="button" onClick={() => removeExpandAddedShelf(ai, si)}
                                style={{ background: 'none', border: 'none', color: '#C0392B', cursor: 'pointer', fontSize: '16px', lineHeight: 1, padding: '2px' }}>✕</button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Filas nuevas */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                <label style={labelStyle}>Filas nuevas {expandState.newAisles.length > 0 ? `(${expandState.newAisles.length})` : ''}</label>
                <button type="button" onClick={addNewAisle}
                  style={{ background: '#F1EFE8', color: '#185FA5', border: 'none', padding: '5px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: '500', cursor: 'pointer' }}>
                  + Añadir fila
                </button>
              </div>
              {expandState.newAisles.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {expandState.newAisles.map((aisle, ai) => (
                    <div key={ai} style={{ border: `0.5px solid ${aisle.is_double ? '#B5D4F4' : '#E5E4E0'}`, borderRadius: '10px', overflow: 'hidden' }}>
                      <div style={{ background: aisle.is_double ? '#EEF4FF' : '#F8F8F6', padding: '10px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{ fontSize: '12px', fontWeight: '500', color: '#5F5E5A' }}>Nueva fila {ai + 1}</span>
                          {aisle.is_double && <span style={{ fontSize: '11px', fontWeight: '500', color: '#185FA5', background: '#DAEAF9', padding: '2px 8px', borderRadius: '20px' }}>Doble</span>}
                        </div>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <label style={{ display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer', fontSize: '12px', color: '#5F5E5A', userSelect: 'none' }}>
                            <input type="checkbox" checked={aisle.is_double} onChange={() => toggleNewAisleDouble(ai)} style={{ cursor: 'pointer', width: '14px', height: '14px', accentColor: '#185FA5' }} />
                            Fila doble
                          </label>
                          <button type="button" onClick={() => addShelfToNewAisle(ai)}
                            style={{ background: 'none', border: '0.5px solid #D3D1C7', color: '#185FA5', padding: '3px 10px', borderRadius: '5px', fontSize: '11px', cursor: 'pointer' }}>
                            + Estantería
                          </button>
                          <button type="button" onClick={() => removeNewAisle(ai)}
                            style={{ background: 'none', border: 'none', color: '#C0392B', cursor: 'pointer', fontSize: '15px', lineHeight: 1, padding: '2px' }}>✕</button>
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
                            <input type="number" min="1" value={shelf.num_levels} onChange={e => updateNewAisleShelf(ai, si, 'num_levels', e.target.value)} style={numInputStyle} />
                            <input type="number" min="1" value={shelf.num_locations} onChange={e => updateNewAisleShelf(ai, si, 'num_locations', e.target.value)} style={numInputStyle} />
                            <button type="button" onClick={() => removeShelfFromNewAisle(ai, si)} disabled={aisle.shelves.length === 1}
                              style={{ background: 'none', border: 'none', color: aisle.shelves.length === 1 ? '#D3D1C7' : '#C0392B', cursor: aisle.shelves.length === 1 ? 'default' : 'pointer', fontSize: '16px', lineHeight: 1, padding: '2px' }}>✕</button>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {expandMutation.isError && (
              <p style={{ color: '#C0392B', fontSize: '13px', margin: 0 }}>
                {expandMutation.error?.response?.data?.detail || 'Error al ampliar el almacén'}
              </p>
            )}

            <div style={{ display: 'flex', gap: '10px' }}>
              <button type="submit"
                disabled={expandMutation.isLoading || (expandState.existingAisles.every(ea => ea.addedShelves.length === 0) && expandState.newAisles.length === 0)}
                style={{ background: '#185FA5', color: 'white', border: 'none', padding: '9px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer', opacity: (expandState.existingAisles.every(ea => ea.addedShelves.length === 0) && expandState.newAisles.length === 0) ? 0.5 : 1 }}>
                {expandMutation.isLoading ? 'Guardando...' : 'Guardar cambios'}
              </button>
              <button type="button" onClick={() => { setShowExpandForm(false); setExpandState(null) }}
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

        {/* Cabecera del gemelo (sin el canvas — el canvas vive más abajo) */}
        {!isLoading && warehouse && (
          <div style={{ background: 'white', borderRadius: '12px 12px 0 0', border: '0.5px solid #E5E4E0', borderBottom: 'none', padding: '24px 24px 0' }}>
            <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#1C1C1A', marginBottom: '16px' }}>Gemelo Digital</h3>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
              <select value={selectedProduct} onChange={handleProductFilter}
                style={{ border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '6px 12px', fontSize: '12px', color: selectedProduct ? '#1C1C1A' : '#888780', background: 'white', outline: 'none', cursor: 'pointer', minWidth: '200px' }}>
                <option value="">Filtrar por producto…</option>
                {products?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>

              <div style={{ flex: 1 }} />

              <button onClick={handleResetCamera}
                style={{ padding: '6px 12px', borderRadius: '8px', border: '0.5px solid #D3D1C7', background: '#F1EFE8', color: '#5F5E5A', fontSize: '12px', cursor: 'pointer' }}>
                ↺ Vista inicial
              </button>
              <button onClick={handleFullscreen}
                style={{ padding: '6px 12px', borderRadius: '8px', border: '0.5px solid #D3D1C7', background: '#F1EFE8', color: '#5F5E5A', fontSize: '12px', cursor: 'pointer' }}>
                ⛶ Pantalla completa
              </button>
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

        {/* DigitalTwin — posición FIJA: siempre el segundo hijo de este div.
            React nunca lo remonta porque index y tipo de componente son constantes. */}
        {warehouse
          ? <DigitalTwin ref={digitalTwinRef} warehouseId={warehouse.id} token={token} onLocationSelected={onLocationSelected} containerStyle={selectionModeConfig ? { flex: '1 1 0', height: undefined } : undefined} />
          : selectionModeConfig
            ? <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, color: '#888780', fontSize: '13px' }}>No hay almacén configurado</div>
            : null
        }
      </div>

      {/* ── Bloque 3.5: Estadísticas del almacén (debajo del gemelo, solo modo normal) ── */}
      {!selectionModeConfig && !isLoading && warehouse && (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '500', color: '#1C1C1A' }}>{warehouse.name}</h3>
            <div style={{ fontSize: '12px', color: '#B4B2A9' }}>{new Date(warehouse.created_at).toLocaleDateString('es-ES')}</div>
          </div>
          {stats ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '12px' }}>
              {[
                { label: 'Filas',              value: stats.aisles,   color: '#1C1C1A' },
                { label: 'Estanterías',        value: stats.shelves,  color: '#1C1C1A' },
                { label: 'Total ubicaciones',  value: stats.total,    color: '#1C1C1A' },
                { label: 'Libres',             value: stats.free,     color: '#5F5E5A' },
                { label: 'Ocupadas',           value: stats.occupied, color: '#185FA5' },
                { label: 'Con tareas',         value: stats.tasks,    color: '#C0392B' },
              ].map((stat) => (
                <div key={stat.label} style={{ padding: '12px 16px', background: '#F8F8F6', borderRadius: '8px' }}>
                  <div style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>{stat.label}</div>
                  <div style={{ fontSize: '24px', fontWeight: '500', color: stat.color }}>{stat.value}</div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ fontSize: '13px', color: '#888780' }}>Cargando estadísticas...</p>
          )}
        </div>
      )}

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
