<template>
  <div class="all-scripts">
    <div class="page-header">
      <h2>所有脚本</h2>
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

    <!-- 筛选条件 -->
    <a-card class="filter-card">
      <a-form layout="inline">
        <a-form-item label="项目">
          <a-select
            v-model:value="filters.project_id"
            style="width: 200px"
            allow-clear
            placeholder="全部项目"
            show-search
            :filter-option="filterProjectOption"
            @change="loadScripts"
          >
            <a-select-option :value="null">全部项目</a-select-option>
            <a-select-option v-for="project in projects" :key="project.id" :value="project.id">
              {{ project.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="类型">
          <a-select
            v-model:value="filters.type"
            style="width: 120px"
            allow-clear
            placeholder="全部类型"
            @change="loadScripts"
          >
            <a-select-option value="">全部类型</a-select-option>
            <a-select-option value="web">Web自动化</a-select-option>
            <a-select-option value="mobile">移动端</a-select-option>
            <a-select-option value="api">API接口</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="框架">
          <a-select
            v-model:value="filters.framework"
            style="width: 120px"
            allow-clear
            placeholder="全部框架"
            @change="loadScripts"
          >
            <a-select-option value="">全部框架</a-select-option>
            <a-select-option value="playwright">Playwright</a-select-option>
            <a-select-option value="appium">Appium</a-select-option>
            <a-select-option value="httprunner">HttpRunner</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="模块">
          <a-select
            v-model:value="filters.is_module"
            style="width: 100px"
            allow-clear
            placeholder="全部"
            @change="loadScripts"
          >
            <a-select-option :value="null">全部</a-select-option>
            <a-select-option :value="true">模块</a-select-option>
            <a-select-option :value="false">普通</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-card>

    <!-- 脚本列表 -->
    <a-card>
      <a-table
        :columns="columns"
        :data-source="scripts"
        :loading="loading"
        :pagination="pagination"
        row-key="id"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <a class="script-name-link" @click="goToEditScript(record.id)">{{ record.name }}</a>
          </template>

          <template v-else-if="column.key === 'project'">
            <a @click="goToProject(record.project)" class="project-link">
              {{ getProjectName(record.project) }}
            </a>
          </template>

          <template v-else-if="column.key === 'type'">
            <a-tag :color="getTypeColor(record.type)">
              {{ getTypeLabel(record.type) }}
            </a-tag>
          </template>

          <template v-else-if="column.key === 'framework'">
            <a-tag>{{ getFrameworkLabel(record.framework) }}</a-tag>
          </template>

          <template v-else-if="column.key === 'is_module'">
            <a-tag v-if="record.is_module" color="purple">模块</a-tag>
            <span v-else class="text-tertiary">普通</span>
          </template>

          <template v-else-if="column.key === 'step_count'">
            <a-statistic :value="record.step_count || 0" :value-style="{ fontSize: '14px' }">
              <template #suffix>个步骤</template>
            </a-statistic>
          </template>

          <template v-else-if="column.key === 'created_at'">
            {{ formatDate(record.created_at) }}
          </template>

          <template v-else-if="column.key === 'updated_at'">
            {{ formatDate(record.updated_at) }}
          </template>

          <template v-else-if="column.key === 'actions'">
            <a-space>
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

    <!-- NL2Script AI 生成对话框 -->
    <NL2ScriptDialog
      ref="nl2scriptRef"
      :projects="projectOptions"
      @saved="loadScripts"
      @edit="goToEditScript"
    />

    <!-- 批量 AI 生成对话框 -->
    <NL2ScriptBatchDialog
      ref="batchNL2ScriptRef"
      :projects="projectOptions"
      @saved="loadScripts"
      @goToTask="goToBatchTask"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  CopyOutlined,
  ThunderboltOutlined
} from '@ant-design/icons-vue'
import { getScriptList as getScriptListApi, deleteScript as deleteScriptApi, duplicateScript as duplicateScriptApi } from '@/api/script'
import { getProjectList } from '@/api/project'
import { createExecution } from '@/api/execution'
import NL2ScriptDialog from '@/components/AI/NL2ScriptDialog.vue'
import NL2ScriptBatchDialog from '@/components/AI/NL2ScriptBatchDialog.vue'
import type { Script } from '@/types/script'

const router = useRouter()

const loading = ref(false)
const scripts = ref<Script[]>([])
const projects = ref<any[]>([])

// NL2Script
const nl2scriptRef = ref()
const batchNL2ScriptRef = ref()
const projectOptions = computed(() => projects.value.map(p => ({ id: p.id, name: p.name })))

function openNL2Script() {
  nl2scriptRef.value?.open()
}

function openBatchNL2Script() {
  batchNL2ScriptRef.value?.open()
}

function goToBatchTask(taskId: number) {
  router.push({ name: 'BatchTaskDetail', params: { id: String(taskId) } })
}

// 筛选条件
const filters = ref({
  project_id: null,
  type: '',
  framework: '',
  is_module: null
})

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

const columns = [
  { title: '脚本名称', key: 'name', dataIndex: 'name' },
  { title: '所属项目', key: 'project', dataIndex: 'project' },
  { title: '类型', key: 'type', dataIndex: 'type', width: 100 },
  { title: '框架', key: 'framework', dataIndex: 'framework', width: 100 },
  { title: '属性', key: 'is_module', dataIndex: 'is_module', width: 80 },
  { title: '步骤数', key: 'step_count', dataIndex: 'step_count', width: 100 },
  { title: '创建时间', key: 'created_at', dataIndex: 'created_at', width: 180 },
  { title: '操作', key: 'actions', width: 240, fixed: 'right' }
]

async function loadScripts() {
  loading.value = true
  try {
    // 使用 project=0 获取所有项目的脚本
    const params: any = { project: 0 }

    if (filters.value.project_id) {
      params.project = filters.value.project_id
    }
    if (filters.value.type) {
      params.type = filters.value.type
    }
    if (filters.value.framework) {
      params.framework = filters.value.framework
    }
    if (filters.value.is_module !== null) {
      params.is_module = filters.value.is_module
    }

    const res = await getScriptListApi(0, params)
    scripts.value = res.results || []
    pagination.total = res.count || scripts.value.length
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

async function loadProjects() {
  try {
    const res = await getProjectList()
    projects.value = res.results || []
  } catch (error) {
    // 错误已由拦截器处理
  }
}

function goToCreateScript() {
  // 检查是否有项目
  if (projects.value.length === 0) {
    message.warning('请先创建项目')
    router.push('/projects')
    return
  }
  // 默认选择第一个项目，from=all 表示从所有脚本页面来的
  router.push(`/script/edit?project_id=${projects.value[0].id}&from=all`)
}

function goToEditScript(id: number) {
  router.push(`/script/edit/${id}?from=all`)
}

function goToProject(projectId: number) {
  router.push(`/projects/${projectId}`)
}

async function runScript(script: Script) {
  try {
    await createExecution({ script_id: script.id })
    message.success('执行任务已创建')
    router.push('/executions')
  } catch (error) {
    // 错误已由拦截器处理
  }
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

function handleTableChange(pag: any) {
  if (pag.current) {
    pagination.current = pag.current
  }
}

function getProjectName(id: number): string {
  const project = projects.value.find(p => p.id === id)
  return project ? project.name : '-'
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
    playwright: 'Playwright',
    appium: 'Appium',
    httprunner: 'HttpRunner'
  }
  return labels[framework] || framework
}

function formatDate(date: string) {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

function filterProjectOption(input: string, option: any): boolean {
  if (!option || !option.children) return false
  const text = String(option.children).toLowerCase()
  return text.includes(input.toLowerCase())
}

onMounted(() => {
  loadProjects()
  loadScripts()
})
</script>

<style scoped>
.all-scripts {
  max-width: 1600px;
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

.filter-card {
  margin-bottom: 16px;
}

.script-name-link {
  color: #1890ff;
  font-weight: 500;
  text-decoration: none;
}

.script-name-link:hover {
  color: #40a9ff;
  text-decoration: underline;
  cursor: pointer;
}

.project-link {
  color: #9CA3AF;
  text-decoration: none;
}

.project-link:hover {
  color: #E5E7EB;
  text-decoration: underline;
  cursor: pointer;
}

.text-tertiary {
  color: #6B7280;
}
</style>
