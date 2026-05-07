<template>
  <div class="project-detail">
    <!-- 项目头部 -->
    <div class="project-header">
      <div class="header-left">
        <a-button @click="goBack">
          <ArrowLeftOutlined /> 返回
        </a-button>
        <h2>{{ project?.name }}</h2>
        <a-tag :color="getTypeColor(project?.type || 'web')">
          {{ getTypeLabel(project?.type || 'web') }}
        </a-tag>
      </div>
      <div class="header-right">
        <a-space>
          <a-button @click="showEditModal">
            <EditOutlined /> 编辑项目
          </a-button>
          <a-button type="primary" @click="goToScripts">
            <PlusOutlined /> 新建脚本
          </a-button>
        </a-space>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="detail-content">
      <!-- 左侧导航 -->
      <div class="side-nav">
        <a-menu
          v-model:selectedKeys="selectedKeys"
          mode="inline"
          :open-keys="openKeys"
          @click="handleMenuClick"
        >
          <a-menu-item key="scripts">
            <template #icon><FileTextOutlined /></template>
            脚本管理
          </a-menu-item>
          <a-menu-item key="plans">
            <template #icon><ProfileOutlined /></template>
            计划管理
          </a-menu-item>
          <a-menu-item key="variables">
            <template #icon><DatabaseOutlined /></template>
            变量管理
          </a-menu-item>
          <a-menu-item key="members">
            <template #icon><TeamOutlined /></template>
            成员管理
          </a-menu-item>
        </a-menu>

        <!-- 项目信息 -->
        <div class="project-info">
          <h4>项目信息</h4>
          <a-descriptions size="small" :column="1" bordered>
            <a-descriptions-item label="描述">
              {{ project?.description || '暂无描述' }}
            </a-descriptions-item>
            <a-descriptions-item label="创建时间">
              {{ formatDate(project?.created_at) }}
            </a-descriptions-item>
            <a-descriptions-item label="脚本数量">
              {{ project?.script_count || 0 }} 个
            </a-descriptions-item>
          </a-descriptions>
        </div>
      </div>

      <!-- 右侧内容 -->
      <div class="main-content">
        <!-- 脚本管理 -->
        <div v-if="currentTab === 'scripts'" class="tab-content">
          <ScriptList :project-id="projectId" embed-mode />
        </div>

        <!-- 计划管理 -->
        <div v-else-if="currentTab === 'plans'" class="tab-content">
          <PlanList :project-id="projectId" embed-mode />
        </div>

        <!-- 变量管理 -->
        <div v-else-if="currentTab === 'variables'" class="tab-content">
          <ProjectVariables :project-id="projectId" />
        </div>

        <!-- 成员管理 -->
        <div v-else-if="currentTab === 'members'" class="tab-content">
          <ProjectMembers :project-id="projectId" />
        </div>
      </div>
    </div>

    <!-- 编辑项目对话框 -->
    <a-modal
      v-model:open="editModalVisible"
      title="编辑项目"
      width="500px"
      @ok="handleEditOk"
      @cancel="editModalVisible = false"
    >
      <a-form :model="editForm" layout="vertical">
        <a-form-item label="项目名称" required>
          <a-input v-model:value="editForm.name" placeholder="请输入项目名称" />
        </a-form-item>
        <a-form-item label="项目类型" required>
          <a-select v-model:value="editForm.type" placeholder="请选择项目类型">
            <a-select-option value="web">Web自动化</a-select-option>
            <a-select-option value="mobile">移动端自动化</a-select-option>
            <a-select-option value="api">API接口测试</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="项目描述">
          <a-textarea v-model:value="editForm.description" :rows="4" placeholder="请输入项目描述" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import {
  ArrowLeftOutlined,
  EditOutlined,
  PlusOutlined,
  FileTextOutlined,
  ProfileOutlined,
  DatabaseOutlined,
  TeamOutlined
} from '@ant-design/icons-vue'
import { getProjectDetail, updateProject } from '@/api/project'
import type { Project, ProjectForm } from '@/types/project'
import ScriptList from '@/components/project/ScriptList.vue'
import PlanList from '@/components/project/PlanList.vue'
import ProjectVariables from '@/components/project/ProjectVariables.vue'
import ProjectMembers from '@/components/project/ProjectMembers.vue'

const router = useRouter()
const route = useRoute()

const projectId = ref<number>(parseInt(route.params.id as string))
const project = ref<Project | null>(null)
const selectedKeys = ref<string[]>(['scripts'])
const openKeys = ref<string[]>([])
const currentTab = ref('scripts')

// 编辑表单
const editModalVisible = ref(false)
const editForm = ref<ProjectForm>({
  name: '',
  description: '',
  type: 'web'
})

// 监听路由参数变化
watch(
  () => route.params.id,
  (newId) => {
    if (newId) {
      projectId.value = parseInt(newId as string)
      loadProject()
    }
  },
  { immediate: true }
)

async function loadProject() {
  try {
    project.value = await getProjectDetail(projectId.value)
  } catch (error) {
    // 错误已由拦截器处理
  }
}

function goBack() {
  router.push('/projects')
}

function goToScripts() {
  router.push(`/script/edit?project_id=${projectId.value}&from=project`)
}

function showEditModal() {
  if (project.value) {
    editForm.value = {
      name: project.value.name,
      description: project.value.description,
      type: project.value.type
    }
    editModalVisible.value = true
  }
}

async function handleEditOk() {
  if (!editForm.value.name) {
    message.error('请输入项目名称')
    return
  }

  try {
    await updateProject(projectId.value, editForm.value)
    message.success('更新成功')
    editModalVisible.value = false
    loadProject()
  } catch (error) {
    // 错误已由拦截器处理
  }
}

function handleMenuClick({ key }: { key: string }) {
  currentTab.value = key
  selectedKeys.value = [key]
}

function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    web: 'Web自动化',
    mobile: '移动端',
    api: 'API测试'
  }
  return labels[type] || type
}

function getTypeColor(type: string): string {
  const colors: Record<string, string> = {
    web: 'blue',
    mobile: 'green',
    api: 'orange'
  }
  return colors[type] || 'default'
}

function formatDate(date?: string): string {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}
</script>

<style scoped>
.project-detail {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h2 {
  margin: 0;
  color: #E5E7EB;
}

.detail-content {
  display: flex;
  gap: 24px;
  flex: 1;
  overflow: hidden;
}

/* 左侧导航 */
.side-nav {
  width: 240px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.side-nav :deep(.ant-menu) {
  background: #FFFFFF;
  border-radius: 8px;
  border: 1px solid #E5E7EB;
}

.side-nav :deep(.ant-menu-item) {
  margin: 0 !important;
  height: 44px !important;
  line-height: 44px !important;
  color: #9CA3AF !important;
}

.side-nav :deep(.ant-menu-item .anticon) {
  color: #6B7280 !important;
}

.side-nav :deep(.ant-menu-item:hover) {
  color: #1890ff !important;
  background: rgba(24, 144, 255, 0.1) !important;
}

.side-nav :deep(.ant-menu-item-selected) {
  color: #1890ff !important;
  background: rgba(24, 144, 255, 0.15) !important;
}

.side-nav :deep(.ant-menu-item-selected .anticon) {
  color: #1890ff !important;
}

.project-info {
  background: #FFFFFF;
  border-radius: 8px;
  border: 1px solid #E5E7EB;
  padding: 16px;
}

.project-info h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #1F2937;
}

.project-info :deep(.ant-descriptions-item-label) {
  background: #F9FAFB;
  color: #374151;
}

.project-info :deep(.ant-descriptions-item-content) {
  color: #1F2937;
}

/* 右侧内容 */
.main-content {
  flex: 1;
  background: #FFFFFF;
  border-radius: 8px;
  border: 1px solid #E5E7EB;
  overflow: hidden;
}

.tab-content {
  height: 100%;
  overflow: auto;
}
</style>
