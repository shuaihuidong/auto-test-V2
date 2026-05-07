<template>
  <SimpleModal
    v-model="visible"
    title="选择测试类型"
    subtitle="请选择脚本类型和测试框架"
    size="medium"
  >
    <!-- Script Type Selection -->
    <div class="script-type-selection">
      <h4 class="selection-title">选择脚本类型</h4>
      <div class="type-grid">
        <div
          v-for="typeOption in scriptTypeOptions"
          :key="typeOption.value"
          :class="typeCardClasses(typeOption.value)"
          @click="selectScriptType(typeOption.value)"
        >
          <component :is="getTypeIcon(typeOption.value)" class="type-icon" />
          <span class="type-label">{{ typeOption.label }}</span>
          <span class="type-description">{{ typeOption.description }}</span>
        </div>
      </div>
    </div>

    <!-- Framework Selection -->
    <div v-if="selectedScriptType && frameworkOptions.length > 1" class="framework-selection">
      <h4 class="selection-title">选择测试框架</h4>
      <div class="framework-grid">
        <div
          v-for="frameworkOption in frameworkOptions"
          :key="frameworkOption.value"
          :class="frameworkCardClasses(frameworkOption.value)"
          @click="selectFramework(frameworkOption.value)"
        >
          <component :is="getFrameworkIcon(frameworkOption.value)" class="framework-icon" />
          <span class="framework-label">{{ frameworkOption.label }}</span>
          <span v-if="frameworkOption.description" class="framework-description">
            {{ frameworkOption.description }}
          </span>
        </div>
      </div>
    </div>

    <!-- Auto-selected framework info (when only one option) -->
    <div v-if="selectedScriptType && frameworkOptions.length === 1 && selectedFramework" class="auto-framework-info">
      <a-tag color="blue">
        <component :is="getFrameworkIcon(selectedFramework)" /> {{ frameworkOptions[0].label }}
      </a-tag>
      <span class="auto-hint">已自动选择测试框架</span>
    </div>

    <!-- Error Message -->
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>

    <!-- Footer Actions -->
    <template #footer>
      <SimpleButton variant="default" @click="handleCancel">
        取消
      </SimpleButton>
      <SimpleButton
        variant="primary"
        :disabled="!canConfirm"
        @click="handleConfirm"
      >
        确定
      </SimpleButton>
    </template>
  </SimpleModal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import SimpleModal from './ui/SimpleModal.vue'
import SimpleButton from './ui/SimpleButton.vue'
import {
  GlobalOutlined,
  MobileOutlined,
  ApiOutlined,
  CodeOutlined,
  RocketOutlined
} from '@ant-design/icons-vue'
import type { ScriptType, Framework } from '@/types/script-editor'

interface ScriptTypeOption {
  value: ScriptType
  label: string
  description: string
  icon: string
}

interface FrameworkOption {
  value: Framework
  label: string
  description?: string
  icon: string
}

interface Props {
  modelValue: boolean
  defaultType?: ScriptType
  defaultFramework?: Framework
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm', selection: { type: ScriptType; framework: Framework }): void
  (e: 'cancel'): void
}

const props = withDefaults(defineProps<Props>(), {
  defaultType: undefined,
  defaultFramework: undefined
})

const emit = defineEmits<Emits>()

const visible = ref(props.modelValue)
const selectedScriptType = ref<ScriptType | null>(props.defaultType || null)
const selectedFramework = ref<Framework | null>(props.defaultFramework || null)
const errorMessage = ref('')

// Script type options
const scriptTypeOptions: ScriptTypeOption[] = [
  {
    value: 'web',
    label: 'Web自动化',
    description: '测试 Web 应用的用户界面和功能',
    icon: 'web'
  },
  {
    value: 'mobile',
    label: '移动端自动化',
    description: '测试 iOS 和 Android 原生应用',
    icon: 'mobile'
  },
  {
    value: 'api',
    label: 'API接口测试',
    description: '测试 RESTful API 和 GraphQL 接口',
    icon: 'api'
  }
]

// Framework options for each type
const frameworkOptionsMap: Record<ScriptType, FrameworkOption[]> = {
  web: [
    {
      value: 'playwright',
      label: 'Playwright',
      description: '现代化 Web 测试框架',
      icon: 'playwright'
    }
  ],
  mobile: [
    {
      value: 'appium',
      label: 'Appium',
      description: '跨平台移动应用自动化测试框架',
      icon: 'appium'
    }
  ],
  api: [
    {
      value: 'httprunner',
      label: 'HttpRunner',
      description: '简洁强大的 HTTP API 测试框架',
      icon: 'httprunner'
    }
  ]
}

// Computed properties
const frameworkOptions = computed(() => {
  if (!selectedScriptType.value) return []
  return frameworkOptionsMap[selectedScriptType.value] || []
})

const canConfirm = computed(() => {
  return selectedScriptType.value && selectedFramework.value
})

// Watch for prop changes
watch(() => props.modelValue, (newValue) => {
  visible.value = newValue
  if (newValue) {
    // Reset to defaults when opening
    selectedScriptType.value = props.defaultType || null
    selectedFramework.value = props.defaultFramework || null
    errorMessage.value = ''
  }
})

watch(visible, (newValue) => {
  emit('update:modelValue', newValue)
  // When modal is closed without selection, emit cancel event
  if (!newValue && !canConfirm.value) {
    emit('cancel')
  }
})

// Methods
function selectScriptType(type: ScriptType) {
  selectedScriptType.value = type
  // Auto-select framework if only one option available
  const options = frameworkOptionsMap[type]
  if (options.length === 1) {
    selectedFramework.value = options[0].value
  } else {
    selectedFramework.value = null
  }
  errorMessage.value = ''
}

function selectFramework(framework: Framework) {
  selectedFramework.value = framework
  errorMessage.value = ''
}

function typeCardClasses(type: ScriptType) {
  return [
    'type-card',
    {
      'type-card--selected': selectedScriptType.value === type
    }
  ]
}

function frameworkCardClasses(framework: Framework) {
  return [
    'framework-card',
    {
      'framework-card--selected': selectedFramework.value === framework
    }
  ]
}

function getTypeIcon(type: ScriptType) {
  const iconMap: Record<ScriptType, any> = {
    web: GlobalOutlined,
    mobile: MobileOutlined,
    api: ApiOutlined
  }
  return iconMap[type] || GlobalOutlined
}

function getFrameworkIcon(framework: Framework) {
  const iconMap: Record<Framework, any> = {
    playwright: RocketOutlined,
    appium: MobileOutlined,
    httprunner: CodeOutlined
  }
  return iconMap[framework] || CodeOutlined
}

function handleConfirm() {
  if (!canConfirm.value) {
    errorMessage.value = '请选择脚本类型和测试框架'
    return
  }

  emit('confirm', {
    type: selectedScriptType.value!,
    framework: selectedFramework.value!
  })

  // Close modal
  visible.value = false
  errorMessage.value = ''
}

function handleCancel() {
  emit('cancel')
  visible.value = false
  errorMessage.value = ''
}

// Expose methods
defineExpose({
  open: () => {
    visible.value = true
  },
  close: () => {
    visible.value = false
  },
  reset: () => {
    selectedScriptType.value = props.defaultType || null
    selectedFramework.value = props.defaultFramework || null
    errorMessage.value = ''
  }
})
</script>

<style scoped>
.script-type-selection,
.framework-selection {
  margin-bottom: var(--spacing-lg);
}

.selection-title {
  margin: 0 0 var(--spacing-md) 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.type-grid,
.framework-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-md);
}

.type-card,
.framework-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--spacing-lg) var(--spacing-md);
  background: var(--color-bg-secondary);
  border: 2px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-base);
  text-align: center;
}

.type-card:hover,
.framework-card:hover {
  border-color: var(--color-primary);
  background: var(--color-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.type-card--selected,
.framework-card--selected {
  border-color: var(--color-primary);
  background: var(--color-hover);
  box-shadow: 0 0 0 2px var(--color-primary-light);
}

.type-icon,
.framework-icon {
  font-size: 32px;
  color: var(--color-primary);
  margin-bottom: var(--spacing-sm);
}

.type-label,
.framework-label {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

.type-description,
.framework-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  line-height: 1.4;
}

.framework-grid {
  grid-template-columns: repeat(2, 1fr);
}

.error-message {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-error-bg);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-md);
  color: var(--color-error);
  font-size: var(--font-size-sm);
  text-align: center;
}

.auto-framework-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-lg);
}

.auto-hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}
</style>
