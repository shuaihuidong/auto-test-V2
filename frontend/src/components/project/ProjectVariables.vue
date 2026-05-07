<template>
  <div class="project-variables">
    <div class="list-header">
      <a-space>
        <span>共 {{ variables.length }} 个变量</span>
      </a-space>
      <a-button type="primary" @click="showCreateModal">
        <PlusOutlined /> 添加变量
      </a-button>
    </div>

    <a-table
      :columns="columns"
      :data-source="variables"
      :loading="loading"
      :pagination="false"
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
        </template>

        <template v-else-if="column.key === 'type'">
          <a-tag :color="getTypeColor(record.type)">
            {{ record.type_display }}
          </a-tag>
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

    <!-- 创建/编辑变量对话框 -->
    <a-modal
      v-model:open="modalVisible"
      :title="isEdit ? '编辑变量' : '添加变量'"
      width="500px"
      @ok="handleSubmit"
      @cancel="handleCancel"
    >
      <a-form :model="form" layout="vertical">
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, LockFilled } from '@ant-design/icons-vue'
import { variableApi } from '@/api/variable'
import type { Variable } from '@/api/variable'

interface Props {
  projectId: number
}

const props = defineProps<Props>()

const loading = ref(false)
const variables = ref<Variable[]>([])

const modalVisible = ref(false)
const isEdit = ref(false)
const form = reactive({
  id: undefined as number | undefined,
  name: '',
  type: 'string',
  value: '' as any,
  json_value: '',
  description: '',
  is_sensitive: false
})

const columns = [
  { title: '变量名', key: 'name', width: 200 },
  { title: '变量值', key: 'value', ellipsis: true },
  { title: '类型', key: 'type', width: 120 },
  { title: '描述', key: 'description', ellipsis: true },
  { title: '创建者', key: 'created_by', width: 120 },
  { title: '操作', key: 'actions', width: 140, fixed: 'right' }
]

async function loadVariables() {
  loading.value = true
  try {
    const data = await variableApi.getByProject(props.projectId)
    variables.value = data
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

function showCreateModal() {
  isEdit.value = false
  Object.assign(form, {
    id: undefined,
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
    name: record.name,
    type: record.type,
    value: record.value,
    json_value: record.type === 'json' ? JSON.stringify(record.value, null, 2) : '',
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

  // 处理不同类型的值
  let value: any = form.value
  if (form.type === 'json') {
    try {
      value = JSON.parse(form.json_value)
    } catch {
      message.error('JSON格式错误')
      return
    }
  } else if (form.type === 'number') {
    value = Number(form.value)
  }

  loading.value = true
  try {
    const data = {
      name: form.name,
      value: value,
      type: form.type as 'string' | 'number' | 'boolean' | 'json',
      scope: 'project' as const,
      project: props.projectId,
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

onMounted(() => {
  loadVariables()
})

defineExpose({
  refresh: loadVariables
})
</script>

<style scoped>
.project-variables {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
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
}
</style>
