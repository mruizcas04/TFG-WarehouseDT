import client from './client'

export const getUsers = async () => {
  const response = await client.get('/auth/users')
  return response.data
}

export const createUser = async (data) => {
  const response = await client.post('/auth/register', data)
  return response.data
}