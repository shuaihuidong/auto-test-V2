<template>
  <div class="script-edit">
    <!-- Type Selection Modal (for new scripts) -->
    <ScriptTypeModal
      v-if="showTypeModal"
      v-model="showTypeModal"
      :default-type="form.type"
      :default-framework="form.framework"
      @confirm="handleTypeSelected"
      @cancel="handleTypeCancel"
    />

    <!-- Execution Monitor -->
    <ExecutionMonitor
      :visible="showMonitor"
      :execution-id="monitorExecutionId"
      :script-name="form.name"
      :total-steps="form.steps?.length || 0"
      :step-names="form.steps?.map((s: any) => s.name || s.type || '未命名步骤')"
      @update:visible="showMonitor = $event"
      @close="showMonitor = false"
    />

    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <SimpleButton @click="goBack">
          <ArrowLeftOutlined /> 返回
        </SimpleButton>
        <h2>{{ isNew ? '新建脚本' : '编辑脚本' }}</h2>
      </div>
      <div class="header-right">
        <SimpleButton @click="handleRun" :disabled="!form.steps?.length" variant="primary">
          <BugOutlined /> 调试
        </SimpleButton>
        <SimpleButton @click="handleSandboxRun" :loading="sandboxRunning" :disabled="sandboxRunning || !form.steps?.length">
          <PlayCircleOutlined /> 沙盒执行
        </SimpleButton>
        <SimpleButton @click="handleSave" :loading="saving">
          <SaveOutlined /> 保存
        </SimpleButton>
      </div>
    </div>

    <!-- Sandbox Result Card -->
    <SimpleCard v-if="showSandboxResult && sandboxResult" class="sandbox-result-card">
      <template #header>
        <div class="card-title">
          <CheckCircleOutlined v-if="!sandboxResult.error && sandboxResult.failed === 0" style="color: var(--color-success)" />
          <CloseCircleOutlined v-else style="color: var(--color-error)" />
          沙盒执行结果
          <a-button type="link" size="small" @click="showSandboxResult = false">关闭</a-button>
        </div>
      </template>
      <div v-if="sandboxResult.error" class="sandbox-error">{{ sandboxResult.error }}</div>
      <template v-else>
        <div class="sandbox-summary">
          <a-tag color="blue">总步骤: {{ sandboxResult.total }}</a-tag>
          <a-tag color="green">通过: {{ sandboxResult.passed }}</a-tag>
          <a-tag color="red">失败: {{ sandboxResult.failed }}</a-tag>
        </div>
        <div class="sandbox-steps">
          <div v-for="(step, idx) in sandboxResult.steps" :key="idx" class="sandbox-step-item" :class="{ 'step-failed': !step.success }">
            <CheckCircleOutlined v-if="step.success" style="color: var(--color-success)" />
            <CloseCircleOutlined v-else style="color: var(--color-error)" />
            <span class="step-index">#{{ (step.index ?? idx) + 1 }}</span>
            <span class="step-name">{{ step.name }}</span>
            <span class="step-type"><a-tag size="small">{{ step.type }}</a-tag></span>
            <span v-if="step.message" class="step-msg">{{ step.message }}</span>
            <span v-if="step.error" class="step-error">{{ step.error }}</span>
          </div>
        </div>
      </template>
    </SimpleCard>

    <div class="edit-content">
      <!-- Basic Info Card -->
      <SimpleCard class="info-card">
        <template #header>
          <div class="card-title">
            <SettingOutlined /> 基本信息
          </div>
        </template>

        <div class="info-form">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">所属项目 <span class="required">*</span></label>
              <a-select
                v-model:value="form.project"
                placeholder="请选择项目"
                :loading="loadingProjects"
                :class="{ 'ant-select-status-error': projectError }"
                style="width: 100%"
                @change="projectError = ''"
              >
                <a-select-option v-for="p in projects" :key="p.id" :value="p.id">
                  {{ p.name }}
                </a-select-option>
              </a-select>
              <div v-if="projectError" class="form-error">{{ projectError }}</div>
            </div>

            <div class="form-group">
              <label class="form-label">脚本名称 <span class="required">*</span></label>
              <SimpleInput
                v-model="form.name"
                placeholder="请输入脚本名称"
                :error="nameError"
              />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">脚本类型</label>
              <div class="type-display">
                <component :is="getTypeIcon(form.type)" class="type-icon" />
                <span>{{ getTypeLabel(form.type) }}</span>
                <SimpleButton
                  v-if="isNew && form.steps.length === 0"
                  variant="text"
                  size="small"
                  @click="showTypeModal = true"
                >
                  修改
                </SimpleButton>
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">测试框架</label>
              <div class="framework-display">
                <span class="framework-badge">{{ form.framework }}</span>
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">描述</label>
              <SimpleInput
                v-model="form.description"
                :type="'text' as any"
                placeholder="请输入脚本描述"
                :rows="2"
              />
            </div>

            <div class="form-group">
              <label class="form-label">设为模块</label>
              <div class="checkbox-wrapper">
                <SimpleCheckbox v-model="form.is_module" label="作为模块复用" />
                <SimpleInput
                  v-if="form.is_module"
                  v-model="form.module_name"
                  placeholder="模块名称"
                  style="margin-top: 8px;"
                />
              </div>
            </div>
          </div>
        </div>
      </SimpleCard>

      <!-- Script Editor Card -->
      <div class="editor-card">
        <ScriptEditor
          v-if="!scriptTypeLoading"
          v-model="form.steps as any"
          :script-type="form.type"
          :framework="form.framework"
          :project-id="form.project"
          :script-id="scriptId ? parseInt(scriptId) : undefined"
          :modules="modules"
          :show-type-selector="isNew && form.steps.length === 0"
          @run="handleRun"
          @type-change="handleTypeChange"
        />
        <div v-else class="loading-container">
          <SkeletonLoader variant="custom" :count="5" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ArrowLeftOutlined,
  SaveOutlined,
  SettingOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  BugOutlined
} from '@ant-design/icons-vue'
import ScriptTypeModal from '@/components/ScriptTypeModal.vue'
import ExecutionMonitor from '@/components/ExecutionMonitor.vue'
import ScriptEditor from '@/components/ScriptEditor/index.vue'
import SimpleButton from '@/components/ui/SimpleButton.vue'
import SimpleInput from '@/components/ui/SimpleInput.vue'
import SimpleCheckbox from '@/components/ui/SimpleCheckbox.vue'
import SimpleCard from '@/components/ui/SimpleCard.vue'
import SkeletonLoader from '@/components/ui/SkeletonLoader.vue'
import { getScript, createScript, updateScript, getScriptModules, sandboxExecute } from '@/api/script'
import { getProjectList } from '@/api/project'
import { createExecution } from '@/api/execution'
import type { ScriptForm } from '@/types/script'

type ScriptType = 'web' | 'mobile' | 'api'
type Framework = 'playwright' | 'appium' | 'httprunner'

const router = useRouter()
const route = useRoute()

const scriptId = route.params.id as string | undefined
const projectId = route.query.project_id as string | undefined
const from = route.query.from as string | undefined
const isNew = computed(() => !scriptId)

const saving = ref(false)
const scriptTypeLoading = ref(false)
const showTypeModal = ref(false)
const modules = ref<any[]>([])
const nameError = ref('')
const projectError = ref('')
const projects = ref<{ id: number; name: string }[]>([])
const loadingProjects = ref(false)

// Sandbox execution
const sandboxRunning = ref(false)
const sandboxResult = ref<any>(null)
const showSandboxResult = ref(false)

// Execution monitor
const showMonitor = ref(false)
const monitorExecutionId = ref(0)

// Track unsaved changes
const hasUnsavedChanges = ref(false)
let originalFormJson = ''

const form = ref<ScriptForm>({
  project: parseInt(projectId || '0'),
  name: '',
  description: '',
  type: 'web',
  framework: 'playwright',
  steps: [],
  is_module: false,
  module_name: '',
  data_driven: false
})

// Watch for form changes to track unsaved changes
watch(() => form.value, (newVal) => {
  const currentJson = JSON.stringify(newVal)
  hasUnsavedChanges.value = currentJson !== originalFormJson
}, { deep: true })

// Show type modal for new scripts without type
onMounted(() => {
  loadModules()
  loadProjects()
  if (!isNew.value) {
    loadScript()
  } else {
    // Show type selection modal for new scripts
    showTypeModal.value = true
  }
})

async function loadScript() {
  if (!scriptId) return
  scriptTypeLoading.value = true
  try {
    const script = await getScript(parseInt(scriptId))
    form.value = {
      project: script.project,
      name: script.name,
      description: script.description,
      type: script.type,
      framework: script.framework,
      steps: script.steps,
      is_module: script.is_module,
      module_name: script.module_name || '',
      data_driven: script.data_driven
    }
    // Record original state after loading
    originalFormJson = JSON.stringify(form.value)
  } catch (error) {
    // Error handled by interceptor
  } finally {
    scriptTypeLoading.value = false
  }
}

async function loadModules() {
  try {
    const res = await getScriptModules()
    modules.value = res || []
  } catch (error) {
    console.error('Failed to load modules:', error)
    modules.value = []
  }
}

async function loadProjects() {
  loadingProjects.value = true
  try {
    const res = await getProjectList()
    projects.value = (res.results || []).map((p: any) => ({ id: p.id, name: p.name }))
  } catch (error) {
    console.error('Failed to load projects:', error)
    projects.value = []
  } finally {
    loadingProjects.value = false
  }
}

function handleTypeSelected(selection: { type: ScriptType; framework: Framework }) {
  form.value.type = selection.type
  form.value.framework = selection.framework
}

function handleTypeCancel() {
  // 用户取消选择，返回项目列表
  goBack()
}

function handleTypeChange(selection: { type: ScriptType; framework: Framework }) {
  form.value.type = selection.type
  form.value.framework = selection.framework
  showTypeModal.value = true
}

function goBack() {
  console.log('[ScriptEdit] goBack called, from:', from, 'project:', form.value.project)
  // 根据 from 参数决定返回到哪里
  if (from === 'all') {
    // 从所有脚本页面来的，返回到所有脚本
    console.log('[ScriptEdit] Returning to all scripts')
    router.push('/scripts')
  } else if (from === 'project-detail' && form.value.project) {
    // 从项目详情页（嵌入模式）来的，返回到项目详情页
    console.log('[ScriptEdit] Returning to project detail:', form.value.project)
    router.push(`/projects/${form.value.project}`)
  } else if ((from === 'project-list' || from === 'project') && form.value.project) {
    // 从项目脚本列表来的，返回到项目详情页（因为用户是从项目管理进入的）
    console.log('[ScriptEdit] Returning to project detail:', form.value.project)
    router.push(`/projects/${form.value.project}`)
  } else if (form.value.project) {
    // 默认返回到项目详情页
    console.log('[ScriptEdit] Returning to default project detail:', form.value.project)
    router.push(`/projects/${form.value.project}`)
  } else {
    console.log('[ScriptEdit] Returning to projects list')
    router.push('/projects')
  }
}

async function handleSave() {
  if (!form.value.name) {
    nameError.value = '请输入脚本名称'
    message.error('请输入脚本名称')
    return
  }

  if (!form.value.project) {
    projectError.value = '请选择项目'
    message.error('请选择项目')
    return
  }

  nameError.value = ''
  projectError.value = ''

  saving.value = true
  try {
    if (isNew.value) {
      await createScript(form.value)
      message.success('创建成功')
      goBack() // 新建脚本后返回列表
    } else {
      await updateScript(parseInt(scriptId!), form.value)
      message.success('保存成功')
      // Update original state after saving
      originalFormJson = JSON.stringify(form.value)
      hasUnsavedChanges.value = false
    }
  } catch (error) {
    // Error handled by interceptor
  } finally {
    saving.value = false
  }
}

async function handleRun() {
  // 验证脚本名称
  if (!form.value.name) {
    nameError.value = '请输入脚本名称'
    message.error('请输入脚本名称')
    return
  }

  if (!form.value.project) {
    projectError.value = '请选择项目'
    message.error('请选择项目')
    return
  }

  if (!form.value.steps || form.value.steps.length === 0) {
    message.error('脚本步骤为空')
    return
  }

  let currentScriptId: number | null = scriptId ? parseInt(scriptId) : null

  // 新建脚本需要先保存
  if (isNew.value) {
    try {
      const created = await createScript(form.value)
      currentScriptId = created.id
      message.success('脚本已保存')
    } catch (error) {
      // Error handled by interceptor
      return
    }
  } else if (hasUnsavedChanges.value) {
    // 已有脚本有未保存修改
    await handleSave()
    if (hasUnsavedChanges.value) return // save failed
  }

  if (!currentScriptId) {
    message.error('脚本 ID 无效，请重新打开编辑')
    return
  }

  try {
    const res = await createExecution({ script_id: currentScriptId })
    monitorExecutionId.value = res.id
    showMonitor.value = true
  } catch (error: any) {
    const errMsg = error?.response?.data?.error || error?.message || '创建执行失败'
    message.error(errMsg)
  }
}

async function handleSandboxRun() {
  const steps = form.value.steps
  if (!steps || steps.length === 0) {
    message.error('脚本步骤为空')
    return
  }

  sandboxRunning.value = true
  sandboxResult.value = null
  showSandboxResult.value = false

  try {
    const res = await sandboxExecute({ steps, headless: true })
    sandboxResult.value = res.results
    showSandboxResult.value = true

    if (res.success) {
      message.success(`执行完成：全部 ${res.results.total} 步通过`)
    } else {
      message.warning(`执行完成：${res.results.passed} 通过，${res.results.failed} 失败`)
    }
  } catch (error: any) {
    const errMsg = error?.response?.data?.error || error?.message || '沙盒执行失败'
    message.error(errMsg)
    sandboxResult.value = { error: errMsg }
    showSandboxResult.value = true
  } finally {
    sandboxRunning.value = false
  }
}

function getTypeLabel(type: ScriptType): string {
  const labels: Record<ScriptType, string> = {
    web: 'Web自动化',
    mobile: '移动端',
    api: 'API测试'
  }
  return labels[type]
}

function getTypeIcon(_type: ScriptType) {
  // Would return appropriate icon component
  return null
}
</script>

<style scoped>
.script-edit {
  max-width: 1600px;
  margin: 0 auto;
  padding: var(--spacing-xl);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.page-header h2 {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.edit-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.info-card {
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.info-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.form-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.required {
  color: var(--color-error);
}

.form-error {
  font-size: var(--font-size-sm);
  color: var(--color-error);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-lg);
}

.type-display,
.framework-display {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.type-icon {
  font-size: 18px;
  color: var(--color-primary);
}

.type-display span {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

.framework-badge {
  padding: 4px 12px;
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  color: #ffffff;
  font-size: var(--font-size-sm);
  font-weight: 600;
  border-radius: var(--radius-sm);
  box-shadow: 0 1px 3px rgba(24, 144, 255, 0.3);
}

.checkbox-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.editor-card {
  min-height: 800px;
}

.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 600px;
  padding: var(--spacing-xl);
}

/* Sandbox Result */
.sandbox-result-card {
  margin-bottom: var(--spacing-md);
}

.sandbox-error {
  color: var(--color-error);
  padding: var(--spacing-sm);
  background: #fff2f0;
  border-radius: var(--radius-sm);
}

.sandbox-summary {
  margin-bottom: var(--spacing-md);
}

.sandbox-steps {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 400px;
  overflow-y: auto;
}

.sandbox-step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: #fafafa;
  border-radius: 4px;
  font-size: 13px;
}

.sandbox-step-item.step-failed {
  background: #fff2f0;
}

.sandbox-step-item .step-index {
  font-weight: 600;
  color: #999;
  min-width: 24px;
}

.sandbox-step-item .step-name {
  font-weight: 500;
}

.sandbox-step-item .step-msg {
  color: #666;
  font-size: 12px;
}

.sandbox-step-item .step-error {
  color: var(--color-error);
  font-size: 12px;
}
</style>
