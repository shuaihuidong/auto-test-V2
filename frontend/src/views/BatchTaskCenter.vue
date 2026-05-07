<template>
  <div class="batch-task-center">
    <div class="page-header">
      <h2>AI 任务中心</h2>
      <a-space>
        <a-button @click="loadTasks">
          <ReloadOutlined /> 刷新
        </a-button>
        <a-button type="primary" @click="showCreateModal = true">
          <PlusOutlined /> 新建任务
        </a-button>
      </a-space>
    </div>

    <!-- 任务列表 -->
    <a-card>
      <a-table
        :columns="columns"
        :data-source="tasks"
        :loading="loading"
        row-key="id"
        :pagination="false"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <a @click="viewDetail(record)">{{ record.name }}</a>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-tag :color="statusColor(record.status)">
              {{ statusText(record.status) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'progress'">
            <a-progress
              v-if="record.status === 'running'"
              :percent="record.total_count ? Math.round((record.completed_count + record.failed_count) / record.total_count * 100) : 0"
              :stroke-color="'#1890ff'"
              size="small"
            />
            <span v-else>
              {{ record.completed_count }}/{{ record.total_count }}
              <span v-if="record.failed_count > 0" style="color: #f5222d; margin-left: 4px;">
                ({{ record.failed_count }} 失败)
              </span>
            </span>
          </template>
          <template v-else-if="column.key === 'created_at'">
            {{ formatDateTime(record.created_at) }}
          </template>
          <template v-else-if="column.key === 'actions'">
            <a-space>
              <a-button size="small" @click="viewDetail(record)">
                <EyeOutlined /> 查看
              </a-button>
              <a-popconfirm title="确定删除此任务？" @confirm="handleDelete(record)">
                <a-button size="small" danger>
                  <DeleteOutlined />
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 新建任务弹窗 -->
    <a-modal
      v-model:open="showCreateModal"
      title="新建批量生成任务"
      width="720px"
      :confirm-loading="creating"
      @ok="handleCreate"
      @cancel="showCreateModal = false"
    >
      <a-form layout="vertical">
        <a-form-item label="任务名称">
          <a-input v-model:value="createForm.name" placeholder="可选，默认自动命名" />
        </a-form-item>
        <a-form-item label="上下文信息">
          <a-textarea
            v-model:value="createForm.context"
            placeholder="可选，如：当前在登录页面、目标系统 URL 等"
            :rows="2"
          />
        </a-form-item>
        <a-form-item label="测试用例描述">
          <div class="prompts-editor">
            <div class="prompts-toolbar">
              <a-button size="small" @click="addPrompt">
                <PlusOutlined /> 添加一条
              </a-button>
              <a-upload
                :before-upload="handleFileUpload"
                :show-upload-list="false"
                accept=".xlsx,.xls,.csv"
              >
                <a-button size="small">
                  <UploadOutlined /> 从 Excel 导入
                </a-button>
              </a-upload>
            </div>
            <div
              v-for="(_prompt, index) in createForm.prompts"
              :key="index"
              class="prompt-row"
            >
              <span class="prompt-index">{{ index + 1 }}</span>
              <a-textarea
                v-model:value="createForm.prompts[index]"
                :placeholder="`请输入第 ${index + 1} 条测试用例描述`"
                :auto-size="{ minRows: 1, maxRows: 3 }"
                style="flex: 1;"
              />
              <a-button
                type="text"
                danger
                size="small"
                @click="createForm.prompts.splice(index, 1)"
              >
                <CloseOutlined />
              </a-button>
            </div>
            <a-empty v-if="!createForm.prompts.length" description="暂无用例，请添加或导入" />
          </div>
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="showCreateModal = false">取消</a-button>
        <a-button
          type="primary"
          :disabled="!createForm.prompts.length"
          :loading="creating"
          @click="handleCreate"
        >
          创建并开始生成 ({{ createForm.prompts.length }} 条)
        </a-button>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ReloadOutlined,
  PlusOutlined,
  DeleteOutlined,
  EyeOutlined,
  UploadOutlined,
  CloseOutlined,
} from '@ant-design/icons-vue'
import {
  getBatchTaskList,
  createBatchTask,
  deleteBatchTask,
  nl2scriptBatchParseFile,
  type BatchTaskInfo,
} from '@/api/script'

const router = useRouter()
const loading = ref(false)
const tasks = ref<BatchTaskInfo[]>([])
const showCreateModal = ref(false)
const creating = ref(false)
const createForm = ref({
  name: '',
  context: '',
  prompts: [''] as string[],
})

let pollingTimer: ReturnType<typeof setInterval> | null = null

// ---- 表格列 ----
const columns = [
  { title: '任务名称', key: 'name', dataIndex: 'name' },
  { title: '状态', key: 'status', width: 120 },
  { title: '进度', key: 'progress', width: 200 },
  { title: '创建时间', key: 'created_at', width: 180 },
  { title: '操作', key: 'actions', width: 150 },
]

// ---- 方法 ----
function statusText(s: string) {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '生成中',
    reviewing: 'AI 评审中',
    completed: '已完成',
    failed: '失败',
  }
  return map[s] || s
}

function statusColor(s: string) {
  const map: Record<string, string> = {
    pending: 'default',
    running: 'processing',
    reviewing: 'warning',
    completed: 'success',
    failed: 'error',
  }
  return map[s] || 'default'
}

function formatDateTime(dt: string) {
  if (!dt) return '-'
  return new Date(dt).toLocaleString('zh-CN')
}

async function loadTasks() {
  loading.value = true
  try {
    const data = await getBatchTaskList() as any
    tasks.value = Array.isArray(data) ? data : (data?.results || [])
  } catch (e: any) {
    message.error('加载任务列表失败')
  } finally {
    loading.value = false
  }
}

function addPrompt() {
  createForm.value.prompts.push('')
}

async function handleFileUpload(file: File) {
  try {
    const res = await nl2scriptBatchParseFile(file)
    const col = res.columns[0]
    if (col) {
      const newPrompts = res.rows
        .map((row: any) => String(row[col] || '').trim())
        .filter(Boolean)
      if (newPrompts.length) {
        if (createForm.value.prompts.length === 1 && !createForm.value.prompts[0]) {
          createForm.value.prompts = newPrompts
        } else {
          createForm.value.prompts.push(...newPrompts)
        }
        message.success(`导入 ${newPrompts.length} 条用例`)
      }
    }
  } catch (e: any) {
    message.error(e?.response?.data?.error || '文件解析失败')
  }
  return false
}

async function handleCreate() {
  const prompts = createForm.value.prompts.filter(p => p.trim())
  if (!prompts.length) {
    message.warning('请至少输入一条用例描述')
    return
  }

  creating.value = true
  try {
    await createBatchTask({
      name: createForm.value.name,
      prompts,
      context: createForm.value.context,
    })
    message.success('任务已创建，正在后台生成')
    showCreateModal.value = false
    createForm.value = { name: '', context: '', prompts: [''] }
    loadTasks()
  } catch (e: any) {
    message.error(e?.response?.data?.error || '创建任务失败')
  } finally {
    creating.value = false
  }
}

function viewDetail(record: BatchTaskInfo) {
  router.push({ name: 'BatchTaskDetail', params: { id: String(record.id) } })
}

async function handleDelete(record: BatchTaskInfo) {
  try {
    await deleteBatchTask(record.id)
    message.success('已删除')
    loadTasks()
  } catch {
    message.error('删除失败')
  }
}

// 自动轮询进行中的任务
function startPolling() {
  stopPolling()
  pollingTimer = setInterval(() => {
    const hasActive = tasks.value.some(
      t => t.status === 'pending' || t.status === 'running' || t.status === 'reviewing'
    )
    if (hasActive) {
      loadTasks()
    }
  }, 5000)
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

// ---- 生命周期 ----
onMounted(() => {
  loadTasks()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.batch-task-center {
  padding: 0;
}

:deep(.ant-table) {
  color: #262626;
}
:deep(.ant-table-cell) {
  color: #262626;
}
:deep(.ant-table a) {
  color: #262626;
}
:deep(.ant-card-body) {
  color: #262626;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  color: var(--color-text-primary, #E5E7EB);
}

.prompts-editor {
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  padding: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.prompts-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.prompt-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 8px;
}

.prompt-index {
  width: 24px;
  height: 32px;
  line-height: 32px;
  text-align: center;
  color: #8c8c8c;
  font-size: 12px;
  flex-shrink: 0;
}
</style>
