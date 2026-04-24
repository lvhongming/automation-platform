import api from './api'

// 用户管理
export function getUsers(params) {
  return api.get('/users', { params })
}

export function getUser(id) {
  return api.get(`/users/${id}`)
}

export function createUser(data) {
  return api.post('/users', data)
}

export function updateUser(id, data) {
  return api.put(`/users/${id}`, data)
}

export function deleteUser(id) {
  return api.delete(`/users/${id}`)
}

export function resetUserPassword(id) {
  return api.post(`/users/${id}/reset-password`)
}

export function changeUserStatus(id, isActive) {
  return api.post(`/users/${id}/toggle-status`, { is_active: isActive })
}

// 角色管理
export function getRoles(params) {
  return api.get('/roles', { params })
}

export function getRole(id) {
  return api.get(`/roles/${id}`)
}

export function createRole(data) {
  return api.post('/roles', data)
}

export function updateRole(id, data) {
  return api.put(`/roles/${id}`, data)
}

export function deleteRole(id) {
  return api.delete(`/roles/${id}`)
}

// 流程权限
export function getFlowPermissions(flowId) {
  return api.get(`/flows/${flowId}/permissions`)
}

export function setFlowPermissions(flowId, permissions) {
  return api.post(`/flows/${flowId}/permissions`, permissions)
}

export function getUserFlows(userId) {
  return api.get(`/users/${userId}/flows`)
}
