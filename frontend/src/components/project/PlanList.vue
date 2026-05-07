<template>
  <div class="plan-list-embed">
    <div class="list-header">
      <a-space>
        <span>共 {{ plans.length }} 个计划</span>
      </a-space>
      <a-button v-if="!embedMode" type="primary" @click="showCreateModal">
        <PlusOutlined /> 新建计划
      </a-button>
    </div>

    <a-table
      :columns="columns"
      :data-source="plans"
      :loading="loading"
      :pagination="pagination"
      row-key="id"
      @change="handleTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          <a @click="viewDetail(record)" class="plan-name">
            {{ record.name }}
          </a>
        </template>

        <template v-else-if="column.key === 'scripts'">
          <a-tag color="blue">{{ record.script_count }} 个脚本</a-tag>
        </template>

        <template v-else-if="column.key === 'status'">
          <a-tag :color="getStatusColor(record.last_status)">
            {{ getStatusLabel(record.last_status) }}
          </a-tag>
        </template>

        <template v-else-if="column.key === 'last_run'">
          {{ record.last_run ? formatTime(record.last_run) : '-' }}
        </template>

        <template v-else-if="column.key === 'actions'">
          <a-space>
            <a-button type="link" size="small" @click="viewDetail(record)">详情</a-button>
            <a-button type="link" size="small" @click="runPlan(record)">运行</a-button>
            <a-dropdown>
              <a class="action-icon"><MoreOutlined /></a>
              <template #overlay>
                <a-menu>
                  <a-menu-item @click="editPlan(record)">
                    <EditOutlined /> 编辑
                  </a-menu-item>
                  <a-menu-item @click="copyPlan(record)">
                    <CopyOutlined /> 复制
                  </a-menu-item>
                  <a-menu-divider />
                  <a-menu-item @click="deletePlan(record)" danger>
                    <DeleteOutlined /> 删除
                  </a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 创建/编辑计划对话框 -->
    <a-modal
      v-model:open="modalVisible"
      :title="isEdit ? '编辑计划' : '新建计划'"
      width="600px"
      @ok="handleSubmit"
      @cancel="handleCancel"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="计划名称" required>
          <a-input v-model:value="form.name" placeholder="请输入计划名称" />
        </a-form-item>

        <a-form-item label="计划描述">
          <a-textarea v-model:value="form.description" :rows="3" placeholder="计划描述" />
        </a-form-item>

        <a-form-item label="执行顺序">
          <a-radio-group v-model:value="form.execution_order">
            <a-radio value="sequential">串行执行</a-radio>
            <a-radio value="parallel">并行执行</a-radio>
          </a-radio-group>
        </a-form-item>

        <a-form-item label="失败时是否继续">
          <a-switch v-model:checked="form.continue_on_failure" />
          <span style="margin-left: 8px">{{ form.continue_on_failure ? '继续执行' : '停止执行' }}</span>
        </a-form-item>

        <a-form-item label="选择脚本">
          <a-select
            v-model:value="form.script_ids"
            mode="multiple"
            placeholder="选择要包含的脚本"
            style="width: 100%"
            show-search
            :filter-option="filterOption"
          >
            <a-select-option v-for="script in availableScripts" :key="script.id" :value="script.id">
              {{ script.name }}
            </a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="定时执行">
          <a-input v-model:value="form.cron_expression" placeholder="Cron 表达式，如: 0 9 * * *" />
          <template #extra>
            <small>留空表示不使用定时执行</small>
          </template>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import {
  PlusOutlined,
  MoreOutlined,
  EditOutlined,
  CopyOutlined,
  DeleteOutlined
} from '@ant-design/icons-vue'
import { planApi } from '@/api/plan'
import { scriptApi } from '@/api/script'

interface Props {
  projectId: number
  embedMode?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  embedMode: false
})

const loading = ref(false)
const plans = ref<any[]>([])
const availableScripts = ref<any[]>([])

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0
})

const modalVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  name: '',
  description: '',
  execution_order: 'sequential' as 'sequential' | 'parallel',
  continue_on_failure: true,
  script_ids: [] as number[],
  cron_expression: ''
})

const columns = [
  { title: '计划名称', key: 'name', ellipsis: true },
  { title: '脚本数量', key: 'scripts', width: 120 },
  { title: '上次状态', key: 'status', width: 120 },
  { title: '上次运行', key: 'last_run', width: 160 },
  { title: '操作', key: 'actions', width: 160, fixed: 'right' }
]

async function loadPlans() {
  loading.value = true
  try {
    const data = await planApi.getList({ project: props.projectId }) as any
    plans.value = data.results || []
    pagination.total = data.count || 0
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

async function loadScripts() {
  try {
    const data = await scriptApi.getList(props.projectId)
    availableScripts.value = data.results || []
  } catch (error) {
    // 错误已由拦截器处理
  }
}

function showCreateModal() {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, {
    name: '',
    description: '',
    execution_order: 'sequential' as 'sequential' | 'parallel',
    continue_on_failure: true,
    script_ids: [],
    cron_expression: ''
  })
  modalVisible.value = true
}

function editPlan(record: any) {
  isEdit.value = true
  editingId.value = record.id
  Object.assign(form, {
    name: record.name,
    description: record.description,
    execution_order: record.execution_order,
    continue_on_failure: record.continue_on_failure,
    script_ids: record.script_ids || [],
    cron_expression: record.cron_expression || ''
  })
  modalVisible.value = true
}

async function handleSubmit() {
  if (!form.name) {
    message.error('请输入计划名称')
    return
  }
  if (form.script_ids.length === 0) {
    message.error('请选择至少一个脚本')
    return
  }

  loading.value = true
  try {
    const data = {
      project: props.projectId,
      ...form
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

function handleCancel() {
  modalVisible.value = false
}

function viewDetail(_record: any) {
  // TODO: 打开计划详情对话框或跳转
  message.info('详情功能开发中')
}

function runPlan(_record: any) {
  // TODO: 运行计划
  message.info('运行功能开发中')
}

function copyPlan(_record: any) {
  // TODO: 复制计划
  message.info('复制功能开发中')
}

function deletePlan(record: any) {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除计划 "${record.name}" 吗？`,
    onOk: async () => {
      try {
        await planApi.delete(record.id)
        message.success('删除成功')
        loadPlans()
      } catch (error) {
        // 错误已由拦截器处理
      }
    }
  })
}

function filterOption(input: string, option: any): boolean {
  return option.name.toLowerCase().includes(input.toLowerCase())
}

function handleTableChange() {
  // 处理分页变化
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    completed: 'success',
    failed: 'error',
    running: 'processing',
    pending: 'default'
  }
  return colors[status] || 'default'
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    completed: '成功',
    failed: '失败',
    running: '运行中',
    pending: '未执行'
  }
  return labels[status] || status
}

function formatTime(time: string): string {
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadPlans()
  loadScripts()
})

// 暴露刷新方法
defineExpose({
  refresh: loadPlans
})
</script>

<style scoped>
.plan-list-embed {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #E5E7EB;
  background: #FFFFFF;
  color: #1F2937;
}

.list-header span {
  color: #374151;
}

.plan-name {
  color: #1890ff;
  cursor: pointer;
  font-weight: 500;
}

.plan-name:hover {
  text-decoration: underline;
}
</style>
