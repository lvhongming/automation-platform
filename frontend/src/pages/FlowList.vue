<template>
  <div class="flow-list page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>流程管理</span>
          <!-- 测试按钮 -->
          <el-button type="primary" @click="goToEditor">
            <el-icon><Plus /></el-icon> 新建流程
          </el-button>
        </div>
      </template>

      <!-- 搜索栏 -->
      <el-form :inline="true" class="search-form">
        <el-form-item label="流程名称">
          <el-input v-model="searchForm.keyword" placeholder="搜索流程" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="选择状态" clearable>
            <el-option label="草稿" value="draft" />
            <el-option label="已发布" value="published" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadFlows">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 流程列表 -->
      <el-table :data="flows" v-loading="loading" stripe>
        <el-table-column prop="name" label="流程名称" min-width="200">
          <template #default="{ row }">
            <el-link type="primary" @click="editFlow(row)">{{ row.name }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'published' ? 'success' : 'info'">
              {{ row.status === 'published' ? '已发布' : '草稿' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="editFlow(row)" :disabled="row.status === 'published'">
              {{ row.status === 'published' ? '已发布' : '编辑' }}
            </el-button>
            <el-button type="success" link @click="executeFlow(row)">
              执行
            </el-button>
            <el-dropdown @command="handleCommand($event, row)">
              <el-button type="primary" link>更多</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="copy">复制</el-dropdown-item>
                  <el-dropdown-item command="publish" v-if="row.status === 'draft'">
                    发布
                  </el-dropdown-item>
                  <el-dropdown-item command="unpublish" v-if="row.status === 'published'">
                    取消发布
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @size-change="loadFlows"
        @current-change="loadFlows"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getFlows, executeFlow as execFlow, copyFlow, publishFlow, unpublishFlow, deleteFlow } from '@/services/flow'
import dayjs from 'dayjs'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const flows = ref([])

const searchForm = reactive({
  keyword: '',
  status: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

function formatTime(time) {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-'
}

function editFlow(row) {
  router.push(`/flows/editor/${row.id}`)
}

function goToEditor() {
  console.log('goToEditor called')
  console.log('Current route:', route.path)
  console.log('Router:', router)
  console.log('Attempting to navigate to /flows/editor')
  
  router.push('/flows/editor').then(() => {
    console.log('Navigation successful, now at:', route.path)
  }).catch((err) => {
    console.error('Navigation failed:', err)
  })
}

async function executeFlow(row) {
  try {
    await ElMessageBox.confirm('确定要执行该流程吗？', '提示', { type: 'warning' })
    const res = await execFlow(row.id)
    ElMessage.success('流程已开始执行')
    router.push(`/executions/${res.execution_id}`)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('执行失败')
    }
  }
}

async function handleCommand(command, row) {
  switch (command) {
    case 'copy':
      await copyFlow(row.id)
      ElMessage.success('流程复制成功')
      loadFlows()
      break
    case 'publish':
      await publishFlow(row.id)
      ElMessage.success('流程发布成功')
      loadFlows()
      break
    case 'unpublish':
      await unpublishFlow(row.id)
      ElMessage.success('已取消发布')
      loadFlows()
      break
    case 'delete':
      handleDeleteFlow(row)
      break
  }
}

async function handleDeleteFlow(row) {
  try {
    await ElMessageBox.confirm('确定要删除该流程吗？', '提示', { type: 'warning' })
    await deleteFlow(row.id)
    ElMessage.success('删除成功')
    loadFlows()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function loadFlows() {
  loading.value = true
  try {
    const res = await getFlows({
      page: pagination.page,
      page_size: pagination.pageSize,
      ...searchForm
    })
    flows.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function resetSearch() {
  searchForm.keyword = ''
  searchForm.status = ''
  pagination.page = 1
  loadFlows()
}

onMounted(() => {
  loadFlows()
})
</script>
