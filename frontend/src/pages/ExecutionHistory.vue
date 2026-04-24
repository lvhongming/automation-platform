<template>
  <div class="execution-history page-container">
    <el-card>
      <template #header>
        <span>执行历史</span>
      </template>

      <!-- 搜索栏 -->
      <el-form :inline="true" class="search-form">
        <el-form-item label="流程名称">
          <el-input v-model="searchForm.flow_id" placeholder="选择流程" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="选择状态" clearable>
            <el-option label="等待中" value="pending" />
            <el-option label="执行中" value="running" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
            <el-option label="已停止" value="stopped" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadExecutions">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 执行列表 -->
      <el-table :data="executions" v-loading="loading" stripe>
        <el-table-column prop="id" label="执行ID" width="180">
          <template #default="{ row }">
            <el-link type="primary" @click="viewDetail(row)">
              #{{ row.id.slice(0, 8) }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="flow_name" label="流程名称" min-width="150">
          <template #default="{ row }">
            {{ row.flow_name || row.flow_id?.slice(0, 8) || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="trigger_type" label="触发方式" width="100">
          <template #default="{ row }">
            {{ row.trigger_type === 'manual' ? '手动' : row.trigger_type === 'scheduled' ? '定时' : 'API' }}
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="耗时" width="100">
          <template #default="{ row }">
            {{ calculateDuration(row.started_at, row.finished_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewDetail(row)">详情</el-button>
            <el-button
              type="danger"
              link
              @click="stopExecution(row)"
              :disabled="row.status !== 'running' && row.status !== 'pending'"
            >
              停止
            </el-button>
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
        @size-change="loadExecutions"
        @current-change="loadExecutions"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getExecutions, stopExecution as stopExec } from '@/services/execution'
import dayjs from 'dayjs'

const router = useRouter()

const loading = ref(false)
const executions = ref([])
const dateRange = ref([])

const searchForm = reactive({
  flow_id: '',
  status: '',
  start_date: '',
  end_date: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

function getStatusType(status) {
  const map = {
    pending: 'info',
    running: 'warning',
    success: 'success',
    failed: 'danger',
    stopped: 'warning'
  }
  return map[status] || 'info'
}

function getStatusText(status) {
  const map = {
    pending: '等待中',
    running: '执行中',
    success: '成功',
    failed: '失败',
    stopped: '已停止'
  }
  return map[status] || status
}

function formatTime(time) {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

function calculateDuration(start, end) {
  if (!start || !end) return '-'
  const diff = dayjs(end).diff(dayjs(start), 'second')
  if (diff < 60) return `${diff}s`
  const minutes = Math.floor(diff / 60)
  const seconds = diff % 60
  return `${minutes}m ${seconds}s`
}

function viewDetail(row) {
  router.push(`/executions/${row.id}`)
}

async function stopExecution(row) {
  try {
    await stopExec(row.id)
    ElMessage.success('已发送停止指令')
    loadExecutions()
  } catch (error) {
    ElMessage.error('停止失败')
  }
}

async function loadExecutions() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      ...searchForm
    }
    if (dateRange.value?.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }

    const res = await getExecutions(params)
    executions.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function resetSearch() {
  searchForm.flow_id = ''
  searchForm.status = ''
  dateRange.value = []
  pagination.page = 1
  loadExecutions()
}

onMounted(() => {
  loadExecutions()
})
</script>

<style lang="scss" scoped>
.execution-history {
  .search-form {
    margin-bottom: 16px;
  }

  .pagination {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }
}
</style>
