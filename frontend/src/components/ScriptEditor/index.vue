<template>
  <div class="script-editor">
    <!-- Header Toolbar -->
    <div class="editor-header">
      <div class="header-left">
        <SimpleButton
          v-if="showTypeSelector"
          variant="default"
          size="small"
          @click="handleTypeChange"
        >
          <SettingOutlined />
          重新选择类型
        </SimpleButton>
        <div v-else class="type-info">
          <component :is="getTypeIcon(scriptType)" class="type-icon" />
          <span>{{ getTypeLabel(scriptType) }}</span>
          <span class="framework-badge">{{ getFrameworkLabel(framework) }}</span>
        </div>
      </div>

      <div class="header-center">
        <div class="mode-switch">
          <button
            :class="['mode-btn', { active: editorMode === 'visual' }]"
            @click="editorMode = 'visual'"
          >
            可视化模式
          </button>
          <button
            :class="['mode-btn', { active: editorMode === 'json' }]"
            @click="editorMode = 'json'"
          >
            JSON模式
          </button>
        </div>
      </div>

      <div class="header-right">
        <span class="step-count">步骤数: {{ steps.length }}</span>
        <SimpleButton variant="default" @click="handleClear">
          <ClearOutlined />
          清空
        </SimpleButton>
        <SimpleButton variant="primary" @click="$emit('run')">
          <PlayCircleOutlined />
          调试
        </SimpleButton>
      </div>
    </div>

    <!-- Three Column Layout -->
    <div class="editor-body">
      <!-- Left: Step Palette -->
      <div class="step-palette">
        <!-- Search Box -->
        <div class="step-search">
          <SearchOutlined class="search-icon" />
          <input
            v-model="stepSearchQuery"
            type="text"
            placeholder="搜索步骤..."
            class="search-input"
          />
          <SimpleButton
            v-if="stepSearchQuery"
            variant="text"
            size="small"
            class="search-clear"
            @click="stepSearchQuery = ''"
          >
            <CloseOutlined />
          </SimpleButton>
        </div>

        <!-- Step Categories -->
        <div v-for="category in stepCategories" :key="category.name" class="step-category">
          <div class="category-title" @click="toggleCategoryCollapse(category.name)">
            <component
              :is="isCategoryCollapsed(category.name) ? RightOutlined : DownOutlined"
              class="collapse-icon"
            />
            <component :is="category.icon" class="category-icon" />
            {{ category.label }}
            <span class="step-count-badge">{{ category.steps.length }}</span>
          </div>
          <div v-show="!isCategoryCollapsed(category.name)" class="category-items">
            <StepCard
              v-for="step in category.steps"
              :key="step.type"
              :label="step.label"
              :icon="step.icon"
              :description="step.description"
              @dragstart="handleDragStart($event, step)"
            />
          </div>
        </div>
      </div>

      <!-- Center: Canvas Area -->
      <div class="canvas-area" @drop="handleDrop" @dragover.prevent>
        <!-- Visual Mode -->
        <div v-if="editorMode === 'visual'" class="canvas-content">
          <EmptyState
            v-if="steps.length === 0"
            icon="inbox"
            title="画布为空"
            message="将左侧步骤拖拽至此开始编排测试用例"
            size="large"
          >
            <template #action>
              <SimpleButton variant="primary" @click="showHelp">
                查看帮助
              </SimpleButton>
            </template>
          </EmptyState>

          <draggable
            v-else
            v-model="localSteps"
            item-key="id"
            handle=".canvas-step__handle"
            @end="handleDragEnd"
            :fallback-tolerance="3"
          >
            <template #item="{ element: step }">
              <CanvasStep
                :step="step"
                :selected="selectedStepId === step.id"
                @click="selectStep(step)"
                @copy="copyStep"
                @delete="removeStep"
              />
            </template>
          </draggable>
        </div>

        <!-- JSON Mode -->
        <div v-else class="json-editor-container">
          <textarea
            v-model="jsonContent"
            class="json-editor"
            placeholder='{"steps": [...]}'
            @blur="syncFromJson"
          />
          <div v-if="jsonError" class="json-error">
            {{ jsonError }}
          </div>
        </div>
      </div>

      <!-- Right: Property Panel -->
      <div class="property-panel">
        <div class="panel-header">
          <h4>步骤属性</h4>
          <SimpleButton
            v-if="selectedStep"
            variant="text"
            size="small"
            @click="clearSelection"
          >
            <CloseOutlined />
          </SimpleButton>
        </div>

        <div class="panel-body">
          <!-- Variable Selector (shown when active) -->
          <div v-if="variableSelectorVisible" class="variable-selector">
            <div class="variable-header">
              <span><DatabaseOutlined /> 选择变量</span>
              <SimpleButton variant="text" size="small" @click="variableSelectorVisible = false">
                <CloseOutlined />
              </SimpleButton>
            </div>
            <div class="variable-list">
              <div v-if="projectVariables.length > 0" class="variable-group">
                <div class="variable-group-title">项目变量</div>
                <div
                  v-for="variable in projectVariables"
                  :key="variable.id"
                  class="variable-item"
                  @click="insertVariable(variable)"
                >
                  <span class="var-name">{{ variable.name }}</span>
                  <span class="var-type">{{ variable.type_display }}</span>
                  <span class="var-preview">: {{ formatVariablePreview(variable) }}</span>
                </div>
              </div>
              <div v-if="scriptVariables.length > 0" class="variable-group">
                <div class="variable-group-title">脚本变量</div>
                <div
                  v-for="variable in scriptVariables"
                  :key="variable.id"
                  class="variable-item"
                  @click="insertVariable(variable)"
                >
                  <span class="var-name">{{ variable.name }}</span>
                  <span class="var-type">{{ variable.type_display }}</span>
                  <span class="var-preview">: {{ formatVariablePreview(variable) }}</span>
                </div>
              </div>
              <EmptyState
                v-if="projectVariables.length === 0 && scriptVariables.length === 0"
                icon="database"
                message="暂无变量"
                size="small"
              />
            </div>
          </div>

          <!-- Step Form -->
          <PropertyForm
            v-if="selectedStep"
            :step="selectedStep"
            :param-schemas="getParamSchemas(selectedStep.type)"
            @update:step="updateStep"
            @showVariableSelector="showVariableSelectorFor"
          />

          <!-- Empty State -->
          <EmptyState
            v-else
            icon="setting"
            message="请在画布中选择步骤以编辑属性"
            size="medium"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import draggable from 'vuedraggable'

// Icons
import {
  SettingOutlined,
  ClearOutlined,
  PlayCircleOutlined,
  CloseOutlined,
  DatabaseOutlined,
  SearchOutlined,
  DownOutlined,
  RightOutlined
} from '@ant-design/icons-vue'

// Components
import SimpleButton from '@/components/ui/SimpleButton.vue'
import StepCard from '@/components/ui/StepCard.vue'
import CanvasStep from '@/components/ui/CanvasStep.vue'
import PropertyForm from '@/components/ui/PropertyForm.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

// Types & Config
import type { TestStep, ScriptType, Framework, StepType } from '@/types/script-editor'
import { getStepCategories, getDefaultParams } from '@/config/steps'
import type { StepDefinition } from '@/types/script-editor'

interface Variable {
  id: string | number
  name: string
  type_display: string
  is_sensitive?: boolean
  value: any
}

interface Props {
  modelValue: TestStep[]
  scriptType: ScriptType
  framework: Framework
  projectId?: number
  scriptId?: number
  modules?: any[]
  showTypeSelector?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: TestStep[]): void
  (e: 'run'): void
  (e: 'typeChange', selection: { type: ScriptType; framework: Framework }): void
}

const props = withDefaults(defineProps<Props>(), {
  modules: () => [],
  showTypeSelector: false
})

const emit = defineEmits<Emits>()

// Ensure all steps have unique IDs (fix for steps with missing/duplicate IDs)
function ensureUniqueIds(steps: TestStep[]): TestStep[] {
  const idMap = new Map<string, number>()
  return steps.map((step, index) => {
    if (!step.id) {
      return { ...step, id: `step_${Date.now()}_${index}` }
    }
    const count = idMap.get(step.id) || 0
    idMap.set(step.id, count + 1)
    if (count > 0) {
      // Duplicate ID found, generate new unique ID
      return { ...step, id: `step_${Date.now()}_${index}_${Math.random().toString(36).substr(2, 9)}` }
    }
    return step
  })
}

// Local state
const localSteps = ref<TestStep[]>(ensureUniqueIds([...props.modelValue]))
const selectedStepId = ref<string | null>(null)
const selectedStep = ref<TestStep | null>(null)
const editorMode = ref<'visual' | 'json'>('visual')
const jsonContent = ref('')
const jsonError = ref('')

// Clipboard
const clipboard = ref<TestStep | null>(null)

// Variable selector
const variableSelectorVisible = ref(false)
const projectVariables = ref<Variable[]>([])
const scriptVariables = ref<Variable[]>([])
const currentInsertField = ref<string>('')

// Step palette search & collapse
const stepSearchQuery = ref('')
const collapsedCategories = ref<Set<string>>(new Set())
const collapseInitialized = ref(false)

// Initialize collapsed categories
function initCollapsedCategories() {
  if (collapseInitialized.value) return
  const categories = getStepCategories(props.scriptType)
  categories.forEach(cat => {
    collapsedCategories.value.add(cat.name)
  })
  collapseInitialized.value = true
}

// Watch for script type changes to reinitialize
watch(() => props.scriptType, () => {
  collapseInitialized.value = false
  collapsedCategories.value = new Set()
  initCollapsedCategories()
}, { immediate: true })

// Computed properties
const steps = computed({
  get: () => localSteps.value,
  set: (value) => {
    localSteps.value = value
    isLocalUpdate = true
    emit('update:modelValue', value)
  }
})

const stepCategories = computed(() => {
  const categories = getStepCategories(props.scriptType)
  const query = stepSearchQuery.value.toLowerCase().trim()

  if (!query) {
    return categories
  }

  // Filter steps based on search query
  return categories
    .map(category => ({
      ...category,
      steps: category.steps.filter(step =>
        step.label.toLowerCase().includes(query) ||
        step.description?.toLowerCase().includes(query)
      )
    }))
    .filter(category => category.steps.length > 0)
})

// Watch for external changes
let isInitializing = true
let lastKnownValue = JSON.stringify(props.modelValue)
let isLocalUpdate = false

watch(() => props.modelValue, (newValue) => {
  const newValueStr = JSON.stringify(newValue)

  if (isLocalUpdate) {
    isLocalUpdate = false
    lastKnownValue = newValueStr
    return
  }

  if (newValueStr !== lastKnownValue) {
    if (isInitializing) {
      localSteps.value = ensureUniqueIds([...newValue])
      lastKnownValue = newValueStr
      isInitializing = false
    } else {
      if (JSON.stringify(localSteps.value) !== newValueStr) {
        localSteps.value = ensureUniqueIds([...newValue])
        lastKnownValue = newValueStr
      }
    }
  }
}, { deep: true })

// Watch editor mode changes
watch(editorMode, (newMode) => {
  if (newMode === 'json') {
    jsonContent.value = JSON.stringify({ steps: steps.value }, null, 2)
    jsonError.value = ''
  } else {
    syncFromJson()
  }
})

// Methods
function selectStep(step: TestStep) {
  selectedStepId.value = step.id
  selectedStep.value = step
}

function clearSelection() {
  selectedStepId.value = null
  selectedStep.value = null
}

function updateStep(step: TestStep) {
  const index = steps.value.findIndex(s => s.id === step.id)
  if (index !== -1) {
    const newSteps = [...steps.value]
    newSteps[index] = step
    steps.value = newSteps

    if (selectedStepId.value === step.id) {
      selectedStep.value = step
    }
  }
}

function handleDragStart(event: DragEvent, stepDef: StepDefinition) {
  if (event.dataTransfer) {
    event.dataTransfer.setData('application/json', JSON.stringify({
      type: stepDef.type,
      label: stepDef.label
    }))
  }
}

function handleDrop(event: DragEvent) {
  event.preventDefault()
  const data = event.dataTransfer?.getData('application/json')
  if (!data) return

  const stepData = JSON.parse(data)
  // Use more unique ID generation to avoid duplicates
  const newStep: TestStep = {
    id: `step_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    type: stepData.type,
    name: stepData.label,
    params: getDefaultParams(stepData.type, props.scriptType)
  }

  steps.value = [...steps.value, newStep]
  selectStep(newStep)
}

function handleDragEnd() {
  const currentSteps = [...localSteps.value]
  isLocalUpdate = true
  emit('update:modelValue', currentSteps)
  message.success('步骤顺序已更新')
}

function removeStep(step: TestStep) {
  steps.value = steps.value.filter(s => s.id !== step.id)
  if (selectedStepId.value === step.id) {
    clearSelection()
  }
}

function copyStep(step: TestStep) {
  clipboard.value = JSON.parse(JSON.stringify(step))
  // Use more unique ID generation to avoid duplicates
  const copied = clipboard.value!
  const newStep: TestStep = {
    ...copied,
    id: `step_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    name: `${copied.name} (副本)`
  }
  const index = steps.value.findIndex(s => s.id === step.id)
  steps.value.splice(index + 1, 0, newStep)
  selectStep(newStep)
  message.success('步骤已复制')
}

function handleClear() {
  if (steps.value.length === 0) return

  Modal.confirm({
    title: '清空画布',
    content: '确定要清空所有步骤吗？此操作不可撤销。',
    okText: '确认清空',
    cancelText: '取消',
    onOk: () => {
      steps.value = []
      clearSelection()
      message.success('画布已清空')
    }
  })
}

function handleTypeChange() {
  if (steps.value.length > 0) {
    Modal.confirm({
      title: '切换测试类型',
      content: '切换类型将清空当前画布，是否继续？',
      okText: '确认切换',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: () => {
        emit('typeChange', { type: props.scriptType, framework: props.framework })
      }
    })
  } else {
    emit('typeChange', { type: props.scriptType, framework: props.framework })
  }
}

function syncFromJson() {
  try {
    const parsed = JSON.parse(jsonContent.value)
    if (parsed && Array.isArray(parsed.steps)) {
      steps.value = parsed.steps
      jsonError.value = ''
      message.success('JSON已同步')
    } else {
      jsonError.value = 'JSON格式错误: 必须包含 steps 数组'
      message.error(jsonError.value)
    }
  } catch (e: any) {
    jsonError.value = `JSON解析错误: ${e.message}`
    message.error(jsonError.value)
  }
}

function getParamSchemas(stepType: StepType) {
  const categories = getStepCategories(props.scriptType)
  for (const category of categories) {
    const step = category.steps.find(s => s.type === stepType)
    if (step) {
      return step.paramSchema || []
    }
  }
  return []
}

function showVariableSelectorFor(field: string) {
  currentInsertField.value = field
  variableSelectorVisible.value = true
  loadVariables()
}

function insertVariable(_variable: Variable) {
  if (!selectedStep.value) return
  variableSelectorVisible.value = false
}

function formatVariablePreview(variable: Variable): string {
  if (variable.is_sensitive) return '***'
  const value = String(variable.value)
  return value.length > 20 ? value.substring(0, 20) + '...' : value
}

function loadVariables() {
  // Load variables from API
}

function getTypeLabel(type: ScriptType): string {
  const labels: Record<ScriptType, string> = {
    web: 'Web自动化',
    mobile: '移动端',
    api: 'API测试'
  }
  return labels[type]
}

function getFrameworkLabel(framework: Framework): string {
  const labels: Record<Framework, string> = {
    playwright: 'Playwright',
    appium: 'Appium',
    httprunner: 'HttpRunner'
  }
  return labels[framework]
}

function getTypeIcon(_type: ScriptType) {
  return null
}

function showHelp() {
  Modal.info({
    title: '使用帮助',
    content: '从左侧步骤库中拖拽步骤到中间画布，点击步骤编辑属性。'
  })
}

function toggleCategoryCollapse(categoryName: string) {
  if (collapsedCategories.value.has(categoryName)) {
    collapsedCategories.value.delete(categoryName)
  } else {
    collapsedCategories.value.add(categoryName)
  }
}

function isCategoryCollapsed(categoryName: string): boolean {
  return collapsedCategories.value.has(categoryName)
}

// Keyboard shortcuts
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Delete' && selectedStepId.value) {
    const step = steps.value.find(s => s.id === selectedStepId.value)
    if (step) removeStep(step)
  }
}

// Lifecycle
onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  initCollapsedCategories()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.script-editor {
  display: flex;
  flex-direction: column;
  min-height: 700px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
}

/* Header */
.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-primary);
  border-bottom: 1px solid var(--color-border-light);
  gap: var(--spacing-md);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.type-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.type-icon {
  font-size: 18px;
  color: var(--color-primary);
}

.type-info > span:not(.framework-badge) {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.framework-badge {
  padding: 4px 10px;
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  color: #ffffff;
  font-size: var(--font-size-xs);
  font-weight: 600;
  border-radius: var(--radius-sm);
  box-shadow: 0 1px 3px rgba(24, 144, 255, 0.3);
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.mode-switch {
  display: flex;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  padding: 2px;
}

.mode-btn {
  padding: 6px 16px;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.mode-btn.active {
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-sm);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.step-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  margin-right: var(--spacing-sm);
}

/* Body - Three Column Layout */
.editor-body {
  flex: 1;
  display: flex;
}

/* Left: Step Palette */
.step-palette {
  width: 280px;
  background: var(--color-bg-primary);
  border-right: 1px solid var(--color-border-light);
  padding: var(--spacing-md);
}

/* Search Box */
.step-search {
  position: relative;
  display: flex;
  align-items: center;
  margin-bottom: var(--spacing-md);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: 0 var(--spacing-sm);
}

.search-icon {
  font-size: 14px;
  color: var(--color-text-tertiary);
  margin-right: var(--spacing-xs);
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  padding: var(--spacing-sm) 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  outline: none;
}

.search-input::placeholder {
  color: var(--color-text-tertiary);
}

.search-clear {
  margin-left: var(--spacing-xs);
  color: var(--color-text-tertiary);
}

.step-category {
  margin-bottom: var(--spacing-md);
}

.category-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--spacing-sm);
  cursor: pointer;
  user-select: none;
  transition: color var(--transition-fast);
}

.category-title:hover {
  color: var(--color-text-secondary);
}

.collapse-icon {
  font-size: 10px;
  transition: transform var(--transition-fast);
}

.category-icon {
  font-size: 14px;
}

.step-count-badge {
  margin-left: auto;
  padding: 2px 6px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-xs);
  font-size: 10px;
  color: var(--color-text-tertiary);
}

.category-items {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

/* Center: Canvas */
.canvas-area {
  flex: 1;
  background: var(--color-bg-secondary);
  padding: var(--spacing-lg);
}

.canvas-content {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

/* JSON Editor */
.json-editor-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.json-editor {
  flex: 1;
  width: 100%;
  padding: var(--spacing-md);
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  line-height: 1.6;
  color: var(--color-text-primary);
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  resize: none;
}

.json-editor:focus {
  outline: none;
  border-color: var(--color-primary);
}

.json-error {
  margin-top: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-error-bg);
  color: var(--color-error);
  font-size: var(--font-size-sm);
  border-radius: var(--radius-sm);
}

/* Right: Property Panel */
.property-panel {
  width: 320px;
  background: var(--color-bg-primary);
  border-left: 1px solid var(--color-border-light);
  display: flex;
  flex-direction: column;
  max-height: 700px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-light);
}

.panel-header h4 {
  margin: 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
}

/* Variable Selector */
.variable-selector {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-md);
  overflow: hidden;
  border: 1px solid var(--color-border-light);
}

.variable-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-hover);
  border-bottom: 1px solid var(--color-border-light);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.variable-list {
  max-height: 200px;
  overflow-y: auto;
  padding: var(--spacing-sm);
}

.variable-group {
  margin-bottom: var(--spacing-sm);
}

.variable-group:last-child {
  margin-bottom: 0;
}

.variable-group-title {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-primary);
  border-radius: var(--radius-xs);
  margin-bottom: var(--spacing-xs);
  font-weight: var(--font-weight-medium);
}

.variable-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  margin-bottom: var(--spacing-xs);
  cursor: pointer;
  transition: all var(--transition-fast);
  font-size: var(--font-size-xs);
}

.variable-item:hover {
  border-color: var(--color-primary);
  background: var(--color-hover);
}

.var-name {
  font-weight: var(--font-weight-medium);
  color: var(--color-primary);
}

.var-type {
  padding: 1px 4px;
  background: var(--color-hover);
  border-radius: var(--radius-xs);
  font-size: 10px;
  color: var(--color-text-secondary);
}

.var-preview {
  color: var(--color-text-tertiary);
  margin-left: auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Scrollbar styling */
.step-palette::-webkit-scrollbar,
.canvas-area::-webkit-scrollbar,
.property-panel::-webkit-scrollbar,
.variable-list::-webkit-scrollbar {
  width: 6px;
}

.step-palette::-webkit-scrollbar-track,
.canvas-area::-webkit-scrollbar-track,
.property-panel::-webkit-scrollbar-track,
.variable-list::-webkit-scrollbar-track {
  background: transparent;
}

.step-palette::-webkit-scrollbar-thumb,
.canvas-area::-webkit-scrollbar-thumb,
.property-panel::-webkit-scrollbar-thumb,
.variable-list::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 3px;
}

.step-palette::-webkit-scrollbar-thumb:hover,
.canvas-area::-webkit-scrollbar-thumb:hover,
.property-panel::-webkit-scrollbar-thumb:hover,
.variable-list::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-tertiary);
}
</style>
