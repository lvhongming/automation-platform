import api from './api'

// 主机组管理
export function getHostGroups(params) {
  return api.get('/hosts/groups', { params })
}

export function createHostGroup(data) {
  return api.post('/hosts/groups', data)
}

export function updateHostGroup(id, data) {
  return api.put(`/hosts/groups/${id}`, data)
}

export function deleteHostGroup(id, moveHosts = false) {
  return api.delete(`/hosts/groups/${id}`, { params: { move_hosts: moveHosts } })
}

export function moveHost(hostId, targetGroupId) {
  return api.post(`/hosts/${hostId}/move`, null, { params: { target_group_id: targetGroupId } })
}

// 主机管理
export function getHosts(params) {
  return api.get('/hosts', { params })
}

export function getHost(id) {
  return api.get(`/hosts/${id}`)
}

export function createHost(data) {
  return api.post('/hosts', data)
}

export function updateHost(id, data) {
  return api.put(`/hosts/${id}`, data)
}

export function deleteHost(id) {
  return api.delete(`/hosts/${id}`)
}

export function testHostConnection(id) {
  return api.post(`/hosts/${id}/test-connection`)
}

// 凭据管理
export function getCredentials(params) {
  return api.get('/hosts/credentials', { params })
}

export function getCredential(id) {
  return api.get(`/hosts/credentials/${id}`)
}

export function createCredential(data) {
  return api.post('/hosts/credentials', data)
}

export function deleteCredential(id) {
  return api.delete(`/hosts/credentials/${id}`)
}

// 导入/导出
export function importInventory(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/hosts/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function exportInventory() {
  return api.get('/hosts/export')
}

// 下载导入模板
export function downloadImportTemplate() {
  return api.get('/hosts/template')
}
