import client from './client'

export const API_BASE = 'http://127.0.0.1:8000'

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

export const uploadProductImage = async ({ productId, file }) => {
  const formData = new FormData()
  formData.append('file', file)
  const response = await client.post(`/products/${productId}/image`, formData)
  return response.data
}