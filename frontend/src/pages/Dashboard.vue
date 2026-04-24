<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <!-- 统计卡片 -->
      <el-col :xs="12" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #409eff">
            <el-icon><Connection /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.flows }}</div>
            <div class="stat-label">流程总数</div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="12" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #67c23a">
            <el-icon><VideoPlay /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.executions }}</div>
            <div class="stat-label">今日执行</div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="12" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #e6a23c">
            <el-icon><Monitor /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.hosts }}</div>
            <div class="stat-label">主机总数</div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="12" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #f56c6c">
            <el-icon><Failed /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.failed }}</div>
            <div class="stat-label">失败执行(7天)</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近执行 -->
    <el-card class="recent-executions">
      <template #header>
        <div class="card-header">
          <span>最近执行</span>
          <el-button type="primary" link @click="$router.push('/executions')">
            查看全部
          </el-button>
        </div>
      </template>

      <el-table :data="recentExecutions" stripe v-loading="loading">
        <el-table-column prop="id" label="执行ID" width="180">
          <template #default="{ row }">
            <el-link type="primary" @click="$router.push(`/executions/${row.id}`)">
              #{{ row.id.slice(0, 8) }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="flow_name" label="流程名称">
          <template #default="{ row }">
            {{ row.flow_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="trigger_type" label="触发方式" width="100">
          <template #default="{ row }">
            {{ getTriggerType(row.trigger_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button type="primary" link @click="$router.push(`/executions/${row.id}`)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && recentExecutions.length === 0" description="暂无执行记录" />
    </el-card>

    <!-- 快捷入口 -->
    <el-row :gutter="20" class="quick-actions">
      <el-col :xs="12" :sm="8">
        <el-card shadow="hover" class="quick-card" @click="$router.push('/flows/editor')">
          <el-icon class="quick-icon"><Plus /></el-icon>
          <span>新建流程</span>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="8">
        <el-card shadow="hover" class="quick-card" @click="$router.push('/hosts')">
          <el-icon class="quick-icon"><Monitor /></el-icon>
          <span>管理主机</span>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="8">
        <el-card shadow="hover" class="quick-card" @click="$router.push('/templates')">
          <el-icon class="quick-icon"><DocumentCopy /></el-icon>
          <span>模板库</span>
        </el-card>
      </el-col>
    </el-row>

    <!-- 运行中的执行 -->
    <el-card class="running-executions" v-if="runningExecutions.length > 0">
      <template #header>
        <div class="card-header">
          <span>
            <el-badge is-dot type="warning" /> 运行中的执行
          </span>
          <el-button type="primary" link @click="$router.push('/executions?status=running')">
            查看全部
          </el-button>
        </div>
      </template>

      <el-table :data="runningExecutions" size="small">
        <el-table-column prop="id" label="执行ID" width="180">
          <template #default="{ row }">
            <el-link type="primary" @click="$router.push(`/executions/${row.id}`)">
              #{{ row.id.slice(0, 8) }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="flow_name" label="流程名称">
          <template #default="{ row }">
            {{ row.flow_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag type="warning">执行中</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button type="primary" link @click="$router.push(`/executions/${row.id}`)">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, VideoPlay, Monitor, Failed, Plus, DocumentCopy } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import api from '@/services/api'

const stats = ref({
  flows: 0,
  executions: 0,
  hosts: 0,
  failed: 0
})

const recentExecutions = ref([])
const runningExecutions = ref([])
const loading = ref(false)

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

function getTriggerType(type) {
  const map = {
    manual: '手动',
    scheduled: '定时',
    api: 'API'
  }
  return map[type] || '-'
}

function formatTime(time) {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

async function loadStats() {
  try {
    const res = await api.get('/dashboard/stats')
    stats.value = res
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
}

async function loadRecentExecutions() {
  loading.value = true
  try {
    const res = await api.get('/dashboard/recent-executions')
    recentExecutions.value = res.items || []
  } catch (error) {
    console.error('Failed to load recent executions:', error)
    ElMessage.error('加载执行记录失败')
  } finally {
    loading.value = false
  }
}

async function loadRunningExecutions() {
  try {
    const res = await api.get('/executions', {
      params: { status: 'running', page_size: 5 }
    })
    runningExecutions.value = res.items || []
  } catch (error) {
    console.error('Failed to load running executions:', error)
  }
}

onMounted(() => {
  loadStats()
  loadRecentExecutions()
  loadRunningExecutions()

  // 每10秒刷新运行中的执行
  setInterval(loadRunningExecutions, 10000)
})
</script>

<style lang="scss" scoped>
.dashboard {
  padding: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
  margin-bottom: 20px;

  .stat-icon {
    width: 60px;
    height: 60px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 20px;

    .el-icon {
      font-size: 28px;
      color: #fff;
    }
  }

  .stat-content {
    .stat-value {
      font-size: 28px;
      font-weight: bold;
      color: #333;
    }

    .stat-label {
      color: #999;
      font-size: 14px;
      margin-top: 4px;
    }
  }
}

.recent-executions {
  margin-bottom: 20px;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}

.running-executions {
  margin-bottom: 20px;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    :deep(.el-badge) {
      margin-right: 8px;
    }
  }
}

.quick-actions {
  margin-bottom: 20px;
}

.quick-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px;
  cursor: pointer;
  transition: all 0.3s;

  &:hover {
    transform: translateY(-5px);
  }

  .quick-icon {
    font-size: 48px;
    color: #409eff;
    margin-bottom: 16px;
  }

  span {
    font-size: 16px;
    color: #333;
  }
}
</style>
