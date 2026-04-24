<template>
  <div class="host-list page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>主机管理</span>
          <div>
            <el-button @click="showAddGroupDialog = true">
              <el-icon><FolderAdd /></el-icon> 添加主机组
            </el-button>
            <el-button @click="showCredentialDialog = true">
              <el-icon><Key /></el-icon> 凭据管理
            </el-button>
            <el-button @click="handleExport">
              <el-icon><Upload /></el-icon> 导出
            </el-button>
            <el-button @click="downloadTemplate">
              <el-icon><Download /></el-icon> 下载模板
            </el-button>
            <el-button @click="showImportDialog = true">
              <el-icon><Upload /></el-icon> 导入
            </el-button>
            <el-button type="primary" @click="openHostDialog()">
              <el-icon><Plus /></el-icon> 添加主机
            </el-button>
          </div>
        </div>
      </template>

      <!-- 搜索栏 -->
      <el-form :inline="true" class="search-form">
        <el-form-item label="关键词">
          <el-input v-model="searchForm.keyword" placeholder="名称/IP" clearable style="width: 150px" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="searchForm.tags"
            multiple
            filterable
            allow-create
            placeholder="选择或输入标签"
            clearable
            style="width: 200px"
          >
            <el-option
              v-for="tag in availableTags"
              :key="tag"
              :label="tag"
              :value="tag"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 主机组列表 -->
      <div class="host-groups" v-loading="loading">
        <el-collapse v-model="activeGroups">
          <el-collapse-item
            v-for="group in hostGroups"
            :key="group.id"
            :name="group.id"
          >
            <template #title>
              <div class="group-title">
                <el-icon><Folder /></el-icon>
                <span>{{ group.name }}</span>
                <span class="host-count">({{ group.hosts?.length || 0 }} 台)</span>
                <el-space class="group-actions" v-if="group.id !== '__ungrouped__'">
                  <el-button :icon="Edit" link size="small" @click.stop="editGroup(group)">编辑</el-button>
                  <el-button :icon="Delete" link size="small" type="danger" @click.stop="deleteGroup(group)">删除</el-button>
                </el-space>
              </div>
            </template>

            <el-table :data="group.hosts" stripe size="small" v-if="group.hosts?.length > 0">
              <el-table-column prop="name" label="主机名" width="150">
                <template #default="{ row }">
                  <el-icon><Monitor /></el-icon>
                  {{ row.name }}
                </template>
              </el-table-column>
              <el-table-column prop="ip_address" label="IP地址" width="150" />
              <el-table-column prop="port" label="端口" width="80" />
              <el-table-column prop="host_type" label="类型" width="100">
                <template #default="{ row }">
                  {{ row.host_type === 'service' ? '服务' : '服务器' }}
                </template>
              </el-table-column>
              <el-table-column label="标签" width="180">
                <template #default="{ row }">
                  <el-tag
                    v-for="tag in (row.tags || [])"
                    :key="tag"
                    size="small"
                    type="info"
                    style="margin-right: 4px"
                  >
                    {{ tag }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'online' ? 'success' : 'danger'" size="small">
                    {{ row.status === 'online' ? '在线' : '离线' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="280">
                <template #default="{ row }">
                  <el-button type="primary" link size="small" @click="editHost(row)">编辑</el-button>
                  <el-button type="success" link size="small" @click="testConnection(row)">测试</el-button>
                  <el-button type="warning" link size="small" @click="showMoveDialog(row)">移动</el-button>
                  <el-button type="danger" link size="small" @click="handleDeleteHost(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="该主机组暂无主机" />
          </el-collapse-item>
        </el-collapse>

        <el-empty v-if="hostGroups.length === 0 && !loading" description="暂无主机组，点击上方按钮添加">
          <el-button type="primary" @click="showAddGroupDialog = true">添加主机组</el-button>
        </el-empty>
      </div>
    </el-card>

    <!-- 添加/编辑主机组对话框 -->
    <el-dialog
      v-model="showAddGroupDialog"
      :title="editingGroup ? '编辑主机组' : '添加主机组'"
      width="500px"
    >
      <el-form :model="groupForm" :rules="groupRules" ref="groupFormRef" label-width="100px">
        <el-form-item label="组名称" prop="name">
          <el-input v-model="groupForm.name" placeholder="web-servers" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="groupForm.description" type="textarea" :rows="2" placeholder="Web 服务器组" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddGroupDialog = false">取消</el-button>
        <el-button type="primary" @click="submitGroupForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- 移动主机对话框 -->
    <el-dialog v-model="showMoveDialogFlag" title="移动主机" width="400px">
      <el-form label-width="80px">
        <el-form-item label="主机">
          <span>{{ movingHost?.name }}</span>
        </el-form-item>
        <el-form-item label="当前组">
          <span>{{ movingHost?.group?.name || '未分组' }}</span>
        </el-form-item>
        <el-form-item label="移动到">
          <el-select v-model="targetGroupId" placeholder="选择目标组（留空则移至未分组）" clearable style="width: 100%">
            <el-option
              v-for="group in hostGroups"
              :key="group.id"
              :label="group.name"
              :value="group.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMoveDialogFlag = false">取消</el-button>
        <el-button type="primary" @click="confirmMove">确定移动</el-button>
      </template>
    </el-dialog>

    <!-- 凭据管理对话框 -->
    <el-dialog
      v-model="showCredentialDialog"
      title="凭据管理"
      width="700px"
    >
      <div class="credential-section">
        <div class="section-header">
          <span>创建新凭据</span>
        </div>
        <el-form :model="credentialForm" :rules="credentialRules" ref="credentialFormRef" inline>
          <el-form-item label="凭据名称" prop="name">
            <el-input v-model="credentialForm.name" placeholder="my-ssh-key" style="width: 150px" />
          </el-form-item>
          <el-form-item label="认证方式" prop="type">
            <el-select v-model="credentialForm.type" placeholder="选择方式" style="width: 120px">
              <el-option label="密码认证" value="password" />
              <el-option label="SSH 密钥" value="ssh_key" />
            </el-select>
          </el-form-item>
          <el-form-item label="用户名" prop="username">
            <el-input v-model="credentialForm.username" placeholder="root" style="width: 120px" />
          </el-form-item>
          <el-form-item label="密码/密钥" prop="password" v-if="credentialForm.type === 'password'">
            <el-input v-model="credentialForm.password" type="password" placeholder="密码" show-password style="width: 150px" />
          </el-form-item>
          <el-form-item label="私钥内容" prop="private_key" v-else>
            <el-input v-model="credentialForm.private_key" type="textarea" :rows="3" placeholder="-----BEGIN RSA PRIVATE KEY-----..." style="width: 300px" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="submitCredential" :loading="savingCredential">添加</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-divider />

      <div class="credential-list">
        <el-table :data="credentials" stripe size="small">
          <el-table-column prop="name" label="凭据名称" width="150">
            <template #default="{ row }">
              <el-icon><Key /></el-icon> {{ row.name }}
            </template>
          </el-table-column>
          <el-table-column prop="type" label="认证方式" width="120">
            <template #default="{ row }">
              {{ row.type === 'password' ? '密码' : 'SSH 密钥' }}
            </template>
          </el-table-column>
          <el-table-column prop="username" label="用户名" width="120" />
          <el-table-column prop="hosts_count" label="关联主机" width="100">
            <template #default="{ row }">
              {{ row.hosts_count }} 台
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button type="danger" link size="small" @click="deleteCredential(row)" :disabled="row.hosts_count > 0">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>

    <!-- 导入主机对话框 -->
    <el-dialog v-model="showImportDialog" title="批量导入主机" width="600px">
      <div class="import-section">
        <el-alert type="info" :closable="false" show-icon>
          <template #title>
            支持 CSV 和 INI 格式文件。
            <el-link type="primary" @click="downloadTemplate" :underline="false">
              <el-icon><Download /></el-icon> 下载 CSV 模板
            </el-link>
          </template>
        </el-alert>

        <div class="upload-area">
          <el-upload
            ref="uploadRef"
            class="upload-component"
            drag
            :auto-upload="false"
            :limit="1"
            accept=".csv,.ini"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处，或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">支持 .csv 和 .ini 格式</div>
            </template>
          </el-upload>
        </div>

        <div class="import-tips" v-if="uploadedFile">
          <el-icon><Document /></el-icon>
          <span>已选择: {{ uploadedFile.name }}</span>
          <span class="file-size">({{ formatFileSize(uploadedFile.size) }})</span>
        </div>
      </div>

      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmImport" :loading="importing" :disabled="!selectedFile">
          开始导入
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加/编辑主机对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="editingHost ? '编辑主机' : '添加主机'"
      width="600px"
    >
      <el-form :model="hostForm" :rules="hostRules" ref="formRef" label-width="100px">
        <el-form-item label="主机名称" prop="name">
          <el-input v-model="hostForm.name" placeholder="web-01" />
        </el-form-item>
        <el-form-item label="IP地址" prop="ip_address">
          <el-input v-model="hostForm.ip_address" placeholder="192.168.1.101" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="hostForm.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="主机组" prop="group_id">
          <el-select v-model="hostForm.group_id" placeholder="选择主机组" clearable>
            <el-option
              v-for="group in hostGroups"
              :key="group.id"
              :label="group.name"
              :value="group.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="类型" prop="host_type">
          <el-radio-group v-model="hostForm.host_type">
            <el-radio label="server">服务器</el-radio>
            <el-radio label="service">服务</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="服务名称" v-if="hostForm.host_type === 'service'">
          <el-input v-model="hostForm.service_name" placeholder="nginx" />
        </el-form-item>
        <el-form-item label="认证凭据" prop="credential_id">
          <el-select v-model="hostForm.credential_id" placeholder="选择认证凭据" clearable style="width: 100%">
            <el-option
              v-for="cred in credentials"
              :key="cred.id"
              :label="`${cred.name} (${cred.username || '无用户名'})`"
              :value="cred.id"
            >
              <span><el-icon><Key /></el-icon> {{ cred.name }}</span>
              <span style="color: #999; margin-left: 8px">{{ cred.type === 'password' ? '密码' : '密钥' }} - {{ cred.username || '无用户名' }}</span>
            </el-option>
          </el-select>
          <div class="form-tip">
            <el-link type="primary" :underline="false" @click="showCredentialDialog = true">
              <el-icon><Plus /></el-icon> 创建新凭据
            </el-link>
          </div>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="hostForm.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="hostForm.tags"
            multiple
            filterable
            allow-create
            placeholder="选择或输入标签"
            style="width: 100%"
          >
            <el-option
              v-for="tag in availableTags"
              :key="tag"
              :label="tag"
              :value="tag"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Monitor, FolderAdd, Folder, Delete, Edit, Key, Download, Upload, UploadFilled, Document } from '@element-plus/icons-vue'
import { getHosts, getHostGroups, createHost, updateHost, deleteHost as deleteHostApi, testHostConnection, createHostGroup, updateHostGroup, deleteHostGroup, getCredentials, createCredential, deleteCredential as deleteCredentialApi, moveHost, importInventory, downloadImportTemplate, exportInventory } from '@/services/host'

const activeGroups = ref([])
const hostGroups = ref([])
const hostList = ref([])
const loading = ref(false)
const showAddDialog = ref(false)
const showAddGroupDialog = ref(false)
const showCredentialDialog = ref(false)
const editingHost = ref(null)
const editingGroup = ref(null)
const formRef = ref()
const groupFormRef = ref()
const credentialFormRef = ref()
const savingCredential = ref(false)

const credentials = ref([])

// 移动主机相关
const showMoveDialogFlag = ref(false)
const movingHost = ref(null)
const targetGroupId = ref(null)

// 导入相关
const showImportDialog = ref(false)
const selectedFile = ref(null)
const uploadedFile = ref(null)
const importing = ref(false)
const uploadRef = ref()

const showMoveDialog = (host) => {
  movingHost.value = host
  targetGroupId.value = null
  showMoveDialogFlag.value = true
}

const confirmMove = async () => {
  if (!movingHost.value) return
  try {
    await moveHost(movingHost.value.id, targetGroupId.value || null)
    ElMessage.success('移动成功')
    showMoveDialogFlag.value = false
    loadData()
  } catch (error) {
    ElMessage.error('移动失败')
  }
}

// 可用的标签列表
const availableTags = ref([])

const searchForm = reactive({
  keyword: '',
  tags: []
})

const credentialForm = reactive({
  name: '',
  type: 'password',
  username: '',
  password: '',
  private_key: ''
})

const credentialRules = {
  name: [{ required: true, message: '请输入凭据名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择认证方式', trigger: 'change' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }]
}

const groupForm = reactive({
  name: '',
  description: ''
})

const groupRules = {
  name: [{ required: true, message: '请输入主机组名称', trigger: 'blur' }]
}

const hostForm = reactive({
  name: '',
  ip_address: '',
  port: 22,
  host_type: 'server',
  service_name: '',
  group_id: null,
  credential_id: null,
  description: '',
  tags: []
})

const hostRules = {
  name: [{ required: true, message: '请输入主机名称', trigger: 'blur' }],
  ip_address: [{ required: true, message: '请输入IP地址', trigger: 'blur' }]
}

async function loadData() {
  loading.value = true
  try {
    // 构建搜索参数
    const params = { page_size: 100 }
    if (searchForm.keyword) {
      params.keyword = searchForm.keyword
    }
    if (searchForm.tags && searchForm.tags.length > 0) {
      params.tags = searchForm.tags.join(',')
    }

    const [groupsRes, hostsRes, credsRes] = await Promise.all([
      getHostGroups(),
      getHosts(params),
      getCredentials()
    ])

    // 按主机组分组
    const groups = groupsRes || []
    groups.forEach(g => {
      g.hosts = (hostsRes?.items || []).filter(h => h.group_id === g.id)
    })
    
    // 添加"未分组"虚拟组
    const ungroupedHosts = (hostsRes?.items || []).filter(h => !h.group_id)
    if (ungroupedHosts.length > 0) {
      groups.push({
        id: '__ungrouped__',
        name: '未分组',
        description: '未分配主机组的主机',
        hosts: ungroupedHosts
      })
    }
    
    hostGroups.value = groups
    hostList.value = hostsRes?.items || []
    credentials.value = credsRes || []

    // 更新可用标签列表
    updateAvailableTags()
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function updateAvailableTags() {
  const tags = new Set()
  hostList.value.forEach(h => {
    if (h.tags && Array.isArray(h.tags)) {
      h.tags.forEach(t => tags.add(t))
    }
  })
  availableTags.value = Array.from(tags).sort()
}

function handleSearch() {
  loadData()
}

function resetSearch() {
  searchForm.keyword = ''
  searchForm.tags = []
  loadData()
}

async function submitCredential() {
  const valid = await credentialFormRef.value.validate().catch(() => false)
  if (!valid) return

  savingCredential.value = true
  try {
    const formData = {
      name: credentialForm.name,
      type: credentialForm.type,
      username: credentialForm.username,
      password: credentialForm.type === 'password' ? credentialForm.password : undefined,
      private_key: credentialForm.type === 'ssh_key' ? credentialForm.private_key : undefined
    }
    await createCredential(formData)
    ElMessage.success('凭据创建成功')
    resetCredentialForm()
    loadData()
  } catch (error) {
    console.error('创建凭据失败:', error)
    const msg = error?.response?.data?.detail || '创建失败'
    ElMessage.error(msg)
  } finally {
    savingCredential.value = false
  }
}

function resetCredentialForm() {
  credentialForm.name = ''
  credentialForm.type = 'password'
  credentialForm.username = ''
  credentialForm.password = ''
  credentialForm.private_key = ''
}

async function deleteCredential(cred) {
  try {
    await ElMessageBox.confirm(`确定要删除凭据「${cred.name}」吗？`, '提示', { type: 'warning' })
    await deleteCredentialApi(cred.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function openHostDialog() {
  editingHost.value = null
  resetForm()
  showAddDialog.value = true
}

function editHost(host) {
  editingHost.value = host
  Object.assign(hostForm, {
    name: host.name,
    ip_address: host.ip_address,
    port: host.port,
    host_type: host.host_type,
    service_name: host.service_name,
    group_id: host.group_id,
    credential_id: host.credential_id,
    description: host.description,
    tags: host.tags || []
  })
  showAddDialog.value = true
}

async function submitForm() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  try {
    // 清理表单数据，只保留需要的字段
    const formData = {
      name: hostForm.name,
      ip_address: hostForm.ip_address,
      port: hostForm.port,
      host_type: hostForm.host_type,
      service_name: hostForm.service_name || undefined,
      group_id: hostForm.group_id || undefined,
      credential_id: hostForm.credential_id || undefined,
      description: hostForm.description || undefined,
      tags: hostForm.tags || []
    }

    if (editingHost.value) {
      await updateHost(editingHost.value.id, formData)
      ElMessage.success('更新成功')
    } else {
      await createHost(formData)
      ElMessage.success('添加成功')
    }
    showAddDialog.value = false
    editingHost.value = null
    resetForm()
    loadData()
  } catch (error) {
    console.error('操作失败:', error)
    const msg = error?.response?.data?.detail || '操作失败'
    ElMessage.error(msg)
  }
}

function resetForm() {
  hostForm.name = ''
  hostForm.ip_address = ''
  hostForm.port = 22
  hostForm.host_type = 'server'
  hostForm.service_name = ''
  hostForm.group_id = null
  hostForm.description = ''
  hostForm.tags = []
}

async function testConnection(host) {
  try {
    const res = await testHostConnection(host.id)
    if (res.success) {
      ElMessage.success(`连接成功 (${res.response_time}ms)`)
    } else {
      ElMessage.error(`连接失败: ${res.message}`)
    }
  } catch (error) {
    ElMessage.error('测试失败')
  }
}

async function handleDeleteHost(host) {
  try {
    await ElMessageBox.confirm('确定要删除该主机吗？', '提示', { type: 'warning' })
    await deleteHostApi(host.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function handleImport() {
  ElMessage.info('导入功能开发中')
}

// 导出主机
async function handleExport() {
  try {
    const res = await exportInventory()
    const blob = new Blob([res.content], { type: 'text/plain;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = res.filename || 'hosts.ini'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(link.href)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

// 下载导入模板
async function downloadTemplate() {
  try {
    const res = await downloadImportTemplate()
    // 创建下载链接
    const blob = new Blob([res.content], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = res.filename || 'hosts_template.csv'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(link.href)
    ElMessage.success('模板下载成功')
  } catch (error) {
    ElMessage.error('下载模板失败')
  }
}

// 文件选择处理
function handleFileChange(file) {
  selectedFile.value = file.raw
  uploadedFile.value = file
}

// 文件移除处理
function handleFileRemove() {
  selectedFile.value = null
  uploadedFile.value = null
}

// 确认导入
async function confirmImport() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  importing.value = true
  try {
    const res = await importInventory(selectedFile.value)
    ElMessage.success(res.message || '导入成功')
    showImportDialog.value = false
    selectedFile.value = null
    uploadedFile.value = null
    uploadRef.value?.clearFiles()
    loadData()
  } catch (error) {
    const msg = error?.response?.data?.detail || '导入失败'
    ElMessage.error(msg)
  } finally {
    importing.value = false
  }
}

// 格式化文件大小
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function editGroup(group) {
  editingGroup.value = group
  groupForm.name = group.name
  groupForm.description = group.description || ''
  showAddGroupDialog.value = true
}

function resetGroupForm() {
  editingGroup.value = null
  groupForm.name = ''
  groupForm.description = ''
}

async function submitGroupForm() {
  const valid = await groupFormRef.value.validate().catch(() => false)
  if (!valid) return

  try {
    if (editingGroup.value) {
      await updateHostGroup(editingGroup.value.id, groupForm)
      ElMessage.success('更新成功')
    } else {
      await createHostGroup(groupForm)
      ElMessage.success('添加成功')
    }
    showAddGroupDialog.value = false
    resetGroupForm()
    loadData()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

async function deleteGroup(group) {
  try {
    const hostCount = group.hosts?.length || 0
    let message = `确定要删除主机组「${group.name}」吗？`
    
    if (hostCount > 0) {
      await ElMessageBox.confirm(
        `主机组「${group.name}」下有 ${hostCount} 台主机。删除后，主机将被移至未分组。是否继续？`,
        '提示',
        { type: 'warning', confirmButtonText: '删除并移至未分组', cancelButtonText: '取消' }
      )
      await deleteHostGroup(group.id, true)
      ElMessage.success(`已删除主机组，${hostCount} 台主机已移至未分组`)
    } else {
      await ElMessageBox.confirm(message, '提示', { type: 'warning' })
      await deleteHostGroup(group.id)
      ElMessage.success('删除成功')
    }
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

watch(showAddGroupDialog, (val) => {
  if (!val) {
    resetGroupForm()
  }
})

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.host-list {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .search-form {
    margin-bottom: 16px;
  }

  .host-groups {
    .group-title {
      display: flex;
      align-items: center;
      gap: 8px;
      flex: 1;
      
      .group-actions {
        margin-left: auto;
      }
    }

    .host-count {
      color: #999;
      font-size: 12px;
      margin-left: 8px;
    }
  }

  .credential-section {
    .section-header {
      font-weight: bold;
      margin-bottom: 12px;
    }
  }

  .form-tip {
    margin-top: 8px;
    font-size: 12px;
  }

  .import-section {
    .upload-area {
      margin: 20px 0;
    }

    .upload-component {
      width: 100%;

      :deep(.el-upload-dragger) {
        padding: 40px 20px;
      }
    }

    .import-tips {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px;
      background: #f5f7fa;
      border-radius: 4px;
      margin-top: 16px;

      .file-size {
        color: #999;
        font-size: 12px;
      }
    }
  }
}
</style>
