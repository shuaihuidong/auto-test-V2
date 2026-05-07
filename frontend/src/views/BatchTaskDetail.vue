<template>
  <div class="batch-task-detail">
    <!-- 页面头部 -->
    <div class="page-header">
      <a-space>
        <a-button @click="goBack">
          <ArrowLeftOutlined /> 返回
        </a-button>
        <h2>{{ task?.name || '任务详情' }}</h2>
      </a-space>
      <a-button :loading="refreshing" @click="refreshTask">
        <ReloadOutlined /> 刷新状态
      </a-button>
    </div>

    <template v-if="task">
      <!-- 任务概况卡片 -->
      <a-card class="info-card" size="small">
        <a-space :size="24">
          <span>状态: <a-tag :color="statusColor(task.status)">{{ statusText(task.status) }}</a-tag></span>
          <span>创建时间: {{ formatDateTime(task.created_at) }}</span>
          <span v-if="duration">耗时: {{ duration }}</span>
          <span style="color: #52c41a;">{{ task.completed_count }} 成功</span>
          <span v-if="task.failed_count > 0" style="color: #f5222d;">{{ task.failed_count }} 失败</span>
        </a-space>

        <a-alert
          v-if="task.error_message"
          type="error"
          :message="task.error_message"
          show-icon
          style="margin-top: 12px;"
        />

        <!-- 重新生成进度 -->
        <div v-if="regenRemaining > 0" class="regen-progress">
          <div class="regen-header">
            <LoadingOutlined class="regen-spinner" />
            <span>{{ regenRemaining }} 条正在重新生成中...</span>
          </div>
        </div>

        <!-- 两阶段进度 -->
        <div v-if="isActive" class="phase-progress">
          <div class="phase-item" :class="genPhaseClass">
            <div class="phase-icon">
              <CheckCircleFilled v-if="genPhase === 'done'" class="phase-icon-done" />
              <LoadingOutlined v-else-if="genPhase === 'active'" class="phase-icon-active" />
              <span v-else class="phase-icon-pending">1</span>
            </div>
            <div class="phase-body">
              <div class="phase-title">
                AI 批量生成
                <span v-if="genPhase === 'active'" class="phase-dots">
                  <span class="tip-dot">.</span><span class="tip-dot">.</span><span class="tip-dot">.</span>
                </span>
                <span v-if="genPhase === 'done'" class="phase-check">已完成</span>
              </div>
              <div class="phase-info">
                {{ task.completed_count }} 成功
                <span v-if="task.failed_count > 0" style="color: #f5222d;"> / {{ task.failed_count }} 失败</span>
                <span style="color: #8c8c8c;"> / 共 {{ task.total_count }} 条</span>
              </div>
              <a-progress
                v-if="genPhase === 'active' || genPhase === 'done'"
                :percent="task.total_count ? Math.round((task.completed_count + task.failed_count) / task.total_count * 100) : 0"
                :stroke-color="genPhase === 'done' ? '#52c41a' : { '0%': '#1890ff', '100%': '#36cfc9' }"
                :show-info="false"
                size="small"
                style="width: 100%; margin-top: 6px;"
              />
            </div>
          </div>

          <div class="phase-connector" :class="{ 'connector-done': genPhase === 'done' }"></div>

          <div class="phase-item" :class="reviewPhaseClass">
            <div class="phase-icon">
              <CheckCircleFilled v-if="reviewPhase === 'done'" class="phase-icon-done" />
              <LoadingOutlined v-else-if="reviewPhase === 'active'" class="phase-icon-active" />
              <span v-else class="phase-icon-pending">2</span>
            </div>
            <div class="phase-body">
              <div class="phase-title">
                AI 质量评审
                <span v-if="reviewPhase === 'active'" class="phase-dots">
                  <span class="tip-dot">.</span><span class="tip-dot">.</span><span class="tip-dot">.</span>
                </span>
                <span v-if="reviewPhase === 'done'" class="phase-check">已完成</span>
              </div>
              <div class="phase-info">
                <template v-if="reviewPhase === 'pending'">等待生成完成后自动开始</template>
                <template v-else-if="reviewPhase === 'active'">正在审查脚本质量和意图匹配度</template>
                <template v-else-if="reviewPhase === 'done'">所有生成结果已通过 AI 评审</template>
              </div>
            </div>
          </div>
        </div>
      </a-card>

      <!-- 筛选 + 操作栏 -->
      <a-card class="filter-card" size="small">
        <div class="toolbar">
          <a-space>
            <a-input-search
              v-model:value="filters.keyword"
              placeholder="搜索提示词"
              style="width: 240px"
              allow-clear
            />
            <a-select
              v-model:value="filters.status"
              style="width: 140px"
              allow-clear
              placeholder="全部状态"
            >
              <a-select-option value="success">成功</a-select-option>
              <a-select-option value="failed">失败</a-select-option>
            </a-select>
          </a-space>
          <a-space v-if="task.status === 'completed' || task.results?.length">
            <a-button :disabled="!selectedRowKeys.length" class="btn-danger" @click="confirmDelete">
              <DeleteOutlined /> 删除<span v-if="selectedRowKeys.length"> ({{ selectedRowKeys.length }})</span>
            </a-button>
            <a-button :disabled="!selectedRowKeys.length" @click="confirmRegenerate">
              <ReloadOutlined /> 重新生成<span v-if="selectedRowKeys.length"> ({{ selectedRowKeys.length }})</span>
            </a-button>
            <a-button :disabled="!selectedRowKeys.length" @click="showSaveModal = true">
              <SaveOutlined /> 应用脚本<span v-if="selectedRowKeys.length"> ({{ selectedRowKeys.length }})</span>
            </a-button>
          </a-space>
        </div>
      </a-card>

      <!-- 结果表格 -->
      <a-card>
        <a-table
          :columns="columns"
          :data-source="filteredResults"
          :loading="loading"
          row-key="index"
          :pagination="pagination"
          :row-selection="{ selectedRowKeys, onChange: onSelectionChange }"
          :expanded-row-keys="expandedRowKeys"
          @expand="onExpand"
          @change="handleTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'index'">
              #{{ record.index + 1 }}
            </template>
            <template v-else-if="column.key === 'prompt'">
              <a-tooltip :title="record.prompt">
                <span class="prompt-text">{{ record.prompt }}</span>
              </a-tooltip>
            </template>
            <template v-else-if="column.key === 'status'">
              <a-tag v-if="record.regenerating" color="processing" size="small">
                <LoadingOutlined /> 生成中
              </a-tag>
              <a-tag v-else :color="record.success ? 'success' : 'error'" size="small">
                {{ record.success ? '成功' : '失败' }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'steps'">
              <template v-if="record.success">
                {{ record.steps?.length || 0 }} 步
              </template>
              <template v-else>
                <span style="color: #bfbfbf;">-</span>
              </template>
            </template>
            <template v-else-if="column.key === 'review'">
              <template v-if="record.review">
                <a-tag :color="record.review.passed ? 'green' : 'orange'" size="small">
                  Q:{{ record.review.quality_score }} I:{{ record.review.intent_match }}
                </a-tag>
              </template>
              <template v-else>
                <span style="color: #bfbfbf;">-</span>
              </template>
            </template>
            <template v-else-if="column.key === 'actions'">
              <a-button type="link" size="small" @click="toggleExpand(record)">
                {{ expandedRowKeys.includes(record.index) ? '收起' : '展开' }}
              </a-button>
            </template>
          </template>

          <template #expandedRowRender="{ record }">
            <div class="expanded-content">
              <!-- 错误信息 -->
              <div v-if="!record.success && record.error" class="expanded-section error-section">
                <div class="section-label">错误信息:</div>
                <div class="section-body">{{ record.error }}</div>
              </div>
              <!-- 步骤摘要 -->
              <div v-if="record.success && record.steps?.length" class="expanded-section">
                <div class="section-label">步骤摘要 ({{ record.steps.length }} 步):</div>
                <div class="section-body">
                  {{ record.steps.map((s: any) => s.name || s.type).join(' → ') }}
                </div>
              </div>
              <!-- 评审建议 -->
              <div v-if="record.review?.suggestions?.length" class="expanded-section">
                <div class="section-label">评审建议:</div>
                <div class="section-body">
                  <ul class="suggestion-list">
                    <li v-for="(s, i) in record.review.suggestions" :key="i">{{ s }}</li>
                  </ul>
                </div>
              </div>
            </div>
          </template>
        </a-table>
      </a-card>
    </template>

    <!-- 加载中 -->
    <div v-if="!task && loading" style="text-align: center; padding: 60px;">
      <a-spin size="large" />
    </div>

    <!-- 任务不存在 -->
    <a-result
      v-if="!task && !loading"
      status="404"
      title="任务不存在"
      sub-title="请检查任务 ID 是否正确"
    >
      <template #extra>
        <a-button type="primary" @click="goBack">返回任务列表</a-button>
      </template>
    </a-result>

    <!-- 保存到项目弹窗 -->
    <a-modal
      v-model:open="showSaveModal"
      title="保存脚本到项目"
      :confirm-loading="saving"
      @ok="handleSave"
    >
      <a-form layout="vertical">
        <a-form-item label="选择项目" required>
          <a-select
            v-model:value="saveProjectId"
            placeholder="请选择项目"
            style="width: 100%;"
          >
            <a-select-option v-for="p in projects" :key="p.id" :value="p.id">
              {{ p.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import {
  ArrowLeftOutlined,
  ReloadOutlined,
  DeleteOutlined,
  SaveOutlined,
  LoadingOutlined,
  CheckCircleFilled,
} from '@ant-design/icons-vue'
import {
  getBatchTask,
  saveBatchTaskScripts,
  deleteBatchTaskResults,
  regenerateBatchTaskResults,
  type BatchTaskInfo,
  type BatchTaskResult,
} from '@/api/script'
import { getProjectList } from '@/api/project'

const route = useRoute()
const router = useRouter()
const taskId = computed(() => Number(route.params.id))

// ---- 状态 ----
const loading = ref(false)
const refreshing = ref(false)
const task = ref<BatchTaskInfo | null>(null)
const expandedRowKeys = ref<number[]>([])
const selectedRowKeys = ref<number[]>([])

// 保存弹窗
const showSaveModal = ref(false)
const saveProjectId = ref<number | null>(null)
const saving = ref(false)
const projects = ref<any[]>([])

// 筛选
const filters = ref({
  keyword: '',
  status: '' as string,
})

// 分页
const pagination = ref({
  current: 1,
  pageSize: 20,
  showSizeChanger: true,
  pageSizeOptions: ['10', '20', '50'],
  showTotal: (total: number) => `共 ${total} 条`,
})

let pollingTimer: ReturnType<typeof setInterval> | null = null

// ---- 表格列 ----
const columns = [
  { title: '#', key: 'index', width: 60 },
  { title: '提示词', key: 'prompt', ellipsis: true },
  { title: '状态', key: 'status', width: 80 },
  { title: '步骤', key: 'steps', width: 80 },
  { title: '评审', key: 'review', width: 140 },
  { title: '操作', key: 'actions', width: 80 },
]

// ---- 计算属性 ----
const isActive = computed(() => {
  if (!task.value) return false
  return ['pending', 'running', 'reviewing'].includes(task.value.status)
})

const duration = computed(() => {
  if (!task.value) return ''
  const created = new Date(task.value.created_at).getTime()
  const updated = new Date(task.value.updated_at).getTime()
  const diffMs = updated - created
  if (diffMs < 60000) return `${(diffMs / 1000).toFixed(0)}s`
  if (diffMs < 3600000) return `${(diffMs / 60000).toFixed(1)}min`
  return `${(diffMs / 3600000).toFixed(1)}h`
})

// 重新生成进度
const regenRemaining = computed(() => {
  if (!task.value?.results) return 0
  return task.value.results.filter((r: any) => r.regenerating).length
})

const filteredResults = computed(() => {
  if (!task.value?.results) return []
  let results = task.value.results

  if (filters.value.keyword) {
    const kw = filters.value.keyword.toLowerCase()
    results = results.filter((r: BatchTaskResult) => r.prompt.toLowerCase().includes(kw))
  }

  if (filters.value.status === 'success') {
    results = results.filter((r: BatchTaskResult) => r.success)
  } else if (filters.value.status === 'failed') {
    results = results.filter((r: BatchTaskResult) => !r.success)
  }

  return results
})

// 两阶段进度
const genPhase = computed<'pending' | 'active' | 'done'>(() => {
  if (!task.value) return 'pending'
  const s = task.value.status
  if (s === 'pending') return 'pending'
  if (s === 'running') return 'active'
  return 'done'
})

const reviewPhase = computed<'pending' | 'active' | 'done'>(() => {
  if (!task.value) return 'pending'
  const s = task.value.status
  if (s === 'reviewing') return 'active'
  if (s === 'completed') return 'done'
  return 'pending'
})

const genPhaseClass = computed(() => `phase-${genPhase.value}`)
const reviewPhaseClass = computed(() => `phase-${reviewPhase.value}`)

// 行选择 — 稳定函数引用，避免表格整表重渲染
function onSelectionChange(keys: number[]) {
  selectedRowKeys.value = keys
}

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

function goBack() {
  router.push({ name: 'BatchTasks' })
}

async function loadTask() {
  loading.value = true
  try {
    task.value = await getBatchTask(taskId.value)
  } catch {
    message.error('加载任务详情失败')
  } finally {
    loading.value = false
  }
}

async function refreshTask() {
  refreshing.value = true
  try {
    task.value = await getBatchTask(taskId.value)
  } catch {
    // ignore
  } finally {
    refreshing.value = false
  }
}

function toggleExpand(record: BatchTaskResult) {
  const idx = expandedRowKeys.value.indexOf(record.index)
  if (idx >= 0) {
    expandedRowKeys.value.splice(idx, 1)
  } else {
    expandedRowKeys.value.push(record.index)
  }
}

function onExpand(expanded: boolean, record: BatchTaskResult) {
  if (expanded) {
    if (!expandedRowKeys.value.includes(record.index)) {
      expandedRowKeys.value.push(record.index)
    }
  } else {
    const idx = expandedRowKeys.value.indexOf(record.index)
    if (idx >= 0) expandedRowKeys.value.splice(idx, 1)
  }
}

function handleTableChange(pag: any) {
  pagination.value.current = pag.current || 1
  pagination.value.pageSize = pag.pageSize || 20
}

function confirmDelete() {
  if (!selectedRowKeys.value.length) return
  Modal.confirm({
    title: '确定删除选中的结果？',
    content: `将删除 ${selectedRowKeys.value.length} 条结果，删除后不可恢复。`,
    okType: 'danger',
    onOk: handleDeleteSelected,
  })
}

async function handleDeleteSelected() {
  try {
    const result = await deleteBatchTaskResults(taskId.value, {
      indexes: selectedRowKeys.value,
    })
    task.value = result
    selectedRowKeys.value = []
    message.success('删除成功')
  } catch (e: any) {
    message.error(e?.response?.data?.error || '删除失败')
  }
}

function confirmRegenerate() {
  if (!selectedRowKeys.value.length) return
  Modal.confirm({
    title: '确定重新生成选中的条目？',
    content: `将重新生成 ${selectedRowKeys.value.length} 条结果。`,
    onOk: handleRegenerateSelected,
  })
}

async function handleRegenerateSelected() {
  try {
    await regenerateBatchTaskResults(taskId.value, {
      indexes: selectedRowKeys.value,
    })
    selectedRowKeys.value = []
    // 立即刷新，拿到 regenerating 标记
    task.value = await getBatchTask(taskId.value)
    message.success('已开始重新生成')
    startRegenPolling()
  } catch (e: any) {
    message.error(e?.response?.data?.error || '重新生成失败')
  }
}

let regenTimer: ReturnType<typeof setInterval> | null = null

function hasRegeneratingItems() {
  return task.value?.results?.some((r: any) => r.regenerating)
}

function startRegenPolling() {
  stopRegenPolling()
  regenTimer = setInterval(async () => {
    if (!hasRegeneratingItems()) {
      stopRegenPolling()
      return
    }
    try {
      task.value = await getBatchTask(taskId.value)
    } catch {
      // ignore
    }
  }, 5000)
}

function stopRegenPolling() {
  if (regenTimer) {
    clearInterval(regenTimer)
    regenTimer = null
  }
}

async function handleSave() {
  if (!saveProjectId.value) {
    message.warning('请选择项目')
    return
  }
  if (!task.value) return

  saving.value = true
  try {
    const items = task.value.results
      .filter((r: BatchTaskResult) => selectedRowKeys.value.includes(r.index) && r.success)
      .map(r => ({
        index: r.index,
        script_name: '',
        steps: r.steps,
      }))
    await saveBatchTaskScripts(task.value.id, {
      project_id: saveProjectId.value,
      items,
    })
    message.success(`已保存 ${items.length} 条脚本`)
    showSaveModal.value = false
    saveProjectId.value = null
  } catch (e: any) {
    message.error(e?.response?.data?.error || '保存失败')
  } finally {
    saving.value = false
  }
}

async function loadProjects() {
  try {
    const res = await getProjectList()
    projects.value = res.results || []
  } catch {
    // ignore
  }
}

// 轮询
function startPolling() {
  stopPolling()
  pollingTimer = setInterval(() => {
    if (isActive.value) {
      refreshTask()
    }
  }, 5000)
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

onMounted(async () => {
  await loadTask()
  loadProjects()
  if (isActive.value) {
    startPolling()
  }
  if (hasRegeneratingItems()) {
    startRegenPolling()
  }
})

onUnmounted(() => {
  stopPolling()
  stopRegenPolling()
})
</script>

<style scoped>
.batch-task-detail {
  padding: 0;
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

.info-card {
  margin-bottom: 12px;
}

.regen-progress {
  margin-top: 12px;
  padding: 12px 16px;
  background: rgba(24, 144, 255, 0.06);
  border-radius: 8px;
  border: 1px solid rgba(24, 144, 255, 0.2);
}

.regen-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #1890ff;
  font-weight: 500;
}

.regen-spinner {
  animation: spin 1s linear infinite;
}

.filter-card {
  margin-bottom: 12px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.toolbar :deep(.ant-btn:not(.ant-btn-disabled)) {
  background: #fff;
  color: #262626;
  border-color: #d9d9d9;
}

.toolbar :deep(.btn-danger:not(.ant-btn-disabled)) {
  color: #f5222d;
  border-color: #ffcfcf;
}

.toolbar :deep(.btn-danger:not(.ant-btn-disabled):hover) {
  color: #ff4d4f;
  border-color: #ff7875;
}

.prompt-text {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.expanded-content {
  padding: 8px 0;
}

.expanded-section {
  margin-bottom: 8px;
}

.expanded-section:last-child {
  margin-bottom: 0;
}

.error-section {
  color: #f5222d;
}

.section-label {
  font-weight: 600;
  font-size: 13px;
  color: #8c8c8c;
  margin-bottom: 4px;
}

.section-body {
  font-size: 13px;
  color: #262626;
}

.suggestion-list {
  margin: 0;
  padding-left: 20px;
}

.suggestion-list li {
  margin-bottom: 2px;
}

/* ant-design 表格文字深色 */
:deep(.ant-table) {
  color: #262626;
}
:deep(.ant-table-cell) {
  color: #262626;
}
:deep(.ant-card-body) {
  color: #262626;
}

/* 两阶段进度 */
.phase-progress {
  display: flex;
  align-items: stretch;
  gap: 0;
  margin-top: 16px;
  padding: 24px;
  background: #fafafa;
  border-radius: 12px;
}

.phase-item {
  flex: 1;
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  transition: background 0.3s;
}

.phase-item.phase-active {
  background: rgba(24, 144, 255, 0.06);
}

.phase-item.phase-done {
  background: rgba(82, 196, 26, 0.04);
}

.phase-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}

.phase-icon-pending {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #d9d9d9;
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.phase-icon-active {
  color: #1890ff;
  animation: spin 1s linear infinite;
}

.phase-icon-done {
  color: #52c41a;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.phase-body {
  flex: 1;
  min-width: 0;
}

.phase-title {
  font-size: 16px;
  font-weight: 600;
  color: #262626;
  display: flex;
  align-items: center;
  gap: 4px;
}

.phase-pending .phase-title {
  color: #bfbfbf;
}

.phase-dots {
  display: inline-flex;
  gap: 2px;
  margin-left: 2px;
}

.tip-dot {
  animation: dotBlink 1.4s infinite;
  font-weight: bold;
  color: #1890ff;
}

.tip-dot:nth-child(2) { animation-delay: 0.2s; }
.tip-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes dotBlink {
  0%, 80%, 100% { opacity: 0.2; }
  40% { opacity: 1; }
}

.phase-check {
  font-size: 12px;
  font-weight: 400;
  color: #52c41a;
  margin-left: 4px;
}

.phase-info {
  font-size: 13px;
  color: #8c8c8c;
  margin-top: 4px;
}

.phase-connector {
  width: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.phase-connector::before {
  content: '';
  width: 2px;
  height: 100%;
  background: #d9d9d9;
  border-radius: 1px;
  transition: background 0.3s;
}

.phase-connector.connector-done::before {
  background: #52c41a;
}
</style>
