import axios from 'axios'

const api = axios.create({
  baseURL: '/api'
})

// 添加响应拦截器处理 token
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export function getSettings() {
  return api.get('/settings').then(res => res.data)
}

export function updateSettings(data) {
  return api.put('/settings', data).then(res => res.data)
}

export default api
