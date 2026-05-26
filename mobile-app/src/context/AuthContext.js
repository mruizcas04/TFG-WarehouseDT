import React, { createContext, useState, useContext } from 'react';
import { apiFetch } from '../api/client';

const AuthContext = createContext(null);

export function decodeJWTPayload(token) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(decodeURIComponent(
      atob(base64).split('').map(c => '%' + c.charCodeAt(0).toString(16).padStart(2, '0')).join('')
    ));
  } catch {
    return {};
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);   // { id, role, token, name, must_change_password }

  const login = (userData) => setUser(userData);

  const logout = async () => {
    const token = user?.token;
    if (token) {
      try {
        await apiFetch('/auth/logout', { method: 'POST' }, token);
      } catch {
        // Si la red falla, desconectamos localmente igualmente para no dejar
        // al usuario atrapado en la app. is_online quedará desfasado hasta
        // el próximo login, pero es preferible a bloquear el cierre de sesión.
      }
    }
    setUser(null);
  };

  const updateToken = (newToken) => {
    const payload = decodeJWTPayload(newToken);
    setUser(prev => ({
      ...prev,
      token: newToken,
      must_change_password: payload.must_change_password ?? false,
    }));
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, updateToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);