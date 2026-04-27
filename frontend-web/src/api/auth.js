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