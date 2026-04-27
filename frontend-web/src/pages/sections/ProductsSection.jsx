import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getProducts, createProduct, deleteProduct } from '../../api/products'

export default function ProductsSection() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', type: '', barcode: '' })

  const { data: products, isLoading } = useQuery({ queryKey: ['products'], queryFn: getProducts })

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
                {['Nombre', 'Tipo', 'Código de barras', 'Descripción', ''].map((h) => (
                  <th key={h} style={{ textAlign: 'left', padding: '10px 20px', color: '#888780', fontWeight: '500', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '0.5px solid #E5E4E0' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {products?.map((product) => (
                <tr key={product.id} style={{ borderTop: '0.5px solid #F1EFE8' }}>
                  <td style={{ padding: '12px 20px', color: '#1C1C1A', fontWeight: '500' }}>{product.name}</td>
                  <td style={{ padding: '12px 20px', color: '#5F5E5A' }}>{product.type || '—'}</td>
                  <td style={{ padding: '12px 20px', color: '#5F5E5A', fontFamily: 'monospace', fontSize: '12px' }}>{product.barcode || '—'}</td>
                  <td style={{ padding: '12px 20px', color: '#5F5E5A' }}>{product.description || '—'}</td>
                  <td style={{ padding: '12px 20px', textAlign: 'right' }}>
                    <button onClick={() => deleteMutation.mutate(product.id)}
                      style={{ background: 'none', border: 'none', color: '#A32D2D', fontSize: '12px', cursor: 'pointer', fontWeight: '500' }}>
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}