<template>
  <div class="execution-detail page-container">
    <!-- 执行概览 -->
    <el-card class="execution-header">
      <div class="execution-info">
        <div class="info-left">
          <h2>
            执行详情
            <span class="execution-id">#{{ shortId }}</span>
          </h2>
          <el-tag :type="getStatusType(execution.status)" size="large">
            {{ getStatusText(execution.status) }}
          </el-tag>
          <el-tag v-if="wsConnected" type="success" effect="plain">
            <el-icon><Connection /></el-icon> 实时
          </el-tag>
        </div>
        <div class="info-right">
          <el-button
            v-if="execution.status === 'running' || execution.status === 'pending'"
            type="danger"
            @click="handleStop"
          >
            停止执行
          </el-button>
          <el-button
            v-if="execution.status === 'failed' || execution.status === 'stopped'"
            type="primary"
            @click="handleRetry"
          >
            重试
          </el-button>
          <el-button @click="loadData">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </div>

      <el-descriptions :column="4" border class="info-descriptions">
        <el-descriptions-item label="流程名称">{{ flowName }}</el-descriptions-item>
        <el-descriptions-item label="触发方式">
          {{ triggerTypeText }}
        </el-descriptions-item>
        <el-descriptions-item label="开始时间">
          {{ formatTime(execution.started_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="结束时间">
          {{ formatTime(execution.finished_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="总节点数">
          {{ execution.result_summary?.total || nodeExecutions.length }}
        </el-descriptions-item>
        <el-descriptions-item label="成功">
          <span style="color: #67c23a">{{ successCount }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="失败">
          <span style="color: #f56c6c">{{ failedCount }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="执行人">{{ execution.user?.username || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 节点执行状态 -->
    <el-card class="node-status">
      <template #header>
        <span>节点执行状态</span>
        <el-progress
          v-if="execution.status === 'running'"
          :percentage="progressPercentage"
          :status="progressStatus"
          style="width: 200px; display: inline-block; margin-left: 20px;"
        />
      </template>

      <el-timeline>
        <el-timeline-item
          v-for="node in nodeExecutions"
          :key="node.id"
          :type="getNodeStatusType(node.status)"
          :hollow="node.status === 'pending'"
          :timestamp="formatTime(node.started_at)"
        >
          <div class="timeline-item">
            <div class="node-info">
              <span class="node-name">{{ node.node_name || '节点' }}</span>
              <el-tag size="small" :type="getNodeStatusType(node.status)">
                {{ getStatusText(node.status) }}
              </el-tag>
              <el-tag v-if="node.node_type" size="small" type="info">
                {{ node.node_type }}
              </el-tag>
            </div>
            <div class="node-meta">
              <span v-if="node.host_id">主机: {{ getHostName(node.host_id) }}</span>
              <span>耗时: {{ calculateDuration(node.started_at, node.finished_at) }}</span>
            </div>
            <div class="node-output" v-if="node.output">
              <pre class="output-preview">{{ truncate(node.output, 200) }}</pre>
            </div>
            <div class="node-error" v-if="node.error">
              <pre class="error-preview">{{ node.error }}</pre>
            </div>
            <div class="node-actions">
              <el-button
                v-if="node.output"
                type="primary"
                link
                size="small"
                @click="showLog(node)"
              >
                查看完整日志
              </el-button>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>

      <!-- 空状态 -->
      <el-empty v-if="nodeExecutions.length === 0" description="暂无节点执行记录" />
    </el-card>



    <!-- 日志对话框 -->
    <el-dialog v-model="showLogDialog" title="执行日志" width="900px">
      <pre class="log-content">{{ currentLog }}</pre>
      <template #footer>
        <el-button @click="exportLog">导出日志</el-button>
        <el-button @click="copyLog">复制日志</el-button>
        <el-button type="primary" @click="showLogDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Connection, Refresh, Close } from '@element-plus/icons-vue'
import { getExecution, getExecutionNodes, stopExecution, retryExecution } from '@/services/execution'
import { useExecutionWebSocket } from '@/services/websocket'
import dayjs from 'dayjs'

const route = useRoute()
const executionId = route.params.id

const execution = ref({
  status: 'pending',
  result_summary: {}
})
const nodeExecutions = ref([])
const flowName = ref('-')
const hosts = ref({})

const showLogDialog = ref(false)
const currentLog = ref('')

const { isConnected: wsConnected, connect, disconnect, on, off } = useExecutionWebSocket()

const shortId = computed(() => executionId?.slice(0, 8) || '')

const successCount = computed(() =>
  nodeExecutions.value.filter(n => n.status === 'success').length
)

const failedCount = computed(() =>
  nodeExecutions.value.filter(n => n.status === 'failed').length
)

const progressPercentage = computed(() => {
  const total = nodeExecutions.value.length
  if (total === 0) return 0
  const completed = nodeExecutions.value.filter(
    n => ['success', 'failed'].includes(n.status)
  ).length
  return Math.round((completed / total) * 100)
})

const progressStatus = computed(() => {
  if (failedCount.value > 0) return 'exception'
  if (progressPercentage.value === 100) return 'success'
  return undefined
})

const triggerTypeText = computed(() => {
  const map = { manual: '手动执行', scheduled: '定时任务', api: 'API调用' }
  return map[execution.value.trigger_type] || '-'
})

function getStatusType(status) {
  const map = {
    pending: 'info',
    running: 'warning',
    success: 'success',
    failed: 'danger',
    stopped: 'warning'
  }
  return map[status] || 'info'
}

function getStatusText(status) {
  const map = {
    pending: '等待中',
    running: '执行中',
    success: '成功',
    failed: '失败',
    stopped: '已停止'
  }
  return map[status] || status
}

function getNodeStatusType(status) {
  const map = {
    pending: 'info',
    running: 'primary',
    success: 'success',
    failed: 'danger'
  }
  return map[status] || 'info'
}

function formatTime(time) {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

function calculateDuration(start, end) {
  if (!start || !end) return '-'
  const diff = dayjs(end).diff(dayjs(start), 'second')
  if (diff < 60) return `${diff}s`
  const minutes = Math.floor(diff / 60)
  const seconds = diff % 60
  return `${minutes}m ${seconds}s`
}

function getHostName(hostId) {
  return hosts.value[hostId] || hostId || '未指定'
}

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

function showLog(node) {
  currentLog.value = node.output || '无输出'
  if (node.error) {
    currentLog.value += '\n\n--- 错误信息 ---\n' + node.error
  }
  showLogDialog.value = true
}

function copyLog() {
  navigator.clipboard.writeText(currentLog.value)
  ElMessage.success('已复制到剪贴板')
}

function exportLog() {
  const blob = new Blob([currentLog.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `execution-${shortId.value}-log.txt`
  a.click()
  URL.revokeObjectURL(url)
}

async function handleStop() {
  try {
    await stopExecution(executionId)
    ElMessage.success('已发送停止指令')
    loadData()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

async function handleRetry() {
  try {
    const res = await retryExecution(executionId)
    ElMessage.success('已重新开始执行')
    route.params.id = res.execution_id
    loadData()
  } catch (error) {
    ElMessage.error('重试失败')
  }
}

async function loadData() {
  try {
    const [execRes, nodesRes] = await Promise.all([
      getExecution(executionId),
      getExecutionNodes(executionId)
    ])

    execution.value = execRes
    flowName.value = execRes.flow_name || '-'
    nodeExecutions.value = nodesRes || []
  } catch (error) {
    ElMessage.error('加载失败')
  }
}

function handleWsMessage(data) {
  console.log('WebSocket message:', data)
  
  // 兼容处理：WebSocket 服务已将 snake_case 转为 camelCase
  const nodeId = data.nodeId || data.node_id
  const resultSummary = data.resultSummary || data.result_summary
  
  if (data.type === 'node_update' || data.type === 'nodeUpdate') {
    const nodeIndex = nodeExecutions.value.findIndex(n => n.id === nodeId)
    if (nodeIndex !== -1) {
      nodeExecutions.value[nodeIndex].status = data.status
      if (data.output) {
        nodeExecutions.value[nodeIndex].output = data.output
      }
    }
  } else if (data.type === 'execution_update' || data.type === 'executionUpdate') {
    execution.value.status = data.status
    if (resultSummary) {
      execution.value.result_summary = resultSummary
    }
  }
}

let pollInterval = null

onMounted(() => {
  loadData()

  // WebSocket 连接（websocket.js 会将 node_update 转为 nodeUpdate）
  connect(executionId)
  on('nodeUpdate', handleWsMessage)
  on('executionUpdate', handleWsMessage)

  // 备用轮询
  pollInterval = setInterval(() => {
    if (!wsConnected.value && (execution.value.status === 'running' || execution.value.status === 'pending')) {
      loadData()
    }
  }, 5000)
})

onUnmounted(() => {
  disconnect()
  off('nodeUpdate', handleWsMessage)
  off('executionUpdate', handleWsMessage)

  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<style lang="scss" scoped>
.execution-detail {
  .execution-header {
    margin-bottom: 20px;

    .execution-info {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 20px;

      .info-left {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;

        h2 {
          margin: 0;
          display: flex;
          align-items: center;
          gap: 10px;

          .execution-id {
            font-size: 14px;
            font-weight: normal;
            color: #999;
          }
        }
      }

      .info-right {
        display: flex;
        gap: 10px;
      }
    }

    .info-descriptions {
      margin-top: 20px;
    }
  }

  .node-status {
    min-height: 400px;
    
    :deep(.el-card__body) {
      max-height: 60vh;
      overflow-y: auto;
    }
    
    .timeline-item {
      .node-info {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
        flex-wrap: wrap;

        .node-name {
          font-weight: bold;
          font-size: 16px;
        }
      }

      .node-meta {
        color: #999;
        font-size: 13px;
        display: flex;
        gap: 20px;
        margin-bottom: 8px;
      }

      .node-output,
      .node-error {
        margin: 8px 0;
        max-height: 300px;
        overflow-y: auto;

        pre {
          margin: 0;
          padding: 10px;
          border-radius: 4px;
          font-size: 12px;
          overflow-x: auto;
          white-space: pre-wrap;
          word-break: break-all;
        }
      }

      .output-preview {
        background: #f5f7fa;
        color: #666;
      }

      .error-preview {
        background: #fef0f0;
        color: #f56c6c;
      }

      .node-actions {
        margin-top: 8px;
      }
    }
  }

  .log-content {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 20px;
    border-radius: 4px;
    max-height: 500px;
    overflow-y: auto;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-all;
  }
}
</style>
