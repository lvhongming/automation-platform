/**
 * WebSocket 服务 - 用于实时执行状态推送
 */
import { ref, readonly } from 'vue'
import { useUserStore } from '@/stores/user'

class ExecutionWebSocket {
  constructor() {
    this.ws = null
    this.executionId = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000
    this.listeners = new Map()
    this.isConnected = ref(false)
  }

  connect(executionId) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      if (this.executionId === executionId) {
        return // 已连接
      }
      this.disconnect()
    }

    this.executionId = executionId
    const userStore = useUserStore()

    // 构建 WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    // 注意：后端 WebSocket 路由是 /ws/executions/，不是 /api/ws/executions/
    const wsUrl = `${protocol}//${host}/ws/executions/${executionId}?token=${userStore.token}`

    try {
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('WebSocket connected to execution:', executionId)
        this.isConnected.value = true
        this.reconnectAttempts = 0
        this.emit('connected', { executionId })
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('WebSocket message received:', data)
          this.handleMessage(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected, code:', event.code, 'reason:', event.reason)
        this.isConnected.value = false
        this.emit('disconnected', { executionId })

        // 如果不是正常关闭，则自动重连
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`)
          setTimeout(() => {
            this.connect(executionId)
          }, this.reconnectDelay)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.emit('error', error)
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.executionId = null
    this.isConnected.value = false
  }

  handleMessage(data) {
    console.log('WebSocket received:', data)
    switch (data.type) {
      case 'node_update':
        this.emit('nodeUpdate', {
          nodeId: data.node_id,
          status: data.status,
          output: data.output
        })
        break

      case 'execution_update':
        this.emit('executionUpdate', {
          status: data.status,
          resultSummary: data.result_summary
        })
        break

      case 'log':
        this.emit('log', {
          nodeId: data.node_id,
          level: data.level,
          message: data.message
        })
        break

      case 'pong':
        // 心跳响应
        break

      default:
        console.log('Unknown message type:', data.type)
        this.emit('message', data)
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  ping() {
    this.send({ type: 'ping' })
  }

  // 事件监听
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event)
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => callback(data))
    }
  }
}

// 创建单例
const executionWs = new ExecutionWebSocket()

export function useExecutionWebSocket() {
  return {
    isConnected: executionWs.isConnected,
    connect: (executionId) => executionWs.connect(executionId),
    disconnect: () => executionWs.disconnect(),
    on: (event, callback) => executionWs.on(event, callback),
    off: (event, callback) => executionWs.off(event, callback)
  }
}

export default executionWs
