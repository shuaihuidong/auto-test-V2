<template>
  <div class="variable-manage">
    <div class="page-header">
      <h2>变量管理</h2>
      <a-button type="primary" @click="showCreateModal">
        <PlusOutlined /> 添加变量
      </a-button>
    </div>

    <!-- 筛选条件 -->
    <a-card class="filter-card">
      <a-form layout="inline">
        <a-form-item label="作用域">
          <a-select v-model:value="filters.scope" style="width: 120px" @change="handleScopeChange">
            <a-select-option value="project">项目级</a-select-option>
            <a-select-option value="script">脚本级</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item v-if="filters.scope === 'project'" label="项目">
          <a-select
            v-model:value="filters.project_id"
            style="width: 200px"
            show-search
            :filter-option="filterOption"
            @change="loadVariables"
          >
            <a-select-option value="">全部项目</a-select-option>
            <a-select-option v-for="project in projects" :key="project.id" :value="project.id">
              {{ project.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item v-if="filters.scope === 'script'" label="脚本">
          <a-select
            v-model:value="filters.script_id"
            style="width: 200px"
            show-search
            :filter-option="filterOption"
            @change="loadVariables"
          >
            <a-select-option value="">全部脚本</a-select-option>
            <a-select-option v-for="script in scripts" :key="script.id" :value="script.id">
              {{ script.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="类型">
          <a-select v-model:value="filters.type" style="width: 120px" allow-clear @change="loadVariables">
            <a-select-option value="">全部</a-select-option>
            <a-select-option value="string">字符串</a-select-option>
            <a-select-option value="number">数字</a-select-option>
            <a-select-option value="boolean">布尔值</a-select-option>
            <a-select-option value="json">JSON</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-card>

    <!-- 变量列表 -->
    <a-card>
      <a-table
        :columns="columns"
        :data-source="variables"
        :loading="loading"
        :pagination="pagination"
        row-key="id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <strong>{{ record.name }}</strong>
            <LockFilled v-if="record.is_sensitive" class="sensitive-icon" />
          </template>

          <template v-else-if="column.key === 'value'">
            <span v-if="record.is_sensitive" class="masked-value">******</span>
            <span v-else class="value-display">{{ formatValue(record) }}</span>
            <a-button
              v-if="!record.is_sensitive && record.type === 'json'"
              type="link"
              size="small"
              @click="showValueJson(record)"
            >
              查看
            </a-button>
          </template>

          <template v-else-if="column.key === 'type'">
            <a-tag :color="getTypeColor(record.type)">
              {{ record.type_display }}
            </a-tag>
          </template>

          <template v-else-if="column.key === 'scope'">
            <a-tag :color="record.scope === 'project' ? 'blue' : 'green'">
              {{ record.scope_display }}
            </a-tag>
            <span v-if="record.scope === 'project' && record.project">
              {{ getProjectName(record.project) }}
            </span>
            <span v-if="record.scope === 'script' && record.script">
              {{ getScriptName(record.script) }}
            </span>
          </template>

          <template v-else-if="column.key === 'description'">
            {{ record.description || '-' }}
          </template>

          <template v-else-if="column.key === 'created_by'">
            {{ record.creator_name }}
          </template>

          <template v-else-if="column.key === 'actions'">
            <a-space>
              <a-button type="link" size="small" @click="editVariable(record)">编辑</a-button>
              <a-popconfirm
                title="确定要删除此变量吗？"
                @confirm="deleteVariable(record.id)"
              >
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 创建/编辑变量对话框 -->
    <a-modal
      v-model:open="modalVisible"
      :title="isEdit ? '编辑变量' : '添加变量'"
      width="600px"
      @ok="handleSubmit"
      @cancel="handleCancel"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="作用域" required>
          <a-radio-group v-model:value="form.scope" @change="handleScopeFormChange">
            <a-radio value="project">项目级</a-radio>
            <a-radio value="script">脚本级</a-radio>
          </a-radio-group>
        </a-form-item>

        <a-form-item v-if="form.scope === 'project'" label="所属项目" required>
          <a-select
            v-model:value="form.project"
            show-search
            :filter-option="filterOption"
            placeholder="选择项目"
          >
            <a-select-option v-for="project in projects" :key="project.id" :value="project.id">
              {{ project.name }}
            </a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item v-if="form.scope === 'script'" label="所属脚本" required>
          <a-select
            v-model:value="form.script"
            show-search
            :filter-option="filterOption"
            placeholder="选择脚本"
          >
            <a-select-option v-for="script in scripts" :key="script.id" :value="script.id">
              {{ script.name }}
            </a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="变量名称" required>
          <a-input
            v-model:value="form.name"
            placeholder="${变量名}"
            :disabled="isEdit"
          />
          <template #extra>
            <small>变量名使用 ${变量名} 格式在脚本中引用</small>
          </template>
        </a-form-item>

        <a-form-item label="变量类型" required>
          <a-select v-model:value="form.type" style="width: 100%">
            <a-select-option value="string">字符串</a-select-option>
            <a-select-option value="number">数字</a-select-option>
            <a-select-option value="boolean">布尔值</a-select-option>
            <a-select-option value="json">JSON对象</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="变量值" required>
          <!-- 字符串类型 -->
          <a-input
            v-if="form.type === 'string'"
            v-model:value="form.value"
            placeholder="输入字符串值"
          />
          <!-- 数字类型 -->
          <a-input-number
            v-else-if="form.type === 'number'"
            v-model:value="form.value"
            style="width: 100%"
            placeholder="输入数字"
          />
          <!-- 布尔类型 -->
          <a-select v-else-if="form.type === 'boolean'" v-model:value="form.value">
            <a-select-option :value="true">true</a-select-option>
            <a-select-option :value="false">false</a-select-option>
          </a-select>
          <!-- JSON类型 -->
          <a-textarea
            v-else-if="form.type === 'json'"
            v-model:value="form.json_value"
            :rows="6"
            placeholder='{"key": "value"}'
          />
        </a-form-item>

        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="2" placeholder="变量用途说明" />
        </a-form-item>

        <a-form-item>
          <a-checkbox v-model:checked="form.is_sensitive">
            敏感数据（如密码、Token等，将在列表中脱敏显示）
          </a-checkbox>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- JSON值查看对话框 -->
    <a-modal
      v-model:open="jsonModalVisible"
      title="JSON值查看"
      :footer="null"
      width="600px"
    >
      <pre class="json-display">{{ jsonValueFormatted }}</pre>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, LockFilled } from '@ant-design/icons-vue'
import { variableApi } from '@/api/variable'
import { projectApi } from '@/api/project'
import { getScriptList } from '@/api/script'
import type { Variable } from '@/api/variable'

interface FormState {
  id?: number
  scope: 'global' | 'project' | 'script'
  project: number | null
  script: number | null
  name: string
  type: 'string' | 'number' | 'boolean' | 'json'
  value: any
  json_value: string
  description: string
  is_sensitive: boolean
}

const columns = [
  { title: '变量名', key: 'name', width: 200 },
  { title: '变量值', key: 'value', ellipsis: true },
  { title: '类型', key: 'type', width: 120 },
  { title: '作用域', key: 'scope', width: 200 },
  { title: '描述', key: 'description', ellipsis: true },
  { title: '创建者', key: 'created_by', width: 120 },
  { title: '操作', key: 'actions', width: 140, fixed: 'right' }
]

const loading = ref(false)
const variables = ref<Variable[]>([])
const projects = ref<any[]>([])
const scripts = ref<any[]>([])

const filters = reactive({
  scope: 'project',
  project_id: null as number | null,
  script_id: null as number | null,
  type: ''
})

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

// 表单
const modalVisible = ref(false)
const isEdit = ref(false)
const form = reactive<FormState>({
  scope: 'project',
  project: null,
  script: null,
  name: '',
  type: 'string',
  value: '',
  json_value: '',
  description: '',
  is_sensitive: false
})

// JSON查看
const jsonModalVisible = ref(false)
const jsonValueFormatted = ref('')

function getTypeColor(type: string): string {
  const colors: Record<string, string> = {
    string: 'blue',
    number: 'green',
    boolean: 'orange',
    json: 'purple'
  }
  return colors[type] || 'default'
}

function formatValue(record: Variable): string {
  if (record.type === 'boolean') {
    return String(record.value)
  } else if (record.type === 'json') {
    return '[JSON对象]'
  } else if (record.type === 'number') {
    return String(record.value)
  }
  return record.value || ''
}

function showValueJson(record: Variable) {
  if (record.type === 'json') {
    jsonValueFormatted.value = JSON.stringify(record.value, null, 2)
    jsonModalVisible.value = true
  }
}

function getProjectName(id: number): string {
  const project = projects.value.find(p => p.id === id)
  return project ? project.name : '-'
}

function getScriptName(id: number): string {
  const script = scripts.value.find(s => s.id === id)
  return script ? script.name : '-'
}

function filterOption(input: string, option: any): boolean {
  // option 结构：option 是 { key, value } 对象，而 slot 内容包含 name
  // 需要从 slot 的 props 中获取实际的数据
  if (!option || !option.children) return false
  const text = String(option.children).toLowerCase()
  return text.includes(input.toLowerCase())
}

async function loadVariables() {
  loading.value = true
  try {
    const params: any = {
      scope: filters.scope,
      type: filters.type || undefined
    }

    if (filters.scope === 'project' && filters.project_id) {
      params.project = filters.project_id
    } else if (filters.scope === 'script' && filters.script_id) {
      params.script = filters.script_id
    }

    const res = await variableApi.getList(params) as any
    variables.value = res.results || res || []
    pagination.total = res.count || res.length || 0
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

async function loadProjects() {
  try {
    const res = await projectApi.getList()
    projects.value = res.results || []
  } catch (error) {
    // 错误已由拦截器处理
  }
}

async function loadScripts() {
  try {
    // 获取所有项目的脚本（使用 project=0 来获取所有脚本）
    const res = await getScriptList(0)
    scripts.value = res.results || []
  } catch (error) {
    // 错误已由拦截器处理
  }
}

function handleScopeChange() {
  filters.project_id = null
  filters.script_id = null
  loadVariables()
}

function handleScopeFormChange() {
  // 切换作用域时清空关联
  if (form.scope === 'project') {
    form.script = null
  } else {
    form.project = null
  }
}

function showCreateModal() {
  isEdit.value = false
  Object.assign(form, {
    scope: filters.scope,
    project: filters.scope === 'project' ? (filters.project_id || null) : null,
    script: filters.scope === 'script' ? (filters.script_id || null) : null,
    name: '',
    type: 'string',
    value: '',
    json_value: '',
    description: '',
    is_sensitive: false
  })
  modalVisible.value = true
}

function editVariable(record: Variable) {
  isEdit.value = true
  Object.assign(form, {
    id: record.id,
    scope: record.scope,
    project: record.project,
    script: record.script,
    name: record.name,
    type: record.type,
    value: record.type === 'boolean' ? (record.value === true || record.value === 'true') : record.value,
    json_value: record.type === 'json' ? JSON.stringify(record.value || {}, null, 2) : '',
    description: record.description,
    is_sensitive: record.is_sensitive
  })
  modalVisible.value = true
}

async function handleSubmit() {
  if (!form.name) {
    message.error('请输入变量名称')
    return
  }
  if (form.scope === 'project' && !form.project) {
    message.error('请选择所属项目')
    return
  }
  if (form.scope === 'script' && !form.script) {
    message.error('请选择所属脚本')
    return
  }

  // 处理不同类型的值
  let value: any
  if (form.type === 'json') {
    try {
      value = JSON.parse(form.json_value || '{}')
    } catch {
      message.error('JSON格式错误')
      return
    }
  } else if (form.type === 'number') {
    value = Number(form.value) || 0
  } else if (form.type === 'boolean') {
    // 布尔类型必须有明确的 true/false 值
    if (form.value === true || form.value === false) {
      value = form.value
    } else {
      value = false
    }
  } else {
    // 字符串类型
    value = form.value || ''
  }

  loading.value = true
  try {
    const data = {
      name: form.name,
      value: value,
      type: form.type,
      scope: form.scope,
      project: form.scope === 'project' ? form.project : null,
      script: form.scope === 'script' ? form.script : null,
      description: form.description,
      is_sensitive: form.is_sensitive
    }

    if (isEdit.value && form.id) {
      await variableApi.update(form.id, data)
      message.success('更新成功')
    } else {
      await variableApi.create(data)
      message.success('创建成功')
    }

    modalVisible.value = false
    loadVariables()
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

function handleCancel() {
  modalVisible.value = false
}

async function deleteVariable(id: number) {
  try {
    await variableApi.delete(id)
    message.success('删除成功')
    loadVariables()
  } catch (error) {
    // 错误已由拦截器处理
  }
}

onMounted(() => {
  loadProjects()
  loadScripts()
  loadVariables()
})
</script>

<style scoped>
.variable-manage {
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

.filter-card {
  margin-bottom: 16px;
}

.sensitive-icon {
  margin-left: 8px;
  color: #ff4d4f;
  font-size: 12px;
}

.masked-value {
  color: #999;
  font-family: monospace;
}

.value-display {
  font-family: monospace;
  word-break: break-all;
}

.json-display {
  background: #f5f5f5;
  padding: 16px;
  border-radius: 4px;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
