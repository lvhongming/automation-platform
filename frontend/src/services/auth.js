import api from './api'

export function login(username, password) {
  // OAuth2PasswordRequestForm 需要 form-urlencoded 格式
  const formData = new URLSearchParams()
  formData.append('username', username)
  formData.append('password', password)
  return api.post('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  })
}

export function logout() {
  return api.post('/auth/logout')
}

export function getCurrentUser() {
  return api.get('/auth/me')
}

export function register(data) {
  return api.post('/auth/register', data)
}

export function updateUser(data) {
  return api.put('/auth/me', data)
}
