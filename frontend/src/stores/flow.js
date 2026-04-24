import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useFlowStore = defineStore('flow', () => {
  // 当前编辑的流程数据
  const currentFlow = ref(null)
  const nodes = ref([])
  const edges = ref([])

  // 节点类型定义
  const nodeTypes = {
    command: {
      label: '命令节点',
      icon: 'Cpu',
      color: '#409EFF',
      description: '执行单个 Ansible 命令'
    },
    script: {
      label: '脚本节点',
      icon: 'Document',
      color: '#67C23A',
      description: '执行本地或远程脚本'
    },
    playbook: {
      label: 'Playbook 节点',
      icon: 'Tickets',
      color: '#E6A23C',
      description: '执行 Ansible Playbook'
    },
    file: {
      label: '文件节点',
      icon: 'FolderOpened',
      color: '#909399',
      description: '推送或拉取文件'
    },
    loop: {
      label: '循环节点',
      icon: 'Refresh',
      color: '#9B59B6',
      description: '遍历执行循环体'
    },
    condition: {
      label: '条件分支',
      icon: 'Operation',
      color: '#F56C6C',
      description: '根据条件分支执行'
    },
    wait: {
      label: '等待节点',
      icon: 'Clock',
      color: '#909399',
      description: '延时等待'
    },
    notify: {
      label: '通知节点',
      icon: 'Bell',
      color: '#E6A23C',
      description: '发送执行通知'
    },
    comment: {
      label: '注释节点',
      icon: 'ChatLineSquare',
      color: '#67C23A',
      description: '添加流程说明'
    }
  }

  function setCurrentFlow(flow) {
    currentFlow.value = flow
    if (flow?.flow_data) {
      nodes.value = flow.flow_data.nodes || []
      edges.value = flow.flow_data.edges || []
    }
  }

  function updateNodes(newNodes) {
    nodes.value = newNodes
  }

  function updateEdges(newEdges) {
    edges.value = newEdges
  }

  function addNode(node) {
    nodes.value.push(node)
  }

  function removeNode(nodeId) {
    nodes.value = nodes.value.filter(n => n.id !== nodeId)
    // 同时删除相关连线
    edges.value = edges.value.filter(
      e => e.source !== nodeId && e.target !== nodeId
    )
  }

  function updateNode(nodeId, updates) {
    const index = nodes.value.findIndex(n => n.id === nodeId)
    if (index !== -1) {
      nodes.value[index] = { ...nodes.value[index], ...updates }
    }
  }

  function getFlowData() {
    return {
      nodes: nodes.value,
      edges: edges.value
    }
  }

  function reset() {
    currentFlow.value = null
    nodes.value = []
    edges.value = []
  }

  return {
    currentFlow,
    nodes,
    edges,
    nodeTypes,
    setCurrentFlow,
    updateNodes,
    updateEdges,
    addNode,
    removeNode,
    updateNode,
    getFlowData,
    reset
  }
})
