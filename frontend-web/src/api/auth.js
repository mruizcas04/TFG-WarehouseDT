import client from './client'

export const login = async (email, password) => {
  const formData = new FormData()
  formData.append('username', email)
  formData.append('password', password)

  const response = await client.post('/auth/login', formData)
  return response.data
}

export const register = async (userData) => {
  const response = await client.post('/auth/register', userData)
  return response.data
}

export const verifyEmail = async (token) => {
  const response = await client.post(`/auth/verify-email?token=${token}`)
  return response.data
}

export const forgotPassword = async (email) => {
  const response = await client.post('/auth/forgot-password', { email })
  return response.data
}

export const resetPassword = async (token, new_password) => {
  const response = await client.post('/auth/reset-password', { token, new_password })
  return response.data
}

export const logoutApi = () =>
  client.post('/auth/logout').catch(() => {/* fire-and-forget; no bloquear el logout local */})