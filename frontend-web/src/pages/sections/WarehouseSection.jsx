import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getWarehouses, createWarehouse } from '../../api/warehouses'
import DigitalTwin from '../../components/DigitalTwin'
import { useAuthStore } from '../../store/authStore'

export default function WarehouseSection() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', num_shelves: '', num_levels: '', num_locations: '' })
  const { token } = useAuthStore()

  const { data: warehouses, isLoading } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })

  const mutation = useMutation({
    mutationFn: createWarehouse,
    onSuccess: () => {
      queryClient.invalidateQueries(['warehouses'])
      setShowForm(false)
      setForm({ name: '', num_shelves: '', num_levels: '', num_locations: '' })
    },
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    mutation.mutate({
      name: form.name,
      num_shelves: parseInt(form.num_shelves),
      num_levels: parseInt(form.num_levels),
      num_locations: parseInt(form.num_locations),
    })
  }

  const warehouse = warehouses?.[0]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '500', color: '#1C1C1A' }}>Almacén</h2>
        {!warehouse && (
          <button
            onClick={() => setShowForm(!showForm)}
            style={{ background: '#185FA5', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}
          >
            + Nuevo almacén
          </button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#1C1C1A' }}>Configurar almacén</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div style={{ gridColumn: '1 / -1' }}>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: '500', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }}>Nombre</label>
              <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                style={{ width: '100%', border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '9px 12px', fontSize: '13px', color: '#1C1C1A', outline: 'none' }} required />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: '500', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }}>Estanterías</label>
              <input type="number" min="1" value={form.num_shelves} onChange={(e) => setForm({ ...form, num_shelves: e.target.value })}
                style={{ width: '100%', border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '9px 12px', fontSize: '13px', color: '#1C1C1A', outline: 'none' }} required />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: '500', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }}>Niveles por estantería</label>
              <input type="number" min="1" value={form.num_levels} onChange={(e) => setForm({ ...form, num_levels: e.target.value })}
                style={{ width: '100%', border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '9px 12px', fontSize: '13px', color: '#1C1C1A', outline: 'none' }} required />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: '500', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }}>Ubicaciones por nivel</label>
              <input type="number" min="1" value={form.num_locations} onChange={(e) => setForm({ ...form, num_locations: e.target.value })}
                style={{ width: '100%', border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '9px 12px', fontSize: '13px', color: '#1C1C1A', outline: 'none' }} required />
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
                <div style={{ display: 'flex', gap: '20px' }}>
                  {[
                    { label: 'Estanterías', value: warehouse.num_shelves },
                    { label: 'Niveles', value: warehouse.num_levels },
                    { label: 'Ubicaciones por nivel', value: warehouse.num_locations },
                    { label: 'Total ubicaciones', value: warehouse.num_shelves * warehouse.num_levels * warehouse.num_locations },
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

            {/* Leyenda de colores */}
            <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
              {[
                { color: '#999', label: 'Libre' },
                { color: '#33cc33', label: 'Producto' },
                { color: '#3366ee', label: 'Caja' },
                { color: '#ffdd00', label: 'Tarea activa' },
              ].map(({ color, label }) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: color }} />
                  <span style={{ fontSize: '12px', color: '#888780' }}>{label}</span>
                </div>
              ))}
            </div>

            <DigitalTwin warehouseId={warehouse.id} token={token} />
          </div>
        </>
      )}
    </div>
  )
}