<template>
  <div
    class="custom-node start-node"
    :class="{ 'selected': selected }"
  >
    <div class="node-header">
      <el-icon class="node-icon"><CaretRight /></el-icon>
      <span class="node-label">开始</span>
    </div>
    
    <!-- 开始节点只有右侧连接点 - 输出红色 -->
    <Handle id="source" type="source" :position="Position.Right" :style="{ background: '#f56c6c', width: '12px', height: '12px', right: '-6px' }" />
  </div>
</template>

<script setup>
import { Position } from '@vue-flow/core'
import { Handle } from '@vue-flow/core'
import { CaretRight } from '@element-plus/icons-vue'

defineProps({
  id: String,
  type: String,
  data: Object,
  selected: Boolean
})

defineExpose({ Position })
</script>

<style lang="scss" scoped>
.start-node {
  min-width: 100px;
  max-width: 140px;
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
  border: 2px solid #67c23a;
  border-radius: 30px;
  overflow: visible;
  box-shadow: 0 2px 8px rgba(103, 194, 58, 0.3);

  &:hover {
    box-shadow: 0 4px 16px rgba(103, 194, 58, 0.4);
    transform: scale(1.02);
  }

  &.selected {
    box-shadow: 0 0 0 3px #67c23a;
  }

  .node-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 10px 16px;
    color: #fff;

    .node-icon {
      font-size: 14px;
    }

    .node-label {
      font-size: 14px;
      font-weight: 600;
    }
  }
}

// 覆盖 Handle 样式
::v-deep(.vue-flow__handle) {
  background: transparent !important;
  width: 12px !important;
  height: 12px !important;
  border: 2px solid #fff !important;
  border-radius: 50% !important;
}

::v-deep(.vue-flow__handle#source) {
  background: #f56c6c !important;
  right: -6px !important;
}
</style>
