import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getUsers, getInactiveUsers, createUser, deactivateUser } from '../../api/users'
import { useAuthStore } from '../../store/authStore'

export default function UsersSection() {
  const queryClient = useQueryClient()
  const currentUser = useAuthStore((s) => s.user)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', role: 'worker' })
  const [createdUserEmail, setCreatedUserEmail] = useState(null)
  const [deactivateModal, setDeactivateModal] = useState(null)
  const [showInactive, setShowInactive] = useState(false)

  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: getUsers,
    staleTime: 30_000,
  })
  const { data: inactiveUsers, isLoading: isLoadingInactive } = useQuery({
    queryKey: ['users-inactive'],
    queryFn: getInactiveUsers,
    enabled: showInactive,
  })

  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: (data) => {
      queryClient.invalidateQueries(['users'])
      setCreatedUserEmail(data.email)
      setShowForm(false)
      setForm({ name: '', email: '', role: 'worker' })
    },
  })

  const deactivateMutation = useMutation({
    mutationFn: deactivateUser,
    onSuccess: () => {
      queryClient.invalidateQueries(['users'])
      queryClient.invalidateQueries(['users-inactive'])
    },
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    createMutation.mutate(form)
  }

  const handleDeactivate = (user) => {
    setDeactivateModal({ userId: user.id, name: user.name })
  }

  const inputStyle = { width: '100%', border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '9px 12px', fontSize: '13px', color: '#1C1C1A', outline: 'none', boxSizing: 'border-box' }
  const labelStyle = { display: 'block', fontSize: '11px', fontWeight: '500', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }

  const roleLabel = (role) => role === 'admin' ? 'Administrador' : 'Operario'
  const roleBadge = (role) => role === 'admin'
    ? { bg: '#EEEDFE', color: '#534AB7' }
    : { bg: '#EAF3DE', color: '#3B6D11' }

  const getInitials = (name) => {
    const parts = name.trim().split(/\s+/)
    return parts.length >= 2 ? (parts[0][0] + parts[1][0]).toUpperCase() : name.slice(0, 2).toUpperCase()
  }

  const UserRow = ({ user, inactive = false }) => {
    const badge = roleBadge(user.role)
    const isCurrentUser = currentUser && currentUser.id === user.id
    const showOnline = !inactive && user.role === 'worker'
    return (
      <tr style={{ borderTop: '0.5px solid #F1EFE8', opacity: inactive ? 0.75 : 1 }}>
        <td style={{ padding: '12px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {/* Avatar con indicador online */}
            <div style={{ position: 'relative', flexShrink: 0 }}>
              <div style={{ width: '30px', height: '30px', borderRadius: '50%', background: inactive ? '#F1EFE8' : '#E6F1FB', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', fontWeight: '500', color: inactive ? '#888780' : '#185FA5' }}>
                {getInitials(user.name)}
              </div>
              {showOnline && (
                <span
                  title={user.is_online ? 'Conectado' : 'Desconectado'}
                  style={{
                    position: 'absolute', bottom: 0, right: 0,
                    width: '9px', height: '9px', borderRadius: '50%',
                    background: user.is_online ? '#2ECC71' : '#D3D1C7',
                    border: '1.5px solid white',
                  }}
                />
              )}
            </div>
            <span style={{ fontWeight: '500', color: '#1C1C1A' }}>{user.name}</span>
            {inactive && (
              <span style={{ background: '#FFE0E0', color: '#CC2929', padding: '1px 7px', borderRadius: '20px', fontSize: '10px', fontWeight: '600' }}>Dado de baja</span>
            )}
          </div>
        </td>
        <td style={{ padding: '12px 20px', color: '#5F5E5A' }}>{user.email}</td>
        <td style={{ padding: '12px 20px' }}>
          <span style={{ background: badge.bg, color: badge.color, padding: '2px 8px', borderRadius: '20px', fontSize: '11px', fontWeight: '500' }}>
            {roleLabel(user.role)}
          </span>
        </td>
        {!inactive && (
          <td style={{ padding: '12px 20px' }}>
            {user.role === 'worker' ? (
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: '5px',
                background: user.is_online ? '#EDFAF3' : '#F8F8F6',
                color: user.is_online ? '#1A9A5A' : '#888780',
                padding: '3px 9px', borderRadius: '20px', fontSize: '11px', fontWeight: '500',
              }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: user.is_online ? '#2ECC71' : '#D3D1C7', flexShrink: 0 }} />
                {user.is_online ? 'Conectado' : 'Desconectado'}
              </span>
            ) : (
              <span style={{ color: '#D3D1C7', fontSize: '12px' }}>—</span>
            )}
          </td>
        )}
        <td style={{ padding: '12px 20px', color: '#888780' }}>
          {new Date(user.created_at).toLocaleDateString('es-ES')}
        </td>
        {!inactive && (
          <td style={{ padding: '12px 20px' }}>
            {!isCurrentUser && user.role !== 'admin' && (
              <button
                onClick={() => handleDeactivate(user)}
                disabled={deactivateMutation.isLoading}
                title="Dar de baja"
                style={{ background: '#FFF0F0', color: '#CC2929', border: '0.5px solid #FFCCCC', padding: '5px 10px', borderRadius: '6px', fontSize: '12px', cursor: 'pointer', fontWeight: '500' }}
              >
                Dar de baja
              </button>
            )}
          </td>
        )}
      </tr>
    )
  }

  const activeHeaders = ['Usuario', 'Email', 'Rol', 'Estado', 'Fecha de registro', 'Acciones']
  const inactiveHeaders = ['Usuario', 'Email', 'Rol', 'Fecha de registro']

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '500', color: '#1C1C1A' }}>Usuarios</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          style={{ background: '#185FA5', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}
        >
          + Nuevo usuario
        </button>
      </div>

      {/* Modal confirmación email enviado */}
      {createdUserEmail && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', borderRadius: '14px', padding: '32px', maxWidth: '400px', width: '90%', boxShadow: '0 8px 32px rgba(0,0,0,0.18)', display: 'flex', flexDirection: 'column', gap: '16px', textAlign: 'center' }}>
            <div style={{ width: '48px', height: '48px', borderRadius: '50%', background: '#EDFAF3', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto' }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1A9A5A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>
            <div>
              <p style={{ fontSize: '15px', fontWeight: '600', color: '#1C1C1A', margin: '0 0 6px 0' }}>Usuario creado</p>
              <p style={{ fontSize: '13px', color: '#5F5E5A', margin: 0, lineHeight: '1.5' }}>
                Se ha enviado un email con las credenciales de acceso a <strong>{createdUserEmail}</strong>.
              </p>
            </div>
            <button
              onClick={() => setCreatedUserEmail(null)}
              style={{ background: '#1C1C1A', color: 'white', border: 'none', padding: '10px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}
            >
              Entendido
            </button>
          </div>
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#1C1C1A' }}>Nuevo usuario</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={labelStyle}>Nombre</label>
              <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} style={inputStyle} required />
            </div>
            <div>
              <label style={labelStyle}>Email</label>
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} style={inputStyle} required />
            </div>
            <div>
              <label style={labelStyle}>Rol</label>
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} style={inputStyle}>
                <option value="worker">Operario</option>
              </select>
            </div>
          </div>
          <p style={{ margin: 0, fontSize: '12px', color: '#888780' }}>Se generará una contraseña temporal y se enviará por email al usuario junto con sus credenciales de acceso.</p>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button type="submit" disabled={createMutation.isLoading}
              style={{ background: '#185FA5', color: 'white', border: 'none', padding: '9px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}>
              {createMutation.isLoading ? 'Creando...' : 'Crear usuario'}
            </button>
            <button type="button" onClick={() => setShowForm(false)}
              style={{ background: '#F1EFE8', color: '#5F5E5A', border: 'none', padding: '9px 16px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer' }}>
              Cancelar
            </button>
          </div>
        </form>
      )}

      {/* Tabla usuarios activos */}
      {isLoading ? (
        <p style={{ color: '#888780', fontSize: '13px' }}>Cargando...</p>
      ) : users?.length === 0 ? (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '40px', textAlign: 'center', color: '#888780', fontSize: '13px' }}>
          No hay usuarios registrados
        </div>
      ) : (
        <>
          <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: '#FAFAFA' }}>
                  {activeHeaders.map((h) => (
                    <th key={h} style={{ textAlign: 'left', padding: '10px 20px', color: '#888780', fontWeight: '500', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '0.5px solid #E5E4E0' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {users.map((user) => <UserRow key={user.id} user={user} />)}
              </tbody>
            </table>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button
              onClick={() => setShowInactive(!showInactive)}
              style={{ background: 'none', border: 'none', color: '#5F5E5A', fontSize: '12px', cursor: 'pointer', padding: '2px 0', display: 'flex', alignItems: 'center', gap: '5px' }}
              onMouseEnter={e => e.currentTarget.style.color = '#1C1C1A'}
              onMouseLeave={e => e.currentTarget.style.color = '#5F5E5A'}
            >
              {showInactive ? 'Ocultar dados de baja' : 'Ver dados de baja'}
            </button>
          </div>
        </>
      )}

      {/* Sección usuarios dados de baja */}
      {showInactive && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '13px', fontWeight: '500', color: '#888780' }}>Dados de baja</span>
            <div style={{ flex: 1, height: '0.5px', background: '#E5E4E0' }} />
          </div>
          {isLoadingInactive ? (
            <p style={{ color: '#888780', fontSize: '13px' }}>Cargando...</p>
          ) : !inactiveUsers?.length ? (
            <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px', textAlign: 'center', color: '#B4B2A9', fontSize: '13px' }}>
              No hay usuarios dados de baja
            </div>
          ) : (
            <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ background: '#FAFAFA' }}>
                    {inactiveHeaders.map((h) => (
                      <th key={h} style={{ textAlign: 'left', padding: '10px 20px', color: '#B4B2A9', fontWeight: '500', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '0.5px solid #E5E4E0' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {inactiveUsers.map((user) => <UserRow key={user.id} user={user} inactive />)}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {deactivateModal && (
        <div
          style={{ position: 'fixed', inset: 0, zIndex: 1100, background: 'rgba(28,28,26,0.18)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={() => setDeactivateModal(null)}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{ background: 'white', borderRadius: '14px', border: '0.5px solid #E5E4E0', padding: '28px 28px 24px', boxShadow: '0 8px 32px rgba(0,0,0,0.10)', width: '360px', display: 'flex', flexDirection: 'column', gap: '20px' }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontSize: '15px', fontWeight: '600', color: '#1C1C1A' }}>Dar de baja</span>
              <span style={{ fontSize: '13px', color: '#5F5E5A', lineHeight: '1.55' }}>
                ¿Seguro que quieres dar de baja a <strong style={{ color: '#1C1C1A' }}>{deactivateModal.name}</strong>? Esta acción desactivará su acceso al sistema.
              </span>
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setDeactivateModal(null)}
                style={{ background: '#F1EFE8', color: '#5F5E5A', border: 'none', padding: '8px 18px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer', fontWeight: '500' }}
              >
                Cancelar
              </button>
              <button
                onClick={() => { deactivateMutation.mutate(deactivateModal.userId); setDeactivateModal(null) }}
                disabled={deactivateMutation.isLoading}
                style={{ background: '#A32D2D', color: 'white', border: 'none', padding: '8px 18px', borderRadius: '8px', fontSize: '13px', fontWeight: '500', cursor: 'pointer' }}
              >
                Dar de baja
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
