<template>
  <div
    class="custom-node end-node"
    :class="{ 'selected': selected }"
  >
    <!-- 结束节点只有左侧连接点 - 输入蓝色 -->
    <Handle id="target" type="target" :position="Position.Left" :style="{ background: '#409EFF', width: '12px', height: '12px', left: '-6px' }" />
    
    <div class="node-header">
      <el-icon class="node-icon"><CircleClose /></el-icon>
      <span class="node-label">结束</span>
    </div>
  </div>
</template>

<script setup>
import { Position } from '@vue-flow/core'
import { Handle } from '@vue-flow/core'
import { CircleClose } from '@element-plus/icons-vue'

defineProps({
  id: String,
  type: String,
  data: Object,
  selected: Boolean
})

defineExpose({ Position })
</script>

<style lang="scss" scoped>
.end-node {
  min-width: 100px;
  max-width: 140px;
  background: linear-gradient(135deg, #f56c6c 0%, #f78989 100%);
  border: 2px solid #f56c6c;
  border-radius: 30px;
  overflow: visible;
  box-shadow: 0 2px 8px rgba(245, 108, 108, 0.3);

  &:hover {
    box-shadow: 0 4px 16px rgba(245, 108, 108, 0.4);
    transform: scale(1.02);
  }

  &.selected {
    box-shadow: 0 0 0 3px #f56c6c;
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

::v-deep(.vue-flow__handle#target) {
  background: #409EFF !important;
  left: -6px !important;
}
</style>
