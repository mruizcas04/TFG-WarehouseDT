import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getProducts, createProduct, deleteProduct, uploadProductImage, API_BASE } from '../../api/products'
import { getCategories, createCategory } from '../../api/categories'
import { getInventorySummary } from '../../api/inventory'
import { getWarehouses } from '../../api/warehouses'

const inputStyle = { width: '100%', border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '9px 12px', fontSize: '13px', color: '#1C1C1A', outline: 'none', boxSizing: 'border-box' }
const labelStyle = { display: 'block', fontSize: '11px', fontWeight: '500', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }

const PRESET_COLORS = ['#185FA5', '#3B6D11', '#854F0B', '#7C6DB5', '#A32D2D', '#0F766E', '#D9800D', '#2244AA']

const hexToRgba = (hex, alpha) => {
  if (!hex || hex.length < 7) return `rgba(136,135,128,${alpha})`
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

function CategoryBadge({ category }) {
  if (!category) return <span style={{ color: '#C8C7C2', fontSize: '12px' }}>—</span>
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px',
      background: hexToRgba(category.color, 0.12),
      color: category.color,
      padding: '3px 9px', borderRadius: '20px', fontSize: '12px', fontWeight: '500',
    }}>
      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: category.color, flexShrink: 0 }} />
      {category.name}
    </span>
  )
}

function CategoryPicker({ categories, value, onChange, onCreateCategory }) {
  const [open, setOpen] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newColor, setNewColor] = useState(PRESET_COLORS[0])
  const [creating, setCreating] = useState(false)
  const ref = useRef(null)
  const selected = categories?.find(c => c.id === value)

  useEffect(() => {
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false)
        setShowCreate(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const handleCreate = async () => {
    if (!newName.trim() || creating) return
    setCreating(true)
    try {
      const created = await onCreateCategory({ name: newName.trim(), color: newColor })
      onChange(created.id)
      setShowCreate(false)
      setNewName('')
      setNewColor(PRESET_COLORS[0])
      setOpen(false)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <div
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', border: '0.5px solid #D3D1C7', borderRadius: '8px',
          padding: '9px 12px', fontSize: '13px', background: 'white', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: '8px', boxSizing: 'border-box',
        }}
      >
        {selected ? (
          <>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: selected.color, flexShrink: 0 }} />
            <span style={{ color: '#1C1C1A', flex: 1 }}>{selected.name}</span>
          </>
        ) : (
          <span style={{ color: '#888780', flex: 1 }}>Sin categoría</span>
        )}
        <span style={{ color: '#B4B2A9', fontSize: '10px', flexShrink: 0 }}>▾</span>
      </div>

      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0, zIndex: 200,
          background: 'white', border: '0.5px solid #D3D1C7', borderRadius: '8px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.08)', maxHeight: '260px', overflowY: 'auto',
        }}>
          <div
            onMouseDown={() => { onChange(''); setOpen(false) }}
            style={{ padding: '8px 12px', cursor: 'pointer', fontSize: '13px', color: '#888780', borderBottom: '0.5px solid #F1EFE8' }}
            onMouseEnter={e => e.currentTarget.style.background = '#F8F8F6'}
            onMouseLeave={e => e.currentTarget.style.background = ''}
          >
            — Sin categoría
          </div>

          {categories?.map(cat => (
            <div
              key={cat.id}
              onMouseDown={() => { onChange(cat.id); setOpen(false) }}
              style={{
                padding: '8px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
                borderBottom: '0.5px solid #F1EFE8', background: value === cat.id ? '#F8F8F6' : '',
              }}
              onMouseEnter={e => e.currentTarget.style.background = '#F8F8F6'}
              onMouseLeave={e => e.currentTarget.style.background = value === cat.id ? '#F8F8F6' : ''}
            >
              <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: cat.color, flexShrink: 0 }} />
              <span style={{ fontSize: '13px', color: '#1C1C1A' }}>{cat.name}</span>
            </div>
          ))}

          {!showCreate ? (
            <div
              onMouseDown={e => { e.preventDefault(); setShowCreate(true) }}
              style={{ padding: '8px 12px', cursor: 'pointer', fontSize: '12px', color: '#185FA5', fontWeight: '500', display: 'flex', alignItems: 'center', gap: '5px' }}
              onMouseEnter={e => e.currentTarget.style.background = '#F8F8F6'}
              onMouseLeave={e => e.currentTarget.style.background = ''}
            >
              + Nueva categoría
            </div>
          ) : (
            <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: '8px', borderTop: '0.5px solid #F1EFE8' }}>
              <input
                type="text"
                placeholder="Nombre de la categoría"
                value={newName}
                onChange={e => setNewName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleCreate()}
                autoFocus
                style={{ border: '0.5px solid #D3D1C7', borderRadius: '6px', padding: '6px 10px', fontSize: '12px', outline: 'none', boxSizing: 'border-box', width: '100%' }}
              />
              <div style={{ display: 'flex', gap: '5px', alignItems: 'center', flexWrap: 'wrap' }}>
                {PRESET_COLORS.map(c => (
                  <button
                    key={c}
                    type="button"
                    onMouseDown={() => setNewColor(c)}
                    style={{
                      width: '18px', height: '18px', borderRadius: '50%', background: c, padding: 0, cursor: 'pointer',
                      border: newColor === c ? '2.5px solid #1C1C1A' : '2px solid transparent', flexShrink: 0,
                    }}
                  />
                ))}
                <input
                  type="color"
                  value={newColor}
                  onChange={e => setNewColor(e.target.value)}
                  title="Color personalizado"
                  style={{ width: '18px', height: '18px', padding: 0, border: 'none', cursor: 'pointer', borderRadius: '50%', flexShrink: 0 }}
                />
              </div>
              <div style={{ display: 'flex', gap: '6px' }}>
                <button
                  type="button"
                  onMouseDown={handleCreate}
                  disabled={creating || !newName.trim()}
                  style={{ background: '#185FA5', color: 'white', border: 'none', padding: '5px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: '500', cursor: 'pointer', flex: 1 }}
                >
                  {creating ? 'Creando...' : 'Crear'}
                </button>
                <button
                  type="button"
                  onMouseDown={() => { setShowCreate(false); setNewName(''); setNewColor(PRESET_COLORS[0]) }}
                  style={{ background: '#F1EFE8', color: '#5F5E5A', border: 'none', padding: '5px 10px', borderRadius: '6px', fontSize: '11px', cursor: 'pointer' }}
                >
                  Cancelar
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ProductsSection() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', barcode: '', category_id: '', units_per_location: '' })
  const [formImage, setFormImage] = useState(null)
  const [imageModal, setImageModal] = useState(null)
  const [deleteModal, setDeleteModal] = useState(null)
  const formImageInputRef = useRef(null)

  const { data: products, isLoading } = useQuery({ queryKey: ['products'], queryFn: getProducts })
  const { data: categories = [] } = useQuery({ queryKey: ['categories'], queryFn: getCategories })
  const { data: summary = [] } = useQuery({ queryKey: ['inventory-summary'], queryFn: getInventorySummary })
  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })

  const createMutation = useMutation({
    mutationFn: createProduct,
    onSuccess: () => queryClient.invalidateQueries(['products']),
  })

  const createCategoryMutation = useMutation({
    mutationFn: createCategory,
    onSuccess: () => queryClient.invalidateQueries(['categories']),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteProduct,
    onSuccess: () => queryClient.invalidateQueries(['products']),
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const created = await createMutation.mutateAsync({
        name: form.name,
        description: form.description || null,
        barcode: form.barcode || null,
        category_id: form.category_id || null,
        units_per_location: form.units_per_location ? parseInt(form.units_per_location) : null,
      })
      if (formImage) {
        await uploadProductImage({ productId: created.id, file: formImage })
        queryClient.invalidateQueries(['products'])
      }
      setShowForm(false)
      setForm({ name: '', description: '', barcode: '', category_id: '', units_per_location: '' })
      setFormImage(null)
    } catch {}
  }

  const summaryMap = Object.fromEntries(summary.map((p) => [p.product_id, p]))

  const totalUnits = summary.reduce((acc, p) => acc + p.total_units, 0)
  const productsWithStock = summary.filter((p) => p.total_units > 0).length
  const totalLocationsCapacity = warehouses.reduce((acc, w) => acc + (w.total_locations || 0), 0)
  const occupiedLocations = summary.reduce((acc, p) => acc + p.locations_count, 0)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '500', color: '#1C1C1A' }}>Productos</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          style={{ background: '#185FA5', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}
        >
          + Nuevo producto
        </button>
      </div>

      {/* Métricas globales */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
        {[
          { label: 'Productos distintos', value: productsWithStock },
          { label: 'Total unidades', value: totalUnits.toLocaleString() },
          {
            label: 'Ocupación',
            value: totalLocationsCapacity > 0
              ? `${occupiedLocations} / ${totalLocationsCapacity}`
              : `${occupiedLocations} huecos`,
          },
        ].map(({ label, value }) => (
          <div key={label} style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '20px 24px' }}>
            <div style={{ fontSize: '11px', fontWeight: '500', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '8px' }}>{label}</div>
            <div style={{ fontSize: '24px', fontWeight: '600', color: '#1C1C1A' }}>{value}</div>
          </div>
        ))}
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#1C1C1A', margin: 0 }}>Nuevo producto</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={labelStyle}>Nombre</label>
              <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} style={inputStyle} required />
            </div>
            <div>
              <label style={labelStyle}>Categoría</label>
              <CategoryPicker
                categories={categories}
                value={form.category_id}
                onChange={v => setForm({ ...form, category_id: v })}
                onCreateCategory={data => createCategoryMutation.mutateAsync(data)}
              />
            </div>
            <div>
              <label style={labelStyle}>Código de barras</label>
              <input type="text" value={form.barcode} onChange={(e) => setForm({ ...form, barcode: e.target.value })} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Descripción</label>
              <input type="text" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Unidades máx. por ubicación</label>
              <input
                type="number"
                min="1"
                value={form.units_per_location}
                onChange={(e) => setForm({ ...form, units_per_location: e.target.value })}
                placeholder="1"
                style={{ ...inputStyle, width: '160px' }}
              />
            </div>
          </div>
          <div>
            <label style={labelStyle}>Foto (opcional)</label>
            <input
              ref={formImageInputRef}
              type="file"
              accept="image/jpeg,image/png,image/gif,image/webp"
              style={{ display: 'none' }}
              onChange={e => setFormImage(e.target.files?.[0] || null)}
            />
            {formImage ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <img src={URL.createObjectURL(formImage)} alt="preview" style={{ width: '56px', height: '56px', objectFit: 'cover', borderRadius: '8px', border: '0.5px solid #D3D1C7' }} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ fontSize: '12px', color: '#5F5E5A' }}>{formImage.name}</span>
                  <button type="button" onClick={() => setFormImage(null)} style={{ background: 'none', border: 'none', color: '#A32D2D', fontSize: '12px', cursor: 'pointer', padding: 0, textAlign: 'left' }}>Quitar</button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => formImageInputRef.current?.click()}
                style={{ background: '#F8F8F6', border: '0.5px dashed #D3D1C7', borderRadius: '8px', padding: '11px 16px', fontSize: '13px', color: '#888780', cursor: 'pointer', width: '100%', textAlign: 'left', display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                  <circle cx="12" cy="13" r="4"/>
                </svg>
                Añadir foto del producto
              </button>
            )}
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button type="submit" disabled={createMutation.isLoading}
              style={{ background: '#185FA5', color: 'white', border: 'none', padding: '9px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}>
              {createMutation.isLoading ? 'Creando...' : 'Crear producto'}
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
      ) : products?.length === 0 ? (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '40px', textAlign: 'center', color: '#888780', fontSize: '13px' }}>
          No hay productos registrados
        </div>
      ) : (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ background: '#FAFAFA' }}>
                {['Nombre', 'Categoría', 'Código de barras', 'Descripción', 'Máx./ubic.', 'Unidades', 'Entradas pend.', 'Salidas pend.', ''].map((h) => (
                  <th key={h} style={{ textAlign: 'left', padding: '10px 20px', color: '#888780', fontWeight: '500', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '0.5px solid #E5E4E0' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {products?.map((product) => {
                const inv = summaryMap[product.id]
                const units = inv?.total_units ?? 0
                return (
                  <tr key={product.id} style={{ borderTop: '0.5px solid #F1EFE8' }}>
                    <td style={{ padding: '12px 20px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <button
                          type="button"
                          onClick={() => setImageModal(product)}
                          title={product.image_url ? 'Ver / cambiar imagen' : 'Añadir imagen'}
                          style={{ flexShrink: 0, width: '36px', height: '36px', borderRadius: '6px', overflow: 'hidden', border: '0.5px solid #E5E4E0', background: '#F8F8F6', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0 }}
                        >
                          {product.image_url ? (
                            <img src={`${API_BASE}/${product.image_url}`} alt={product.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                          ) : (
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#C8C7C2" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                              <circle cx="12" cy="13" r="4"/>
                            </svg>
                          )}
                        </button>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'flex-start' }}>
                          <span style={{ color: '#1C1C1A', fontWeight: '500' }}>{product.name}</span>
                          {units === 0 && (
                            <span style={{ background: '#FEE2E2', color: '#B91C1C', fontSize: '10px', fontWeight: '500', padding: '2px 7px', borderRadius: '10px', textTransform: 'uppercase', letterSpacing: '0.04em', whiteSpace: 'nowrap' }}>Sin stock</span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '12px 20px' }}>
                      <CategoryBadge category={product.category} />
                    </td>
                    <td style={{ padding: '12px 20px', color: '#5F5E5A', fontFamily: 'monospace', fontSize: '12px' }}>{product.barcode || '—'}</td>
                    <td style={{ padding: '12px 20px', color: '#5F5E5A' }}>{product.description || '—'}</td>
                    <td style={{ padding: '12px 20px', color: '#5F5E5A', textAlign: 'center' }}>
                      {product.units_per_location != null ? product.units_per_location : <span style={{ color: '#C8C7C2' }}>—</span>}
                    </td>
                    <td style={{ padding: '12px 20px' }}>
                      <span style={{ fontSize: '15px', fontWeight: '600', color: '#1C1C1A' }}>{units}</span>
                    </td>
                    <td style={{ padding: '12px 20px' }}>
                      {inv?.pending_in > 0 ? (
                        <span style={{ background: '#ECFDF5', color: '#15803D', fontSize: '12px', fontWeight: '500', padding: '3px 9px', borderRadius: '10px' }}>↑ {inv.pending_in} ud.</span>
                      ) : (
                        <span style={{ color: '#C8C7C2', fontSize: '12px' }}>—</span>
                      )}
                    </td>
                    <td style={{ padding: '12px 20px' }}>
                      {inv?.pending_out > 0 ? (
                        <span style={{ background: '#FFFBEB', color: '#B45309', fontSize: '12px', fontWeight: '500', padding: '3px 9px', borderRadius: '10px' }}>↓ {inv.pending_out} ud.</span>
                      ) : (
                        <span style={{ color: '#C8C7C2', fontSize: '12px' }}>—</span>
                      )}
                    </td>
                    <td style={{ padding: '12px 20px', textAlign: 'right' }}>
                      <button onClick={() => setDeleteModal(product)}
                        style={{ background: 'none', border: 'none', color: '#C8C7C2', cursor: 'pointer', padding: '4px', lineHeight: 0 }}
                        onMouseEnter={e => e.currentTarget.style.color = '#A32D2D'}
                        onMouseLeave={e => e.currentTarget.style.color = '#C8C7C2'}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                          <path d="M10 11v6" />
                          <path d="M14 11v6" />
                          <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {imageModal && (
        <div
          style={{ position: 'fixed', inset: 0, zIndex: 1100, background: 'rgba(28,28,26,0.18)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={() => setImageModal(null)}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{ background: 'white', borderRadius: '14px', border: '0.5px solid #E5E4E0', padding: '28px', boxShadow: '0 8px 32px rgba(0,0,0,0.10)', width: '380px', display: 'flex', flexDirection: 'column', gap: '16px' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '15px', fontWeight: '600', color: '#1C1C1A' }}>{imageModal.name}</span>
              <button onClick={() => setImageModal(null)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#888780', fontSize: '16px', lineHeight: 1 }}>✕</button>
            </div>

            <div style={{ borderRadius: '10px', overflow: 'hidden', border: '0.5px solid #E5E4E0', background: '#F8F8F6', minHeight: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {imageModal.image_url ? (
                <img src={`${API_BASE}/${imageModal.image_url}`} alt={imageModal.name} style={{ width: '100%', maxHeight: '260px', objectFit: 'contain' }} />
              ) : (
                <div style={{ textAlign: 'center', color: '#B4B2A9', padding: '40px 20px' }}>
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: '10px', opacity: 0.5 }}>
                    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                    <circle cx="12" cy="13" r="4"/>
                  </svg>
                  <p style={{ fontSize: '13px', margin: 0 }}>Sin imagen</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {deleteModal && (() => {
        const hasStock = (summaryMap[deleteModal.id]?.total_units ?? 0) > 0
        return (
          <div
            style={{ position: 'fixed', inset: 0, zIndex: 1100, background: 'rgba(28,28,26,0.18)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            onClick={() => setDeleteModal(null)}
          >
            <div
              onClick={e => e.stopPropagation()}
              style={{ background: 'white', borderRadius: '14px', border: '0.5px solid #E5E4E0', padding: '28px 28px 24px', boxShadow: '0 8px 32px rgba(0,0,0,0.10)', width: '360px', display: 'flex', flexDirection: 'column', gap: '20px' }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <span style={{ fontSize: '15px', fontWeight: '600', color: '#1C1C1A' }}>Eliminar producto</span>
                {hasStock ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ background: '#FEF3C7', border: '0.5px solid #FCD34D', borderRadius: '8px', padding: '10px 14px', display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                      <span style={{ fontSize: '14px', flexShrink: 0, marginTop: '1px' }}>⚠️</span>
                      <span style={{ fontSize: '13px', color: '#92400E', lineHeight: '1.55' }}>
                        <strong>{deleteModal.name}</strong> tiene {summaryMap[deleteModal.id].total_units} unidades en el almacén. Retira todo el stock antes de eliminar el producto.
                      </span>
                    </div>
                  </div>
                ) : (
                  <span style={{ fontSize: '13px', color: '#5F5E5A', lineHeight: '1.55' }}>
                    ¿Seguro que quieres eliminar <strong style={{ color: '#1C1C1A' }}>{deleteModal.name}</strong>? Esta acción no se puede deshacer.
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                <button
                  onClick={() => setDeleteModal(null)}
                  style={{ background: '#F1EFE8', color: '#5F5E5A', border: 'none', padding: '8px 18px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer' }}
                >
                  {hasStock ? 'Cerrar' : 'Cancelar'}
                </button>
                {!hasStock && (
                  <button
                    onClick={() => { deleteMutation.mutate(deleteModal.id); setDeleteModal(null) }}
                    disabled={deleteMutation.isLoading}
                    style={{ background: '#A32D2D', color: 'white', border: 'none', padding: '8px 18px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}
                  >
                    Eliminar
                  </button>
                )}
              </div>
            </div>
          </div>
        )
      })()}
    </div>
  )
}
