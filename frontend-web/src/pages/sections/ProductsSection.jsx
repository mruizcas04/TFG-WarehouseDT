import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getProducts, createProduct, deleteProduct } from '../../api/products'
import { getInventorySummary } from '../../api/inventory'
import { getWarehouses } from '../../api/warehouses'

export default function ProductsSection() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', type: '', barcode: '' })

  const { data: products, isLoading } = useQuery({ queryKey: ['products'], queryFn: getProducts })
  const { data: summary = [] } = useQuery({ queryKey: ['inventory-summary'], queryFn: getInventorySummary })
  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })

  const createMutation = useMutation({
    mutationFn: createProduct,
    onSuccess: () => {
      queryClient.invalidateQueries(['products'])
      setShowForm(false)
      setForm({ name: '', description: '', type: '', barcode: '' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteProduct,
    onSuccess: () => queryClient.invalidateQueries(['products']),
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    createMutation.mutate(form)
  }

  const inputStyle = { width: '100%', border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '9px 12px', fontSize: '13px', color: '#1C1C1A', outline: 'none' }
  const labelStyle = { display: 'block', fontSize: '11px', fontWeight: '500', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }

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
          <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#1C1C1A' }}>Nuevo producto</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={labelStyle}>Nombre</label>
              <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} style={inputStyle} required />
            </div>
            <div>
              <label style={labelStyle}>Tipo</label>
              <input type="text" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Código de barras</label>
              <input type="text" value={form.barcode} onChange={(e) => setForm({ ...form, barcode: e.target.value })} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Descripción</label>
              <input type="text" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} style={inputStyle} />
            </div>
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
                {['Nombre', 'Tipo', 'Código de barras', 'Descripción', 'Unidades', 'Entradas pend.', 'Salidas pend.', ''].map((h) => (
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
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'flex-start' }}>
                        <span style={{ color: '#1C1C1A', fontWeight: '500' }}>{product.name}</span>
                        {units === 0 && (
                          <span style={{ background: '#FEE2E2', color: '#B91C1C', fontSize: '10px', fontWeight: '500', padding: '2px 7px', borderRadius: '10px', textTransform: 'uppercase', letterSpacing: '0.04em', whiteSpace: 'nowrap' }}>Sin stock</span>
                        )}
                      </div>
                    </td>
                    <td style={{ padding: '12px 20px', color: '#5F5E5A' }}>{product.type || '—'}</td>
                    <td style={{ padding: '12px 20px', color: '#5F5E5A', fontFamily: 'monospace', fontSize: '12px' }}>{product.barcode || '—'}</td>
                    <td style={{ padding: '12px 20px', color: '#5F5E5A' }}>{product.description || '—'}</td>
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
                      <button onClick={() => deleteMutation.mutate(product.id)}
                        style={{ background: 'none', border: 'none', color: '#A32D2D', cursor: 'pointer', padding: '4px', lineHeight: 0 }}>
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
    </div>
  )
}
