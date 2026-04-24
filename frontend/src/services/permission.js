/**
 * 权限检查指令和工具
 */
import { useUserStore } from '@/stores/user'

/**
 * 检查用户是否有指定权限
 */
export function hasPermission(resource, action) {
  const userStore = useUserStore()

  if (userStore.isAdmin) return true

  return userStore.permissions.some(
    p => p.resource === resource && p.actions.includes(action)
  )
}

/**
 * 权限检查指令
 * 用法: v-permission="'flow:execute'"
 */
export const permissionDirective = {
  mounted(el, binding) {
    const [resource, action] = binding.value.split(':')

    if (!hasPermission(resource, action)) {
      el.style.display = 'none'
    }
  }
}

/**
 * 角色检查
 */
export function hasRole(roles) {
  const userStore = useUserStore()

  if (typeof roles === 'string') {
    roles = [roles]
  }

  return roles.includes(userStore.userInfo?.role)
}

export default {
  hasPermission,
  hasRole,
  permissionDirective
}
