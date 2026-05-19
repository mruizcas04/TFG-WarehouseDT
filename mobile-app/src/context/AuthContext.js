import React, { createContext, useState, useContext } from 'react';

const AuthContext = createContext(null);

function decodeJWTPayload(token) {
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
  const logout = () => setUser(null);

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