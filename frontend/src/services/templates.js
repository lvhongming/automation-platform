import api from './api'

// Playbook 模板
export function getPlaybooks(params) {
  return api.get('/templates/playbooks', { params })
}

export function getPlaybook(id) {
  return api.get(`/templates/playbooks/${id}`)
}

export function createPlaybook(data) {
  return api.post('/templates/playbooks', data)
}

export function updatePlaybook(id, data) {
  return api.put(`/templates/playbooks/${id}`, data)
}

export function deletePlaybook(id) {
  return api.delete(`/templates/playbooks/${id}`)
}

export function copyPlaybook(id) {
  return api.post(`/templates/playbooks/${id}/copy`)
}

// 脚本模板
export function getScripts(params) {
  return api.get('/templates/scripts', { params })
}

export function getScript(id) {
  return api.get(`/templates/scripts/${id}`)
}

export function createScript(data) {
  return api.post('/templates/scripts', data)
}

export function updateScript(id, data) {
  return api.put(`/templates/scripts/${id}`, data)
}

export function deleteScript(id) {
  return api.delete(`/templates/scripts/${id}`)
}

export function copyScript(id) {
  return api.post(`/templates/scripts/${id}/copy`)
}
