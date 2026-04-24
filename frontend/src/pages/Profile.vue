<template>
  <div class="profile-container">
    <el-card>
      <template #header>
        <span>个人中心</span>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        v-loading="loading"
      >
        <el-form-item label="用户名">
          <el-input v-model="form.username" disabled />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>

        <el-form-item label="姓名" prop="full_name">
          <el-input v-model="form.full_name" placeholder="请输入姓名" />
        </el-form-item>

        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入手机号" />
        </el-form-item>

        <el-form-item label="部门" prop="department">
          <el-input v-model="form.department" placeholder="请输入部门" />
        </el-form-item>

        <el-form-item label="创建时间">
          <el-input :model-value="formatTime(userInfo?.created_at)" disabled />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleUpdate" :loading="submitting">
            保存修改
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="mt-20">
      <template #header>
        <span>修改密码</span>
      </template>

      <el-form
        ref="pwdFormRef"
        :model="pwdForm"
        :rules="pwdRules"
        label-width="100px"
      >
        <el-form-item label="新密码" prop="password">
          <el-input
            v-model="pwdForm.password"
            type="password"
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="pwdForm.confirm_password"
            type="password"
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button type="warning" @click="handleChangePassword" :loading="pwdSubmitting">
            修改密码
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'
import { getCurrentUser, updateUser } from '@/services/auth'

const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const pwdSubmitting = ref(false)
const formRef = ref()
const pwdFormRef = ref()

const form = reactive({
  email: '',
  full_name: '',
  phone: '',
  department: ''
})

const rules = {
  email: [
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ]
}

const pwdForm = reactive({
  password: '',
  confirm_password: ''
})

const pwdRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== pwdForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

function formatTime(time) {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-'
}

async function loadUserInfo() {
  loading.value = true
  try {
    const res = await getCurrentUser()
    userStore.userInfo = res
    Object.assign(form, {
      email: res.email || '',
      full_name: res.full_name || '',
      phone: res.phone || '',
      department: res.department || ''
    })
  } catch (error) {
    console.error('Failed to load user info:', error)
  } finally {
    loading.value = false
  }
}

async function handleUpdate() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await updateUser(form)
    ElMessage.success('更新成功')
    await userStore.fetchUserInfo()
  } catch (error) {
    ElMessage.error(error.message || '更新失败')
  } finally {
    submitting.value = false
  }
}

async function handleChangePassword() {
  const valid = await pwdFormRef.value.validate().catch(() => false)
  if (!valid) return

  pwdSubmitting.value = true
  try {
    await updateUser({ password: pwdForm.password })
    ElMessage.success('密码修改成功')
    pwdForm.password = ''
    pwdForm.confirm_password = ''
    pwdFormRef.value.resetFields()
  } catch (error) {
    ElMessage.error(error.message || '密码修改失败')
  } finally {
    pwdSubmitting.value = false
  }
}

onMounted(() => {
  loadUserInfo()
})
</script>

<style lang="scss" scoped>
.profile-container {
  max-width: 600px;

  .mt-20 {
    margin-top: 20px;
  }
}
</style>
