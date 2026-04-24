<template>
  <div class="node-library">
    <div class="library-header">
      <el-icon><Grid /></el-icon>
      节点库
    </div>

    <!-- 搜索 -->
    <el-input
      v-model="searchText"
      placeholder="搜索节点..."
      prefix-icon="Search"
      size="small"
      clearable
      class="library-search"
    />

    <!-- 节点分类 -->
    <el-collapse v-model="activeCategories">
      <!-- 基础节点 -->
      <el-collapse-item title="基础节点" name="basic">
        <div class="node-list">
          <div
            v-for="node in filterNodes(basicNodes)"
            :key="node.type"
            class="node-item"
            draggable="true"
            @dragstart="onDragStart($event, node.type)"
            @click="onNodeClick(node.type)"
          >
            <el-icon :style="{ color: node.color }">
              <component :is="node.icon" />
            </el-icon>
            <div class="node-info">
              <span class="node-label">{{ node.label }}</span>
              <span class="node-desc">{{ node.description }}</span>
            </div>
          </div>
        </div>
      </el-collapse-item>

      <!-- 逻辑节点 -->
      <el-collapse-item title="逻辑节点" name="logic">
        <div class="node-list">
          <div
            v-for="node in filterNodes(logicNodes)"
            :key="node.type"
            class="node-item"
            draggable="true"
            @dragstart="onDragStart($event, node.type)"
            @click="onNodeClick(node.type)"
          >
            <el-icon :style="{ color: node.color }">
              <component :is="node.icon" />
            </el-icon>
            <div class="node-info">
              <span class="node-label">{{ node.label }}</span>
              <span class="node-desc">{{ node.description }}</span>
            </div>
          </div>
        </div>
      </el-collapse-item>

      <!-- 辅助节点 -->
      <el-collapse-item title="辅助节点" name="helper">
        <div class="node-list">
          <div
            v-for="node in filterNodes(helperNodes)"
            :key="node.type"
            class="node-item"
            draggable="true"
            @dragstart="onDragStart($event, node.type)"
            @click="onNodeClick(node.type)"
          >
            <el-icon :style="{ color: node.color }">
              <component :is="node.icon" />
            </el-icon>
            <div class="node-info">
              <span class="node-label">{{ node.label }}</span>
              <span class="node-desc">{{ node.description }}</span>
            </div>
          </div>
        </div>
      </el-collapse-item>
    </el-collapse>

    <!-- 常用主机快捷选择 -->
    <div class="library-section">
      <div class="section-header">
        <el-icon><Monitor /></el-icon>
        快捷主机
      </div>
      <el-select
        v-model="selectedHostId"
        placeholder="选择默认主机"
        clearable
        size="small"
        class="host-select"
      >
        <el-option
          v-for="host in hosts"
          :key="host.id"
          :label="`${host.name} (${host.ip_address})`"
          :value="host.id"
        />
      </el-select>
    </div>

    <!-- 模板快捷添加 -->
    <div class="library-section">
      <div class="section-header">
        <el-icon><DocumentCopy /></el-icon>
        快速模板
      </div>
      <div class="template-list">
        <el-tag
          v-for="template in templates"
          :key="template.id"
          class="template-tag"
          @click="useTemplate(template)"
        >
          {{ template.name }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  Grid, Search, Monitor, DocumentCopy,
  Cpu, Document, Tickets, FolderOpened,
  Refresh, Operation, Clock, Bell, ChatLineSquare
} from '@element-plus/icons-vue'
import { getHosts } from '@/services/host'

const emit = defineEmits(['dragstart', 'node-click', 'host-select'])

const searchText = ref('')
const selectedHostId = ref(null)
const hosts = ref([])

const basicNodes = [
  { type: 'command', label: '命令节点', icon: 'Cpu', color: '#409EFF', description: '执行 Ansible 命令' },
  { type: 'script', label: '脚本节点', icon: 'Document', color: '#67C23A', description: '执行本地脚本' },
  { type: 'playbook', label: 'Playbook', icon: 'Tickets', color: '#E6A23C', description: '执行 Playbook' },
  { type: 'file', label: '文件节点', icon: 'FolderOpened', color: '#909399', description: '推送/拉取文件' }
]

const logicNodes = [
  { type: 'variable', label: '变量设置', icon: 'Setting', color: '#409EFF', description: '设置流程变量' },
  { type: 'loop', label: '循环节点', icon: 'Refresh', color: '#9B59B6', description: '遍历执行' },
  { type: 'condition', label: '条件分支', icon: 'Operation', color: '#F56C6C', description: '条件判断' },
  { type: 'wait', label: '等待节点', icon: 'Clock', color: '#909399', description: '延时等待' }
]

const helperNodes = [
  { type: 'notify', label: '通知节点', icon: 'Bell', color: '#E6A23C', description: '发送通知' },
  { type: 'comment', label: '注释节点', icon: 'ChatLineSquare', color: '#67C23A', description: '添加说明' }
]

const templates = ref([
  { id: '1', name: '服务器巡检', nodes: ['command', 'command', 'notify'] },
  { id: '2', name: '批量部署', nodes: ['command', 'script', 'notify'] },
  { id: '3', name: '服务回滚', nodes: ['command', 'command'] }
])

const allNodes = computed(() => [...basicNodes, ...logicNodes, ...helperNodes])

const activeCategories = ref(['basic', 'logic', 'helper'])

function filterNodes(nodes) {
  if (!searchText.value) return nodes
  const keyword = searchText.value.toLowerCase()
  return nodes.filter(n =>
    n.label.toLowerCase().includes(keyword) ||
    n.description.toLowerCase().includes(keyword)
  )
}

function onDragStart(event, type) {
  event.dataTransfer.setData('nodeType', type)
  event.dataTransfer.effectAllowed = 'move'
}

function onNodeClick(type) {
  emit('node-click', type)
}

function useTemplate(template) {
  emit('template-select', template)
}

async function loadHosts() {
  try {
    const res = await getHosts({ page_size: 100 })
    hosts.value = res?.items || []
  } catch (error) {
    console.error('Failed to load hosts:', error)
  }
}

onMounted(() => {
  loadHosts()
})
</script>

<style lang="scss" scoped>
.node-library {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;

  .library-header {
    padding: 16px;
    font-weight: bold;
    border-bottom: 1px solid #e8e8e8;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .library-search {
    padding: 12px 16px;
    border-bottom: 1px solid #e8e8e8;
  }

  :deep(.el-collapse) {
    border: none;
    flex: 1;
    overflow-y: auto;

    .el-collapse-item__header {
      padding: 0 16px;
      font-weight: 500;
    }

    .el-collapse-item__content {
      padding: 0;
    }
  }

  .node-list {
    padding: 8px;
  }

  .node-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 10px 12px;
    margin-bottom: 6px;
    background: #f5f7fa;
    border-radius: 6px;
    cursor: grab;
    transition: all 0.2s;

    &:hover {
      background: #e8e8e8;
      transform: translateX(4px);
    }

    &:active {
      cursor: grabbing;
    }

    .el-icon {
      font-size: 20px;
      margin-top: 2px;
    }

    .node-info {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 2px;

      .node-label {
        font-size: 13px;
        font-weight: 500;
        color: #333;
      }

      .node-desc {
        font-size: 11px;
        color: #999;
      }
    }
  }

  .library-section {
    border-top: 1px solid #e8e8e8;
    padding: 12px;

    .section-header {
      display: flex;
      align-items: center;
      gap: 6px;
      font-weight: 500;
      font-size: 13px;
      margin-bottom: 10px;
      color: #666;
    }

    .host-select {
      width: 100%;
    }

    .template-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;

      .template-tag {
        cursor: pointer;
        &:hover {
          opacity: 0.8;
        }
      }
    }
  }
}
</style>
