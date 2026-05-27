import { useQuery } from '@tanstack/react-query'
import { getMe } from '../../api/auth'

const ROLE_LABELS = {
  admin:  'Administrador',
  worker: 'Operario',
}

const formatDate = (iso) => {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' })
  } catch { return iso }
}

export default function SettingsSection({ onLogout }) {
  const { data: me, isLoading, error } = useQuery({ queryKey: ['me'], queryFn: getMe })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <h2 style={{ fontSize: '20px', fontWeight: '500', color: '#1C1C1A' }}>Ajustes</h2>

      {isLoading && <p style={{ color: '#888780', fontSize: '13px' }}>Cargando datos…</p>}
      {error && <p style={{ color: '#C0392B', fontSize: '13px' }}>No se pudieron cargar los datos.</p>}

      {me && (
        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #E5E4E0', padding: '24px' }}>
          {/* Avatar + datos: avatar fijo en esquina superior izquierda */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '20px', marginBottom: '24px' }}>
            {/* Avatar */}
            <div style={{
              width: '56px', height: '56px', borderRadius: '14px',
              background: '#E6F1FB', border: '1.5px solid #C5DEFA',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="8" r="4" stroke="#185FA5" strokeWidth="1.5"/>
                <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="#185FA5" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </div>

            {/* Nombre y rol como cabecera */}
            <div style={{ paddingTop: '4px' }}>
              <div style={{ fontSize: '15px', fontWeight: '500', color: '#1C1C1A' }}>{me.name || '—'}</div>
              <div style={{ fontSize: '12px', color: '#888780', marginTop: '2px' }}>{ROLE_LABELS[me.role] || me.role}</div>
            </div>
          </div>

          {/* Campos de datos */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
            {[
              { label: 'Nombre',        value: me.name },
              { label: 'Email',         value: me.email },
              { label: 'Rol',           value: ROLE_LABELS[me.role] || me.role },
              { label: 'Cuenta creada', value: formatDate(me.created_at) },
            ].map((f) => (
              <div key={f.label}>
                <div style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>{f.label}</div>
                <div style={{ fontSize: '13px', color: '#1C1C1A' }}>{f.value || '—'}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Botón de cerrar sesión centrado */}
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: '8px' }}>
        <button
          onClick={onLogout}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: '8px',
            background: '#A32D2D', color: 'white', border: 'none',
            padding: '10px 24px', borderRadius: '8px', fontSize: '13px',
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
