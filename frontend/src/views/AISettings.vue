<template>
  <div class="ai-settings">
    <div class="page-header">
      <h2>AI 设置</h2>
    </div>

    <a-card :bordered="false">
      <a-tabs v-model:activeKey="activeTab">
        <!-- API 配置 -->
        <a-tab-pane key="api" tab="API 配置">
          <!-- 配置状态摘要 -->
          <a-alert v-if="configStatus" :type="configStatus.configured ? 'success' : 'warning'" show-icon style="margin-bottom: 16px">
            <template #message>
              <span v-if="configStatus.configured">
                AI 服务已配置 — 当前使用 <strong>{{ providerLabel(configStatus.primary_provider) }}</strong>
                <template v-if="configStatus.fallback_provider">
                  ，备用 <strong>{{ providerLabel(configStatus.fallback_provider) }}</strong>
                </template>
              </span>
              <span v-else>
                AI 服务未配置，请设置 <strong>PRIMARY_PROVIDER</strong> 对应的 API Key
              </span>
            </template>
          </a-alert>

          <a-spin :spinning="configLoading">
            <div v-for="category in categories" :key="category.key" class="config-section">
              <h3>{{ category.label }}</h3>
              <a-form layout="vertical">
                <a-row :gutter="16">
                  <a-col :span="24" v-for="item in getSettingsByCategory(category.key)" :key="item.key">
                    <a-form-item :label="item.description || item.key">
                      <a-input-password
                        v-if="item.is_secret"
                        v-model:value="configForm[item.key]"
                        :placeholder="item.is_secret ? '留空则不修改' : ''"
                      />
                      <a-select
                        v-else-if="item.key === 'PRIMARY_PROVIDER' || item.key === 'FALLBACK_PROVIDER'"
                        v-model:value="configForm[item.key]"
                        :placeholder="'留空则使用环境变量默认值'"
                        allow-clear
                      >
                        <a-select-option value="">自动（使用环境变量默认值）</a-select-option>
                        <a-select-option value="openai">OpenAI</a-select-option>
                        <a-select-option value="qwen">通义千问 (Qwen)</a-select-option>
                      </a-select>
                      <a-input
                        v-else
                        v-model:value="configForm[item.key]"
                        :placeholder="'留空则使用环境变量默认值'"
                      />
                    </a-form-item>
                  </a-col>
                </a-row>
              </a-form>
            </div>
            <div class="action-bar">
              <a-button type="primary" :loading="saving" @click="handleSaveConfig">
                保存配置
              </a-button>
            </div>
          </a-spin>
        </a-tab-pane>

        <!-- 自愈提示词 -->
        <a-tab-pane key="healing" tab="自愈提示词">
          <div class="template-header">
            <a-button type="primary" @click="showCreateTemplate('healing')">
              <PlusOutlined /> 新建模板
            </a-button>
          </div>
          <a-table
            :columns="templateColumns"
            :data-source="healingTemplates"
            :loading="templateLoading"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'is_active'">
                <a-tag :color="record.is_active ? 'green' : 'default'">
                  {{ record.is_active ? '已激活' : '未激活' }}
                </a-tag>
              </template>
              <template v-else-if="column.key === 'temperature'">
                {{ record.temperature }}
              </template>
              <template v-else-if="column.key === 'actions'">
                <a-space>
                  <a-button type="link" size="small" @click="showEditTemplate(record)">
                    编辑
                  </a-button>
                  <a-button
                    type="link"
                    size="small"
                    :disabled="record.is_active"
                    @click="handleActivateTemplate(record)"
                  >
                    激活
                  </a-button>
                  <a-popconfirm
                    title="确定删除此模板？"
                    @confirm="handleDeleteTemplate(record)"
                  >
                    <a-button type="link" size="small" danger>删除</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-tab-pane>

        <!-- NL2Script 提示词 -->
        <a-tab-pane key="nl2script" tab="NL2Script 提示词">
          <div class="template-header">
            <a-button type="primary" @click="showCreateTemplate('nl2script')">
              <PlusOutlined /> 新建模板
            </a-button>
          </div>
          <a-table
            :columns="templateColumns"
            :data-source="nl2scriptTemplates"
            :loading="templateLoading"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'is_active'">
                <a-tag :color="record.is_active ? 'green' : 'default'">
                  {{ record.is_active ? '已激活' : '未激活' }}
                </a-tag>
              </template>
              <template v-else-if="column.key === 'temperature'">
                {{ record.temperature }}
              </template>
              <template v-else-if="column.key === 'actions'">
                <a-space>
                  <a-button type="link" size="small" @click="showEditTemplate(record)">
                    编辑
                  </a-button>
                  <a-button
                    type="link"
                    size="small"
                    :disabled="record.is_active"
                    @click="handleActivateTemplate(record)"
                  >
                    激活
                  </a-button>
                  <a-popconfirm
                    title="确定删除此模板？"
                    @confirm="handleDeleteTemplate(record)"
                  >
                    <a-button type="link" size="small" danger>删除</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-tab-pane>

        <!-- 执行引擎 -->
        <a-tab-pane key="execution" tab="执行引擎">
          <a-spin :spinning="engineStatusLoading">
            <div v-if="engineStatus" class="engine-status-section">
              <h3>线程池状态</h3>
              <a-row :gutter="16" style="margin-bottom: 24px">
                <a-col :span="6">
                  <a-statistic title="最大并发数" :value="engineStatus.max_workers" />
                </a-col>
                <a-col :span="6">
                  <a-statistic title="正在执行" :value="engineStatus.active" :value-style="{ color: '#1890ff' }" />
                </a-col>
                <a-col :span="6">
                  <a-statistic title="排队等待" :value="engineStatus.queued" :value-style="{ color: '#faad14' }" />
                </a-col>
                <a-col :span="6">
                  <a-statistic title="空闲槽位" :value="engineStatus.max_workers - engineStatus.active - engineStatus.queued" />
                </a-col>
              </a-row>

              <a-alert
                v-if="engineStatus.needs_restart"
                type="warning"
                show-icon
                style="margin-bottom: 16px"
                message="配置已变更，需要重启服务才能生效"
                description="最大并发数的修改已保存到数据库，但线程池在服务启动时初始化。请重启后端服务使新配置生效。"
              />
            </div>

            <div v-if="getSettingsByCategory('execution').length > 0" class="config-section">
              <h3>并发配置</h3>
              <p class="config-hint">
                设置同时运行的最大测试脚本数。每个脚本会启动一个独立的浏览器实例，约占 80-150MB 内存。
                建议值：4GB 内存 → 3，8GB → 5，16GB → 8。
              </p>
              <a-form layout="vertical">
                <a-row :gutter="16">
                  <a-col :span="12" v-for="item in getSettingsByCategory('execution')" :key="item.key">
                    <a-form-item :label="item.description || item.key">
                      <a-input-number
                        v-model:value="configForm[item.key]"
                        :min="1"
                        :max="20"
                        :step="1"
                        style="width: 100%"
                      />
                    </a-form-item>
                  </a-col>
                </a-row>
              </a-form>
              <div class="action-bar">
                <a-button type="primary" :loading="saving" @click="handleSaveConfig">
                  保存配置
                </a-button>
              </div>
            </div>
          </a-spin>
        </a-tab-pane>
      </a-tabs>
    </a-card>

    <!-- 模板编辑 Modal -->
    <a-modal
      v-model:open="templateModalVisible"
      :title="isEditingTemplate ? '编辑模板' : '新建模板'"
      :confirm-loading="templateSaving"
      @ok="handleSaveTemplate"
      width="800px"
    >
      <a-form :model="templateForm" layout="vertical">
        <a-form-item label="模板名称" required>
          <a-input v-model:value="templateForm.name" placeholder="输入模板名称" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="场景" required>
              <a-select v-model:value="templateForm.scenario" :disabled="isEditingTemplate">
                <a-select-option value="strict">严格模式</a-select-option>
                <a-select-option value="relaxed">宽松模式</a-select-option>
                <a-select-option value="custom">自定义</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Temperature">
              <a-slider v-model:value="templateForm.temperature" :min="0" :max="1" :step="0.1" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="描述">
          <a-textarea v-model:value="templateForm.description" :rows="2" placeholder="模板描述" />
        </a-form-item>
        <a-form-item label="系统提示词" required>
          <a-textarea
            v-model:value="templateForm.system_prompt"
            :rows="12"
            placeholder="输入系统提示词"
            class="prompt-textarea"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import {
  getAISettings,
  updateAISettings,
  checkAIConfig,
  getPromptTemplates,
  createPromptTemplate,
  updatePromptTemplate,
  activatePromptTemplate,
  deletePromptTemplate,
  getExecutionEngineStatus,
  type AISettingItem,
  type PromptTemplate,
  type AIConfigCheck,
  type ExecutionEngineStatus,
} from '@/api/settings'

const activeTab = ref('api')

// ==================== 配置状态 ====================
const configStatus = ref<AIConfigCheck | null>(null)

function providerLabel(provider: string): string {
  const map: Record<string, string> = { openai: 'OpenAI', qwen: '通义千问' }
  return map[provider] || provider
}

async function loadConfigStatus() {
  try {
    configStatus.value = await checkAIConfig()
  } catch {
    // ignore
  }
}

// ==================== API 配置 ====================

const categories = [
  { key: 'provider', label: 'Provider 选择' },
  { key: 'openai', label: 'OpenAI 配置' },
  { key: 'qwen', label: '通义千问配置' },
  { key: 'general', label: '通用参数' },
  { key: 'execution', label: '执行引擎' },
]

// ==================== 执行引擎状态 ====================

const engineStatus = ref<ExecutionEngineStatus | null>(null)
const engineStatusLoading = ref(false)

async function loadEngineStatus() {
  engineStatusLoading.value = true
  try {
    engineStatus.value = await getExecutionEngineStatus()
  } catch {
    // Non-super-admin or service unavailable, ignore
  } finally {
    engineStatusLoading.value = false
  }
}

const configLoading = ref(false)
const saving = ref(false)
const configItems = ref<AISettingItem[]>([])
const configForm = ref<Record<string, string>>({})

function getSettingsByCategory(category: string): AISettingItem[] {
  return configItems.value.filter(item => item.category === category)
}

async function loadAISettings() {
  configLoading.value = true
  try {
    configItems.value = await getAISettings()
    const form: Record<string, string> = {}
    for (const item of configItems.value) {
      form[item.key] = item.value
    }
    configForm.value = form
  } catch {
    // error handled by interceptor
  } finally {
    configLoading.value = false
  }
}

async function handleSaveConfig() {
  saving.value = true
  try {
    const settings = Object.entries(configForm.value).map(([key, value]) => ({
      key,
      value,
    }))
    configItems.value = await updateAISettings(settings)
    // Update form with returned (masked) values
    const form: Record<string, string> = {}
    for (const item of configItems.value) {
      form[item.key] = item.value
    }
    configForm.value = form
    message.success('配置已保存')
    await loadConfigStatus()
    await loadEngineStatus()
  } catch {
    // error handled by interceptor
  } finally {
    saving.value = false
  }
}

// ==================== Prompt 模板 ====================

const templateLoading = ref(false)
const templateSaving = ref(false)
const templateForm = ref({
  name: '',
  scenario: 'custom' as 'custom' | 'strict' | 'relaxed',
  description: '',
  system_prompt: '',
  temperature: 0.3,
  service: 'healing' as 'healing' | 'nl2script',
})
const templateModalVisible = ref(false)
const isEditingTemplate = ref(false)
const editingTemplateId = ref<number | null>(null)

const healingTemplates = ref<PromptTemplate[]>([])
const nl2scriptTemplates = ref<PromptTemplate[]>([])

const templateColumns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '场景', dataIndex: 'scenario', key: 'scenario', customRender: ({ text }: { text: string }) => {
    const map: Record<string, string> = { strict: '严格', relaxed: '宽松', custom: '自定义' }
    return map[text] || text
  }},
  { title: 'Temperature', dataIndex: 'temperature', key: 'temperature' },
  { title: '状态', dataIndex: 'is_active', key: 'is_active' },
  { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at' },
  { title: '操作', key: 'actions', width: 200 },
]

async function loadTemplates() {
  templateLoading.value = true
  try {
    const all = await getPromptTemplates()
    healingTemplates.value = all.filter(t => t.service === 'healing')
    nl2scriptTemplates.value = all.filter(t => t.service === 'nl2script')
  } catch {
    // error handled by interceptor
  } finally {
    templateLoading.value = false
  }
}

function showCreateTemplate(service: string) {
  isEditingTemplate.value = false
  editingTemplateId.value = null
  templateForm.value = {
    name: '',
    scenario: 'custom',
    description: '',
    system_prompt: '',
    temperature: 0.3,
    service: service as 'healing' | 'nl2script',
  }
  templateModalVisible.value = true
}

function showEditTemplate(record: PromptTemplate) {
  isEditingTemplate.value = true
  editingTemplateId.value = record.id
  templateForm.value = {
    name: record.name,
    scenario: record.scenario,
    description: record.description,
    system_prompt: record.system_prompt,
    temperature: record.temperature,
    service: record.service as 'healing' | 'nl2script',
  }
  templateModalVisible.value = true
}

async function handleSaveTemplate() {
  if (!templateForm.value.name || !templateForm.value.system_prompt) {
    message.error('请填写模板名称和系统提示词')
    return
  }

  templateSaving.value = true
  try {
    if (isEditingTemplate.value && editingTemplateId.value) {
      await updatePromptTemplate(editingTemplateId.value, templateForm.value)
      message.success('模板已更新')
    } else {
      await createPromptTemplate(templateForm.value)
      message.success('模板已创建')
    }
    templateModalVisible.value = false
    await loadTemplates()
  } catch {
    // error handled by interceptor
  } finally {
    templateSaving.value = false
  }
}

async function handleActivateTemplate(record: PromptTemplate) {
  try {
    await activatePromptTemplate(record.id)
    message.success('模板已激活')
    await loadTemplates()
  } catch {
    // error handled by interceptor
  }
}

async function handleDeleteTemplate(record: PromptTemplate) {
  try {
    await deletePromptTemplate(record.id)
    message.success('模板已删除')
    await loadTemplates()
  } catch {
    // error handled by interceptor
  }
}

onMounted(() => {
  loadAISettings()
  loadTemplates()
  loadConfigStatus()
  loadEngineStatus()
})
</script>

<style scoped>
.ai-settings {
  padding: 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.config-section {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.config-section h3 {
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 500;
}

.action-bar {
  margin-top: 16px;
  text-align: right;
}

.template-header {
  margin-bottom: 16px;
  text-align: right;
}

.prompt-textarea {
  font-family: monospace;
}

.engine-status-section h3 {
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 500;
}

.config-hint {
  color: var(--color-text-secondary, #999);
  font-size: 13px;
  margin-bottom: 16px;
}
</style>
