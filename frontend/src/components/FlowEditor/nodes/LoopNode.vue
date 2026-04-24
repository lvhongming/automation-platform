<template>
  <div
    class="custom-node loop-node"
    :class="[`node-${nodeStatus || 'pending'}`, { 'selected': selected }]"
  >
    <!-- 左侧入口连接点（居中） -->
    <Handle id="target" type="target" :position="Position.Left" :style="{ top: '50%', transform: 'translateY(-50%)', background: '#409EFF' }" class="outer-handle" />
    
    <div class="node-header">
      <el-icon class="node-icon"><Refresh /></el-icon>
      <span class="node-label">{{ data.label || '循环节点' }}</span>
    </div>
    
    <div class="node-body">
      <!-- 循环配置信息 -->
      <div class="loop-info">
        <div class="info-item">
          <el-icon><Timer /></el-icon>
          <span>{{ loopTypeLabel }} - {{ displayCount }} 次</span>
        </div>
        <div class="info-item">
          <el-icon><Document /></el-icon>
          <span>变量: {{ loopVar || 'item' }}</span>
        </div>
        <div class="info-item" v-if="failStrategyLabel">
          <el-icon><Warning /></el-icon>
          <span>{{ failStrategyLabel }}</span>
        </div>
      </div>
    </div>
    
    <!-- 循环体区域 - 居中布局，底部有连接点 -->
    <div class="loop-body-area">
      <div class="loop-body-content">
        <span>循环体</span>
        <div class="loop-hint">连接循环内的第一个节点</div>
      </div>
      
      <!-- 底部连接点：循环开始入口 -->
      <Handle id="loop-start" type="source" :position="Position.Bottom" 
        :style="{ bottom: '-6px', backgroundColor: '#67c23a', width: '14px', height: '14px' }" 
        class="loop-handle-solid" />
    </div>
    
    <!-- 右侧出口连接点（循环结束后离开，居中） -->
    <Handle id="source" type="source" :position="Position.Right" :style="{ top: '50%', transform: 'translateY(-50%)', background: '#f56c6c' }" class="outer-handle" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Position, Handle } from '@vue-flow/core'
import { Refresh, Timer, Document, Warning } from '@element-plus/icons-vue'

const props = defineProps({
  id: String,
  type: String,
  data: Object,
  selected: Boolean,
  nodeStatus: String
})

const loopTypeMap = {
  count: '计数',
  hosts: '主机',
  items: '列表'
}

const failStrategyMap = {
  stop: '失败停止',
  skip: '失败跳过',
  continue: '失败继续'
}

const loopType = computed(() => props.data?.config?.loop_type || 'count')
const displayCount = computed(() => {
  const type = loopType.value
  if (type === 'count') {
    return props.data?.config?.loop_count || 1
  } else if (type === 'hosts') {
    const hosts = props.data?.config?.hosts || []
    return hosts.length > 0 ? hosts.length : '?'
  } else if (type === 'array') {
    const items = props.data?.config?.loop_items || ''
    if (items.trim() === '') return 0
    if (items.includes(',')) {
      return items.split(',').filter(item => item.trim()).length
    }
    return items.split('\n').filter(item => item.trim()).length
  }
  return 1
})
const loopVar = computed(() => props.data?.config?.loop_var || 'item')
const failStrategy = computed(() => props.data?.config?.fail_strategy || 'continue')
const loopTypeLabel = computed(() => loopTypeMap[loopType.value] || '计数')
const failStrategyLabel = computed(() => failStrategyMap[failStrategy.value] || '')

defineExpose({ Position })
</script>

<style lang="scss" scoped>
.loop-node {
  min-width: 180px;
  max-width: 220px;
  background: #fff;
  border: 2px solid #9B59B6;
  border-radius: 12px;
  overflow: visible;
  box-shadow: 0 2px 8px rgba(155, 89, 182, 0.2);

  &:hover {
    box-shadow: 0 4px 16px rgba(155, 89, 182, 0.3);
  }

  &.selected {
    box-shadow: 0 0 0 3px #9B59B6;
  }

  &.node-running {
    border-color: #e6a23c;
    animation: pulse 1.5s infinite;
  }

  &.node-success {
    border-color: #67c23a;
  }

  &.node-failed {
    border-color: #f56c6c;
  }
}

.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: linear-gradient(135deg, #9B59B6, #8E44AD);
  color: #fff;
  border-radius: 10px 10px 0 0;

  .node-icon {
    font-size: 16px;
  }

  .node-label {
    font-size: 13px;
    font-weight: 600;
    flex: 1;
  }
}

.node-body {
  padding: 10px 12px;

  .loop-info {
    display: flex;
    flex-direction: column;
    gap: 4px;

    .info-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      color: #666;
      background: #f5f0f7;
      padding: 4px 8px;
      border-radius: 4px;

      .el-icon {
        font-size: 12px;
        color: #9B59B6;
      }
    }
  }
}

.loop-body-area {
  position: relative;
  padding: 16px 12px 24px;
  margin-top: 4px;

  .loop-body-content {
    min-height: 50px;
    border: 2px dashed #d0a9db;
    border-radius: 8px;
    background: linear-gradient(135deg, #faf5fc 0%, #f5f0f7 100%);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    color: #9B59B6;
    font-weight: 500;

    .loop-hint {
      font-size: 9px;
      color: #b19cc7;
      margin-top: 4px;
      font-weight: normal;
    }
  }
}

// 外层 Handle 样式
:deep(.vue-flow__handle.outer-handle) {
  width: 14px !important;
  height: 14px !important;
  border: 2px solid #fff !important;
  border-radius: 50% !important;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
  top: 50% !important;
  transform: translateY(-50%) !important;

  &:hover {
    transform: translateY(-50%) scale(1.2) !important;
  }
}

:deep(.vue-flow__handle#target) {
  left: -7px !important;
  background: #409EFF !important;
  transform: translateY(-50%) !important;
}

:deep(.vue-flow__handle#source) {
  right: -7px !important;
  background: #f56c6c !important;
  transform: translateY(-50%) !important;
}

// 底部循环开始连接点样式
:deep(.vue-flow__handle#loop-start) {
  bottom: -6px !important;
  top: auto !important;
  background-color: #67c23a !important;
  border: 2px solid #fff !important;
  border-radius: 50% !important;
  box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
}

// 循环体内部 Handle 样式 - 实心点
:deep(.vue-flow__handle.loop-handle-solid) {
  border-radius: 50% !important;
  border: 2px solid #fff !important;
  box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
</style>
