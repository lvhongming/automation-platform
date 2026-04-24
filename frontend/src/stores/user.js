import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login, getCurrentUser, logout } from '@/services/auth'
import Cookies from 'js-cookie'

export const useUserStore = defineStore('user', () => {
  const token = ref(Cookies.get('token') || '')
  const userInfo = ref(null)
  const permissions = ref([])

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => {
    // 有 role_id 的用户都可以看到系统管理菜单
    return !!userInfo.value?.role_id
  })

  async function loginAction(username, password) {
    const res = await login(username, password)
    token.value = res.token
    userInfo.value = res.user
    permissions.value = res.permissions || []
    Cookies.set('token', res.token, { expires: 7 })
    return res
  }

  async function fetchUserInfo() {
    if (!token.value) return null
    try {
      const res = await getCurrentUser()
      // /me 返回的是用户对象，不是 {user: ...}
      userInfo.value = res
      permissions.value = res.permissions || []
      return res
    } catch (error) {
      // 401 错误由 API 拦截器统一处理，这里只清除本地数据
      if (error.response?.status !== 401) {
        console.error('获取用户信息失败', error)
      }
      throw error
    }
  }

  function logoutAction() {
    logout()
    token.value = ''
    userInfo.value = null
    permissions.value = []
    Cookies.remove('token')
  }

  function hasPermission(action, resource) {
    if (isAdmin.value) return true
    return permissions.value.some(
      p => p.resource === resource && p.actions.includes(action)
    )
  }

  return {
    token,
    userInfo,
    permissions,
    isAuthenticated,
    isAdmin,
    loginAction,
    fetchUserInfo,
    logoutAction,
    hasPermission
  }
})
