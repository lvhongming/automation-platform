<template>
  <el-container class="main-layout">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="sidebar">
      <div class="logo">
        <el-icon v-if="isCollapsed"><Box /></el-icon>
        <span v-else>流程运维自动化平台</span>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        :unique-opened="true"
        :router="true"
        class="sidebar-menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <template #title>控制台</template>
        </el-menu-item>

        <el-sub-menu index="flow">
          <template #title>
            <el-icon><Connection /></el-icon>
            <span>流程管理</span>
          </template>
          <el-menu-item index="/flows">
            流程列表
          </el-menu-item>
          <el-menu-item index="/flows/editor">
            新建流程
          </el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/hosts">
          <el-icon><Monitor /></el-icon>
          <template #title>主机管理</template>
        </el-menu-item>

        <el-menu-item index="/templates">
          <el-icon><DocumentCopy /></el-icon>
          <template #title>模板库</template>
        </el-menu-item>

        <el-menu-item index="/executions">
          <el-icon><List /></el-icon>
          <template #title>执行历史</template>
        </el-menu-item>

        <el-menu-item index="/scheduler">
          <el-icon><Clock /></el-icon>
          <template #title>定时任务</template>
        </el-menu-item>

        <el-sub-menu index="system" v-if="userStore.isAdmin">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item index="/users">
            用户管理
          </el-menu-item>
          <el-menu-item index="/settings">
            系统设置
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-left">
          <el-button
            :icon="isCollapsed ? 'Expand' : 'Fold'"
            text
            @click="isCollapsed = !isCollapsed"
          />
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
              {{ item.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">{{ userStore.userInfo?.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>个人中心
                </el-dropdown-item>
                <el-dropdown-item command="settings">
                  <el-icon><Setting /></el-icon>系统设置
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主内容区 -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import {
  Box, Odometer, Connection, Monitor, DocumentCopy,
  List, Clock, Setting, User, UserFilled, ArrowDown, SwitchButton
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const isCollapsed = ref(false)

const activeMenu = computed(() => route.path)
const breadcrumbs = computed(() => {
  return route.matched
    .filter(r => r.meta?.title)
    .map(r => ({ title: r.meta.title, path: r.path }))
})

async function handleCommand(command) {
  switch (command) {
    case 'logout':
      try {
        await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
          type: 'warning'
        })
        userStore.logoutAction()
        router.push('/login')
      } catch {
        // 取消
      }
      break
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      router.push('/settings')
      break
  }
}

onMounted(async () => {
  // 获取用户信息
  if (userStore.isAuthenticated && !userStore.userInfo) {
    try {
      await userStore.fetchUserInfo()
    } catch (error) {
      // 401 错误由 API 拦截器处理，这里不显示额外错误
      if (!error.response || error.response.status !== 401) {
        ElMessage.error('获取用户信息失败')
      }
    }
  }
})
</script>

<style lang="scss" scoped>
.main-layout {
  height: 100vh;
}

.sidebar {
  background: #304156;
  transition: width 0.3s;
  overflow-x: hidden;

  .logo {
    height: 60px;
    line-height: 60px;
    text-align: center;
    color: #fff;
    font-size: 18px;
    font-weight: bold;
    background: #2b3a4a;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;

    .el-icon {
      font-size: 24px;
    }
  }

  .sidebar-menu {
    border-right: none;
    background: transparent;

    :deep(.el-menu-item),
    :deep(.el-sub-menu__title) {
      color: #bfcbd9;

      &:hover {
        background: #263445;
      }
    }

    :deep(.el-menu-item.is-active) {
      background: #263445;
      color: #409eff;
    }
  }
}

.header {
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .header-right {
    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      padding: 8px;
      border-radius: 4px;

      &:hover {
        background: #f5f5f5;
      }

      .username {
        font-size: 14px;
        color: #333;
      }
    }
  }
}

.main-content {
  background: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}
</style>
