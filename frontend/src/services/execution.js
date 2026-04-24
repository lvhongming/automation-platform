import api from './api'
import { useUserStore } from '@/stores/user'

// 获取执行历史
export function getExecutions(params) {
  return api.get('/executions', { params })
}

// 获取执行详情
export function getExecution(id) {
  return api.get(`/executions/${id}`)
}

// 获取节点执行列表
export function getExecutionNodes(executionId) {
  return api.get(`/executions/${executionId}/nodes`)
}

// 获取节点执行日志
export function getNodeExecutionLogs(executionId, nodeExecutionId) {
  return api.get(`/executions/${executionId}/nodes/${nodeExecutionId}/logs`)
}

// 实时日志（通过 WebSocket）
export function createExecutionWebSocket(executionId) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const userStore = useUserStore()
  return new WebSocket(
    `${protocol}//${host}/ws/executions/${executionId}?token=${userStore.token}`
  )
}

// 导出执行日志
export function exportExecutionLogs(id) {
  return api.get(`/executions/${id}/logs/export`, { responseType: 'blob' })
}

// 停止执行
export function stopExecution(id) {
  return api.post(`/executions/${id}/stop`)
}

// 重试执行
export function retryExecution(id) {
  return api.post(`/executions/${id}/retry`)
}
