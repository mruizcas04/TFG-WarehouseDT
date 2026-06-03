import { useEffect, useState, useRef } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { verifyEmail } from '../api/auth'

export default function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState('loading')
  const called = useRef(false)

  useEffect(() => {
    if (called.current) return
    called.current = true

    const token = searchParams.get('token')
    if (!token) {
      setStatus('error')
      return
    }
    verifyEmail(token)
      .then(() => setStatus('success'))
      .catch(() => setStatus('error'))
  }, [searchParams])

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

        <div style={{ background: 'white', borderRadius: '12px', border: '0.5px solid #D3D1C7', padding: '32px', textAlign: 'center' }}>
          {status === 'loading' && (
            <>
              <div style={{ width: '48px', height: '48px', border: '3px solid #E8E6DF', borderTopColor: '#185FA5', borderRadius: '50%', margin: '0 auto 16px', animation: 'spin 0.8s linear infinite' }} />
              <p style={{ fontSize: '14px', color: '#5F5E5A' }}>Verificando tu cuenta...</p>
              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </>
          )}

          {status === 'success' && (
            <>
              <div style={{ width: '48px', height: '48px', background: '#EDFAF3', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#1A9A5A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </div>
              <h1 style={{ fontSize: '18px', fontWeight: '500', color: '#2C2C2A', marginBottom: '8px' }}>Cuenta verificada</h1>
              <p style={{ fontSize: '14px', color: '#5F5E5A', marginBottom: '24px' }}>
                Tu cuenta ha sido activada correctamente. Ya puedes iniciar sesión.
              </p>
              <Link
                to="/login"
                style={{ display: 'block', background: '#185FA5', color: 'white', textDecoration: 'none', borderRadius: '8px', padding: '11px', fontSize: '14px', fontWeight: '500' }}
              >
                Iniciar sesión
              </Link>
            </>
          )}

          {status === 'error' && (
            <>
              <div style={{ width: '48px', height: '48px', background: '#FCEBEB', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#A32D2D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="8" x2="12" y2="12"/>
                  <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
              </div>
              <h1 style={{ fontSize: '18px', fontWeight: '500', color: '#2C2C2A', marginBottom: '8px' }}>Enlace inválido</h1>
              <p style={{ fontSize: '14px', color: '#5F5E5A', marginBottom: '24px' }}>
                El enlace de verificación no es válido o ya ha sido utilizado.
              </p>
              <Link
                to="/register"
                style={{ display: 'block', background: '#185FA5', color: 'white', textDecoration: 'none', borderRadius: '8px', padding: '11px', fontSize: '14px', fontWeight: '500' }}
              >
                Volver al registro
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
