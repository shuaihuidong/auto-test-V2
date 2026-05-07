<template>
  <div class="execution-list">
    <div class="page-header">
      <h2>执行记录</h2>
      <a-space>
        <a-button @click="loadExecutions">
          <ReloadOutlined /> 刷新
        </a-button>
      </a-space>
    </div>

    <a-card>
      <!-- 切换 Tabs -->
      <a-tabs v-model:activeKey="activeTab" @change="handleTabChange">
        <a-tabPane key="plan" tab="计划执行记录">
          <!-- 计划执行记录筛选区域 -->
          <div class="filter-section">
            <a-space wrap>
              <a-input
                v-model:value="planFilters.name"
                placeholder="搜索计划名称"
                style="width: 200px;"
                @pressEnter="applyPlanFilters"
                allowClear
              >
                <template #prefix><SearchOutlined /></template>
              </a-input>
              <a-range-picker
                v-model:value="planFilters.dateRange"
                :placeholder="['开始时间', '结束时间']"
                format="YYYY-MM-DD HH:mm:ss"
                show-time
                style="width: 380px;"
              />
              <a-button type="primary" @click="applyPlanFilters">
                <SearchOutlined /> 搜索
              </a-button>
              <a-button @click="resetPlanFilters">
                <ReloadOutlined /> 重置
              </a-button>
            </a-space>
          </div>

          <!-- 计划执行记录表格 -->
          <a-table
            :columns="planColumns"
            :data-source="planExecutions"
            :loading="planLoading"
            :pagination="planPagination"
            row-key="id"
            @change="handlePlanTableChange"
            style="margin-top: 16px;"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'">
                <div class="execution-name">
                  <AppstoreOutlined class="execution-icon plan-icon" />
                  <span>{{ record.plan_name || '-' }}</span>
                </div>
              </template>
              <template v-else-if="column.key === 'status'">
                <a-badge :status="getStatusBadge(record.status)" :text="getStatusText(record)" />
              </template>
              <template v-else-if="column.key === 'result'">
                <a-space>
                  <span style="color: #52c41a;">已完成: {{ record.passed_count }}</span>
                  <span style="color: #f5222d;">失败: {{ record.failed_count }}</span>
                </a-space>
              </template>
              <template v-else-if="column.key === 'created_at'">
                <span>{{ formatDateTime(record.created_at) }}</span>
              </template>
              <template v-else-if="column.key === 'actions'">
                <a-space>
                  <a-button size="small" @click="viewDetail(record)">
                    <EyeOutlined /> 详情
                  </a-button>
                  <a-button size="small" @click="viewReport(record)">
                    <FileTextOutlined /> 报告
                  </a-button>
                  <a-button
                    v-if="record.status === 'running' || record.status === 'pending'"
                    size="small"
                    danger
                    @click="stopExecution(record)"
                  >
                    <StopOutlined /> 停止
                  </a-button>
                  <a-button size="small" @click="viewLogs(record)">
                    <UnorderedListOutlined /> 日志
                  </a-button>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-tabPane>

        <a-tabPane key="script" tab="脚本执行记录">
          <!-- 脚本执行记录筛选区域 -->
          <div class="filter-section">
            <a-space wrap>
              <a-input
                v-model:value="scriptFilters.name"
                placeholder="搜索脚本名称"
                style="width: 200px;"
                @pressEnter="applyScriptFilters"
                allowClear
              >
                <template #prefix><SearchOutlined /></template>
              </a-input>
              <a-range-picker
                v-model:value="scriptFilters.dateRange"
                :placeholder="['开始时间', '结束时间']"
                format="YYYY-MM-DD HH:mm:ss"
                show-time
                style="width: 380px;"
              />
              <a-button type="primary" @click="applyScriptFilters">
                <SearchOutlined /> 搜索
              </a-button>
              <a-button @click="resetScriptFilters">
                <ReloadOutlined /> 重置
              </a-button>
            </a-space>
          </div>

          <!-- 脚本执行记录表格 -->
          <a-table
            :columns="scriptColumns"
            :data-source="scriptExecutions"
            :loading="scriptLoading"
            :pagination="scriptPagination"
            row-key="id"
            @change="handleScriptTableChange"
            style="margin-top: 16px;"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'">
                <div class="execution-name">
                  <FileTextOutlined class="execution-icon script-icon" />
                  <span>{{ record.script_name || '-' }}</span>
                </div>
              </template>
              <template v-else-if="column.key === 'status'">
                <a-badge :status="getStatusBadge(record.status)" :text="getStatusText(record)" />
              </template>
              <template v-else-if="column.key === 'result'">
                <a-space>
                  <span>总步骤数: {{ record.total_count }}</span>
                  <span style="color: #52c41a;">通过: {{ record.passed_count }}</span>
                  <span style="color: #f5222d;">失败: {{ record.failed_count }}</span>
                </a-space>
              </template>
              <template v-else-if="column.key === 'created_at'">
                <span>{{ formatDateTime(record.created_at) }}</span>
              </template>
              <template v-else-if="column.key === 'actions'">
                <a-space>
                  <a-button size="small" @click="viewReport(record)">
                    <FileTextOutlined /> 报告
                  </a-button>
                  <a-button
                    v-if="record.status === 'running' || record.status === 'pending'"
                    size="small"
                    danger
                    @click="stopExecution(record)"
                  >
                    <StopOutlined /> 停止
                  </a-button>
                  <a-button size="small" @click="viewLogs(record)">
                    <UnorderedListOutlined /> 日志
                  </a-button>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-tabPane>
      </a-tabs>
    </a-card>

    <!-- 日志弹窗 -->
    <a-modal
      v-model:open="logsVisible"
      title="执行日志"
      width="800px"
      :footer="null"
    >
      <div class="logs-content">
        <div v-for="(log, index) in logs" :key="index" class="log-entry" :class="log.level">
          <span class="log-time">{{ log.timestamp }}</span>
          <span class="log-message">[{{ log.level.toUpperCase() }}] Step {{ log.step }}: {{ log.message }}</span>
        </div>
        <a-empty v-if="!logs.length" description="暂无日志" />
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import dayjs, { Dayjs } from 'dayjs'
import {
  ReloadOutlined,
  FileTextOutlined,
  StopOutlined,
  UnorderedListOutlined,
  SearchOutlined,
  AppstoreOutlined,
  EyeOutlined
} from '@ant-design/icons-vue'
import { getExecutionList, stopExecution as stopExecutionApi, getExecutionLogs } from '@/api/execution'
import type { Execution } from '@/types/execution'

const router = useRouter()
const route = useRoute()

// 当前激活的 tab - 从 URL query 参数获取，默认为 'plan'
const activeTab = ref((route.query.tab as string) || 'plan')

// 计划执行记录状态
const planLoading = ref(false)
const planExecutions = ref<any[]>([])
const planPagination = ref({
  current: 1,
  pageSize: 20,
  total: 0
})

// 脚本执行记录状态
const scriptLoading = ref(false)
const scriptExecutions = ref<any[]>([])
const scriptPagination = ref({
  current: 1,
  pageSize: 20,
  total: 0
})

// 日志弹窗状态
const logsVisible = ref(false)
const logs = ref<any[]>([])

// 计划执行记录筛选条件
const planFilters = ref({
  name: '',
  dateRange: [undefined as Dayjs | undefined, undefined as Dayjs | undefined] as [Dayjs | undefined, Dayjs | undefined]
})

const planCurrentFilters = ref({
  name: '',
  start_time: '',
  end_time: ''
})

// 脚本执行记录筛选条件
const scriptFilters = ref({
  name: '',
  dateRange: [undefined as Dayjs | undefined, undefined as Dayjs | undefined] as [Dayjs | undefined, Dayjs | undefined]
})

const scriptCurrentFilters = ref({
  name: '',
  start_time: '',
  end_time: ''
})

// 计划执行记录列定义
const planColumns = [
  { title: 'ID', key: 'display_id', dataIndex: 'display_id', width: 150 },
  { title: '计划名称', key: 'name', width: 250 },
  { title: '状态', key: 'status', width: 120 },
  { title: '结果', key: 'result', width: 250 },
  { title: '脚本数', key: 'children_count', dataIndex: 'children_count', width: 100 },
  { title: '执行者', key: 'created_by_name', dataIndex: 'created_by_name', width: 120 },
  { title: '创建时间', key: 'created_at', dataIndex: 'created_at', width: 180 },
  { title: '操作', key: 'actions', width: 200, fixed: 'right' }
]

// 脚本执行记录列定义
const scriptColumns = [
  { title: 'ID', key: 'display_id', dataIndex: 'display_id', width: 150 },
  { title: '脚本名称', key: 'name', width: 250 },
  { title: '状态', key: 'status', width: 120 },
  { title: '结果', key: 'result', width: 250 },
  { title: '耗时(秒)', key: 'duration', dataIndex: 'duration', width: 100 },
  { title: '执行者', key: 'created_by_name', dataIndex: 'created_by_name', width: 120 },
  { title: '创建时间', key: 'created_at', dataIndex: 'created_at', width: 180 },
  { title: '操作', key: 'actions', width: 200, fixed: 'right' }
]

let refreshTimer: ReturnType<typeof setTimeout> | null = null

// 加载计划执行记录
async function loadPlanExecutions() {
  planLoading.value = true
  try {
    const params: any = {
      page: planPagination.value.current,
      page_size: planPagination.value.pageSize,
      execution_type: 'plan'
    }

    if (planCurrentFilters.value.name) {
      params.name = planCurrentFilters.value.name
    }
    if (planCurrentFilters.value.start_time) {
      params.start_time = planCurrentFilters.value.start_time
    }
    if (planCurrentFilters.value.end_time) {
      params.end_time = planCurrentFilters.value.end_time
    }

    const res = await getExecutionList(params)
    planExecutions.value = res.results
    planPagination.value.total = res.count
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    planLoading.value = false
  }
}

// 加载脚本执行记录
async function loadScriptExecutions() {
  scriptLoading.value = true
  try {
    const params: any = {
      page: scriptPagination.value.current,
      page_size: scriptPagination.value.pageSize,
      execution_type: 'script'
    }

    if (scriptCurrentFilters.value.name) {
      params.name = scriptCurrentFilters.value.name
    }
    if (scriptCurrentFilters.value.start_time) {
      params.start_time = scriptCurrentFilters.value.start_time
    }
    if (scriptCurrentFilters.value.end_time) {
      params.end_time = scriptCurrentFilters.value.end_time
    }

    const res = await getExecutionList(params)
    scriptExecutions.value = res.results
    scriptPagination.value.total = res.count
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    scriptLoading.value = false
  }
}

// 加载当前激活的 tab 数据
function loadExecutions() {
  if (activeTab.value === 'plan') {
    loadPlanExecutions()
  } else {
    loadScriptExecutions()
  }
}

// Tab 切换事件
function handleTabChange(key: string) {
  activeTab.value = key
  loadExecutions()
}

// 计划执行记录筛选
function applyPlanFilters() {
  planCurrentFilters.value.name = planFilters.value.name
  if (planFilters.value.dateRange[0]) {
    planCurrentFilters.value.start_time = planFilters.value.dateRange[0].format('YYYY-MM-DD HH:mm:ss')
  } else {
    planCurrentFilters.value.start_time = ''
  }
  if (planFilters.value.dateRange[1]) {
    planCurrentFilters.value.end_time = planFilters.value.dateRange[1].format('YYYY-MM-DD HH:mm:ss')
  } else {
    planCurrentFilters.value.end_time = ''
  }
  planPagination.value.current = 1
  loadPlanExecutions()
}

function resetPlanFilters() {
  planFilters.value = {
    name: '',
    dateRange: [undefined, undefined] as [Dayjs | undefined, Dayjs | undefined]
  }
  planCurrentFilters.value = {
    name: '',
    start_time: '',
    end_time: ''
  }
  planPagination.value.current = 1
  loadPlanExecutions()
}

// 脚本执行记录筛选
function applyScriptFilters() {
  scriptCurrentFilters.value.name = scriptFilters.value.name
  if (scriptFilters.value.dateRange[0]) {
    scriptCurrentFilters.value.start_time = scriptFilters.value.dateRange[0].format('YYYY-MM-DD HH:mm:ss')
  } else {
    scriptCurrentFilters.value.start_time = ''
  }
  if (scriptFilters.value.dateRange[1]) {
    scriptCurrentFilters.value.end_time = scriptFilters.value.dateRange[1].format('YYYY-MM-DD HH:mm:ss')
  } else {
    scriptCurrentFilters.value.end_time = ''
  }
  scriptPagination.value.current = 1
  loadScriptExecutions()
}

function resetScriptFilters() {
  scriptFilters.value = {
    name: '',
    dateRange: [undefined, undefined] as [Dayjs | undefined, Dayjs | undefined]
  }
  scriptCurrentFilters.value = {
    name: '',
    start_time: '',
    end_time: ''
  }
  scriptPagination.value.current = 1
  loadScriptExecutions()
}

// 分页变化
function handlePlanTableChange(pag: any) {
  planPagination.value.current = pag.current
  planPagination.value.pageSize = pag.pageSize
  loadPlanExecutions()
}

function handleScriptTableChange(pag: any) {
  scriptPagination.value.current = pag.current
  scriptPagination.value.pageSize = pag.pageSize
  loadScriptExecutions()
}

// 查看报告
function viewReport(execution: Execution) {
  openReportPage(execution.id)
}

// 停止执行
async function stopExecution(execution: Execution) {
  try {
    await stopExecutionApi(execution.id)
    message.success('已停止执行')
    loadExecutions()
  } catch (error) {
    // 错误已由拦截器处理
  }
}

// 查看日志
function viewDetail(execution: Execution) {
  openReportPage(execution.id)
}

function openReportPage(executionId: number) {
  const target = router.resolve({ name: 'ReportView', params: { executionId: String(executionId) } })
  window.location.assign(target.href)
}

async function viewLogs(execution: Execution) {
  try {
    const res = await getExecutionLogs(execution.id)
    logs.value = res.logs
    logsVisible.value = true
  } catch (error) {
    // 错误已由拦截器处理
  }
}

// 获取状态徽章
function getStatusBadge(status: string) {
  const badges: Record<string, string> = {
    pending: 'default',
    running: 'processing',
    completed: 'success',
    failed: 'error',
    stopped: 'warning'
  }
  return badges[status] || 'default'
}

// 获取状态显示文本（计划执行和脚本执行区分显示）
function getStatusText(record: any): string {
  if (record.execution_type === 'plan') {
    // 计划执行：completed 和 failed 都显示为"已完成"
    if (record.status === 'completed' || record.status === 'failed') {
      return '已完成'
    }
    return record.status_display || record.status
  } else {
    // 脚本执行保持原样
    return record.status_display || record.status
  }
}

// 格式化日期时间
function formatDateTime(date: string) {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

// 自动刷新运行中的任务
function startAutoRefresh() {
  refreshTimer = setInterval(() => {
    const planHasRunning = planExecutions.value.some(e => e.status === 'running' || e.status === 'pending')
    const scriptHasRunning = scriptExecutions.value.some(e => e.status === 'running' || e.status === 'pending')
    if (planHasRunning || scriptHasRunning) {
      loadExecutions()
    }
  }, 5000)
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

// 监听 URL query 参数变化
watch(() => route.query.tab, (newTab) => {
  if (newTab && newTab !== activeTab.value) {
    activeTab.value = newTab as string
    loadExecutions()
  }
})

// 监听 tab 切换，更新 URL
watch(activeTab, (newTab) => {
  router.replace({ query: { tab: newTab } })
})

onMounted(() => {
  // 从 URL 参数设置初始 tab
  const tabParam = route.query.tab as string
  if (tabParam && (tabParam === 'plan' || tabParam === 'script')) {
    activeTab.value = tabParam
  }

  loadPlanExecutions()
  loadScriptExecutions()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.execution-list {
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

.filter-section {
  padding: 16px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 4px;
}

.execution-name {
  display: flex;
  align-items: center;
}

.execution-icon {
  margin-right: 8px;
  font-size: 16px;
}

.script-icon {
  color: #1890ff;
}

.plan-icon {
  color: #722ed1;
}

.logs-content {
  max-height: 400px;
  overflow-y: auto;
  font-family: monospace;
  font-size: 12px;
}

.log-entry {
  padding: 6px 0;
  border-bottom: 1px solid #f0f0f0;
}

.log-entry.info {
  color: #1890ff;
}

.log-entry.error {
  color: #f5222d;
}

.log-entry.warning {
  color: #faad14;
}

.log-time {
  color: #999;
  margin-right: 8px;
}
</style>
