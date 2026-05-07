<template>
  <div class="property-form">
    <!-- Step Name -->
    <div class="property-form__field">
      <label class="property-form__label">步骤名称</label>
      <SimpleInput
        v-model="localStep.name"
        placeholder="输入步骤名称"
      />
    </div>

    <!-- Dynamic fields based on step type -->
    <template v-for="schema in paramSchemas" :key="schema.name">
      <div v-if="shouldShowField(schema)" class="property-form__field">
        <label class="property-form__label">
          {{ schema.label }}
          <span v-if="schema.required" class="property-form__required">*</span>
        </label>

        <!-- Text input -->
        <SimpleInput
          v-if="schema.type === 'text' || schema.type === 'textarea'"
          v-model="localStep.params[schema.name]"
          :type="schema.type === 'textarea' ? 'text' : 'text'"
          :placeholder="schema.placeholder"
          :error="getFieldError(schema.name)"
        >
          <template v-if="hasVariableSupport(schema.name)" #suffix>
            <DatabaseOutlined @click="showVariableSelector(schema.name)" />
          </template>
        </SimpleInput>

        <!-- Textarea -->
        <textarea
          v-if="schema.type === 'textarea'"
          v-model="localStep.params[schema.name]"
          :placeholder="schema.placeholder"
          :rows="schema.rows || 4"
          class="property-form__textarea"
        />

        <!-- Number input -->
        <SimpleInput
          v-if="schema.type === 'number'"
          v-model.number="localStep.params[schema.name]"
          type="number"
          :placeholder="schema.placeholder"
          :min="schema.min"
          :max="schema.max"
          :step="schema.step"
        />

        <!-- Select -->
        <SimpleSelect
          v-if="schema.type === 'select'"
          v-model="localStep.params[schema.name]"
          :options="schema.options || []"
          :placeholder="schema.placeholder"
        />

        <!-- Checkbox -->
        <SimpleCheckbox
          v-if="schema.type === 'checkbox'"
          v-model="localStep.params[schema.name]"
          :label="schema.label"
        />

        <!-- Radio group -->
        <div v-if="schema.type === 'radio'" class="property-form__radio-group">
          <label
            v-for="option in schema.options"
            :key="String(option.value)"
            class="property-form__radio"
          >
            <input
              v-model="localStep.params[schema.name]"
              type="radio"
              :value="option.value"
            />
            <span>{{ option.label }}</span>
          </label>
        </div>

        <!-- Locator input -->
        <div v-if="schema.type === 'locator'" class="property-form__locator">
          <SimpleSelect
            v-model="localStep.params.locator!.type"
            :options="locatorTypeOptions"
            placeholder="定位器类型"
            size="small"
          />
          <SimpleInput
            v-model="localStep.params.locator!.value"
            placeholder="定位器值"
          >
            <template #suffix>
              <DatabaseOutlined @click="showVariableSelector('locator.value')" />
            </template>
          </SimpleInput>
        </div>

        <!-- JSON editor -->
        <textarea
          v-if="schema.type === 'json'"
          v-model="jsonValues[schema.name]"
          :placeholder="schema.placeholder"
          :rows="schema.rows || 6"
          class="property-form__json"
          @blur="updateJsonField(schema.name)"
        />

        <!-- Description -->
        <p v-if="schema.description" class="property-form__description">
          {{ schema.description }}
        </p>

        <!-- Error message -->
        <p v-if="getFieldError(schema.name)" class="property-form__error">
          {{ getFieldError(schema.name) }}
        </p>
      </div>
    </template>

    <!-- Advanced / JSON fallback -->
    <details v-if="showAdvanced" class="property-form__advanced">
      <summary>高级参数 (JSON)</summary>
      <textarea
        v-model="advancedJson"
        :rows="10"
        class="property-form__json"
        placeholder='{"key": "value"}'
        @blur="updateAdvancedJson"
      />
    </details>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { DatabaseOutlined } from '@ant-design/icons-vue'
import SimpleInput from './SimpleInput.vue'
import SimpleSelect from './SimpleSelect.vue'
import SimpleCheckbox from './SimpleCheckbox.vue'
import type { TestStep, ParamSchema } from '@/types/script-editor'

interface Props {
  step: TestStep
  paramSchemas?: ParamSchema[]
  showAdvanced?: boolean
}

interface Emits {
  (e: 'update:step', step: TestStep): void
  (e: 'showVariableSelector', field: string): void
}

const props = withDefaults(defineProps<Props>(), {
  paramSchemas: () => [],
  showAdvanced: true
})

const emit = defineEmits<Emits>()

const localStep = ref<TestStep>(JSON.parse(JSON.stringify(props.step)))
const jsonValues = ref<Record<string, string>>({})
const advancedJson = ref('')
const fieldErrors = ref<Record<string, string>>({})
const isUpdatingFromProps = ref(false)

// Locator type options — Playwright locator strategies
const locatorTypeOptions = [
  { label: 'CSS Selector', value: 'css' },
  { label: 'XPath', value: 'xpath' },
  { label: 'ID', value: 'id' },
  { label: '文本内容', value: 'text' },
  { label: '关联标签', value: 'label' },
  { label: '占位文本', value: 'placeholder' },
  { label: 'ARIA角色', value: 'role' },
  { label: '测试ID (data-testid)', value: 'test_id' },
]

// Watch for step changes
watch(() => props.step, (newStep) => {
  isUpdatingFromProps.value = true
  localStep.value = JSON.parse(JSON.stringify(newStep))
  updateJsonValues()
  updateAdvancedJson()
  setTimeout(() => {
    isUpdatingFromProps.value = false
  }, 0)
}, { deep: true })

// Watch local step changes and emit
watch(localStep, (newStep) => {
  if (!isUpdatingFromProps.value) {
    emit('update:step', newStep)
  }
}, { deep: true })

function updateJsonValues() {
  for (const schema of props.paramSchemas) {
    if (schema.type === 'json') {
      const value = localStep.value.params[schema.name]
      jsonValues.value[schema.name] = typeof value === 'object'
        ? JSON.stringify(value, null, 2)
        : value || ''
    }
  }
}

function updateJsonField(fieldName: string) {
  try {
    const value = jsonValues.value[fieldName]
    localStep.value.params[fieldName] = value ? JSON.parse(value) : {}
    delete fieldErrors.value[fieldName]
  } catch (e) {
    fieldErrors.value[fieldName] = 'Invalid JSON format'
  }
}

function updateAdvancedJson() {
  try {
    const parsed = JSON.parse(advancedJson.value)
    localStep.value.params = { ...localStep.value.params, ...parsed }
    delete fieldErrors.value['_advanced']
  } catch (e) {
    fieldErrors.value['_advanced'] = 'Invalid JSON format'
  }
}

function shouldShowField(schema: ParamSchema): boolean {
  if (schema.showIf) {
    return schema.showIf(localStep.value.params)
  }
  return true
}

function getFieldError(fieldName: string): string | undefined {
  return fieldErrors.value[fieldName]
}

function hasVariableSupport(fieldName: string): boolean {
  const variableFields = ['url', 'value', 'text', 'expected', 'name', 'script']
  return variableFields.includes(fieldName)
}

function showVariableSelector(field: string) {
  emit('showVariableSelector', field)
}

// Initialize
updateJsonValues()
updateAdvancedJson()
</script>

<style scoped>
.property-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.property-form__field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.property-form__label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.property-form__required {
  color: var(--color-error);
}

.property-form__textarea,
.property-form__json {
  width: 100%;
  padding: var(--spacing-sm);
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  resize: vertical;
  transition: border-color var(--transition-fast);
}

.property-form__textarea:focus,
.property-form__json:focus {
  outline: none;
  border-color: var(--color-primary);
}

.property-form__locator {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.property-form__radio-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.property-form__radio {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
}

.property-form__radio input {
  cursor: pointer;
}

.property-form__radio span {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.property-form__description {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin: 0;
}

.property-form__error {
  font-size: var(--font-size-xs);
  color: var(--color-error);
  margin: 0;
}

.property-form__advanced {
  margin-top: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.property-form__advanced summary {
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  user-select: none;
}

.property-form__advanced summary:hover {
  color: var(--color-text-primary);
}
</style>
