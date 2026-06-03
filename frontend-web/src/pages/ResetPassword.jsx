import { useState } from 'react'
import { useSearchParams, Link, useNavigate } from 'react-router-dom'
import { resetPassword } from '../api/auth'

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

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')

  const [form, setForm] = useState({ password: '', confirmPassword: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  if (!token) {
    return (
      <div style={{ minHeight: '100vh', background: '#F1EFE8', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: '100%', maxWidth: '400px', padding: '0 24px' }}>
          <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #D3D1C7', padding: '32px', textAlign: 'center' }}>
            <p style={{ fontSize: '14px', color: '#A32D2D', marginBottom: '16px' }}>Enlace de recuperación no válido.</p>
            <Link to="/login" style={{ color: '#185FA5', fontSize: '14px' }}>Volver al inicio de sesión</Link>
          </div>
        </div>
      </div>
    )
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.password !== form.confirmPassword) {
      setError('Las contraseñas no coinciden')
      return
    }
    if (form.password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await resetPassword(token, form.password)
      setSuccess(true)
      setTimeout(() => navigate('/login'), 2500)
    } catch (err) {
      setError(err.response?.data?.detail || 'El enlace no es válido o ha expirado')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = { width: '100%', border: '0.5px solid #D3D1C7', borderRadius: '8px', padding: '10px 12px', fontSize: '14px', color: '#2C2C2A', background: 'white', outline: 'none' }
  const labelStyle = { display: 'block', fontSize: '12px', fontWeight: '500', color: '#5F5E5A', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.04em' }

  return (
    <div style={{ minHeight: '100vh', background: '#F1EFE8', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ width: '100%', maxWidth: '400px', padding: '0 24px' }}>
        <div style={{ marginBottom: '32px' }}>
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

        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #D3D1C7', padding: '32px' }}>
          {success ? (
            <div style={{ textAlign: 'center' }}>
              <div style={{ width: '48px', height: '48px', background: '#EDFAF3', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#1A9A5A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </div>
              <h1 style={{ fontSize: '18px', fontWeight: '500', color: '#2C2C2A', marginBottom: '8px' }}>Contraseña restablecida</h1>
              <p style={{ fontSize: '14px', color: '#5F5E5A' }}>Redirigiendo al inicio de sesión...</p>
            </div>
          ) : (
            <>
              <h1 style={{ fontSize: '18px', fontWeight: '500', color: '#2C2C2A', marginBottom: '6px' }}>Nueva contraseña</h1>
              <p style={{ fontSize: '13px', color: '#888780', marginBottom: '24px' }}>Introduce tu nueva contraseña.</p>

              <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <label style={labelStyle}>Nueva contraseña</label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={form.password}
                      onChange={(e) => setForm({ ...form, password: e.target.value })}
                      placeholder="••••••••"
                      required
                      style={{ ...inputStyle, paddingRight: '40px', boxSizing: 'border-box' }}
                    />
                    <button type="button" onClick={() => setShowPassword(v => !v)}
                      style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', padding: '0', color: '#888780', display: 'flex', alignItems: 'center' }}>
                      {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                    </button>
                  </div>
                </div>
                <div>
                  <label style={labelStyle}>Confirmar contraseña</label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showConfirm ? 'text' : 'password'}
                      value={form.confirmPassword}
                      onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
                      placeholder="••••••••"
                      required
                      style={{ ...inputStyle, paddingRight: '40px', boxSizing: 'border-box' }}
                    />
                    <button type="button" onClick={() => setShowConfirm(v => !v)}
                      style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', padding: '0', color: '#888780', display: 'flex', alignItems: 'center' }}>
                      {showConfirm ? <EyeOffIcon /> : <EyeIcon />}
                    </button>
                  </div>
                </div>

                {error && (
                  <div style={{ background: '#FCEBEB', border: '0.5px solid #F7C1C1', borderRadius: '8px', padding: '10px 12px', fontSize: '13px', color: '#A32D2D' }}>
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  style={{ width: '100%', background: loading ? '#B5D4F4' : '#185FA5', color: 'white', border: 'none', borderRadius: '8px', padding: '11px', fontSize: '14px', fontWeight: '500', cursor: loading ? 'not-allowed' : 'pointer', marginTop: '4px' }}
                >
                  {loading ? 'Guardando...' : 'Establecer contraseña'}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
