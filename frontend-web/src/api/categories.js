import client from './client'

export const getCategories = async () => {
  const response = await client.get('/categories')
  return response.data
}

export const createCategory = async (data) => {
  const response = await client.post('/categories', data)
  return response.data
}
