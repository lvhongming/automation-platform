import api from './api'

// 流程列表
export function getFlows(params) {
  return api.get('/flows', { params })
}

// 获取流程详情
export function getFlow(id) {
  return api.get(`/flows/${id}`)
}

// 创建流程
export function createFlow(data) {
  return api.post('/flows', data)
}

// 更新流程
export function updateFlow(id, data) {
  return api.put(`/flows/${id}`, data)
}

// 删除流程
export function deleteFlow(id) {
  return api.delete(`/flows/${id}`)
}

// 保存流程设计（节点和连线）
export function saveFlowDesign(id, flowData) {
  console.log('保存流程设计:', id, flowData)
  return api.put(`/flows/${id}/design`, flowData)
}

// 校验流程
export function validateFlow(id) {
  return api.post(`/flows/${id}/validate`)
}

// 发布流程
export function publishFlow(id) {
  return api.post(`/flows/${id}/publish`)
}

// 复制流程
export function copyFlow(id) {
  return api.post(`/flows/${id}/copy`)
}

// 取消发布流程
export function unpublishFlow(id) {
  return api.post(`/flows/${id}/unpublish`)
}

// 执行流程
export function executeFlow(id, params) {
  return api.post(`/flows/${id}/execute`, {}, { params })
}

// 停止执行
export function stopExecution(executionId) {
  return api.post(`/executions/${executionId}/stop`)
}

// 重试执行
export function retryExecution(executionId) {
  return api.post(`/executions/${executionId}/retry`)
}
