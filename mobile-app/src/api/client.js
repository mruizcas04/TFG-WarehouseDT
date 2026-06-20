export const API_URL = 'https://tfg-production-1c10.up.railway.app';

export async function apiFetch(path, options = {}, token = null) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) throw new Error(`Error ${res.status}: ${res.statusText}`);
  if (res.status === 204) return null;
  return res.json();
}