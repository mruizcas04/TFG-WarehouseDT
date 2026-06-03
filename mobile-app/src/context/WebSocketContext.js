import React, { createContext, useContext, useEffect, useRef, useCallback } from 'react';
import { API_URL } from '../api/client';
import { useAuth } from './AuthContext';

const WebSocketContext = createContext(null);

export function WebSocketProvider({ children }) {
  const { user } = useAuth();
  const listenersRef = useRef({});

  useEffect(() => {
    if (!user?.token) return;

    const wsUrl = API_URL.replace(/^http/, 'ws') + `/ws?token=${user.token}`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (e) => {
      try {
        const { event, data } = JSON.parse(e.data);
        (listenersRef.current[event] || []).forEach(cb => cb(data));
      } catch {}
    };

    return () => ws.close();
  }, [user?.token]);

  const subscribe = useCallback((event, callback) => {
    if (!listenersRef.current[event]) listenersRef.current[event] = [];
    listenersRef.current[event].push(callback);
    return () => {
      listenersRef.current[event] = (listenersRef.current[event] || []).filter(cb => cb !== callback);
    };
  }, []);

  return (
    <WebSocketContext.Provider value={{ subscribe }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export const useWebSocket = () => useContext(WebSocketContext);
