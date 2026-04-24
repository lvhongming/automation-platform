<template>
  <div class="settings page-container">
    <el-card>
      <template #header>
        <span>系统设置</span>
      </template>

      <el-tabs v-model="activeTab">
        <!-- 基本设置 -->
        <el-tab-pane label="基本设置" name="basic">
          <el-form :model="basicSettings" label-width="120px" class="settings-form">
            <el-form-item label="系统名称">
              <el-input v-model="basicSettings.system_name" />
            </el-form-item>
            <el-form-item label="系统描述">
              <el-input v-model="basicSettings.description" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item label="时区">
              <el-select v-model="basicSettings.timezone">
                <el-option label="Asia/Shanghai (UTC+8)" value="Asia/Shanghai" />
                <el-option label="UTC" value="UTC" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveBasicSettings">保存</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 通知设置 -->
        <el-tab-pane label="通知设置" name="notification">
          <el-form :model="notificationSettings" label-width="120px" class="settings-form">
            <el-divider content-position="left">邮件通知</el-divider>
            <el-form-item label="启用邮件">
              <el-switch v-model="notificationSettings.email.enabled" />
            </el-form-item>
            <el-form-item label="SMTP 服务器" v-if="notificationSettings.email.enabled">
              <el-input v-model="notificationSettings.email.smtp_host" placeholder="smtp.example.com" />
            </el-form-item>
            <el-form-item label="端口" v-if="notificationSettings.email.enabled">
              <el-input-number v-model="notificationSettings.email.smtp_port" :min="1" :max="65535" />
            </el-form-item>
            <el-form-item label="用户名" v-if="notificationSettings.email.enabled">
              <el-input v-model="notificationSettings.email.username" placeholder="your-email@example.com" />
            </el-form-item>
            <el-form-item label="密码" v-if="notificationSettings.email.enabled">
              <el-input v-model="notificationSettings.email.password" type="password" show-password placeholder="SMTP 密码或授权码" />
            </el-form-item>
            <el-form-item label="发件人" v-if="notificationSettings.email.enabled">
              <el-input v-model="notificationSettings.email.from_email" placeholder="noreply@example.com" />
            </el-form-item>
            <el-form-item label="使用 TLS" v-if="notificationSettings.email.enabled">
              <el-switch v-model="notificationSettings.email.use_tls" />
            </el-form-item>

            <el-divider content-position="left">企业微信</el-divider>
            <el-form-item label="启用企业微信">
              <el-switch v-model="notificationSettings.wecom.enabled" />
            </el-form-item>
            <el-form-item label="WebHook URL" v-if="notificationSettings.wecom.enabled">
              <el-input v-model="notificationSettings.wecom.webhook_url" />
            </el-form-item>

            <el-divider content-position="left">钉钉</el-divider>
            <el-form-item label="启用钉钉">
              <el-switch v-model="notificationSettings.dingtalk.enabled" />
            </el-form-item>
            <el-form-item label="WebHook URL" v-if="notificationSettings.dingtalk.enabled">
              <el-input v-model="notificationSettings.dingtalk.webhook_url" />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="saveNotificationSettings">保存</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 执行设置 -->
        <el-tab-pane label="执行设置" name="execution">
          <el-form :model="executionSettings" label-width="120px" class="settings-form">
            <el-form-item label="默认超时时间">
              <el-input-number v-model="executionSettings.default_timeout" :min="10" :max="3600" />
              <span class="unit">秒</span>
            </el-form-item>
            <el-form-item label="最大并发数">
              <el-input-number v-model="executionSettings.max_concurrency" :min="1" :max="100" />
            </el-form-item>
            <el-form-item label="日志保留天数">
              <el-input-number v-model="executionSettings.log_retention_days" :min="1" :max="365" />
              <span class="unit">天</span>
            </el-form-item>
            <el-form-item label="失败重试次数">
              <el-input-number v-model="executionSettings.retry_count" :min="0" :max="5" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveExecutionSettings">保存</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettings, updateSettings } from '@/services/settings'

const activeTab = ref('basic')
const loading = ref(false)

const basicSettings = reactive({
  system_name: 'Ansible 自动化流程平台',
  description: '',
  timezone: 'Asia/Shanghai'
})

const notificationSettings = reactive({
  email: {
    enabled: false,
    smtp_host: '',
    smtp_port: 465,
    username: '',
    password: '',
    from_email: '',
    use_tls: true
  },
  wecom: {
    enabled: false,
    webhook_url: ''
  },
  dingtalk: {
    enabled: false,
    webhook_url: ''
  }
})

const executionSettings = reactive({
  default_timeout: 300,
  max_concurrency: 10,
  log_retention_days: 30,
  retry_count: 0
})

// 加载设置
async function loadSettings() {
  try {
    loading.value = true
    const data = await getSettings()
    
    // 基本设置
    if (data.basic) {
      basicSettings.system_name = data.basic.system_name
      basicSettings.description = data.basic.description
      basicSettings.timezone = data.basic.timezone
    }
    
    // 邮件设置
    if (data.email) {
      notificationSettings.email.enabled = data.email.enabled
      notificationSettings.email.smtp_host = data.email.smtp_host
      notificationSettings.email.smtp_port = data.email.smtp_port
      notificationSettings.email.username = data.email.username
      notificationSettings.email.password = data.email.password
      notificationSettings.email.from_email = data.email.from_email
      notificationSettings.email.use_tls = data.email.use_tls
    }
    
    // 企业微信
    if (data.wecom) {
      notificationSettings.wecom.enabled = data.wecom.enabled
      notificationSettings.wecom.webhook_url = data.wecom.webhook_url
    }
    
    // 钉钉
    if (data.dingtalk) {
      notificationSettings.dingtalk.enabled = data.dingtalk.enabled
      notificationSettings.dingtalk.webhook_url = data.dingtalk.webhook_url
    }
    
    // 执行设置
    if (data.execution) {
      executionSettings.default_timeout = data.execution.default_timeout
      executionSettings.max_concurrency = data.execution.max_concurrency
      executionSettings.log_retention_days = data.execution.log_retention_days
      executionSettings.retry_count = data.execution.retry_count
    }
  } catch (error) {
    console.error('加载设置失败:', error)
    ElMessage.error('加载设置失败')
  } finally {
    loading.value = false
  }
}

async function saveBasicSettings() {
  try {
    await updateSettings({ basic: basicSettings })
    ElMessage.success('保存成功')
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  }
}

async function saveNotificationSettings() {
  try {
    await updateSettings({
      email: notificationSettings.email,
      wecom: notificationSettings.wecom,
      dingtalk: notificationSettings.dingtalk
    })
    ElMessage.success('保存成功')
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  }
}

async function saveExecutionSettings() {
  try {
    await updateSettings({ execution: executionSettings })
    ElMessage.success('保存成功')
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style lang="scss" scoped>
.settings {
  .settings-form {
    max-width: 600px;

    .unit {
      margin-left: 10px;
      color: #999;
    }
  }
}
</style>
