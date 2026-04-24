import api from './api'

// 系统设置
export function getSystemSettings() {
  return api.get('/settings')
}

export function updateSystemSettings(data) {
  return api.put('/settings', data)
}

// 通知设置
export function getNotificationSettings() {
  return api.get('/settings/notifications')
}

export function updateNotificationSettings(data) {
  return api.put('/settings/notifications', data)
}

export function testNotification(channel, data) {
  return api.post(`/settings/notifications/${channel}/test`, data)
}

// 系统统计
export function getDashboardStats() {
  return api.get('/statistics/dashboard')
}

export function getExecutionStats(params) {
  return api.get('/statistics/executions', { params })
}

// 审计日志
export function getAuditLogs(params) {
  return api.get('/audit-logs', { params })
}
