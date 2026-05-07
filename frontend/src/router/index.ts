import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import Layout from '@/layout/Index.vue'
import { useUserStore } from '@/store/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: Layout,
    redirect: '/projects',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'projects',
        name: 'Projects',
        component: () => import('@/views/ProjectList.vue'),
        meta: { title: '项目管理' }
      },
      {
        path: 'projects/:id',
        name: 'ProjectDetail',
        component: () => import('@/views/ProjectDetail.vue'),
        meta: { title: '项目详情' }
      },
      {
        path: 'scripts/:projectId',
        name: 'ProjectScripts',
        component: () => import('@/views/ScriptList.vue'),
        meta: { title: '脚本管理' }
      },
      {
        path: 'scripts',
        name: 'Scripts',
        component: () => import('@/views/AllScripts.vue'),
        meta: { title: '所有脚本' }
      },
      {
        path: 'script/edit/:id?',
        name: 'ScriptEdit',
        component: () => import('@/views/ScriptEdit.vue'),
        meta: { title: '脚本编辑' }
      },
      {
        path: 'plans',
        name: 'Plans',
        component: () => import('@/views/PlanManage.vue'),
        meta: { title: '计划管理' }
      },
      {
        path: 'executions',
        name: 'Executions',
        component: () => import('@/views/ExecutionList.vue'),
        meta: { title: '执行记录' }
      },
      {
        path: 'batch-tasks',
        name: 'BatchTasks',
        component: () => import('@/views/BatchTaskCenter.vue'),
        meta: { title: 'AI 任务中心' }
      },
      {
        path: 'batch-tasks/:id',
        name: 'BatchTaskDetail',
        component: () => import('@/views/BatchTaskDetail.vue'),
        meta: { title: '任务详情' }
      },
      {
        path: 'reports/:executionId',
        name: 'ReportView',
        component: () => import('@/views/ReportView.vue'),
        meta: { title: '测试报告' }
      },
      {
        path: 'account-role',
        name: 'AccountRole',
        component: () => import('@/views/AccountRoleManage.vue'),
        meta: { title: '账号角色管理', requiresAuth: true }
      },
      {
        path: 'ai-settings',
        name: 'AISettings',
        component: () => import('@/views/AISettings.vue'),
        meta: { title: 'AI 设置', requiresAuth: true, requiresAdmin: true }
      },
      {
        path: 'help',
        name: 'Help',
        component: () => import('@/views/HelpCenter.vue'),
        meta: { title: '帮助中心' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  const userStore = useUserStore()

  // 需要登录且未登录
  if (to.meta.requiresAuth !== false && !userStore.isLoggedIn) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }

  // 需要管理员权限且不是管理员/超级管理员
  if (to.meta.requiresAdmin && userStore.user?.role && userStore.user.role !== 'admin' && userStore.user.role !== 'super_admin') {
    next({ name: 'Projects' })
    return
  }

  next()
})

export default router
