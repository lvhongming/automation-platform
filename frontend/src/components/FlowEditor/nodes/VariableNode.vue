<template>
  <div
    class="custom-node variable-node"
    :class="[`node-${nodeStatus || 'pending'}`, { 'selected': selected }]"
  >
    <!-- 左侧输入 Handle -->
    <Handle id="target" type="target" :position="Position.Left" 
      :style="{ top: '50%', background: '#409EFF' }" class="handle" />

    <div class="node-header">
      <el-icon class="node-icon"><Setting /></el-icon>
      <span class="node-label">{{ data.label || '变量设置' }}</span>
    </div>

    <div class="node-body">
      <div class="var-list" v-if="varEntries.length > 0">
        <div class="var-item" v-for="(item, idx) in varEntries" :key="idx">
          <span class="var-key">{{ item.key }}</span>
          <span class="var-separator">=</span>
          <span class="var-value">{{ item.value || '(空)' }}</span>
        </div>
      </div>
      <div class="var-empty" v-else>
        <span>点击配置变量</span>
      </div>
    </div>

    <!-- 右侧输出 Handle -->
    <Handle id="source" type="source" :position="Position.Right" 
      :style="{ top: '50%', background: '#f56c6c' }" class="handle" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Position, Handle } from '@vue-flow/core'
import { Setting } from '@element-plus/icons-vue'

const props = defineProps({
  id: String,
  type: String,
  data: Object,
  selected: Boolean,
  nodeStatus: String
})

const varEntries = computed(() => {
  const varText = props.data?.config?.variables || ""
  if (!varText) return []
  
  return varText.split("\n")
    .map(line => {
      const trimmed = line.trim()
      if (!trimmed) return null
      if (trimmed.includes("=")) {
        const [key, ...rest] = trimmed.split("=")
        return { key: key.trim(), value: rest.join("=").trim() }
      }
      if (trimmed.includes(":")) {
        const [key, ...rest] = trimmed.split(":")
        return { key: key.trim(), value: rest.join(":").trim() }
      }
      return { key: trimmed, value: '' }
    })
    .filter(Boolean)
    .slice(0, 5)  // 最多显示5个
})
</script>

<style lang="scss" scoped>
.variable-node {
  min-width: 180px;
  max-width: 240px;
  background: #fff;
  border: 2px solid #409eff;
  border-radius: 12px;
  overflow: visible;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);

  &:hover {
    box-shadow: 0 4px 16px rgba(64, 158, 255, 0.3);
  }

  &.selected {
    box-shadow: 0 0 0 3px #409eff;
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
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;

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

  .var-list {
    display: flex;
    flex-direction: column;
    gap: 4px;

    .var-item {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      padding: 4px 6px;
      background: #ecf5ff;
      border-radius: 4px;

      .var-key {
        color: #409eff;
        font-weight: 600;
      }

      .var-separator {
        color: #909399;
      }

      .var-value {
        color: #606266;
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }

  .var-empty {
    text-align: center;
    color: #909399;
    font-size: 11px;
    padding: 8px;
  }
}

::v-deep(.vue-flow__handle) {
  width: 12px !important;
  height: 12px !important;
  border: 2px solid #fff !important;
  border-radius: 50% !important;

  &:hover {
    transform: scale(1.2);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
</style>
