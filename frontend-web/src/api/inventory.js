import client from './client'

export const getInventorySummary = async () => {
  const response = await client.get('/inventory/summary')
  return response.data
}
