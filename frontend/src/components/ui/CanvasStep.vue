<template>
  <div
    :class="canvasStepClasses"
    @click="handleClick"
  >
    <!-- Drag Handle -->
    <div class="canvas-step__handle" @dragstart.stop>
      <HolderOutlined />
    </div>

    <!-- Icon -->
    <component :is="icon" class="canvas-step__icon" />

    <!-- Step Info -->
    <div class="canvas-step__info">
      <div class="canvas-step__name">{{ step.name }}</div>
      <div v-if="description" class="canvas-step__description">{{ description }}</div>
    </div>

    <!-- Actions -->
    <div class="canvas-step__actions">
      <SimpleButton
        variant="text"
        size="small"
        @click.stop="handleCopy"
        title="复制"
      >
        <CopyOutlined />
      </SimpleButton>
      <SimpleButton
        variant="text"
        danger
        size="small"
        @click.stop="handleDelete"
        title="删除"
      >
        <DeleteOutlined />
      </SimpleButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { HolderOutlined, CopyOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import SimpleButton from './SimpleButton.vue'
import type { TestStep } from '@/types/script-editor'

interface Props {
  step: TestStep
  selected?: boolean
  disabled?: boolean
}

interface Emits {
  (e: 'click', step: TestStep): void
  (e: 'copy', step: TestStep): void
  (e: 'delete', step: TestStep): void
  (e: 'dragstart', event: DragEvent, step: TestStep): void
}

const props = withDefaults(defineProps<Props>(), {
  selected: false,
  disabled: false
})

const emit = defineEmits<Emits>()

const canvasStepClasses = computed(() => [
  'canvas-step',
  {
    'canvas-step--selected': props.selected,
    'canvas-step--disabled': props.disabled
  }
])

const description = computed(() => {
  // Generate description from step params
  const params = props.step.params
  if (params.url) {
    return `URL: ${params.url}`
  }
  if (params.locator?.value) {
    return `定位: ${params.locator.value}`
  }
  if (params.value) {
    return `值: ${params.value}`
  }
  if (params.text) {
    return `文本: ${params.text}`
  }
  if (params.expected) {
    return `期望: ${params.expected}`
  }
  return ''
})

const icon = computed(() => {
  // Return default icon, parent component can override
  return HolderOutlined
})

function handleClick() {
  if (!props.disabled) {
    emit('click', props.step)
  }
}

function handleCopy() {
  emit('copy', props.step)
}

function handleDelete() {
  emit('delete', props.step)
}

defineExpose({
  step: computed(() => props.step)
})
</script>

<style scoped>
.canvas-step {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  user-select: none;
}

.canvas-step:hover {
  border-color: var(--color-primary);
  background: var(--color-hover);
  box-shadow: var(--shadow-sm);
}

.canvas-step--selected {
  border-color: var(--color-primary);
  background: var(--color-hover);
  box-shadow: 0 0 0 2px var(--color-primary-light);
}

.canvas-step--disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.canvas-step__handle {
  flex-shrink: 0;
  color: var(--color-text-tertiary);
  cursor: grab;
  padding: 2px;
}

.canvas-step__handle:hover {
  color: var(--color-primary);
}

.canvas-step__icon {
  flex-shrink: 0;
  font-size: 18px;
  color: var(--color-primary);
}

.canvas-step__info {
  flex: 1;
  min-width: 0;
}

.canvas-step__name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.canvas-step__description {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 2px;
}

.canvas-step__actions {
  display: flex;
  gap: var(--spacing-xs);
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.canvas-step:hover .canvas-step__actions {
  opacity: 1;
}
</style>
