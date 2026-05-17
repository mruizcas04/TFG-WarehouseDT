import client from './client'

export const getTasks = async () => {
  const response = await client.get('/tasks')
  return response.data
}

export const createTask = async (data) => {
  const response = await client.post('/tasks', data)
  return response.data
}

export const updateTaskStatus = async ({ id, status }) => {
  const response = await client.put(`/tasks/${id}/status`, { status })
  return response.data
}

export const deleteTask = async (id) => {
  await client.delete(`/tasks/${id}`)
}