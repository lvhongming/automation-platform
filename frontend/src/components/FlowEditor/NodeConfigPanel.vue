<template>
  <div class="node-config-panel" v-if="node">
    <div class="panel-header">
      <div class="header-title">
        <el-icon :style="{ color: nodeConfig.color }">
          <component :is="nodeConfig.icon" />
        </el-icon>
        <span>{{ nodeConfig.label }}</span>
      </div>
      <el-button :icon="Close" text @click="emit('close')" />
    </div>

    <el-form
      :model="config"
      label-position="top"
      class="config-form"
      ref="formRef"
    >
      <!-- 通用配置 -->
      <el-form-item label="节点名称">
        <el-input v-model="config.label" placeholder="输入节点名称" />
      </el-form-item>

      <el-form-item label="节点描述">
        <el-input
          v-model="config.description"
          type="textarea"
          :rows="2"
          placeholder="可选描述"
        />
      </el-form-item>

      <!-- 主机选择 -->
      <el-form-item label="执行主机" v-if="showHostSelect">
        <el-select
          v-model="config.config.host_id"
          placeholder="选择主机"
          clearable
          filterable
        >
          <el-option-group label="主机组">
            <el-option
              v-for="group in hostGroups"
              :key="'g-' + group.id"
              :label="group.name"
              :value="'group:' + group.id"
              disabled
            >
              <el-icon><Folder /></el-icon> {{ group.name }}
            </el-option>
          </el-option-group>
          <el-option-group label="单独主机">
            <el-option
              v-for="host in hosts"
              :key="host.id"
              :label="`${host.name} (${host.ip_address})`"
              :value="host.id"
            >
              <el-icon><Monitor /></el-icon> {{ host.name }} ({{ host.ip_address }})
            </el-option>
          </el-option-group>
        </el-select>
      </el-form-item>

      <el-divider content-position="left">执行配置</el-divider>

      <!-- 命令节点配置 -->
      <template v-if="node.type === 'command'">
        <el-form-item label="Ansible 命令">
          <el-input
            v-model="config.config.command"
            type="textarea"
            :rows="4"
            placeholder="yum install nginx -y"
            class="code-input"
          />
          <div class="input-tip">支持 Ansible 模块，如 shell、yum、service 等</div>
        </el-form-item>

        <el-form-item label="执行选项">
          <el-checkbox v-model="config.config.sudo">sudo 权限</el-checkbox>
          <el-checkbox v-model="config.config.ignore_errors">忽略错误</el-checkbox>
        </el-form-item>

        <el-form-item label="超时时间">
          <el-input-number
            v-model="config.config.timeout"
            :min="10"
            :max="3600"
            :step="10"
          />
          <span class="unit">秒</span>
        </el-form-item>
      </template>

      <!-- 脚本节点配置 -->
      <template v-else-if="node.type === 'script'">
        <el-form-item label="脚本类型">
          <el-select v-model="config.config.script_type">
            <el-option label="Shell" value="shell" />
            <el-option label="Python" value="python" />
            <el-option label="PowerShell" value="powershell" />
          </el-select>
        </el-form-item>

        <el-form-item label="脚本来源">
          <el-radio-group v-model="scriptSource">
            <el-radio label="input">手动输入</el-radio>
            <el-radio label="template">从模板选择</el-radio>
            <el-radio label="upload">上传脚本</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="脚本内容" v-if="scriptSource === 'input'">
          <el-input
            v-model="config.config.script_content"
            type="textarea"
            :rows="8"
            placeholder="#!/bin/bash&#10;echo 'Hello World'"
            class="code-input"
          />
        </el-form-item>

        <el-form-item label="选择模板" v-if="scriptSource === 'template'">
          <el-select v-model="selectedTemplate" placeholder="选择模板">
            <el-option
              v-for="t in scriptTemplates"
              :key="t.id"
              :label="t.name"
              :value="t.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="脚本参数">
          <el-input
            v-model="config.config.args"
            placeholder="--env production --version 1.0"
          />
        </el-form-item>
      </template>

      <!-- Playbook 节点配置 -->
      <template v-else-if="node.type === 'playbook'">
        <el-form-item label="选择 Playbook">
          <el-select
            v-model="config.config.playbook_id"
            placeholder="选择 Playbook"
            filterable
          >
            <el-option
              v-for="pb in playbooks"
              :key="pb.id"
              :label="pb.name"
              :value="pb.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="Playbook 内容">
          <el-input
            v-model="config.config.playbook_content"
            type="textarea"
            :rows="8"
            placeholder="- hosts: all&#10;  tasks:&#10;    - name: 示例任务"
            class="code-input"
          />
        </el-form-item>

        <el-form-item label="额外变量">
          <el-input
            v-model="extraVarsText"
            type="textarea"
            :rows="4"
            placeholder="key1: value1&#10;key2: value2"
            class="code-input"
          />
        </el-form-item>
      </template>

      <!-- 循环节点配置 -->
      <template v-else-if="node.type === 'loop'">
        <el-form-item label="循环类型">
          <el-radio-group v-model="config.config.loop_type">
            <el-radio label="count">固定次数</el-radio>
            <el-radio label="hosts">遍历主机</el-radio>
            <el-radio label="array">遍历数组</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="循环次数" v-if="config.config.loop_type === 'count'">
          <el-input-number
            v-model="config.config.loop_count"
            :min="1"
            :max="1000"
          />
        </el-form-item>

        <el-form-item label="循环变量名">
          <el-input v-model="config.config.loop_var" placeholder="item" />
        </el-form-item>

        <el-form-item label="失败策略">
          <el-select v-model="config.config.fail_strategy">
            <el-option label="失败继续（continue）" value="continue" />
            <el-option label="失败跳过（skip）" value="skip" />
            <el-option label="失败停止（break）" value="stop" />
          </el-select>
        </el-form-item>
      </template>

      <!-- 条件节点配置 -->
      <template v-else-if="node.type === 'condition'">
        <el-form-item label="条件类型">
          <el-select v-model="config.config.condition_type">
            <el-option label="节点结果" value="node_result" />
            <el-option label="变量比较" value="var_compare" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
      </template>

      <!-- 变量设置节点配置 -->
      <template v-else-if="node.type === 'variable'">
        <el-form-item label="变量定义">
          <el-input
            v-model="config.config.variables"
            type="textarea"
            :rows="6"
            placeholder="定义流程变量，格式: key=value
示例:
host=192.168.1.10
user=admin
port=22

或使用冒号分隔:
host: 192.168.1.10
user: admin"
          />
          <div class="input-tip">
            支持格式: key=value 或 key: value
            <br/>使用 ${变量名} 或 {{变量名}} 在其他节点中引用
          </div>
        </el-form-item>
      </template>

      <!-- 等待节点配置 -->
      <template v-else-if="node.type === 'wait'">
        <el-form-item label="等待时间">
          <el-input-number
            v-model="config.config.wait_seconds"
            :min="1"
            :max="3600"
          />
          <span class="unit">秒</span>
        </el-form-item>
      </template>

      <!-- 通知节点配置 -->
      <template v-else-if="node.type === 'notify'">
        <el-form-item label="通知渠道">
          <el-select v-model="config.config.channel">
            <el-option label="邮件" value="email" />
            <el-option label="企业微信" value="wecom" />
            <el-option label="钉钉" value="dingtalk" />
          </el-select>
        </el-form-item>

        <el-form-item label="通知内容">
          <el-input
            v-model="config.config.message"
            type="textarea"
            :rows="3"
            placeholder="流程「${flow_name}」执行完成"
          />
          <div class="input-tip">
            支持变量: ${flow_name}, ${status}, ${start_time}, ${end_time}
          </div>
        </el-form-item>

        <el-form-item label="通知时机">
          <el-checkbox-group v-model="config.config.notify_on">
            <el-checkbox label="success">成功时</el-checkbox>
            <el-checkbox label="failed">失败时</el-checkbox>
            <el-checkbox label="always">始终</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </template>

      <!-- 注释节点配置 -->
      <template v-else-if="node.type === 'comment'">
        <el-form-item label="注释内容">
          <el-input
            v-model="config.config.comment"
            type="textarea"
            :rows="6"
            placeholder="添加流程说明..."
          />
        </el-form-item>
      </template>

      <el-divider content-position="left">高级配置</el-divider>

      <el-form-item label="失败策略">
        <el-select v-model="config.config.fail_policy">
          <el-option label="停止执行" value="stop" />
          <el-option label="继续执行" value="continue" />
          <el-option label="重试" value="retry" />
        </el-select>
      </el-form-item>

      <el-form-item label="重试次数" v-if="config.config.fail_policy === 'retry'">
        <el-input-number
          v-model="config.config.retry_count"
          :min="1"
          :max="5"
        />
      </el-form-item>
    </el-form>

    <!-- 底部操作 -->
    <div class="panel-footer">
      <el-button type="primary" @click="saveConfig" :loading="saving">
        保存配置
      </el-button>
      <el-button type="danger" @click="deleteNode">
        删除节点
      </el-button>
    </div>
  </div>

  <!-- 空状态 -->
  <div class="panel-empty" v-else>
    <el-icon :size="64"><Setting /></el-icon>
    <p>选择节点以编辑配置</p>
  </div>
</template>

<script setup>
import { ref, computed, watch, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Close, Folder, Monitor, Setting,
  Cpu, Document, Tickets, Refresh, Operation,
  Clock, Bell, ChatLineSquare, FolderOpened
} from '@element-plus/icons-vue'
import { getHosts, getHostGroups } from '@/services/host'
import { getPlaybooks, getScripts } from '@/services/templates'

const props = defineProps({
  node: Object
})

const emit = defineEmits(['close', 'save', 'delete'])

const formRef = ref()
const saving = ref(false)
const hosts = ref([])
const hostGroups = ref([])
const scriptTemplates = ref([])
const playbooks = ref([])
const scriptSource = ref('input')
const selectedTemplate = ref(null)
const extraVarsText = ref('')

const nodeConfig = computed(() => {
  const configs = {
    command: { label: '命令节点', icon: 'Cpu', color: '#409EFF' },
    script: { label: '脚本节点', icon: 'Document', color: '#67C23A' },
    playbook: { label: 'Playbook', icon: 'Tickets', color: '#E6A23C' },
    file: { label: '文件节点', icon: 'FolderOpened', color: '#909399' },
    loop: { label: '循环节点', icon: 'Refresh', color: '#9B59B6' },
    condition: { label: '条件分支', icon: 'Operation', color: '#F56C6C' },
    wait: { label: '等待节点', icon: 'Clock', color: '#909399' },
    notify: { label: '通知节点', icon: 'Bell', color: '#E6A23C' },
    comment: { label: '注释节点', icon: 'ChatLineSquare', color: '#67C23A' },
    variable: { label: '变量设置', icon: 'Setting', color: '#409EFF' }
  }
  return configs[props.node?.type] || configs.command
})

const showHostSelect = computed(() => {
  return ['command', 'script', 'playbook', 'file'].includes(props.node?.type)
})

const config = reactive({
  label: '',
  description: '',
  config: {
    host_id: null,
    command: '',
    script_type: 'shell',
    script_content: '',
    playbook_id: null,
    playbook_content: '',
    extra_vars_text: '',
    args: '',
    sudo: false,
    ignore_errors: false,
    timeout: 60,
    loop_type: 'count',
    loop_count: 1,
    loop_var: 'item',
    wait_seconds: 10,
    channel: 'email',
    message: '',
    notify_on: ['always'],
    condition_type: 'node_result',
    fail_policy: 'stop',
    retry_count: 1,
    comment: ''
  }
})

watch(() => props.node, (newNode) => {
  if (newNode) {
    config.label = newNode.data?.label || ''
    config.description = newNode.data?.description || ''
    Object.assign(config.config, newNode.data?.config || {})
    // 根据配置决定脚本来源
    if (newNode.data?.config?.template_id) {
      scriptSource.value = 'template'
      selectedTemplate.value = newNode.data.config.template_id
    } else if (newNode.data?.config?.script_content) {
      scriptSource.value = 'input'
      selectedTemplate.value = null
    } else {
      scriptSource.value = 'input'
      selectedTemplate.value = null
    }
  }
}, { immediate: true })

// 监听模板选择
watch(selectedTemplate, (templateId) => {
  if (templateId && scriptSource.value === 'template') {
    const template = scriptTemplates.value.find(t => t.id === templateId)
    if (template) {
      config.config.template_id = templateId
      config.config.script_content = template.content || ''
      config.config.script_type = template.script_type || 'shell'
    }
  }
})


async function loadData() {
  try {
    const [hostsRes, groupsRes, playbooksRes, scriptsRes] = await Promise.all([
      getHosts({ page_size: 100 }),
      getHostGroups(),
      getPlaybooks({ page_size: 100 }),
      getScripts({ page_size: 100 })
    ])
    hosts.value = hostsRes?.items || []
    hostGroups.value = groupsRes || []
    playbooks.value = playbooksRes?.items || []
    scriptTemplates.value = scriptsRes?.items || []
  } catch (error) {
    console.error('Failed to load data:', error)
  }
}

function saveConfig() {
  emit('save', {
    ...props.node,
    data: {
      ...props.node.data,
      label: config.label,
      description: config.description,
      config: { ...config.config }
    }
  })
  ElMessage.success('配置已保存')
}

function deleteNode() {
  emit('delete', props.node)
}

loadData()
</script>

<style lang="scss" scoped>
.node-config-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;

  .panel-header {
    padding: 16px;
    border-bottom: 1px solid #e8e8e8;
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: bold;

      .el-icon {
        font-size: 20px;
      }
    }
  }

  .config-form {
    flex: 1;
    overflow-y: auto;
    padding: 16px;

    .unit {
      margin-left: 8px;
      color: #999;
    }

    .input-tip {
      font-size: 12px;
      color: #999;
      margin-top: 4px;
    }

    .code-input {
      :deep(.el-textarea__inner) {
        font-family: 'Courier New', monospace;
        font-size: 13px;
      }
    }
  }

  .panel-footer {
    padding: 16px;
    border-top: 1px solid #e8e8e8;
    display: flex;
    gap: 10px;

    .el-button {
      flex: 1;
    }
  }
}

.panel-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;
  background: #fafafa;

  .el-icon {
    margin-bottom: 16px;
    color: #dcdfe6;
  }
}
</style>
