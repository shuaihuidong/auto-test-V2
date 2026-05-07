<template>
  <a-layout class="layout">
    <a-layout-header class="header">
      <div class="logo">
        <img src="/logo.svg" alt="Logo" />
        <span class="title">自动化测试管理平台</span>
      </div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        theme="light"
        mode="horizontal"
        :style="{ lineHeight: '64px', flex: 1 }"
      >
        <a-menu-item key="projects" @click="$router.push('/projects')">
          <template #icon><ProjectOutlined /></template>
          项目管理
        </a-menu-item>
        <a-menu-item key="scripts" @click="$router.push('/scripts')">
          <template #icon><FileTextOutlined /></template>
          脚本管理
        </a-menu-item>
        <a-menu-item key="plans" @click="$router.push('/plans')">
          <template #icon><ProfileOutlined /></template>
          计划管理
        </a-menu-item>
        <a-menu-item key="executions" @click="$router.push('/executions')">
          <template #icon><PlayCircleOutlined /></template>
          执行记录
        </a-menu-item>
        <a-menu-item key="batch-tasks" @click="$router.push('/batch-tasks')">
          <template #icon><ThunderboltOutlined /></template>
          AI 任务中心
        </a-menu-item>
        <a-menu-item key="account-role" @click="$router.push('/account-role')" v-if="isTesterOrAdmin">
          <template #icon><TeamOutlined /></template>
          账号角色管理
        </a-menu-item>
        <a-menu-item key="ai-settings" @click="$router.push('/ai-settings')" v-if="isAdmin">
          <template #icon><RobotOutlined /></template>
          AI 设置
        </a-menu-item>
        <a-menu-item key="help" @click="$router.push('/help')">
          <template #icon><QuestionCircleOutlined /></template>
          帮助中心
        </a-menu-item>
      </a-menu>
      <div class="user-info">
        <a-dropdown>
          <a class="user-dropdown" @click.prevent>
            <a-avatar :size="32" style="margin-right: 8px;">
              <template #icon><UserOutlined /></template>
            </a-avatar>
            {{ userStore.user?.username }}
            <DownOutlined />
          </a>
          <template #overlay>
            <a-menu>
              <a-menu-item @click="showChangePassword">
                <LockOutlined /> 修改密码
              </a-menu-item>
              <a-menu-divider />
              <a-menu-item @click="handleLogout">
                <LogoutOutlined /> 退出登录
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </div>
    </a-layout-header>

    <a-layout-content class="content">
      <router-view />
    </a-layout-content>

    <a-modal
      v-model:open="changePasswordVisible"
      title="修改密码"
      @ok="handleChangePassword"
    >
      <a-form :model="passwordForm" layout="vertical">
        <a-form-item label="原密码" required>
          <a-input-password v-model:value="passwordForm.oldPassword" />
        </a-form-item>
        <a-form-item label="新密码" required>
          <a-input-password v-model:value="passwordForm.newPassword" />
        </a-form-item>
        <a-form-item label="确认密码" required>
          <a-input-password v-model:value="passwordForm.confirmPassword" />
        </a-form-item>
      </a-form>
    </a-modal>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ProjectOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  ProfileOutlined,
  TeamOutlined,
  RobotOutlined,
  QuestionCircleOutlined,
  ThunderboltOutlined,
  UserOutlined,
  DownOutlined,
  LogoutOutlined,
  LockOutlined
} from '@ant-design/icons-vue'
import { useUserStore } from '@/store/user'
import { changePassword } from '@/api/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const selectedKeys = ref<string[]>([])
const changePasswordVisible = ref(false)
const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const isAdmin = computed(() => userStore.user?.role === 'admin' || userStore.user?.role === 'super_admin')
const isTesterOrAdmin = computed(() => {
  const role = userStore.user?.role || 'guest'
  // tester, admin, super_admin 都可以访问
  return ['tester', 'admin', 'super_admin'].includes(role)
})

// 监听路由变化，更新菜单选中状态
watch(
  () => route.path,
  (path) => {
    const key = path.split('/')[1] || 'projects'
    selectedKeys.value = [key]
  },
  { immediate: true }
)

function handleLogout() {
  userStore.logout()
  router.push('/login')
  message.success('退出登录成功')
}

function showChangePassword() {
  changePasswordVisible.value = true
}

async function handleChangePassword() {
  if (!passwordForm.value.oldPassword || !passwordForm.value.newPassword) {
    message.error('请填写完整信息')
    return
  }
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    message.error('两次输入的密码不一致')
    return
  }

  try {
    await changePassword(passwordForm.value.oldPassword, passwordForm.value.newPassword)
    message.success('密码修改成功')
    changePasswordVisible.value = false
    passwordForm.value = {
      oldPassword: '',
      newPassword: '',
      confirmPassword: ''
    }
  } catch (error) {
    // 错误已由拦截器处理
  }
}
</script>

<style scoped>
.layout {
  min-height: 100vh;
}

.header {
  display: flex;
  align-items: center;
  padding: 0 var(--spacing-xl, 24px);
  background: var(--color-bg-elevated, #1E2A5C);
  border-bottom: 1px solid var(--color-border, #1E2A5C);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.logo {
  display: flex;
  align-items: center;
  margin-right: 48px;
  color: var(--color-text-primary, #E5E7EB);
  cursor: pointer;
}

.logo img {
  width: 36px;
  height: 36px;
  margin-right: 12px;
}

.logo .title {
  font-size: var(--font-size-lg, 18px);
  font-weight: var(--font-weight-semibold, 600);
  color: var(--color-text-primary, #E5E7EB);
}

.user-info {
  margin-left: auto;
}

.user-dropdown {
  color: var(--color-text-primary, #E5E7EB);
  display: flex;
  align-items: center;
  transition: color 0.3s;
}

.user-dropdown:hover {
  color: var(--color-text-primary, #E5E7EB);
}

.content {
  padding: var(--spacing-xl, 24px);
  background: var(--color-bg-secondary, #121936);
  min-height: calc(100vh - 64px);
}

/* Menu Styles - Light theme on dark header */
:deep(.ant-menu-light) {
  background: transparent;
}

:deep(.ant-menu-item) {
  color: var(--color-text-secondary, #9CA3AF);
  font-weight: var(--font-weight-medium, 500);
  transition: all 0.3s;
  background: transparent !important;
}

:deep(.ant-menu-item .anticon) {
  font-size: 16px;
  color: var(--color-text-secondary, #9CA3AF);
  transition: color 0.3s;
}

:deep(.ant-menu-item .anticon svg) {
  fill: var(--color-text-secondary, #9CA3AF);
  transition: fill 0.3s;
}

:deep(.ant-menu-item:hover) {
  color: var(--color-text-primary, #E5E7EB);
  background: transparent !important;
}

:deep(.ant-menu-item:hover .anticon) {
  color: var(--color-text-primary, #E5E7EB);
}

:deep(.ant-menu-item:hover .anticon svg) {
  fill: var(--color-text-primary, #E5E7EB);
}

:deep(.ant-menu-item-selected) {
  color: var(--color-text-primary, #E5E7EB) !important;
  background: transparent !important;
}

:deep(.ant-menu-item-selected .anticon) {
  color: var(--color-text-primary, #E5E7EB);
}

:deep(.ant-menu-item-selected .anticon svg) {
  fill: var(--color-text-primary, #E5E7EB);
}

/* Avatar */
:deep(.ant-avatar) {
  background: var(--color-primary-light, rgba(255, 255, 255, 0.1));
  color: var(--color-text-primary, #E5E7EB);
  border: 1px solid var(--color-primary-light, rgba(255, 255, 255, 0.2));
}
</style>
