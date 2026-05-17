import client from './client'

export const getBoxes = async () => {
  const response = await client.get('/boxes')
  return response.data
}

export const createBox = async (data) => {
  const response = await client.post('/boxes', data)
  return response.data
}

export const getBox = async (id) => {
  const response = await client.get(`/boxes/${id}`)
  return response.data
}

export const updateBox = async (id, data) => {
  const response = await client.put(`/boxes/${id}`, data)
  return response.data
}
