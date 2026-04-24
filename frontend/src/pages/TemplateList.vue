<template>
  <div class="template-list page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>脚本模板库</span>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon> 新建模板
          </el-button>
        </div>
      </template>

      <!-- 搜索栏 -->
      <el-form :inline="true" class="search-form">
        <el-form-item label="关键词">
          <el-input v-model="searchForm.keyword" placeholder="名称/描述" clearable style="width: 150px" />
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
        <el-form-item label="类型" v-if="activeTab === 'script'">
          <el-select v-model="searchForm.script_type" placeholder="选择类型" clearable style="width: 120px">
            <el-option label="Shell" value="shell" />
            <el-option label="Python" value="python" />
            <el-option label="PowerShell" value="powershell" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="Playbook 模板" name="playbook">
          <div class="template-grid" v-loading="loading">
            <el-card
              v-for="template in playbookTemplates"
              :key="template.id"
              class="template-card"
              shadow="hover"
            >
              <template #header>
                <div class="template-header">
                  <span>{{ template.name }}</span>
                  <el-tag size="small">{{ template.category }}</el-tag>
                </div>
              </template>
              <div class="template-content">
                <p class="description">{{ template.description || '暂无描述' }}</p>
                <div class="tags">
                  <el-tag
                    v-for="tag in (template.tags || [])"
                    :key="tag"
                    size="small"
                    type="info"
                  >
                    {{ tag }}
                  </el-tag>
                </div>
              </div>
              <div class="template-footer">
                <el-button type="primary" size="small" @click="useTemplate(template)">
                  使用
                </el-button>
                <el-button size="small" @click="viewTemplate(template)">
                  详情
                </el-button>
                <el-button size="small" @click="handleCopyTemplate(template, 'playbook')">
                  复制
                </el-button>
                <el-button size="small" type="danger" link @click="handleDeleteTemplate(template, 'playbook')">
                  删除
                </el-button>
              </div>
            </el-card>
          </div>
          <el-empty v-if="playbookTemplates.length === 0 && !loading" description="暂无模板" />
        </el-tab-pane>

        <el-tab-pane label="脚本模板" name="script">
          <div class="template-grid" v-loading="loading">
            <el-card
              v-for="template in scriptTemplates"
              :key="template.id"
              class="template-card"
              shadow="hover"
            >
              <template #header>
                <div class="template-header">
                  <span>{{ template.name }}</span>
                  <el-tag size="small" type="success">{{ template.script_type }}</el-tag>
                </div>
              </template>
              <div class="template-content">
                <p class="description">{{ template.description || '暂无描述' }}</p>
                <div class="tags">
                  <el-tag
                    v-for="tag in (template.tags || [])"
                    :key="tag"
                    size="small"
                    type="info"
                  >
                    {{ tag }}
                  </el-tag>
                </div>
              </div>
              <div class="template-footer">
                <el-button type="primary" size="small" @click="useTemplate(template)">
                  使用
                </el-button>
                <el-button size="small" @click="viewTemplate(template)">
                  详情
                </el-button>
                <el-button size="small" @click="handleCopyTemplate(template, 'script')">
                  复制
                </el-button>
                <el-button size="small" type="danger" link @click="handleDeleteTemplate(template, 'script')">
                  删除
                </el-button>
              </div>
            </el-card>
          </div>
          <el-empty v-if="scriptTemplates.length === 0 && !loading" description="暂无模板" />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 模板详情对话框 -->
    <el-dialog v-model="showDetailDialog" :title="currentTemplate?.name" width="700px">
      <pre class="template-code">{{ currentTemplate?.content }}</pre>
      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
        <el-button type="primary" @click="useTemplate(currentTemplate)">使用此模板</el-button>
      </template>
    </el-dialog>

    <!-- 创建模板对话框 -->
    <el-dialog v-model="showCreateDialog" :title="'新建' + (activeTab === 'playbook' ? 'Playbook' : '脚本') + '模板'" width="600px">
      <el-form :model="templateForm" :rules="templateRules" ref="formRef" label-width="100px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="templateForm.name" placeholder="模板名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="templateForm.description" type="textarea" :rows="2" placeholder="模板描述" />
        </el-form-item>
        <el-form-item label="分类" v-if="activeTab === 'playbook'">
          <el-input v-model="templateForm.category" placeholder="如: Web服务, 数据库" />
        </el-form-item>
        <el-form-item label="类型" v-if="activeTab === 'script'" prop="script_type">
          <el-select v-model="templateForm.script_type" placeholder="选择类型" style="width: 100%">
            <el-option label="Shell" value="shell" />
            <el-option label="Python" value="python" />
            <el-option label="PowerShell" value="powershell" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="templateForm.tags"
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
        <el-form-item label="内容" prop="content">
          <el-input
            v-model="templateForm.content"
            type="textarea"
            :rows="10"
            placeholder="模板内容"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="submitTemplate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getPlaybooks, getScripts,
  createPlaybook, createScript,
  deletePlaybook, deleteScript,
  copyPlaybook, copyScript
} from '@/services/templates'

const router = useRouter()

const activeTab = ref('playbook')
const playbookTemplates = ref([])
const scriptTemplates = ref([])
const showDetailDialog = ref(false)
const showCreateDialog = ref(false)
const currentTemplate = ref(null)
const loading = ref(false)
const formRef = ref()

// 可用标签列表
const availableTags = ref([])

const searchForm = reactive({
  keyword: '',
  tags: [],
  script_type: ''
})

const templateForm = reactive({
  name: '',
  description: '',
  category: '',
  script_type: 'shell',
  tags: [],
  content: ''
})

const templateRules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  script_type: [{ required: true, message: '请选择脚本类型', trigger: 'change' }],
  content: [{ required: true, message: '请输入模板内容', trigger: 'blur' }]
}

async function loadPlaybooks() {
  loading.value = true
  try {
    const params = {}
    if (searchForm.keyword) {
      params.keyword = searchForm.keyword
    }
    if (searchForm.tags && searchForm.tags.length > 0) {
      params.tags = searchForm.tags.join(',')
    }
    const res = await getPlaybooks(params)
    playbookTemplates.value = res?.items || []
    updateAvailableTags()
  } catch (error) {
    ElMessage.error('加载 Playbook 模板失败')
  } finally {
    loading.value = false
  }
}

async function loadScripts() {
  loading.value = true
  try {
    const params = {}
    if (searchForm.keyword) {
      params.keyword = searchForm.keyword
    }
    if (searchForm.tags && searchForm.tags.length > 0) {
      params.tags = searchForm.tags.join(',')
    }
    if (searchForm.script_type) {
      params.script_type = searchForm.script_type
    }
    const res = await getScripts(params)
    scriptTemplates.value = res?.items || []
    updateAvailableTags()
  } catch (error) {
    ElMessage.error('加载脚本模板失败')
  } finally {
    loading.value = false
  }
}

function updateAvailableTags() {
  const tags = new Set()
  playbookTemplates.value.forEach(t => {
    if (t.tags && Array.isArray(t.tags)) {
      t.tags.forEach(tag => tags.add(tag))
    }
  })
  scriptTemplates.value.forEach(t => {
    if (t.tags && Array.isArray(t.tags)) {
      t.tags.forEach(tag => tags.add(tag))
    }
  })
  availableTags.value = Array.from(tags).sort()
}

function handleTabChange() {
  if (activeTab.value === 'playbook') {
    loadPlaybooks()
  } else {
    loadScripts()
  }
}

function handleSearch() {
  if (activeTab.value === 'playbook') {
    loadPlaybooks()
  } else {
    loadScripts()
  }
}

function resetSearch() {
  searchForm.keyword = ''
  searchForm.tags = []
  searchForm.script_type = ''
  if (activeTab.value === 'playbook') {
    loadPlaybooks()
  } else {
    loadScripts()
  }
}

function viewTemplate(template) {
  currentTemplate.value = template
  showDetailDialog.value = true
}

function useTemplate(template) {
  showDetailDialog.value = false
  router.push({ name: 'FlowEditor', query: { template_id: template.id } })
  ElMessage.success('已选择模板，请拖入节点后使用')
}

async function submitTemplate() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  try {
    if (activeTab.value === 'playbook') {
      await createPlaybook({
        name: templateForm.name,
        description: templateForm.description,
        category: templateForm.category || '未分类',
        tags: templateForm.tags || [],
        content: templateForm.content
      })
    } else {
      await createScript({
        name: templateForm.name,
        description: templateForm.description,
        script_type: templateForm.script_type,
        tags: templateForm.tags || [],
        content: templateForm.content
      })
    }
    ElMessage.success('创建成功')
    showCreateDialog.value = false
    resetTemplateForm()
    handleTabChange()
  } catch (error) {
    ElMessage.error('创建失败')
  }
}

function resetTemplateForm() {
  templateForm.name = ''
  templateForm.description = ''
  templateForm.category = ''
  templateForm.script_type = 'shell'
  templateForm.tags = []
  templateForm.content = ''
}

async function handleDeleteTemplate(template, type) {
  try {
    await ElMessageBox.confirm(`确定要删除模板「${template.name}」吗？`, '提示', { type: 'warning' })
    if (type === 'playbook') {
      await deletePlaybook(template.id)
      loadPlaybooks()
    } else {
      await deleteScript(template.id)
      loadScripts()
    }
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function handleCopyTemplate(template, type) {
  try {
    if (type === 'playbook') {
      await copyPlaybook(template.id)
      ElMessage.success('Playbook 模板复制成功')
      loadPlaybooks()
    } else {
      await copyScript(template.id)
      ElMessage.success('脚本模板复制成功')
      loadScripts()
    }
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

onMounted(() => {
  loadPlaybooks()
})
</script>

<style lang="scss" scoped>
.template-list {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .search-form {
    margin-bottom: 16px;
  }

  .template-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
    padding: 10px;
  }

  .template-card {
    .template-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .template-content {
      .description {
        color: #666;
        font-size: 14px;
        margin-bottom: 10px;
      }

      .tags {
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
      }
    }

    .template-footer {
      margin-top: 15px;
      display: flex;
      justify-content: flex-end;
      gap: 10px;
    }
  }

  .template-code {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 20px;
    border-radius: 4px;
    max-height: 400px;
    overflow: auto;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.5;
  }
}
</style>
