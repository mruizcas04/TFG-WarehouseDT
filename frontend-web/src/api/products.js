import client from './client'

export const getProducts = async () => {
  const response = await client.get('/products')
  return response.data
}

export const createProduct = async (data) => {
  const response = await client.post('/products', data)
  return response.data
}

export const deleteProduct = async (id) => {
  await client.delete(`/products/${id}`)
}