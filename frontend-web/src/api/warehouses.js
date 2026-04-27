import client from './client'

export const getWarehouses = async () => {
  const response = await client.get('/warehouses')
  return response.data
}

export const createWarehouse = async (data) => {
  const response = await client.post('/warehouses', data)
  return response.data
}

export const getWarehouse = async (id) => {
  const response = await client.get(`/warehouses/${id}`)
  return response.data
}

export const getShelves = async (warehouseId) => {
  const response = await client.get(`/warehouses/${warehouseId}/shelves`)
  return response.data
}

export const getLevels = async (shelfId) => {
  const response = await client.get(`/shelves/${shelfId}/levels`)
  return response.data
}

export const getLocations = async (levelId) => {
  const response = await client.get(`/levels/${levelId}/locations`)
  return response.data
}