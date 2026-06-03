import client from './client'

export const getUsers = async () => {
  const response = await client.get('/auth/users')
  return response.data
}

export const getInactiveUsers = async () => {
  const response = await client.get('/auth/users?show_inactive=true')
  return response.data
}

export const createUser = async (data) => {
  const response = await client.post('/auth/register', data)
  return response.data
}

export const deactivateUser = async (id) => {
  await client.delete(`/auth/users/${id}`)
}