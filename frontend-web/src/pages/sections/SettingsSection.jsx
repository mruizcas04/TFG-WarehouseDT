import { useQuery } from '@tanstack/react-query'
import { getMe } from '../../api/auth'

const ROLE_LABELS = {
  administrador: 'Administrador',
  trabajador:    'Trabajador',
}

const formatDate = (iso) => {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

export default function SettingsSection({ onLogout }) {
  const { data: me, isLoading, error } = useQuery({ queryKey: ['me'], queryFn: getMe })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <h2 style={{ fontSize: '20px', fontWeight: '500', color: '#1C1C1A' }}>Ajustes</h2>

      {isLoading && <p style={{ color: '#888780', fontSize: '13px' }}>Cargando datos del administrador…</p>}
      {error && <p style={{ color: '#C0392B', fontSize: '13px' }}>No se pudieron cargar los datos del administrador.</p>}

      {me && (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px' }}>
          <h3 style={{ fontSize: '15px', fontWeight: '500', color: '#1C1C1A', marginBottom: '16px' }}>Mi cuenta</h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
            {[
              { label: 'Nombre',         value: me.name },
              { label: 'Email',          value: me.email },
              { label: 'Rol',            value: ROLE_LABELS[me.role] || me.role },
              { label: 'Estado',         value: me.is_active ? 'Activo' : 'Inactivo' },
              { label: 'Conexión',       value: me.is_online ? 'En línea' : 'Desconectado' },
              { label: 'Último login',   value: formatDate(me.last_login) },
              { label: 'Cuenta creada',  value: formatDate(me.created_at) },
            ].map((f) => (
              <div key={f.label}>
                <div style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>{f.label}</div>
                <div style={{ fontSize: '13px', color: '#1C1C1A' }}>{f.value || '—'}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px' }}>
        <h3 style={{ fontSize: '15px', fontWeight: '500', color: '#1C1C1A', marginBottom: '4px' }}>Sesión</h3>
        <p style={{ fontSize: '12px', color: '#888780', marginBottom: '16px' }}>Cerrar la sesión actual y volver a la pantalla de login.</p>
        <button
          onClick={onLogout}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: '8px',
            background: '#A32D2D', color: 'white', border: 'none',
            padding: '9px 18px', borderRadius: '8px', fontSize: '13px',
            fontWeight: '500', cursor: 'pointer',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 15 15" fill="none">
            <path d="M6 13H3a1 1 0 01-1-1V3a1 1 0 011-1h3M10 10l3-2.5L10 5M13 7.5H6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Cerrar sesión
        </button>
      </div>
    </div>
  )
}
