import { useState } from 'react'
import { Link } from 'react-router-dom'
import { register } from '../api/auth'

const EyeIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
)

const EyeOffIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
    <line x1="1" y1="1" x2="23" y2="23" />
  </svg>
)

const Logo = () => (
  <div style={{ marginBottom: '24px' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      <div style={{ width: '36px', height: '36px', background: '#185FA5', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M1 8L9 2L17 8" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M1 8V16H17V8" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M6 16V12H12V16" stroke="white" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      <div>
        <div style={{ fontSize: '16px', fontWeight: '500', color: '#2C2C2A' }}>Warehouse DT</div>
        <div style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Sistema de gestión</div>
      </div>
    </div>
  </div>
)

const StepDots = ({ step }) => (
  <div style={{ display: 'flex', gap: '6px', justifyContent: 'center', marginBottom: '20px' }}>
    {[1, 2].map((n) => (
      <div key={n} style={{ width: n === step ? '20px' : '8px', height: '8px', borderRadius: '4px', background: n === step ? '#185FA5' : '#D3D1C7', transition: 'all 0.2s' }} />
    ))}
  </div>
)

export default function Register() {
  const [step, setStep] = useState(1)
  const [form, setForm] = useState({ company_name: '', name: '', email: '', password: '', confirmPassword: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [registered, setRegistered] = useState(false)
  const [registeredEmail, setRegisteredEmail] = useState('')

  const inputStyle = { width: '100%', border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '10px 12px', fontSize: '14px', color: '#2C2C2A', background: 'white', outline: 'none' }
  const labelStyle = { display: 'block', fontSize: '12px', fontWeight: '500', color: '#5F5E5A', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.04em' }

  const handleStep1 = (e) => {
    e.preventDefault()
    setError(null)
    setStep(2)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.password !== form.confirmPassword) {
      setError('Las contraseñas no coinciden')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await register({ company_name: form.company_name, name: form.name, email: form.email, password: form.password, role: 'admin' })
      setRegisteredEmail(form.email)
      setRegistered(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al crear la cuenta')
    } finally {
      setLoading(false)
    }
  }

  if (registered) {
    return (
      <div style={{ minHeight: '100vh', background: '#F1EFE8', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: '100%', maxWidth: '400px', padding: '0 24px' }}>
          <Logo />
          <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #D3D1C7', padding: '32px', textAlign: 'center' }}>
            <div style={{ width: '48px', height: '48px', background: '#EBF4FF', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#185FA5" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                <polyline points="22,6 12,13 2,6"/>
              </svg>
            </div>
            <h1 style={{ fontSize: '18px', fontWeight: '500', color: '#2C2C2A', marginBottom: '8px' }}>Revisa tu email</h1>
            <p style={{ fontSize: '14px', color: '#5F5E5A', marginBottom: '6px' }}>Hemos enviado un enlace de verificación a:</p>
            <p style={{ fontSize: '14px', fontWeight: '500', color: '#185FA5', marginBottom: '20px' }}>{registeredEmail}</p>
            <p style={{ fontSize: '13px', color: '#888780', marginBottom: '24px' }}>
              Haz clic en el enlace del email para activar tu cuenta. Puede tardar unos minutos.
            </p>
            <Link to="/login" style={{ display: 'block', width: '100%', background: '#185FA5', color: 'white', textDecoration: 'none', borderRadius: '8px', padding: '11px', fontSize: '14px', fontWeight: '500', textAlign: 'center', boxSizing: 'border-box' }}>
              Ir al inicio de sesión
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: '#F1EFE8', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ width: '100%', maxWidth: '400px', padding: '0 24px' }}>
        <Logo />

        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #D3D1C7', padding: '28px 32px' }}>
          <StepDots step={step} />

          {step === 1 ? (
            <>
              <h1 style={{ fontSize: '18px', fontWeight: '500', color: '#2C2C2A', marginBottom: '4px' }}>Crear cuenta</h1>
              <p style={{ fontSize: '13px', color: '#888780', marginBottom: '20px' }}>Paso 1 de 2 · Datos de la empresa</p>

              <form onSubmit={handleStep1} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div>
                  <label style={labelStyle}>Nombre de la empresa</label>
                  <input type="text" value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                    placeholder="Almacenes García S.L." required style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Tu nombre</label>
                  <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="Tu nombre" required style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Email</label>
                  <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                    placeholder="admin@empresa.com" required style={inputStyle} />
                </div>
                <button type="submit" style={{ width: '100%', background: '#185FA5', color: 'white', border: 'none', borderRadius: '8px', padding: '11px', fontSize: '14px', fontWeight: '500', cursor: 'pointer', marginTop: '4px' }}>
                  Continuar
                </button>
              </form>
            </>
          ) : (
            <>
              <h1 style={{ fontSize: '18px', fontWeight: '500', color: '#2C2C2A', marginBottom: '4px' }}>Crear cuenta</h1>
              <p style={{ fontSize: '13px', color: '#888780', marginBottom: '20px' }}>Paso 2 de 2 · Elige una contraseña</p>

              <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div>
                  <label style={labelStyle}>Contraseña</label>
                  <div style={{ position: 'relative' }}>
                    <input type={showPassword ? 'text' : 'password'} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
                      placeholder="••••••••" required style={{ ...inputStyle, paddingRight: '40px', boxSizing: 'border-box' }} />
                    <button type="button" onClick={() => setShowPassword(v => !v)}
                      style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', padding: '0', color: '#888780', display: 'flex', alignItems: 'center' }}>
                      {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                    </button>
                  </div>
                </div>
                <div>
                  <label style={labelStyle}>Confirmar contraseña</label>
                  <div style={{ position: 'relative' }}>
                    <input type={showConfirmPassword ? 'text' : 'password'} value={form.confirmPassword} onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
                      placeholder="••••••••" required style={{ ...inputStyle, paddingRight: '40px', boxSizing: 'border-box' }} />
                    <button type="button" onClick={() => setShowConfirmPassword(v => !v)}
                      style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', padding: '0', color: '#888780', display: 'flex', alignItems: 'center' }}>
                      {showConfirmPassword ? <EyeOffIcon /> : <EyeIcon />}
                    </button>
                  </div>
                </div>

                {error && (
                  <div style={{ background: '#FCEBEB', border: '0.5px solid #F7C1C1', borderRadius: '8px', padding: '10px 12px', fontSize: '13px', color: '#A32D2D' }}>
                    {error}
                  </div>
                )}

                <div style={{ display: 'flex', gap: '10px', marginTop: '4px' }}>
                  <button type="button" onClick={() => { setStep(1); setError(null) }}
                    style={{ flex: 1, background: 'transparent', color: '#5F5E5A', border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '11px', fontSize: '14px', fontWeight: '500', cursor: 'pointer' }}>
                    Atrás
                  </button>
                  <button type="submit" disabled={loading}
                    style={{ flex: 2, background: loading ? '#B5D4F4' : '#185FA5', color: 'white', border: 'none', borderRadius: '8px', padding: '11px', fontSize: '14px', fontWeight: '500', cursor: loading ? 'not-allowed' : 'pointer' }}>
                    {loading ? 'Creando cuenta...' : 'Crear cuenta'}
                  </button>
                </div>
              </form>
            </>
          )}

          <p style={{ textAlign: 'center', fontSize: '13px', color: '#888780', marginTop: '18px' }}>
            ¿Ya tienes cuenta?{' '}
            <Link to="/login" style={{ color: '#185FA5', textDecoration: 'none', fontWeight: '500' }}>Iniciar sesión</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
