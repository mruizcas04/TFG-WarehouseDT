import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getTasks, createTask } from '../../api/tasks'
import { getUsers } from '../../api/users'

export default function TasksSection() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ assigned_to: '', type: 'entrada' })

  const { data: tasks, isLoading } = useQuery({ queryKey: ['tasks'], queryFn: getTasks })
  const { data: users } = useQuery({ queryKey: ['users'], queryFn: getUsers })

  const workers = users?.filter((u) => u.role === 'worker')

  const createMutation = useMutation({
    mutationFn: createTask,
    onSuccess: () => {
      queryClient.invalidateQueries(['tasks'])
      setShowForm(false)
      setForm({ assigned_to: '', type: 'entrada' })
    },
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    createMutation.mutate(form)
  }

  const inputStyle = { width: '100%', border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '9px 12px', fontSize: '13px', color: '#1C1C1A', outline: 'none' }
  const labelStyle = { display: 'block', fontSize: '11px', fontWeight: '500', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }

  const statusLabel = (s) => ({ pendiente: 'Pendiente', en_curso: 'En curso', completada: 'Completada' })[s] || s
  const statusBadge = (s) => ({ pendiente: { bg: '#FAEEDA', color: '#854F0B' }, en_curso: { bg: '#E6F1FB', color: '#185FA5' }, completada: { bg: '#EAF3DE', color: '#3B6D11' } })[s] || { bg: '#F1EFE8', color: '#888780' }
  const typeLabel = (t) => ({ entrada: 'Entrada', salida: 'Salida', traslado: 'Traslado' })[t] || t
  const typeBadge = (t) => ({ entrada: { bg: '#EAF3DE', color: '#3B6D11' }, salida: { bg: '#FAEEDA', color: '#854F0B' }, traslado: { bg: '#EEEDFE', color: '#534AB7' } })[t] || { bg: '#F1EFE8', color: '#888780' }
  const getUserName = (id) => users?.find((u) => u.id === id)?.name || '—'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '500', color: '#1C1C1A' }}>Tareas</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          style={{ background: '#185FA5', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}
        >
          + Nueva tarea
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#1C1C1A' }}>Nueva tarea</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={labelStyle}>Asignar a</label>
              <select value={form.assigned_to} onChange={(e) => setForm({ ...form, assigned_to: e.target.value })} style={inputStyle} required>
                <option value="">Selecciona un trabajador</option>
                {workers?.map((w) => (
                  <option key={w.id} value={w.id}>{w.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Tipo de operación</label>
              <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} style={inputStyle}>
                <option value="entrada">Entrada</option>
                <option value="salida">Salida</option>
                <option value="traslado">Traslado</option>
              </select>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button type="submit" disabled={createMutation.isLoading}
              style={{ background: '#185FA5', color: 'white', border: 'none', padding: '9px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}>
              {createMutation.isLoading ? 'Creando...' : 'Crear tarea'}
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
      ) : tasks?.length === 0 ? (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '40px', textAlign: 'center', color: '#888780', fontSize: '13px' }}>
          No hay tareas creadas
        </div>
      ) : (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ background: '#FAFAFA' }}>
                {['Tipo', 'Asignado a', 'Creado por', 'Estado', 'Fecha'].map((h) => (
                  <th key={h} style={{ textAlign: 'left', padding: '10px 20px', color: '#888780', fontWeight: '500', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '0.5px solid #E5E4E0' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tasks?.map((task) => {
                const sb = statusBadge(task.status)
                const tb = typeBadge(task.type)
                return (
                  <tr key={task.id} style={{ borderTop: '0.5px solid #F1EFE8' }}>
                    <td style={{ padding: '12px 20px' }}>
                      <span style={{ background: tb.bg, color: tb.color, padding: '2px 8px', borderRadius: '20px', fontSize: '11px', fontWeight: '500' }}>
                        {typeLabel(task.type)}
                      </span>
                    </td>
                    <td style={{ padding: '12px 20px', color: '#1C1C1A', fontWeight: '500' }}>{getUserName(task.assigned_to)}</td>
                    <td style={{ padding: '12px 20px', color: '#5F5E5A' }}>{getUserName(task.created_by)}</td>
                    <td style={{ padding: '12px 20px' }}>
                      <span style={{ background: sb.bg, color: sb.color, padding: '2px 8px', borderRadius: '20px', fontSize: '11px', fontWeight: '500' }}>
                        {statusLabel(task.status)}
                      </span>
                    </td>
                    <td style={{ padding: '12px 20px', color: '#888780' }}>
                      {new Date(task.created_at).toLocaleDateString('es-ES')}
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