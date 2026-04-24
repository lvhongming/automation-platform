import api from './api'

// 定时任务
export function getScheduledJobs(params) {
  return api.get('/scheduled-jobs', { params })
}

export function getScheduledJob(id) {
  return api.get(`/scheduled-jobs/${id}`)
}

export function createScheduledJob(data) {
  return api.post('/scheduled-jobs', data)
}

export function updateScheduledJob(id, data) {
  return api.put(`/scheduled-jobs/${id}`, data)
}

export function deleteScheduledJob(id) {
  return api.delete(`/scheduled-jobs/${id}`)
}

export function toggleScheduledJob(id, enabled) {
  return api.post(`/scheduled-jobs/${id}/toggle`, { enabled })
}

export function triggerScheduledJob(id) {
  return api.post(`/scheduled-jobs/${id}/trigger`)
}
