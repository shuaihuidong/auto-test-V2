<template>
  <div
    :class="inputWrapperClasses"
    @click="focusInput"
  >
    <label v-if="label" class="simple-input__label">
      {{ label }}
      <span v-if="required" class="simple-input__required">*</span>
    </label>

    <div class="simple-input__container">
      <div v-if="$slots.prefix" class="simple-input__prefix">
        <slot name="prefix" />
      </div>

      <input
        ref="inputRef"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        :maxlength="maxlength"
        :class="inputClasses"
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
        @keydown="handleKeydown"
      />

      <div v-if="$slots.suffix || showClearButton" class="simple-input__suffix">
        <slot name="suffix" />
        <span
          v-if="showClearButton && !disabled && !readonly"
          class="simple-input__clear"
          @click.stop="handleClear"
        >
          ×
        </span>
      </div>
    </div>

    <span v-if="error" class="simple-input__error">
      {{ error }}
    </span>

    <span v-if="hint && !error" class="simple-input__hint">
      {{ hint }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, useSlots } from 'vue'

interface Props {
  modelValue?: string | number
  type?: 'text' | 'password' | 'email' | 'number' | 'tel' | 'url'
  label?: string
  placeholder?: string
  disabled?: boolean
  readonly?: boolean
  required?: boolean
  error?: string
  hint?: string
  maxlength?: number
  clearable?: boolean
  size?: 'small' | 'medium' | 'large'
}

interface Emits {
  (e: 'update:modelValue', value: string | number): void
  (e: 'focus', event: FocusEvent): void
  (e: 'blur', event: FocusEvent): void
  (e: 'change', value: string | number): void
  (e: 'clear'): void
  (e: 'keydown', event: KeyboardEvent): void
  (e: 'enter'): void
}

const props = withDefaults(defineProps<Props>(), {
  type: 'text',
  disabled: false,
  readonly: false,
  required: false,
  clearable: false,
  size: 'medium'
})

const emit = defineEmits<Emits>()

const slots = useSlots()
const inputRef = ref<HTMLInputElement>()
const focused = ref(false)

const inputWrapperClasses = computed(() => [
  'simple-input',
  `simple-input--${props.size}`,
  {
    'simple-input--focused': focused.value,
    'simple-input--error': props.error,
    'simple-input--disabled': props.disabled,
    'simple-input--readonly': props.readonly
  }
])

const inputClasses = computed(() => [
  'simple-input__field',
  {
    'simple-input__field--with-prefix': !!slots.prefix,
    'simple-input__field--with-suffix': !!slots.suffix || showClearButton.value
  }
])

const showClearButton = computed(() => {
  return props.clearable && props.modelValue && !props.disabled && !props.readonly
})

function handleInput(event: Event) {
  const target = event.target as HTMLInputElement
  const value = props.type === 'number' ? parseFloat(target.value) || 0 : target.value
  emit('update:modelValue', value)
  emit('change', value)
}

function handleFocus(event: FocusEvent) {
  focused.value = true
  emit('focus', event)
}

function handleBlur(event: FocusEvent) {
  focused.value = false
  emit('blur', event)
}

function handleKeydown(event: KeyboardEvent) {
  emit('keydown', event)
  if (event.key === 'Enter') {
    emit('enter')
  }
}

function handleClear() {
  emit('update:modelValue', '')
  emit('clear')
}

function focusInput() {
  inputRef.value?.focus()
}

defineExpose({
  focus: focusInput,
  blur: () => inputRef.value?.blur()
})
</script>

<style scoped>
.simple-input {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.simple-input__label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.simple-input__required {
  color: var(--color-error);
  margin-left: 2px;
}

.simple-input__container {
  position: relative;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--color-border);
  transition: border-color var(--transition-base);
}

.simple-input--focused .simple-input__container {
  border-bottom-color: var(--color-focus);
}

.simple-input--error .simple-input__container {
  border-bottom-color: var(--color-error);
}

.simple-input--disabled .simple-input__container {
  border-bottom-color: var(--color-border-light);
  opacity: 0.5;
}

.simple-input__field {
  flex: 1;
  padding: 10px 0;
  font-family: var(--font-family);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  background: transparent;
  border: none;
  outline: none;
  transition: all var(--transition-base);
}

.simple-input__field::placeholder {
  color: var(--color-text-disabled);
}

.simple-input__field--with-prefix {
  padding-left: var(--spacing-sm);
}

.simple-input__field--with-suffix {
  padding-right: var(--spacing-sm);
}

.simple-input__prefix,
.simple-input__suffix {
  display: flex;
  align-items: center;
  color: var(--color-text-tertiary);
}

.simple-input__clear {
  cursor: pointer;
  font-size: 18px;
  color: var(--color-text-tertiary);
  transition: color var(--transition-fast);
  padding: 0 4px;
}

.simple-input__clear:hover {
  color: var(--color-text-secondary);
}

/* Sizes */
.simple-input--small .simple-input__field {
  padding: 6px 0;
  font-size: var(--font-size-sm);
}

.simple-input--large .simple-input__field {
  padding: 14px 0;
  font-size: var(--font-size-lg);
}

/* Error & Hint */
.simple-input__error {
  font-size: var(--font-size-xs);
  color: var(--color-error);
}

.simple-input__hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* Disabled */
.simple-input--disabled .simple-input__field {
  cursor: not-allowed;
}

/* Readonly */
.simple-input--readonly .simple-input__field {
  cursor: default;
}
</style>
