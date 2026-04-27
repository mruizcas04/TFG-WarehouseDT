import client from './client'

export const getMovements = async () => {
  const response = await client.get('/movements')
  return response.data
}