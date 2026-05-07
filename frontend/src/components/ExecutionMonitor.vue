<template>
  <div v-if="visible" class="execution-monitor-overlay" @click.self="handleClose">
    <div class="execution-monitor">
      <!-- Header -->
      <div class="monitor-header">
        <div class="header-left">
          <span class="status-icon" :class="statusClass">
            <LoadingOutlined v-if="status === 'running'" spin />
            <CheckCircleFilled v-else-if="status === 'completed'" />
            <CloseCircleFilled v-else-if="status === 'failed'" />
            <ExclamationCircleFilled v-else-if="errorMsg" />
            <ClockCircleOutlined v-else />
          </span>
          <span class="header-title">
            {{ status === 'running' ? '执行中' : status === 'completed' ? '执行完成' : status === 'failed' ? '执行失败' : '准备执行' }}
            <template v-if="scriptName"> - {{ scriptName }}</template>
          </span>
        </div>
        <div class="header-actions">
          <a-button v-if="isDone" type="link" size="small" @click="viewReport">查看报告</a-button>
          <a-button type="link" size="small" @click="handleClose">关闭</a-button>
        </div>
      </div>

      <!-- Progress Bar -->
      <div class="monitor-progress">
        <div class="progress-bar">
          <div class="progress-fill" :style="progressStyle"></div>
        </div>
        <div class="progress-info">
          <span class="progress-percent">{{ progressPercent }}%</span>
          <span class="progress-detail">
            <span class="passed-count">{{ passed }} 通过</span>
            <span v-if="failed > 0" class="failed-count">{{ failed }} 失败</span>
            <span class="step-count">{{ currentStep }}/{{ totalSteps }}步</span>
          </span>
        </div>
      </div>

      <!-- Step List -->
      <div class="monitor-steps">
        <div
          v-for="(stepName, index) in allStepNames"
          :key="index"
          class="step-item"
          :class="getStepClass(index)"
        >
          <!-- Step icon -->
          <span class="step-icon">
            <LoadingOutlined v-if="isStepRunning(index)" spin />
            <CheckCircleFilled v-else-if="isStepPassed(index)" />
            <CloseCircleFilled v-else-if="isStepFailed(index)" />
            <span v-else class="step-pending-dot"></span>
          </span>

          <!-- Step info -->
          <span class="step-index">#{{ index + 1 }}</span>
          <span class="step-name">{{ stepName }}</span>
          <a-tag v-if="getStepResult(index)?.step_type" size="small" class="step-type-tag">
            {{ getStepResult(index)!.step_type }}
          </a-tag>

          <!-- Step duration -->
          <span class="step-duration">
            <template v-if="isStepRunning(index)">执行中...</template>
            <template v-else-if="getStepResult(index)?.duration">
              {{ getStepResult(index)!.duration }}ms
            </template>
            <template v-else-if="index > currentStep">-</template>
          </span>

          <!-- Self-heal badge -->
          <a-tag v-if="getStepResult(index)?.healed" color="orange" size="small" class="heal-badge">
            自愈
          </a-tag>

          <!-- Screenshot thumbnail -->
          <a-image
            v-if="getStepResult(index)?.screenshot"
            :src="getStepResult(index)!.screenshot"
            :width="24"
            :height="24"
            :preview="{ src: getStepResult(index)!.screenshot }"
            class="step-screenshot-thumb"
          />
        </div>

        <!-- Step detail: error -->
        <template v-for="index in stepErrors.keys()" :key="'error-' + index">
          <div v-if="stepErrors.get(index)" class="step-error-detail">
            <div class="error-message">{{ stepErrors.get(index) }}</div>

            <!-- Self-heal info -->
            <div v-if="stepHealInfo.has(index)" class="heal-info">
              <div class="heal-status">
                <LoadingOutlined v-if="stepHealInfo.get(index)!.status === 'analyzing'" spin />
                <CheckCircleFilled v-else-if="stepHealInfo.get(index)!.status === 'success'" />
                <CloseCircleFilled v-else />
                <span class="heal-label">
                  {{ stepHealInfo.get(index)!.status === 'analyzing' ? 'AI 自愈中...' : stepHealInfo.get(index)!.status === 'success' ? 'AI 自愈完成' : 'AI 自愈失败' }}
                </span>
              </div>
              <div v-if="stepHealInfo.get(index)!.original_locator" class="heal-detail">
                <span class="heal-original">原定位器: {{ formatLocator(stepHealInfo.get(index)!.original_locator) }}</span>
                <span v-if="stepHealInfo.get(index)!.suggested_locator" class="heal-arrow">&rarr;</span>
                <span v-if="stepHealInfo.get(index)!.suggested_locator" class="heal-suggested">
                  {{ formatLocator(stepHealInfo.get(index)!.suggested_locator) }}
                  <span v-if="stepHealInfo.get(index)!.confidence" class="heal-confidence">
                    (置信度: {{ ((stepHealInfo.get(index)!.confidence ?? 0) * 100).toFixed(0) }}%)
                  </span>
                </span>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Error banner -->
      <div v-if="errorMsg" class="monitor-error">
        <ExclamationCircleFilled />
        <span>{{ errorMsg }}</span>
      </div>

      <!-- Footer -->
      <div class="monitor-footer">
        <div class="footer-info">
          <template v-if="isDone">
            <span :class="status === 'completed' ? 'footer-success' : 'footer-fail'">
              执行{{ status === 'completed' ? '成功' : '失败' }}
            </span>
            <span class="footer-stats">
              共 {{ totalSteps }} 步, {{ passed }} 通过, {{ failed }} 失败
            </span>
          </template>
          <span v-else class="footer-running">正在执行中...</span>
        </div>
        <div class="footer-actions">
          <SimpleButton @click="handleClose">关闭</SimpleButton>
          <SimpleButton v-if="isDone" variant="primary" @click="viewReport">查看报告</SimpleButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import {
  LoadingOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  ExclamationCircleFilled,
  ClockCircleOutlined,
} from '@ant-design/icons-vue'
import SimpleButton from '@/components/ui/SimpleButton.vue'

interface StepResultData {
  success: boolean
  duration?: number
  error?: string
  message?: string
  healed?: boolean
  original_locator?: any
  suggested_locator?: any
  confidence?: number
  step_type?: string
  screenshot?: string
}

interface HealInfo {
  status: 'analyzing' | 'success' | 'failed'
  original_locator?: any
  suggested_locator?: any
  confidence?: number
}

const props = defineProps<{
  visible: boolean
  executionId: number
  scriptName?: string
  totalSteps: number
  stepNames?: string[]
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'close'): void
}>()

const router = useRouter()

// State
const status = ref<string>('pending')
const total = ref(props.totalSteps)
const currentStep = ref(0)
const passed = ref(0)
const failed = ref(0)
const isDone = ref(false)
const errorMsg = ref('')
const stepResults = ref<Map<number, StepResultData>>(new Map())
const stepErrors = ref<Map<number, string>>(new Map())
const stepHealInfo = ref<Map<number, HealInfo>>(new Map())

let ws: WebSocket | null = null

// Computed
const statusClass = computed(() => `status-${status.value}`)

const allStepNames = computed(() => {
  const names: string[] = []
  for (let i = 0; i < total.value; i++) {
    names.push(props.stepNames?.[i] || `步骤 ${i + 1}`)
  }
  return names
})

const progressPercent = computed(() => {
  if (total.value === 0) return 0
  return Math.round((currentStep.value / total.value) * 100)
})

const progressStyle = computed(() => ({
  width: `${progressPercent.value}%`,
  background: failed.value > 0
    ? 'linear-gradient(90deg, var(--color-success) 0%, var(--color-success) 60%, var(--color-error) 60%, var(--color-error) 100%)'
    : 'var(--color-success)',
}))

// Methods
function getStepResult(index: number): StepResultData | undefined {
  return stepResults.value.get(index)
}

function isStepRunning(index: number): boolean {
  return index === currentStep.value && !stepResults.value.has(index) && !isDone.value
}

function isStepPassed(index: number): boolean {
  const r = stepResults.value.get(index)
  return r?.success === true
}

function isStepFailed(index: number): boolean {
  const r = stepResults.value.get(index)
  return r?.success === false
}

function getStepClass(index: number): string {
  if (isStepPassed(index)) return 'step-passed'
  if (isStepFailed(index)) return 'step-failed'
  if (isStepRunning(index)) return 'step-running'
  return 'step-pending'
}

function formatLocator(locator: any): string {
  if (!locator) return ''
  if (typeof locator === 'string') return locator
  const type = locator.type || ''
  const value = locator.value || ''
  if (type === 'css') return `css=${value}`
  if (type === 'xpath') return `xpath=${value}`
  if (type === 'id') return `#${value}`
  return `${type}=${value}`
}

function handleClose() {
  emit('update:visible', false)
  emit('close')
}

function viewReport() {
  handleClose()
  router.push(`/executions/${props.executionId}`)
}

// WebSocket connection
function connectWS() {
  if (!props.executionId) return

  // Close existing connection
  disconnectWS()

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${location.host}/ws/execution/${props.executionId}/`

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    // Connection established
  }

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      handleMessage(msg)
    } catch (e) {
      console.error('Failed to parse WS message:', e)
    }
  }

  ws.onerror = () => {
    errorMsg.value = 'WebSocket 连接失败'
  }

  ws.onclose = () => {
    // Connection closed
  }
}

function disconnectWS() {
  if (ws) {
    ws.close()
    ws = null
  }
}

function handleMessage(msg: any) {
  switch (msg.type) {
    case 'execution_started':
      total.value = msg.total || props.totalSteps
      status.value = 'running'
      break

    case 'step_result': {
      const index = msg.index as number
      const stepData: StepResultData = {
        success: msg.success,
        duration: msg.duration,
        error: msg.error,
        message: msg.message,
        healed: msg.healed,
        original_locator: msg.original_locator,
        suggested_locator: msg.suggested_locator,
        confidence: msg.confidence,
        step_type: msg.step_type,
        screenshot: msg.screenshot,
      }

      stepResults.value.set(index, stepData)

      if (msg.error) {
        stepErrors.value.set(index, msg.error)
      }

      // Handle healing info
      if (msg.healing) {
        stepHealInfo.value.set(index, {
          status: 'analyzing',
          original_locator: msg.healing.original_locator,
        })
      }

      if (msg.healed) {
        stepHealInfo.value.set(index, {
          status: 'success',
          original_locator: msg.original_locator,
          suggested_locator: msg.suggested_locator,
          confidence: msg.confidence,
        })
        // Remove error for healed step
        stepErrors.value.delete(index)
      }

      if (msg.success) {
        passed.value++
      } else if (!msg.healed) {
        failed.value++
      }

      currentStep.value = index + 1
      break
    }

    case 'execution_completed':
      status.value = msg.status || 'completed'
      isDone.value = true
      break

    case 'execution_error':
      errorMsg.value = msg.error || '执行失败'
      status.value = 'failed'
      isDone.value = true
      break
  }
}

// Watch visibility to connect/disconnect
watch(() => props.visible, (val) => {
  if (val) {
    // Reset state
    status.value = 'pending'
    currentStep.value = 0
    passed.value = 0
    failed.value = 0
    isDone.value = false
    errorMsg.value = ''
    stepResults.value.clear()
    stepErrors.value.clear()
    stepHealInfo.value.clear()
    total.value = props.totalSteps

    nextTick(() => connectWS())
  } else {
    disconnectWS()
  }
})

onUnmounted(() => {
  disconnectWS()
})
</script>

<style scoped>
.execution-monitor-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.execution-monitor {
  width: 680px;
  max-height: 80vh;
  background: var(--color-bg-primary, #fff);
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.monitor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border-light, #f0f0f0);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-icon {
  font-size: 18px;
}

.status-icon.status-running {
  color: var(--color-primary, #1890ff);
}

.status-icon.status-completed {
  color: var(--color-success, #52c41a);
}

.status-icon.status-failed {
  color: var(--color-error, #ff4d4f);
}

.status-icon.status-pending {
  color: var(--color-text-secondary, #999);
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary, #333);
}

.header-actions {
  display: flex;
  gap: 4px;
}

/* Progress */
.monitor-progress {
  padding: 12px 20px;
  border-bottom: 1px solid var(--color-border-light, #f0f0f0);
}

.progress-bar {
  height: 6px;
  background: var(--color-bg-secondary, #f5f5f5);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
  background: var(--color-success, #52c41a);
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-text-secondary, #999);
}

.progress-detail {
  display: flex;
  gap: 12px;
}

.passed-count {
  color: var(--color-success, #52c41a);
}

.failed-count {
  color: var(--color-error, #ff4d4f);
}

/* Step List */
.monitor-steps {
  flex: 1;
  overflow-y: auto;
  padding: 12px 20px;
  max-height: 400px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 4px;
  font-size: 13px;
  margin-bottom: 2px;
  transition: background 0.15s;
}

.step-item.step-passed {
  background: rgba(82, 196, 26, 0.06);
}

.step-item.step-failed {
  background: rgba(255, 77, 79, 0.06);
}

.step-item.step-running {
  background: rgba(24, 144, 255, 0.06);
}

.step-item.step-pending {
  color: var(--color-text-secondary, #bbb);
}

.step-icon {
  font-size: 14px;
  width: 18px;
  text-align: center;
}

.step-passed .step-icon {
  color: var(--color-success, #52c41a);
}

.step-failed .step-icon {
  color: var(--color-error, #ff4d4f);
}

.step-running .step-icon {
  color: var(--color-primary, #1890ff);
}

.step-pending-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-border-light, #d9d9d9);
}

.step-index {
  font-weight: 600;
  color: var(--color-text-secondary, #999);
  min-width: 24px;
}

.step-name {
  flex: 1;
  font-weight: 500;
}

.step-type-tag {
  font-size: 11px;
}

.step-duration {
  font-size: 12px;
  color: var(--color-text-secondary, #999);
  min-width: 60px;
  text-align: right;
}

.heal-badge {
  font-size: 11px;
  margin-left: 4px;
}

.step-screenshot-thumb {
  margin-left: 6px;
  border-radius: 3px;
  object-fit: cover;
  cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

/* Step error detail */
.step-error-detail {
  margin-left: 50px;
  padding: 6px 10px;
  margin-bottom: 6px;
  border-left: 3px solid var(--color-error, #ff4d4f);
  background: rgba(255, 77, 79, 0.04);
  border-radius: 0 4px 4px 0;
}

.error-message {
  font-size: 12px;
  color: var(--color-error, #ff4d4f);
  word-break: break-all;
}

.heal-info {
  margin-top: 6px;
  padding: 6px 8px;
  background: rgba(250, 173, 20, 0.08);
  border-radius: 4px;
  border-left: 3px solid var(--color-warning, #faad14);
}

.heal-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--color-warning, #d48806);
  margin-bottom: 4px;
}

.heal-label {
  font-weight: 500;
}

.heal-detail {
  font-size: 11px;
  color: var(--color-text-secondary, #666);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.heal-original {
  text-decoration: line-through;
  color: var(--color-error, #ff4d4f);
}

.heal-arrow {
  color: var(--color-text-secondary, #999);
}

.heal-suggested {
  color: var(--color-success, #52c41a);
  font-weight: 500;
}

.heal-confidence {
  color: var(--color-text-secondary, #999);
  font-size: 10px;
}

/* Error banner */
.monitor-error {
  padding: 10px 20px;
  background: rgba(255, 77, 79, 0.08);
  color: var(--color-error, #ff4d4f);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Footer */
.monitor-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-top: 1px solid var(--color-border-light, #f0f0f0);
}

.footer-info {
  display: flex;
  gap: 12px;
  font-size: 13px;
}

.footer-success {
  color: var(--color-success, #52c41a);
  font-weight: 600;
}

.footer-fail {
  color: var(--color-error, #ff4d4f);
  font-weight: 600;
}

.footer-stats {
  color: var(--color-text-secondary, #999);
}

.footer-running {
  color: var(--color-primary, #1890ff);
}

.footer-actions {
  display: flex;
  gap: 8px;
}
</style>
