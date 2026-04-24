<template>
  <div class="scheduler page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>定时任务</span>
          <el-button type="primary" @click="openAddDialog">
            <el-icon><Plus /></el-icon> 新建定时任务
          </el-button>
        </div>
      </template>

      <el-table :data="scheduledJobs" stripe v-loading="loading">
        <el-table-column prop="name" label="任务名称" min-width="150" />
        <el-table-column label="关联流程" min-width="150">
          <template #default="{ row }">
            {{ row.flow_name }}
          </template>
        </el-table-column>
        <el-table-column prop="cron_expression" label="执行周期" width="150">
          <template #default="{ row }">
            <el-tag type="info">{{ formatCron(row.cron_expression) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="next_run_time" label="下次执行" width="180">
          <template #default="{ row }">
            {{ formatTime(row.next_run_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="last_run_time" label="上次执行" width="180">
          <template #default="{ row }">
            {{ formatTime(row.last_run_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              :model-value="row.enabled"
              @change="toggleJob(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="editJob(row)">编辑</el-button>
            <el-button type="warning" link @click="triggerJob(row)">立即执行</el-button>
            <el-button type="danger" link @click="deleteJob(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > 0"
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadJobs"
        @current-change="loadJobs"
        style="margin-top: 20px"
      />
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="showDialog"
      :title="editingJob ? '编辑定时任务' : '新建定时任务'"
      width="500px"
    >
      <el-form :model="jobForm" :rules="jobRules" ref="formRef" label-width="100px">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="jobForm.name" placeholder="每日备份" />
        </el-form-item>
        <el-form-item label="关联流程" prop="flow_id">
          <el-select v-model="jobForm.flow_id" placeholder="选择流程" filterable>
            <el-option
              v-for="flow in flows"
              :key="flow.id"
              :label="flow.name"
              :value="flow.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="执行周期" prop="cron_expression">
          <el-input v-model="jobForm.cron_expression" placeholder="0 2 * * *">
            <template #append>
              <el-tooltip content="格式: 分 时 日 月 周">
                <el-icon><QuestionFilled /></el-icon>
              </el-tooltip>
            </template>
          </el-input>
          <div class="cron-helper">
            <el-link @click="setCron('0 2 * * *')" type="primary">每天 2:00</el-link>
            <el-link @click="setCron('0 9 * * 1')" type="primary">每周一 9:00</el-link>
            <el-link @click="setCron('0 0 1 * *')" type="primary">每月 1 日</el-link>
            <el-link @click="setCron('*/5 * * * *')" type="primary">每 5 分钟</el-link>
          </div>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="jobForm.description" type="textarea" rows="2" placeholder="任务描述（可选）" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, QuestionFilled } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import api from '@/services/api'
import {
  getScheduledJobs,
  createScheduledJob,
  updateScheduledJob,
  deleteScheduledJob,
  toggleScheduledJob,
  triggerScheduledJob
} from '@/services/scheduler'

const loading = ref(false)
const submitting = ref(false)
const showDialog = ref(false)
const editingJob = ref(null)
const scheduledJobs = ref([])
const flows = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const formRef = ref()

const jobForm = reactive({
  name: '',
  flow_id: '',
  cron_expression: '',
  description: ''
})

const jobRules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  flow_id: [{ required: true, message: '请选择关联流程', trigger: 'change' }],
  cron_expression: [{ required: true, message: '请输入执行周期', trigger: 'blur' }]
}

function formatTime(time) {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-'
}

function formatCron(cron) {
  if (!cron) return '-'
  const parts = cron.split(' ')
  if (parts.length === 5) {
    const [minute, hour, day, month, week] = parts
    if (day === '*' && month === '*' && week === '*') {
      return `每天 ${hour}:${minute.padStart(2, '0')}`
    }
    if (week !== '*') {
      const weekNames = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
      return `每周${weekNames[parseInt(week)]} ${hour}:${minute.padStart(2, '0')}`
    }
    if (day !== '*') {
      return `每月 ${day} 日 ${hour}:${minute.padStart(2, '0')}`
    }
  }
  return cron
}

function setCron(cron) {
  jobForm.cron_expression = cron
}

function openAddDialog() {
  editingJob.value = null
  Object.assign(jobForm, {
    name: '',
    flow_id: '',
    cron_expression: '',
    description: ''
  })
  showDialog.value = true
}

function editJob(job) {
  editingJob.value = job
  Object.assign(jobForm, {
    name: job.name,
    flow_id: job.flow_id,
    cron_expression: job.cron_expression,
    description: job.description || ''
  })
  showDialog.value = true
}

async function submitForm() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (editingJob.value) {
      await updateScheduledJob(editingJob.value.id, jobForm)
      ElMessage.success('更新成功')
    } else {
      await createScheduledJob(jobForm)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadJobs()
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function deleteJob(job) {
  try {
    await ElMessageBox.confirm('确定要删除该定时任务吗？', '提示', { type: 'warning' })
    await deleteScheduledJob(job.id)
    ElMessage.success('删除成功')
    loadJobs()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

async function toggleJob(job) {
  try {
    await toggleScheduledJob(job.id, !job.enabled)
    ElMessage.success(job.enabled ? '已暂停' : '已启用')
    loadJobs()
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
    // 恢复原状态
    job.enabled = !job.enabled
  }
}

async function triggerJob(job) {
  try {
    await ElMessageBox.confirm(`确定要立即执行「${job.name}」吗？`, '提示', { type: 'warning' })
    const res = await triggerScheduledJob(job.id)
    ElMessage.success(`已触发执行，ID: ${res.execution_id.slice(0, 8)}`)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '触发失败')
    }
  }
}

async function loadFlows() {
  try {
    const res = await api.get('/flows', { params: { page_size: 100 } })
    flows.value = res.items || []
  } catch (error) {
    console.error('Failed to load flows:', error)
  }
}

async function loadJobs() {
  loading.value = true
  try {
    const res = await getScheduledJobs({
      page: page.value,
      page_size: pageSize.value
    })
    scheduledJobs.value = res.items || []
    total.value = res.total || 0
  } catch (error) {
    console.error('Failed to load jobs:', error)
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadJobs()
  loadFlows()
})
</script>

<style lang="scss" scoped>
.scheduler {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .cron-helper {
    margin-top: 8px;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }
}
</style>
