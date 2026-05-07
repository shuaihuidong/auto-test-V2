<template>
  <div class="plan-manage">
    <div class="page-header">
      <h2>测试计划</h2>
      <a-button type="primary" @click="showCreateModal">
        <PlusOutlined /> 新建计划
      </a-button>
    </div>

    <a-card>
      <!-- 筛选区域 -->
      <div class="filter-section">
        <a-row :gutter="16">
          <a-col :span="6">
            <a-input
              v-model:value="filterName"
              placeholder="搜索计划名称"
              allow-clear
              @change="handleFilterChange"
            >
              <template #prefix>
                <SearchOutlined style="color: #9CA3AF" />
              </template>
            </a-input>
          </a-col>
          <a-col :span="5">
            <a-select
              v-model:value="filterProject"
              placeholder="筛选项目"
              allow-clear
              style="width: 100%"
              @change="handleFilterChange"
            >
              <a-select-option v-for="project in projects" :key="project.id" :value="project.id">
                {{ project.name }}
              </a-select-option>
            </a-select>
          </a-col>
          <a-col :span="5">
            <a-select
              v-model:value="filterScheduleType"
              placeholder="执行方式"
              allow-clear
              style="width: 100%"
              @change="handleFilterChange"
            >
              <a-select-option value="manual">手动执行</a-select-option>
              <a-select-option value="cron">定时执行</a-select-option>
            </a-select>
          </a-col>
          <a-col :span="8">
            <a-button @click="resetFilters">重置筛选</a-button>
          </a-col>
        </a-row>
      </div>

      <a-table
        :columns="columns"
        :data-source="filteredPlans"
        :loading="loading"
        :pagination="{ pageSize: 20 }"
        row-key="id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <a @click="viewPlan(record)">
              <ClockCircleOutlined v-if="record.schedule_type === 'cron'" style="margin-right: 4px;" />
              <FileTextOutlined v-else style="margin-right: 4px;" />
              {{ record.name }}
            </a>
          </template>
          <template v-else-if="column.key === 'schedule_type'">
            <a-tag v-if="record.schedule_type === 'cron'" color="blue">
              <ClockCircleOutlined /> {{ record.cron_expression || '未配置' }}
            </a-tag>
            <a-tag v-else color="default">
              <FileTextOutlined /> 手动执行
            </a-tag>
          </template>
          <template v-else-if="column.key === 'script_count'">
            {{ record.script_count }} 个脚本
          </template>
          <template v-else-if="column.key === 'created_at'">
            {{ formatDate(record.created_at) }}
          </template>
          <template v-else-if="column.key === 'actions'">
            <a-space>
              <a-button size="small" @click="editPlan(record)">
                <EditOutlined /> 编辑
              </a-button>
              <a-button size="small" type="primary" @click="runPlan(record)">
                <PlayCircleOutlined /> 运行
              </a-button>
              <a-popconfirm title="确定删除此计划？" @confirm="handleDelete(record)">
                <a-button size="small" danger>
                  <DeleteOutlined />
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 新建/编辑计划弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="isEdit ? '编辑计划' : '新建计划'"
      width="700px"
      @ok="handleModalOk"
      @cancel="handleModalCancel"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="计划名称" required>
          <a-input v-model:value="form.name" placeholder="请输入计划名称" />
        </a-form-item>
        <a-form-item label="所属项目" required>
          <a-select v-model:value="form.project" placeholder="请选择项目">
            <a-select-option v-for="project in projects" :key="project.id" :value="project.id">
              {{ project.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="执行方式" required>
          <a-radio-group v-model:value="form.schedule_type">
            <a-radio value="manual">手动执行</a-radio>
            <a-radio value="cron">定时执行</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="执行模式">
          <a-radio-group v-model:value="form.execution_mode">
            <a-radio value="parallel">并行执行</a-radio>
            <a-radio value="sequential">顺序执行</a-radio>
          </a-radio-group>
          <template #extra>
            <small style="color: #6B7280;">
              并行执行：同时执行多个脚本（受并发数限制）<br>
              顺序执行：按队列依次执行脚本，一次执行一个
            </small>
          </template>
        </a-form-item>
        <a-form-item v-if="form.schedule_type === 'cron'" label="Cron表达式">
          <a-input
            v-model:value="form.cron_expression"
            placeholder="例如: 0 2 * * * (每天凌晨2点)"
            style="margin-bottom: 8px;"
          />
          <div class="cron-helper">
            <span class="cron-label">常用:</span>
            <a-tag @click="form.cron_expression = '0 2 * * *'" style="cursor: pointer">每天凌晨2点</a-tag>
            <a-tag @click="form.cron_expression = '0 9 * * 1-5'" style="cursor: pointer">工作日早上9点</a-tag>
            <a-tag @click="form.cron_expression = '0 */6 * * *'" style="cursor: pointer">每6小时</a-tag>
            <a-tag @click="form.cron_expression = '0 0 * * 0'" style="cursor: pointer">每周日0点</a-tag>
          </div>
          <a-alert
            v-if="form.cron_expression"
            :message="`预览: ${parseCron(form.cron_expression)}`"
            type="info"
            style="margin-top: 8px;"
          />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="3" />
        </a-form-item>
        <a-form-item label="包含脚本" required>
          <a-select
            v-model:value="selectedScriptIds"
            mode="multiple"
            placeholder="请选择脚本"
            :filter-option="filterScripts"
            show-search
          >
            <a-select-option v-for="script in availableScripts" :key="script.id" :value="script.id">
              {{ script.name }} ({{ script.framework }})
            </a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 运行确认对话框 -->
    <a-modal
      v-model:open="runModalVisible"
      title="运行计划"
      width="500px"
      @ok="handleRunConfirm"
      @cancel="handleRunCancel"
    >
      <a-form layout="vertical">
        <a-form-item label="计划">
          <a-input :value="selectedPlan?.name" disabled />
        </a-form-item>
        <a-form-item label="执行模式">
          <a-radio-group v-model:value="selectedExecutionMode">
            <a-radio value="parallel">并行执行</a-radio>
            <a-radio value="sequential">顺序执行</a-radio>
          </a-radio-group>
          <template #extra>
            <small style="color: #6B7280;">
              并行执行：同时执行多个脚本（受并发数限制）<br>
              顺序执行：按队列依次执行脚本，一次执行一个
            </small>
          </template>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  SearchOutlined,
  ClockCircleOutlined,
  FileTextOutlined
} from '@ant-design/icons-vue'
import { getProjectList } from '@/api/project'
import { getScriptList } from '@/api/script'
import { createExecution } from '@/api/execution'
import { planApi } from '@/api/plan'

const router = useRouter()

const loading = ref(false)
const plans = ref<any[]>([])
const projects = ref<any[]>([])
const availableScripts = ref<any[]>([])
const modalVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const selectedScriptIds = ref<number[]>([])

// 运行相关
const runModalVisible = ref(false)
const selectedPlan = ref<any>(null)
const selectedExecutionMode = ref<string>('parallel')

// 筛选条件
const filterName = ref('')
const filterProject = ref<number | undefined>(undefined)
const filterScheduleType = ref<string | undefined>(undefined)

// 过滤后的计划列表
const filteredPlans = computed(() => {
  let result = plans.value

  // 按名称筛选
  if (filterName.value) {
    result = result.filter(plan =>
      plan.name.toLowerCase().includes(filterName.value.toLowerCase())
    )
  }

  // 按项目筛选
  if (filterProject.value !== undefined && filterProject.value !== null) {
    result = result.filter(plan => plan.project === filterProject.value)
  }

  // 按执行方式筛选
  if (filterScheduleType.value) {
    result = result.filter(plan => plan.schedule_type === filterScheduleType.value)
  }

  return result
})

const form = ref({
  name: '',
  project: undefined as number | undefined,
  description: '',
  schedule_type: 'manual',
  cron_expression: '',
  execution_mode: 'parallel'
})

const columns = [
  { title: '计划名称', key: 'name', dataIndex: 'name' },
  { title: '执行方式', key: 'schedule_type', dataIndex: 'schedule_type', width: 180 },
  { title: '所属项目', key: 'project_name', dataIndex: 'project_name' },
  { title: '脚本数量', key: 'script_count', dataIndex: 'script_count' },
  { title: '创建者', key: 'created_by_name', dataIndex: 'created_by_name' },
  { title: '创建时间', key: 'created_at', dataIndex: 'created_at' },
  { title: '操作', key: 'actions', width: 240 }
]

// 筛选变化处理
function handleFilterChange() {
  // 计算属性会自动更新
}

// 重置筛选
function resetFilters() {
  filterName.value = ''
  filterProject.value = undefined
  filterScheduleType.value = undefined
}

async function loadPlans() {
  loading.value = true
  try {
    const res = await planApi.getList() as any
    plans.value = res.results || []
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

async function loadProjects() {
  try {
    const res = await getProjectList()
    projects.value = res.results
  } catch (error) {
    // 错误已由拦截器处理
  }
}

async function loadScripts(projectId?: number) {
  try {
    const res = await getScriptList(projectId || 0)
    availableScripts.value = res.results
  } catch (error) {
    // 错误已由拦截器处理
  }
}

function showCreateModal() {
  isEdit.value = false
  form.value = {
    name: '',
    project: undefined,
    description: '',
    schedule_type: 'manual',
    cron_expression: '',
    execution_mode: 'parallel'
  }
  selectedScriptIds.value = []
  modalVisible.value = true
}

function editPlan(plan: any) {
  isEdit.value = true
  editingId.value = plan.id
  form.value = {
    name: plan.name,
    project: plan.project,
    description: plan.description || '',
    schedule_type: plan.schedule_type || 'manual',
    cron_expression: plan.cron_expression || '',
    execution_mode: plan.execution_mode || 'parallel'
  }
  selectedScriptIds.value = plan.script_ids || []
  modalVisible.value = true
}

async function handleModalOk() {
  if (!form.value.name || !form.value.project) {
    message.error('请填写完整信息')
    return
  }

  loading.value = true
  try {
    const data = {
      ...form.value,
      project: form.value.project!,
      script_ids: selectedScriptIds.value
    }

    if (isEdit.value && editingId.value) {
      await planApi.update(editingId.value, data)
      message.success('更新成功')
    } else {
      await planApi.create(data)
      message.success('创建成功')
    }

    modalVisible.value = false
    loadPlans()
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

function handleModalCancel() {
  modalVisible.value = false
}

async function handleDelete(plan: any) {
  try {
    await planApi.delete(plan.id)
    message.success('删除成功')
    loadPlans()
  } catch (error) {
    // 错误已由拦截器处理
  }
}

function viewPlan(_plan: any) {
  // TODO: 查看计划详情
}

async function runPlan(plan: any) {
  selectedPlan.value = plan
  selectedExecutionMode.value = plan.execution_mode || 'parallel'
  runModalVisible.value = true
}

async function handleRunConfirm() {
  if (!selectedPlan.value) return

  try {
    await createExecution({
      plan_id: selectedPlan.value.id,
      execution_mode: selectedExecutionMode.value
    })
    message.success('执行任务已创建')
    runModalVisible.value = false
    router.push('/executions')
  } catch (error) {
    // 错误已由拦截器处理
  }
}

function handleRunCancel() {
  runModalVisible.value = false
  selectedPlan.value = null
}

function filterScripts(input: string, option: any) {
  return option.children[0].children.toLowerCase().includes(input.toLowerCase())
}

function formatDate(date: string) {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

function parseCron(cron: string): string {
  // 简单的 cron 表达式解析
  const parts = cron.split(' ')
  if (parts.length !== 5) return '无效的 cron 表达式'

  const [minute, hour, day, month, weekday] = parts

  // 解析分钟
  let minuteStr = minute === '*' ? '每分钟' : minute + '分'

  // 解析小时
  let hourStr = hour === '*' ? '每小时' : hour + '点'

  // 解析日期
  let dayStr = day === '*' ? '每天' : day + '号'

  // 解析月份
  let monthStr = month === '*' ? '' : '的' + month + '月'

  // 解析星期
  let weekdayStr = ''
  if (weekday !== '*') {
    const weekdays = ['日', '一', '二', '三', '四', '五', '六']
    weekdayStr = '，周' + (weekdays[parseInt(weekday)] || weekday)
  }

  return `${dayStr}${monthStr} ${hourStr}${minuteStr}${weekdayStr}`
}

onMounted(() => {
  loadPlans()
  loadProjects()
  loadScripts()
})
</script>

<style scoped>
.plan-manage {
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
  color: #ffffff;
}

.filter-section {
  margin-bottom: 16px;
  padding: 16px;
  background: #F9FAFB;
  border-radius: 8px;
}

/* Card white theme */
:deep(.ant-card) {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
}

:deep(.ant-card-body) {
  background: #FFFFFF;
}

/* Table white theme */
:deep(.ant-table) {
  background: #FFFFFF;
  color: #1F2937;
}

:deep(.ant-table-thead > tr > th) {
  background: #F9FAFB;
  color: #1F2937;
  border-bottom: 1px solid #E5E7EB;
}

:deep(.ant-table-tbody > tr > td) {
  background: #FFFFFF;
  color: #374151;
  border-bottom: 1px solid #E5E7EB;
}

:deep(.ant-table-tbody > tr:hover > td) {
  background: #F9FAFB !important;
}

:deep(.ant-empty-description) {
  color: #6B7280;
}

/* Links */
:deep(.ant-table-wrapper a) {
  color: #1F2937;
}

:deep(.ant-table-wrapper a:hover) {
  color: #374151;
}

.cron-helper {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.cron-label {
  font-size: 12px;
  color: #6B7280;
}
</style>
