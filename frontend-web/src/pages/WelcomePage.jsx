import { useNavigate } from 'react-router-dom'

const WarehouseLogoIcon = () => (
  <svg width="22" height="22" viewBox="0 0 18 18" fill="none">
    <path d="M1 8L9 2L17 8" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M1 8V16H17V8" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M6 16V12H12V16" stroke="white" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

const BoxIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
    <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
    <line x1="12" y1="22.08" x2="12" y2="12"/>
  </svg>
)

const CubeIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2L2 7l10 5 10-5-10-5z"/>
    <path d="M2 17l10 5 10-5"/>
    <path d="M2 12l10 5 10-5"/>
  </svg>
)

const UsersIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
)

const features = [
  {
    icon: <BoxIcon />,
    title: 'Inventario en tiempo real',
    description: 'Cada movimiento NFC se refleja al instante en el sistema.',
  },
  {
    icon: <CubeIcon />,
    title: 'Gemelo digital 3D',
    description: 'Visualiza el almacén desde el navegador, sin instalar nada.',
  },
  {
    icon: <UsersIcon />,
    title: 'Gestión de equipos',
    description: 'Asigna tareas a trabajadores y haz seguimiento del estado.',
  },
]

export default function WelcomePage() {
  const navigate = useNavigate()

  return (
    <div style={{ minHeight: '100vh', background: '#F1EFE8', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '20px 24px' }}>

      {/* Logo — outside the card */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
        <div style={{ width: '40px', height: '40px', background: '#185FA5', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <WarehouseLogoIcon />
        </div>
        <div>
          <div style={{ fontSize: '17px', fontWeight: '600', color: '#2C2C2A', lineHeight: '1.2' }}>Warehouse DT</div>
          <div style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Sistema de gestión</div>
        </div>
      </div>

      {/* Main card */}
      <div style={{ width: '100%', maxWidth: '860px', background: 'white', borderRadius: '16px', border: '0.5px solid #ddd', padding: '36px 44px' }}>

        <h1 style={{ fontSize: '24px', fontWeight: '500', color: '#2C2C2A', textAlign: 'center', margin: '0 0 10px' }}>
          Bienvenido a Warehouse DT
        </h1>

        <p style={{ fontSize: '14px', color: '#888780', textAlign: 'center', lineHeight: '1.6', maxWidth: '460px', margin: '0 auto 28px' }}>
          Gestiona tu almacén en tiempo real. Conecta el espacio físico con su gemelo digital y toma decisiones basadas en datos visuales.
        </p>

        {/* Feature grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px', marginBottom: '28px' }}>
          {features.map((f) => (
            <div key={f.title} style={{ background: '#F4F7FC', borderRadius: '12px', padding: '20px', textAlign: 'center' }}>
              <div style={{ width: '38px', height: '38px', background: '#D6E4F7', borderRadius: '9px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 12px', color: '#185FA5' }}>
                {f.icon}
              </div>
              <div style={{ fontSize: '13px', fontWeight: '600', color: '#2C2C2A', marginBottom: '6px' }}>{f.title}</div>
              <div style={{ fontSize: '12px', color: '#888780', lineHeight: '1.5' }}>{f.description}</div>
            </div>
          ))}
        </div>

        {/* Buttons */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => navigate('/login')}
            style={{ width: '100%', maxWidth: '320px', background: '#185FA5', color: 'white', border: 'none', borderRadius: '10px', padding: '12px', fontSize: '14px', fontWeight: '500', cursor: 'pointer' }}
          >
            Iniciar sesión
          </button>
          <button
            onClick={() => navigate('/register')}
            style={{ width: '100%', maxWidth: '320px', background: 'transparent', color: '#185FA5', border: '1.5px solid #185FA5', borderRadius: '10px', padding: '11px', fontSize: '14px', fontWeight: '500', cursor: 'pointer' }}
          >
            Crear cuenta de administrador
          </button>
        </div>
      </div>

      {/* Footer */}
      <div style={{ marginTop: '16px', fontSize: '12px', color: '#aaa' }}>
        © 2026 Warehouse DT · Sistema de gestión para PYMEs
      </div>
    </div>
  )
}
