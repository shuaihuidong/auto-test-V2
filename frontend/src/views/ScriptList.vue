<template>
  <div class="script-list">
    <div class="page-header">
      <a-space>
        <a-button @click="goBack">
          <ArrowLeftOutlined /> 返回
        </a-button>
        <h2>{{ projectName }} - 脚本列表</h2>
      </a-space>
      <a-space>
        <a-button @click="openNL2Script">
          <ThunderboltOutlined /> AI 生成
        </a-button>
        <a-button @click="openBatchNL2Script">
          <ThunderboltOutlined /> 批量生成
        </a-button>
        <a-button type="primary" @click="goToCreateScript">
          <PlusOutlined /> 新建脚本
        </a-button>
      </a-space>
    </div>

    <a-card>
      <a-table
        :columns="columns"
        :data-source="scripts"
        :loading="loading"
        :pagination="{ pageSize: 20 }"
        row-key="id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <a-tooltip placement="top" :title="record.name">
              <a class="script-name-link" @click="goToEditScript(record.id)">{{ record.name }}</a>
            </a-tooltip>
          </template>
          <template v-else-if="column.key === 'type'">
            <a-tag :color="getTypeColor(record.type)">
              {{ getTypeLabel(record.type) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'step_count'">
            {{ record.step_count }} 个步骤
          </template>
          <template v-else-if="column.key === 'created_at'">
            {{ formatDate(record.created_at) }}
          </template>
          <template v-else-if="column.key === 'actions'">
            <a-space :size="4">
              <a-button size="small" @click="goToEditScript(record.id)">
                <EditOutlined /> 编辑
              </a-button>
              <a-button size="small" @click="runScript(record)">
                <PlayCircleOutlined /> 运行
              </a-button>
              <a-button size="small" @click="duplicateScript(record)">
                <CopyOutlined /> 复制
              </a-button>
              <a-popconfirm
                title="确定删除此脚本？"
                @confirm="handleDelete(record)"
              >
                <a-button size="small" danger>
                  <DeleteOutlined />
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 执行机选择模态框 -->
    <a-modal
      v-model:open="showExecutorModal"
      title="选择执行机"
      @ok="confirmRunScript"
      @cancel="cancelRunScript"
    >
      <a-form :label-col="{ span: 5 }" :wrapper-col="{ span: 19 }">
        <a-form-item label="执行机">
          <a-select
            v-model:value="selectedExecutorId"
            placeholder="自动分配可用执行机"
            allow-clear
            :loading="loadingExecutors"
            show-search
            :filter-option="filterExecutorOption"
          >
            <a-select-option v-for="executor in availableExecutors" :key="executor.id" :value="executor.id">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>{{ executor.name }}</span>
                <span>
                  <a-tag v-if="executor.is_online" color="green" size="small">在线</a-tag>
                  <a-tag v-else color="red" size="small">离线</a-tag>
                  <span style="color: #999; font-size: 12px;">
                    {{ executor.current_tasks }}/{{ executor.max_concurrent }}
                  </span>
                </span>
              </div>
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item>
          <template #label>
            <span style="color: #999;">提示</span>
          </template>
          <span style="color: #666;">不选择则系统自动分配可用的在线执行机</span>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- NL2Script AI 生成对话框 -->
    <NL2ScriptDialog
      ref="nl2scriptRef"
      :projects="[{ id: projectId, name: projectName }]"
      @saved="loadScripts"
    />

    <!-- 批量 AI 生成对话框 -->
    <NL2ScriptBatchDialog
      ref="batchNL2ScriptRef"
      :projects="[{ id: projectId, name: projectName }]"
      @saved="loadScripts"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import {
  ArrowLeftOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  CopyOutlined,
  ThunderboltOutlined
} from '@ant-design/icons-vue'
import { getScriptList, deleteScript as deleteScriptApi, duplicateScript as duplicateScriptApi } from '@/api/script'
import { getProject } from '@/api/project'
import { createExecution } from '@/api/execution'
import { executorApi, type Executor } from '@/api/executor'
import NL2ScriptDialog from '@/components/AI/NL2ScriptDialog.vue'
import NL2ScriptBatchDialog from '@/components/AI/NL2ScriptBatchDialog.vue'
import type { Script } from '@/types/script'

interface Props {
  projectId: number
  embedMode?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  embedMode: false
})

const router = useRouter()
const route = useRoute()

const projectId = props.embedMode ? props.projectId : parseInt(route.params.projectId as string)
const projectName = ref('')
const loading = ref(false)
const scripts = ref<Script[]>([])

// 执行机选择相关
const showExecutorModal = ref(false)
const selectedExecutorId = ref<number | null>(null)
const availableExecutors = ref<Executor[]>([])
const loadingExecutors = ref(false)
const scriptToRun = ref<Script | null>(null)

// NL2Script
const nl2scriptRef = ref()
const batchNL2ScriptRef = ref()

function openNL2Script() {
  nl2scriptRef.value?.open()
}

function openBatchNL2Script() {
  batchNL2ScriptRef.value?.open()
}

const columns = [
  { title: '脚本名称', key: 'name', dataIndex: 'name', width: 350, ellipsis: true },
  { title: '类型', key: 'type', dataIndex: 'type', width: 130 },
  { title: '步骤数', key: 'step_count', dataIndex: 'step_count', width: 110 },
  { title: '创建时间', key: 'created_at', dataIndex: 'created_at', width: 180 },
  { title: '操作', key: 'actions', width: 250, fixed: 'right' }
]

async function loadScripts() {
  loading.value = true
  try {
    const res = await getScriptList(projectId)
    scripts.value = res.results
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

async function loadProject() {
  try {
    const project = await getProject(projectId)
    projectName.value = project.name
  } catch (error) {
    // 错误已由拦截器处理
  }
}

function goBack() {
  router.push('/projects')
}

function goToCreateScript() {
  // 根据嵌入模式决定返回参数
  const fromParam = props.embedMode ? 'project-detail' : 'project-list'
  console.log('[ScriptList] goToCreateScript, embedMode:', props.embedMode, 'fromParam:', fromParam)
  router.push(`/script/edit?project_id=${projectId}&from=${fromParam}`)
}

function goToEditScript(id: number) {
  // 根据嵌入模式决定返回参数
  const fromParam = props.embedMode ? 'project-detail' : 'project-list'
  console.log('[ScriptList] goToEditScript, embedMode:', props.embedMode, 'fromParam:', fromParam)
  router.push(`/script/edit/${id}?from=${fromParam}`)
}

async function runScript(script: Script) {
  scriptToRun.value = script
  selectedExecutorId.value = null
  showExecutorModal.value = true
  await loadExecutors()
}

async function loadExecutors() {
  loadingExecutors.value = true
  try {
    availableExecutors.value = await executorApi.getAvailable({ project_id: projectId })
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    loadingExecutors.value = false
  }
}

async function confirmRunScript() {
  if (!scriptToRun.value) return

  try {
    const params: any = { script_id: scriptToRun.value.id }
    if (selectedExecutorId.value) {
      params.executor_id = selectedExecutorId.value
    }
    await createExecution(params)
    message.success('执行任务已创建')
    showExecutorModal.value = false
    router.push(`/executions`)
  } catch (error) {
    // 错误已由拦截器处理
  }
}

function cancelRunScript() {
  showExecutorModal.value = false
  scriptToRun.value = null
  selectedExecutorId.value = null
}

async function duplicateScript(script: Script) {
  try {
    await duplicateScriptApi(script.id)
    message.success('复制成功')
    loadScripts()
  } catch (error) {
    // 错误已由拦截器处理
  }
}

async function handleDelete(script: Script) {
  try {
    await deleteScriptApi(script.id)
    message.success('删除成功')
    loadScripts()
  } catch (error) {
    // 错误已由拦截器处理
  }
}

function getTypeLabel(type: string) {
  const labels: Record<string, string> = {
    web: 'Web',
    mobile: '移动端',
    api: 'API'
  }
  return labels[type] || type
}

function getTypeColor(type: string) {
  const colors: Record<string, string> = {
    web: 'blue',
    mobile: 'green',
    api: 'orange'
  }
  return colors[type] || 'default'
}

function getFrameworkLabel(framework: string) {
  const labels: Record<string, string> = {
    selenium: 'Selenium',
    playwright: 'Playwright',
    appium: 'Appium',
    httprunner: 'HttpRunner'
  }
  return labels[framework] || framework
}

function formatDate(date: string) {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

function filterExecutorOption(input: string, option: any): boolean {
  if (!option || !option.children) return false
  const text = String(option.children[0]?.children || '').toLowerCase()
  return text.includes(input.toLowerCase())
}

onMounted(() => {
  loadProject()
  loadScripts()
})
</script>

<style scoped>
.script-list {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  color: rgba(255, 255, 255, 0.9);
}

.script-name-link {
  color: #1890ff;
  font-weight: 500;
  text-decoration: none;
}

.script-name-link {
  color: #1890ff;
  font-weight: 500;
  text-decoration: none;
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.script-name-link:hover {
  color: #40a9ff;
}

/* 优化表格布局 */
:deep(.ant-table) {
  table-layout: fixed;
}

:deep(.ant-table-thead > tr > th) {
  padding: 12px 24px;
}

:deep(.ant-table-tbody > tr > td) {
  padding: 12px 24px;
}

/* 操作按钮样式 */
:deep(.ant-btn-sm) {
  padding: 4px 12px;
  height: auto;
}

/* 确保表格占满宽度 */
:deep(.ant-table-container) {
  width: 100%;
}

:deep(.ant-table-body) {
  table {
    width: 100% !important;
  }
}
</style>
