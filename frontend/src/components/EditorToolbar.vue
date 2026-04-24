<template>
  <div class="editor-toolbar">
    <div class="toolbar-left">
      <el-button-group>
        <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
      </el-button-group>

      <el-input
        v-model="flowName"
        class="flow-name-input"
        placeholder="输入流程名称"
        @blur="handleNameChange"
      />

      <el-tag :type="flowStatusType">{{ flowStatusText }}</el-tag>

      <el-button
        v-if="flowStatus === 'draft'"
        type="success"
        size="small"
        @click="handlePublish"
      >
        发布流程
      </el-button>
    </div>

    <div class="toolbar-center">
      <el-button-group>
        <el-tooltip content="撤销 (Ctrl+Z)" placement="bottom">
          <el-button :icon="RefreshLeft" @click="undo" :disabled="!canUndo" />
        </el-tooltip>
        <el-tooltip content="重做 (Ctrl+Y)" placement="bottom">
          <el-button :icon="RefreshRight" @click="redo" :disabled="!canRedo" />
        </el-tooltip>
      </el-button-group>

      <el-divider direction="vertical" />

      <el-button-group>
        <el-tooltip content="放大" placement="bottom">
          <el-button :icon="ZoomIn" @click="zoomIn" />
        </el-tooltip>
        <el-tooltip content="缩小" placement="bottom">
          <el-button :icon="ZoomOut" @click="zoomOut" />
        </el-tooltip>
        <el-tooltip content="适应画布" placement="bottom">
          <el-button :icon="FullScreen" @click="fitView" />
        </el-tooltip>
        <el-tooltip content="实际大小" placement="bottom">
          <el-button :icon="Aim" @click="resetZoom" />
        </el-tooltip>
      </el-button-group>

      <el-divider direction="vertical" />

      <el-tooltip content="对齐网格" placement="bottom">
        <el-button :icon="Grid" @click="toggleSnap" :type="snapToGrid ? 'primary' : ''">
          <span style="font-size: 12px; margin-left: 4px;">网格</span>
        </el-button>
      </el-tooltip>

      <el-tooltip content="显示迷你地图" placement="bottom">
        <el-button :icon="MapLocation" @click="toggleMinimap" :type="showMinimap ? 'primary' : ''" />
      </el-tooltip>
    </div>

    <div class="toolbar-right">
      <el-button :icon="Check" @click="validateFlow">校验</el-button>
      <el-button :icon="Document" @click="saveFlow" :loading="saving">
        保存
      </el-button>
      <el-button type="primary" :icon="VideoPlay" @click="executeFlow" :loading="executing">
        执行
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, RefreshLeft, RefreshRight, ZoomIn, ZoomOut,
  FullScreen, Aim, Grid, MapLocation, Check, Document, VideoPlay
} from '@element-plus/icons-vue'

const props = defineProps({
  flowName: String,
  flowStatus: {
    type: String,
    default: 'draft'
  },
  canUndo: Boolean,
  canRedo: Boolean,
  saving: Boolean,
  executing: Boolean,
  snapToGrid: Boolean,
  showMinimap: Boolean
})

const emit = defineEmits([
  'update:flowName', 'save', 'execute', 'validate', 'publish',
  'undo', 'redo', 'zoomIn', 'zoomOut', 'fitView', 'resetZoom',
  'toggleSnap', 'toggleMinimap', 'back'
])

const router = useRouter()

const flowStatusType = computed(() => {
  const map = { draft: 'info', published: 'success' }
  return map[props.flowStatus] || 'info'
})

const flowStatusText = computed(() => {
  const map = { draft: '草稿', published: '已发布' }
  return map[props.flowStatus] || '草稿'
})

function handleNameChange() {
  emit('update:flowName', props.flowName)
}

function goBack() {
  emit('back')
}

function handlePublish() {
  emit('publish')
}

function validateFlow() {
  emit('validate')
}

function saveFlow() {
  emit('save')
}

function executeFlow() {
  emit('execute')
}

function undo() {
  emit('undo')
}

function redo() {
  emit('redo')
}

function zoomIn() {
  emit('zoomIn')
}

function zoomOut() {
  emit('zoomOut')
}

function fitView() {
  emit('fitView')
}

function resetZoom() {
  emit('resetZoom')
}

function toggleSnap() {
  emit('toggleSnap')
}

function toggleMinimap() {
  emit('toggleMinimap')
}
</script>

<style lang="scss" scoped>
.editor-toolbar {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;

  .toolbar-left,
  .toolbar-center,
  .toolbar-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .toolbar-left {
    .flow-name-input {
      width: 200px;
    }
  }

  .toolbar-center {
    :deep(.el-divider) {
      margin: 0 4px;
    }
  }
}
</style>
