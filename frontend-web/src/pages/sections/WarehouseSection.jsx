import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getWarehouses, createWarehouse } from '../../api/warehouses'
import { getProducts } from '../../api/products'
import DigitalTwin from '../../components/DigitalTwin'
import { useAuthStore } from '../../store/authStore'

const DEFAULT_SHELF = { num_levels: 3, num_locations: 5 }
const DEFAULT_AISLE = () => ({ shelves: [{ ...DEFAULT_SHELF }] })

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

export default function WarehouseSection() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [aisles, setAisles] = useState([DEFAULT_AISLE()])
  const [activeFilter, setActiveFilter] = useState('all')
  const [selectedProduct, setSelectedProduct] = useState('')
  const digitalTwinRef = useRef(null)
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

  const addShelf = (ai) => {
    const updated = [...aisles]
    updated[ai] = { shelves: [...updated[ai].shelves, { ...DEFAULT_SHELF }] }
    setAisles(updated)
  }
  const removeShelf = (ai, si) => {
    const updated = [...aisles]
    updated[ai] = { shelves: updated[ai].shelves.filter((_, i) => i !== si) }
    setAisles(updated)
  }
  const updateShelf = (ai, si, field, value) => {
    const updated = aisles.map((aisle, i) => {
      if (i !== ai) return aisle
      return {
        shelves: aisle.shelves.map((shelf, j) =>
          j !== si ? shelf : { ...shelf, [field]: Math.max(1, parseInt(value) || 1) }
        ),
      }
    })
    setAisles(updated)
  }

  const totalLocations = aisles.reduce(
    (acc, aisle) => acc + aisle.shelves.reduce((a, s) => a + s.num_levels * s.num_locations, 0), 0
  )
  const totalShelves = aisles.reduce((acc, aisle) => acc + aisle.shelves.length, 0)

  const handleSubmit = (e) => {
    e.preventDefault()
    mutation.mutate({ name, aisles })
  }

  const warehouse = warehouses?.[0]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '500', color: '#1C1C1A' }}>Almacén</h2>
        {!warehouse && (
          <button onClick={() => setShowForm(!showForm)}
            style={{ background: '#185FA5', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}>
            + Nuevo almacén
          </button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#1C1C1A' }}>Configurar almacén</h3>

          {/* Nombre */}
          <div>
            <label style={labelStyle}>Nombre del almacén</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)}
              style={{ ...inputStyle, maxWidth: '320px' }} required />
          </div>

          {/* Filas */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <label style={labelStyle}>Filas ({aisles.length})</label>
              <button type="button" onClick={addAisle}
                style={{ background: '#F1EFE8', color: '#185FA5', border: 'none', padding: '5px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: '500', cursor: 'pointer' }}>
                + Añadir fila
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {aisles.map((aisle, ai) => (
                <div key={ai} style={{ border: '0.5px solid #E5E4E0', borderRadius: '10px', overflow: 'hidden' }}>
                  {/* Cabecera de la fila */}
                  <div style={{ background: '#F8F8F6', padding: '10px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '12px', fontWeight: '500', color: '#5F5E5A' }}>Fila {ai + 1}</span>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
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

                  {/* Estanterías de la fila */}
                  <div style={{ padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {/* Cabecera columnas */}
                    <div style={{ display: 'grid', gridTemplateColumns: '40px 1fr 100px 100px 36px', gap: '8px', padding: '0 4px' }}>
                      <span style={{ fontSize: '11px', color: '#B4B2A9' }}>#</span>
                      <span style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Estantería</span>
                      <span style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Niveles</span>
                      <span style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Ubic./nivel</span>
                      <span />
                    </div>

                    {aisle.shelves.map((shelf, si) => (
                      <div key={si} style={{ display: 'grid', gridTemplateColumns: '40px 1fr 100px 100px 36px', gap: '8px', alignItems: 'center', background: '#FAFAF8', borderRadius: '8px', padding: '8px 10px' }}>
                        <span style={{ fontSize: '12px', color: '#888780', textAlign: 'center' }}>{si + 1}</span>
                        <span style={{ fontSize: '13px', color: '#5F5E5A' }}>Estantería {si + 1}</span>
                        <input type="number" min="1" value={shelf.num_levels}
                          onChange={(e) => updateShelf(ai, si, 'num_levels', e.target.value)}
                          style={numInputStyle} />
                        <input type="number" min="1" value={shelf.num_locations}
                          onChange={(e) => updateShelf(ai, si, 'num_locations', e.target.value)}
                          style={numInputStyle} />
                        <button type="button" onClick={() => removeShelf(ai, si)}
                          disabled={aisle.shelves.length === 1}
                          style={{ background: 'none', border: 'none', color: aisle.shelves.length === 1 ? '#D3D1C7' : '#C0392B', cursor: aisle.shelves.length === 1 ? 'default' : 'pointer', fontSize: '16px', lineHeight: 1, padding: '2px' }}>
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Resumen */}
            <div style={{ marginTop: '10px', fontSize: '12px', color: '#888780' }}>
              Total: <strong style={{ color: '#1C1C1A' }}>{totalLocations}</strong> ubicaciones en{' '}
              <strong style={{ color: '#1C1C1A' }}>{totalShelves}</strong> estantería{totalShelves !== 1 ? 's' : ''} y{' '}
              <strong style={{ color: '#1C1C1A' }}>{aisles.length}</strong> fila{aisles.length !== 1 ? 's' : ''}
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

      {isLoading ? (
        <p style={{ color: '#888780', fontSize: '13px' }}>Cargando...</p>
      ) : !warehouse ? (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '40px', textAlign: 'center', color: '#888780', fontSize: '13px' }}>
          No hay ningún almacén configurado
        </div>
      ) : (
        <>
          {/* Métricas del almacén */}
          <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: '500', color: '#1C1C1A', marginBottom: '8px' }}>{warehouse.name}</h3>
                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  {[
                    { label: 'Estanterías', value: warehouse.num_shelves },
                    { label: 'Total ubicaciones', value: warehouse.total_locations ?? '—' },
                  ].map((stat) => (
                    <div key={stat.label} style={{ padding: '12px 16px', background: '#F8F8F6', borderRadius: '8px', minWidth: '120px' }}>
                      <div style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>{stat.label}</div>
                      <div style={{ fontSize: '24px', fontWeight: '500', color: '#1C1C1A' }}>{stat.value}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ fontSize: '12px', color: '#B4B2A9' }}>
                {new Date(warehouse.created_at).toLocaleDateString('es-ES')}
              </div>
            </div>
          </div>

          {/* Gemelo Digital */}
          <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#1C1C1A', marginBottom: '16px' }}>Gemelo Digital</h3>
            <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
              {[
                { color: '#999', label: 'Libre' },
                { color: '#33cc33', label: 'Producto / Caja' },
                { color: '#ffdd00', label: 'Tarea activa' },
              ].map(({ color, label }) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: color }} />
                  <span style={{ fontSize: '12px', color: '#888780' }}>{label}</span>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
              {FILTERS.map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => handleFilter(key)}
                  style={{
                    padding: '5px 14px',
                    borderRadius: '20px',
                    border: activeFilter === key ? 'none' : '0.5px solid #D3D1C7',
                    background: activeFilter === key ? '#185FA5' : '#F1EFE8',
                    color: activeFilter === key ? 'white' : '#5F5E5A',
                    fontSize: '12px',
                    fontWeight: activeFilter === key ? '500' : '400',
                    cursor: 'pointer',
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
            <div style={{ marginBottom: '12px' }}>
              <select
                value={selectedProduct}
                onChange={handleProductFilter}
                style={{
                  border: '0.5px solid #D3D1C7',
                  borderRadius: '8px',
                  padding: '6px 12px',
                  fontSize: '12px',
                  color: selectedProduct ? '#1C1C1A' : '#888780',
                  background: 'white',
                  outline: 'none',
                  cursor: 'pointer',
                  minWidth: '200px',
                }}
              >
                <option value="">Todos los productos</option>
                {products?.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <DigitalTwin ref={digitalTwinRef} warehouseId={warehouse.id} token={token} />
          </div>
        </>
      )}
    </div>
  )
}
