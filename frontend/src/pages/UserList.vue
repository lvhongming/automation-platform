<template>
  <div class="user-list page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" @click="openAddDialog">
            <el-icon><Plus /></el-icon> 添加用户
          </el-button>
        </div>
      </template>

      <el-table :data="users" stripe>
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="full_name" label="姓名" width="120" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="department" label="部门" width="120" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag>{{ getRoleName(row.role_id) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最后登录" width="180">
          <template #default="{ row }">
            {{ formatTime(row.last_login_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="editUser(row)">编辑</el-button>
            <el-button type="danger" link @click="deleteUser(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="editingUser ? '编辑用户' : '添加用户'"
      width="500px"
    >
      <el-form :model="userForm" :rules="userRules" ref="formRef" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" :disabled="!!editingUser" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="userForm.email" />
        </el-form-item>
        <el-form-item label="密码" prop="password" v-if="!editingUser">
          <el-input v-model="userForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="姓名" prop="full_name">
          <el-input v-model="userForm.full_name" />
        </el-form-item>
        <el-form-item label="部门" prop="department">
          <el-input v-model="userForm.department" />
        </el-form-item>
        <el-form-item label="角色" prop="role_id">
          <el-select v-model="userForm.role_id" placeholder="选择角色">
            <el-option
              v-for="role in roles"
              :key="role.id"
              :label="role.name"
              :value="role.id"
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import {
  getUsers,
  getRoles,
  createUser,
  updateUser,
  deleteUser as removeUser
} from '@/services/users'

const loading = ref(false)
const showAddDialog = ref(false)
const editingUser = ref(null)
const users = ref([])
const roles = ref([])
const formRef = ref()

const userForm = reactive({
  username: '',
  email: '',
  password: '',
  full_name: '',
  phone: '',
  department: '',
  role_id: ''
})

const userRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  role_id: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

function getRoleName(roleId) {
  const role = roles.value.find(r => r.id === roleId)
  return role?.name || '-'
}

function formatTime(time) {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-'
}

function openAddDialog() {
  editingUser.value = null
  resetForm()
  showAddDialog.value = true
}

function resetForm() {
  Object.assign(userForm, {
    username: '',
    email: '',
    password: '',
    full_name: '',
    phone: '',
    department: '',
    role_id: ''
  })
}

function editUser(user) {
  editingUser.value = user
  Object.assign(userForm, {
    username: user.username,
    email: user.email,
    password: '',
    full_name: user.full_name || '',
    phone: user.phone || '',
    department: user.department || '',
    role_id: user.role_id
  })
  showAddDialog.value = true
}

async function submitForm() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  try {
    if (editingUser.value) {
      await updateUser(editingUser.value.id, userForm)
      ElMessage.success('更新成功')
    } else {
      await createUser(userForm)
      ElMessage.success('添加成功')
    }
    showAddDialog.value = false
    editingUser.value = null
    resetForm()
    loadUsers()
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  }
}

async function deleteUser(user) {
  try {
    await ElMessageBox.confirm('确定要删除该用户吗？', '提示', { type: 'warning' })
    await removeUser(user.id)
    ElMessage.success('删除成功')
    loadUsers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

async function loadUsers() {
  loading.value = true
  try {
    const [usersRes, rolesRes] = await Promise.all([
      getUsers({ page_size: 100 }),
      getRoles({ page_size: 100 })
    ])
    users.value = usersRes.items || []
    roles.value = rolesRes.items || []
  } catch (error) {
    console.error('Failed to load users:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style lang="scss" scoped>
.user-list {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
