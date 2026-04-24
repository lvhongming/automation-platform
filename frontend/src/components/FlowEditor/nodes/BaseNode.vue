<template>
  <div
    class="custom-node"
    :class="[`node-${nodeStatus || 'pending'}`, `node-type-${type}`]"
    :style="{ borderColor: color }"
  >
    <!-- 左侧连接点 -->
    <Handle id="target" type="target" :position="Position.Left" class="node-handle" />

    <div class="node-header" :style="{ backgroundColor: color }">
      <el-icon class="node-icon"><component :is="iconComponent" /></el-icon>
      <span class="node-label">{{ data.label || label }}</span>
    </div>
    <div class="node-body">
      <div class="node-info" v-if="showInfo">
        <span v-if="data.config?.host_id" class="info-item">
          <el-icon><Monitor /></el-icon>
          主机已选
        </span>
        <span v-if="data.config?.command" class="info-item command-preview">
          {{ truncate(data.config.command, 30) }}
        </span>
        <span v-if="data.config?.script_content" class="info-item script-preview">
          脚本已配置
        </span>
      </div>
      
      <!-- 节点描述 - 用户输入的描述优先显示 -->
      <div class="node-description" :class="{ 'has-user-desc': hasUserDescription }">
        <span class="desc-text">{{ displayDescription }}</span>
      </div>
      
      <!-- 条件分支节点的状态分支指示 -->
      <div class="condition-branches" v-if="type === 'condition'">
        <div class="branch success-branch">
          <el-icon><CircleCheck /></el-icon>
          <span>成功</span>
        </div>
        <div class="branch fail-branch">
          <el-icon><CircleClose /></el-icon>
          <span>失败</span>
        </div>
      </div>
      
      <div class="node-status" v-if="nodeStatus">
        <!-- 运行中 -->
        <span v-if="nodeStatus === 'running'" class="status-badge running">
          <el-icon class="is-loading"><Loading /></el-icon>
        </span>
        <!-- 成功 - 绿色小旗 -->
        <span v-else-if="nodeStatus === 'success'" class="status-badge success">
          <el-icon><Flag /></el-icon>
        </span>
        <!-- 失败 - 红色错误符号 -->
        <span v-else-if="nodeStatus === 'failed'" class="status-badge failed">
          <el-icon><CircleCloseFilled /></el-icon>
        </span>
      </div>
    </div>
    <div class="drag-handle">
      <el-icon><Rank /></el-icon>
    </div>

    <!-- 条件分支节点：两个输出 Handle（成功/失败） -->
    <template v-if="type === 'condition'">
      <Handle id="success" type="source" :position="Position.Right" :style="{ top: '30%' }" class="handle-success" />
      <Handle id="failed" type="source" :position="Position.Right" :style="{ top: '70%' }" class="handle-failed" />
    </template>
    <!-- 普通节点：单个输出 Handle -->
    <Handle v-else id="source" type="source" :position="Position.Right" class="node-handle" />
  </div>
</template>

<script setup>
import { computed, markRaw } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import {
  Monitor, CircleCheck, CircleClose, Loading, Rank,
  Cpu, Document, Tickets, Refresh, Operation,
  Clock, Bell, ChatLineSquare, FolderOpened, Flag, CircleCloseFilled,
  VideoPause, WarnTriangleFilled
} from '@element-plus/icons-vue'

// 导出 Position 供模板使用
defineExpose({ Position })

const props = defineProps({
  id: String,
  type: String,
  data: Object,
  selected: Boolean
})

const iconMap = {
  Cpu: markRaw(Cpu),
  Document: markRaw(Document),
  Tickets: markRaw(Tickets),
  Refresh: markRaw(Refresh),
  Operation: markRaw(Operation),
  Clock: markRaw(Clock),
  Bell: markRaw(Bell),
  ChatLineSquare: markRaw(ChatLineSquare),
  FolderOpened: markRaw(FolderOpened),
  VideoPause: markRaw(VideoPause)
}

const nodeConfig = {
  command: { label: '命令节点', icon: 'Cpu', color: '#409EFF' },
  script: { label: '脚本节点', icon: 'Document', color: '#67C23A' },
  playbook: { label: 'Playbook', icon: 'Tickets', color: '#E6A23C' },
  file: { label: '文件节点', icon: 'FolderOpened', color: '#909399' },
  loop: { label: '循环节点', icon: 'Refresh', color: '#9B59B6' },
  condition: { label: '条件分支', icon: 'Operation', color: '#F56C6C' },
  parallel: { label: '并行分支', icon: 'VideoPause', color: '#909399' },
  wait: { label: '等待节点', icon: 'Clock', color: '#909399' },
  notify: { label: '通知节点', icon: 'Bell', color: '#E6A23C' },
  comment: { label: '注释', icon: 'ChatLineSquare', color: '#67C23A' }
}

const config = computed(() => nodeConfig[props.type] || nodeConfig.command)
const label = computed(() => config.value.label)
const iconComponent = computed(() => iconMap[config.value.icon] || iconMap.Cpu)
const color = computed(() => config.value.color)
const showInfo = computed(() => ['command', 'script', 'playbook'].includes(props.type))
// 强制追踪 status 变化
const nodeStatus = computed(() => props.data?.status)

// 节点描述 - 优先显示用户输入的节点描述字段
const hasUserDescription = computed(() => {
  const userDesc = props.data?.description || props.data?.config?.description
  return userDesc && userDesc.trim().length > 0
})

const displayDescription = computed(() => {
  // 优先使用用户输入的节点描述
  const userDescription = props.data?.description || props.data?.config?.description
  if (userDescription && userDescription.trim()) {
    return truncate(userDescription, 25)
  }
  
  // 如果没有用户描述，根据节点类型显示默认信息
  const cfg = props.data?.config || {}
  switch (props.type) {
    case 'command':
      return cfg.command ? truncate(cfg.command, 25) : '未配置命令'
    case 'script':
      return cfg.script_content ? '脚本已配置' : '未配置脚本'
    case 'playbook':
      return cfg.playbook_content ? 'Playbook已配置' : '未配置Playbook'
    case 'loop':
      if (cfg.loop_type === 'count') {
        return `循环 ${cfg.loop_count || 1} 次`
      } else if (cfg.loop_type === 'items') {
        return `遍历 ${cfg.loop_var || 'items'}`
      }
      return '循环节点'
    case 'condition':
      return cfg.conditions?.length ? `${cfg.conditions.length} 个条件` : '未配置条件'
    case 'parallel':
      const strategy = { all: '全部完成', any: '任一成功', collect: '收集结果' }
      return strategy[cfg.fail_strategy] || '并行分支'
    case 'wait':
      return `等待 ${cfg.wait_seconds || 10} 秒`
    case 'notify':
      return cfg.channel === 'email' ? '邮件通知' : cfg.channel === 'wecom' ? '企业微信' : '钉钉'
    case 'comment':
      return cfg.comment ? truncate(cfg.comment, 20) : ''
    default:
      return ''
  }
})

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}
</script>

<style lang="scss" scoped>
.custom-node {
  min-width: 180px;
  max-width: 240px;
  background: #fff;
  border: 2px solid #dcdfe6;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  }

  &.selected {
    box-shadow: 0 0 0 2px v-bind(color);
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

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  color: #fff;

  .node-icon {
    font-size: 16px;
  }

  .node-label {
    font-size: 13px;
    font-weight: 500;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.node-body {
  padding: 10px 12px;
  position: relative;

  .node-info {
    .info-item {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: #666;
      margin-bottom: 4px;

      .el-icon {
        font-size: 12px;
      }

      &.command-preview,
      &.script-preview {
        background: #f5f7fa;
        padding: 4px 8px;
        border-radius: 4px;
        font-family: monospace;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }

  .node-description {
    margin-top: 6px;
    padding: 4px 6px;
    background: #f5f7fa;
    border-radius: 4px;
    border-left: 3px solid v-bind(color);
    
    .desc-text {
      font-size: 11px;
      color: #666;
      line-height: 1.4;
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    
    &.has-user-desc {
      background: linear-gradient(135deg, #e8f4fd 0%, #f0f9ff 100%);
      border-left-color: #409EFF;
      
      .desc-text {
        color: #409EFF;
        font-weight: 500;
      }
    }
  }

  // 条件分支节点的状态分支指示
  .condition-branches {
    display: flex;
    justify-content: space-around;
    margin-top: 8px;
    padding: 6px 8px;
    background: #f5f7fa;
    border-radius: 4px;
    font-size: 11px;

    .branch {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 2px 6px;
      border-radius: 3px;

      .el-icon {
        font-size: 12px;
      }

      &.success-branch {
        color: #67c23a;
        background: #f0f9eb;
      }

      &.fail-branch {
        color: #f56c6c;
        background: #fef0f0;
      }
    }
  }

  .node-status {
    position: absolute;
    top: 8px;
    right: 8px;
    z-index: 10;

    .status-badge {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: #fff;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
      border: 2px solid;

      .el-icon {
        font-size: 14px;

        &.is-loading {
          animation: rotating 2s linear infinite;
        }
      }

      &.running {
        border-color: #e6a23c;
        color: #e6a23c;
      }

      &.success {
        border-color: #67c23a;
        color: #67c23a;
      }

      &.failed {
        border-color: #f56c6c;
        color: #f56c6c;
      }
    }
  }
}

.drag-handle {
  position: absolute;
  bottom: 4px;
  right: 4px;
  opacity: 0;
  transition: opacity 0.2s;
  cursor: move;

  .el-icon {
    font-size: 12px;
    color: #999;
  }
}

.custom-node:hover .drag-handle {
  opacity: 1;
}

// 连接点样式 - 输入蓝色，输出红色
::v-deep(.vue-flow__handle) {
  width: 12px !important;
  height: 12px !important;
  border: 2px solid #fff !important;
  border-radius: 50% !important;
  background: transparent !important;
}

::v-deep(.vue-flow__handle-left) {
  left: -6px !important;
  background: #409EFF !important;
}

::v-deep(.vue-flow__handle-left:hover) {
  background: #66b1ff !important;
}

::v-deep(.vue-flow__handle-right) {
  right: -6px !important;
  background: #f56c6c !important;
}

::v-deep(.vue-flow__handle-right:hover) {
  background: #f78989 !important;
}

// 条件分支节点的双 Handle 样式 - 保持绿红用于区分成功/失败
::v-deep(.vue-flow__handle-right.handle-success) {
  background: #67c23a !important;
  &:hover {
    background: #85ce61 !important;
  }
}

::v-deep(.vue-flow__handle-right.handle-failed) {
  background: #f56c6c !important;
  &:hover {
    background: #f78989 !important;
  }
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
