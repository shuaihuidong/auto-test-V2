<template>
  <div class="script-list-embed">
    <div class="list-header">
      <a-space>
        <span>共 {{ scripts.length }} 个脚本</span>
        <a-divider type="vertical" />
        <a-input
          v-model:value="searchText"
          placeholder="搜索脚本"
          style="width: 200px"
          allow-clear
        >
          <template #prefix><SearchOutlined /></template>
        </a-input>
        <a-select v-model:value="filterType" style="width: 120px" placeholder="类型筛选" allow-clear>
          <a-select-option value="">全部</a-select-option>
          <a-select-option value="web">Web自动化</a-select-option>
          <a-select-option value="mobile">移动端</a-select-option>
          <a-select-option value="api">API测试</a-select-option>
        </a-select>
      </a-space>
      <a-space>
        <a-button @click="openNL2Script">
          <ThunderboltOutlined /> AI 生成
        </a-button>
        <a-button @click="openBatchNL2Script">
          <ThunderboltOutlined /> 批量生成
        </a-button>
        <a-button v-if="!embedMode" type="primary" @click="goToCreate">
          <PlusOutlined /> 新建脚本
        </a-button>
      </a-space>
    </div>

    <a-table
      :columns="columns"
      :data-source="filteredScripts"
      :loading="loading"
      :pagination="false"
      row-key="id"
      :scroll="{ y: 500 }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          <a-tooltip placement="top" :title="record.name">
            <a @click="goToEdit(record)" class="script-name">
              {{ record.name }}
            </a>
          </a-tooltip>
          <a-tag v-if="record.is_module" color="purple" size="small" style="margin-left: 8px">模块</a-tag>
        </template>

        <template v-else-if="column.key === 'type'">
          <a-tag :color="getTypeColor(record.type)">
            {{ getTypeLabel(record.type) }}
          </a-tag>
        </template>

        <template v-else-if="column.key === 'steps'">
          {{ record.step_count }}
        </template>

        <template v-else-if="column.key === 'updated_at'">
          {{ formatTime(record.updated_at) }}
        </template>

        <template v-else-if="column.key === 'actions'">
          <a-space :size="4">
            <a-button type="link" size="small" @click="goToEdit(record)">编辑</a-button>
            <a-button type="link" size="small" @click="runScript(record)">运行</a-button>
            <a-button type="link" size="small" @click="copyScript(record)">
              <CopyOutlined style="margin-right: 2px;" /> 复制
            </a-button>
            <a-dropdown>
              <template #overlay>
                <a-menu>
                  <a-menu-item @click="exportScript(record)">
                    <ExportOutlined /> 导出
                  </a-menu-item>
                  <a-menu-divider />
                  <a-menu-item @click="deleteScript(record)" danger>
                    <DeleteOutlined /> 删除
                  </a-menu-item>
                </a-menu>
              </template>
              <a class="action-btn" @click.prevent>
                <MoreOutlined />
              </a>
            </a-dropdown>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 运行确认对话框 -->
    <a-modal
      v-model:open="runModalVisible"
      title="确认运行"
      width="500px"
      @ok="handleRunConfirm"
      @cancel="runModalVisible = false"
    >
      <a-form layout="vertical">
        <a-form-item label="脚本">
          <a-input :value="selectedScript?.name" disabled />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- NL2Script AI 生成对话框 -->
    <NL2ScriptDialog
      ref="nl2scriptRef"
      :projects="[{ id: projectId, name: projectName }]"
      @saved="loadScripts"
      @edit="goToEditById"
    />

    <!-- 批量 AI 生成对话框 -->
    <NL2ScriptBatchDialog
      ref="batchNL2ScriptRef"
      :projects="[{ id: projectId, name: projectName }]"
      @saved="loadScripts"
      @goToTask="goToBatchTask"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import {
  SearchOutlined,
  PlusOutlined,
  MoreOutlined,
  CopyOutlined,
  ExportOutlined,
  DeleteOutlined,
  ThunderboltOutlined
} from '@ant-design/icons-vue'
import { scriptApi } from '@/api/script'
import { getProject } from '@/api/project'
import { executionApi } from '@/api/execution'

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
const loading = ref(false)
const scripts = ref<Script[]>([])
const searchText = ref('')
const filterType = ref('')

const projectId = props.projectId
const projectName = ref('')

// NL2Script
const nl2scriptRef = ref()
const batchNL2ScriptRef = ref()

function openNL2Script() {
  nl2scriptRef.value?.open()
}

function openBatchNL2Script() {
  batchNL2ScriptRef.value?.open()
}

function goToBatchTask(taskId: number) {
  router.push({ name: 'BatchTaskDetail', params: { id: String(taskId) } })
}

function goToEditById(scriptId: number) {
  router.push(`/script/edit/${scriptId}?from=project-detail`)
}

// 运行确认相关
const runModalVisible = ref(false)
const selectedScript = ref<Script | null>(null)

const columns = [
  { title: '脚本名称', key: 'name', width: 350, ellipsis: true },
  { title: '类型', key: 'type', width: 130 },
  { title: '步骤', key: 'steps', width: 110 },
  { title: '更新时间', key: 'updated_at', width: 180 },
  { title: '操作', key: 'actions', width: 250, fixed: 'right' }
]

const filteredScripts = computed(() => {
  let result = scripts.value

  if (searchText.value) {
    result = result.filter(s => s.name.toLowerCase().includes(searchText.value.toLowerCase()))
  }

  if (filterType.value) {
    result = result.filter(s => s.type === filterType.value)
  }

  return result
})

async function loadScripts() {
  loading.value = true
  try {
    const data = await scriptApi.getList(props.projectId)
    scripts.value = data.results || []
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

function goToCreate() {
  // 从项目详情页来的，使用 from=project-detail
  router.push(`/script/edit?project_id=${props.projectId}&from=project-detail`)
}

function goToEdit(record: Script) {
  // 从项目详情页来的，使用 from=project-detail
  router.push(`/script/edit/${record.id}?from=project-detail`)
}

async function runScript(record: Script) {
  selectedScript.value = record
  runModalVisible.value = true
}

async function handleRunConfirm() {
  if (!selectedScript.value) return

  try {
    await executionApi.create({
      script_id: selectedScript.value.id
    })
    message.success('执行任务已创建')
    runModalVisible.value = false
    router.push('/executions')
  } catch (error) {
    // 错误已由拦截器处理
  }
}

async function copyScript(record: Script) {
  try {
    await scriptApi.duplicate(record.id)
    message.success('复制成功')
    loadScripts()
  } catch (error) {
    // 错误已由拦截器处理
  }
}

function exportScript(_record: Script) {
  // TODO: 实现导出功能
  message.info('导出功能开发中')
}

function deleteScript(record: Script) {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除脚本 "${record.name}" 吗？`,
    onOk: async () => {
      try {
        await scriptApi.delete(record.id)
        message.success('删除成功')
        loadScripts()
      } catch (error) {
        // 错误已由拦截器处理
      }
    }
  })
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

function formatTime(time: string): string {
  const date = new Date(time)
  const now = new Date()
  const diff = Math.floor((now.getTime() - date.getTime()) / 60000)

  if (diff < 1) return '刚刚'
  if (diff < 60) return `${diff}分钟前`
  if (diff < 1440) return `${Math.floor(diff / 60)}小时前`
  return date.toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadScripts()
  loadProjectName()
})

async function loadProjectName() {
  try {
    const project = await getProject(projectId)
    projectName.value = project.name
  } catch (error) {
    // ignore
  }
}

// 暴露刷新方法给父组件
defineExpose({
  refresh: loadScripts
})
</script>

<style scoped>
.script-list-embed {
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

.script-name {
  color: #1890ff;
  cursor: pointer;
  font-weight: 500;
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.script-name:hover {
  color: #40a9ff;
}

.action-btn {
  color: #374151;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}

.action-btn:hover {
  background: rgba(0, 0, 0, 0.06);
}

/* 优化表格列宽 */
:deep(.ant-table) {
  table-layout: fixed;
}

:deep(.ant-table-thead > tr > th) {
  padding: 12px 24px;
}

:deep(.ant-table-tbody > tr > td) {
  padding: 12px 24px;
}

/* 操作按钮样式优化 */
:deep(.ant-btn-link) {
  padding: 4px 8px;
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
