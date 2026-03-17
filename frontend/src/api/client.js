import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || '/api'

console.log('API URL:', import.meta.env.VITE_API_URL)

const http = axios.create({ baseURL: BASE_URL })

export async function parseAddress(address, userId) {
  const { data } = await http.post(
    '/parse',
    { address },
    { headers: userId ? { 'X-User-Id': userId } : {} }
  )
  return data
}

export async function fetchHistory(userId, limit = 20, offset = 0) {
  const { data } = await http.get('/history', {
    params: { limit, offset },
    headers: userId ? { 'X-User-Id': userId } : {},
  })
  return data
}

export async function submitFeedback(payload) {
  const { data } = await http.post('/feedback', payload)
  return data
}

export async function fetchStats() {
  const { data } = await http.get('/stats')
  return data
}