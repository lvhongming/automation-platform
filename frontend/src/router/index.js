import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/components/Layout/MainLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/pages/Dashboard.vue'),
        meta: { title: '控制台' }
      },
      {
        path: 'flows',
        name: 'FlowList',
        component: () => import('@/pages/FlowList.vue'),
        meta: { title: '流程管理' }
      },
      {
        path: 'flows/editor/:id?',
        name: 'FlowEditor',
        component: () => import('@/pages/FlowEditor.vue'),
        meta: { title: '流程编辑器' }
      },
      {
        path: 'hosts',
        name: 'HostList',
        component: () => import('@/pages/HostList.vue'),
        meta: { title: '主机管理' }
      },
      {
        path: 'templates',
        name: 'TemplateList',
        component: () => import('@/pages/TemplateList.vue'),
        meta: { title: '模板库' }
      },
      {
        path: 'executions',
        name: 'ExecutionHistory',
        component: () => import('@/pages/ExecutionHistory.vue'),
        meta: { title: '执行历史' }
      },
      {
        path: 'executions/:id',
        name: 'ExecutionDetail',
        component: () => import('@/pages/ExecutionDetail.vue'),
        meta: { title: '执行详情' }
      },
      {
        path: 'scheduler',
        name: 'Scheduler',
        component: () => import('@/pages/Scheduler.vue'),
        meta: { title: '定时任务' }
      },
      {
        path: 'users',
        name: 'UserList',
        component: () => import('@/pages/UserList.vue'),
        meta: { title: '用户管理', roles: ['admin'] }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/pages/Settings.vue'),
        meta: { title: '系统设置' }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/pages/Profile.vue'),
        meta: { title: '个人中心' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/pages/NotFound.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  console.log('Router guard:', to.path, 'isAuthenticated:', userStore.isAuthenticated)

  if (to.meta.requiresAuth !== false && !userStore.isAuthenticated) {
    console.log('Not authenticated, redirecting to login')
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }

  // 检查角色权限 - 只要有 role_id 就可以访问
  if (to.meta.roles && to.meta.roles.length > 0) {
    if (!userStore.userInfo?.role_id) {
      console.log('No role_id, redirecting to dashboard')
      next({ name: 'Dashboard' })
      return
    }
  }

  console.log('Route allowed:', to.path)
  next()
})

export default router
