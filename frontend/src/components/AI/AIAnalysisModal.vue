<template>
  <a-modal
    :visible="visible"
    title="AI 智能分析"
    :width="800"
    :footer="null"
    @cancel="close"
  >
    <!-- 加载态 -->
    <div v-if="analyzing" class="analysis-loading">
      <div class="loading-icon-wrap">
        <a-spin size="large" />
      </div>
      <div class="loading-text">{{ loadingTip }}</div>
      <div class="loading-sub">AI 正在逐个分析失败步骤的定位器并推荐替代方案</div>
      <div class="loading-dots">
        <span class="dot" :class="{ active: dotIndex >= 0 }"></span>
        <span class="dot" :class="{ active: dotIndex >= 1 }"></span>
        <span class="dot" :class="{ active: dotIndex >= 2 }"></span>
      </div>
    </div>

    <!-- 错误态 -->
    <div v-else-if="analysisError">
      <a-alert type="error" :message="analysisError" show-icon />
    </div>

    <!-- 结果态 -->
    <div v-else-if="results.length > 0" class="analysis-results">
      <!-- 全选 + 统计 -->
      <div class="results-header">
        <a-checkbox
          :checked="isAllSuccessSelected"
          :indeterminate="isPartialSelected"
          @change="toggleSelectAll"
        >
          全选（{{ selectedCount }}/{{ successCount }} 个可应用）
        </a-checkbox>
        <span class="results-summary">
          共 {{ results.length }} 个失败步骤，{{ successCount }} 个找到替代定位器
        </span>
      </div>

      <!-- 分析结果列表 -->
      <div class="results-list">
        <div
          v-for="item in results"
          :key="item.heal_log_id"
          class="result-item"
          :class="{ 'result-success': item.heal_status === 'success', 'result-failed': item.heal_status !== 'success' }"
        >
          <div class="result-row">
            <a-checkbox
              v-if="item.heal_status === 'success'"
              :checked="item.selected"
              @change="item.selected = !item.selected"
            />
            <span v-else class="result-no-checkbox" />
            <span class="result-step-name">
              步骤 #{{ item.step_index + 1 }}: {{ item.step_name }}
            </span>
            <a-tag :color="item.heal_status === 'success' ? 'success' : 'error'" size="small">
              {{ item.heal_status === 'success' ? '可修复' : '无法修复' }}
            </a-tag>
          </div>

          <!-- 成功：定位器变化详情 -->
          <div v-if="item.heal_status === 'success'" class="result-detail">
            <div class="locator-change">
              <code class="locator-old">{{ item.original_locator }}</code>
              <RightOutlined class="locator-arrow" />
              <code class="locator-new">{{ item.suggested_locator }}</code>
            </div>
            <div class="result-meta">
              <span class="confidence">
                置信度 {{ (item.confidence * 100).toFixed(0) }}%
              </span>
              <span v-if="item.reason" class="reason">{{ item.reason }}</span>
            </div>
          </div>

          <!-- 失败：灰色说明 -->
          <div v-else class="result-detail result-detail-failed">
            <span class="failed-text">
              AI 无法找到合适的替代定位器{{ item.reason ? `: ${item.reason}` : '' }}
            </span>
          </div>
        </div>
      </div>

      <!-- 底部按钮 -->
      <div class="results-footer">
        <a-button @click="close">取消</a-button>
        <a-button
          type="primary"
          :disabled="selectedCount === 0"
          :loading="applying"
          @click="handleApply"
        >
          应用选中建议并编辑脚本
          <template #icon><EditOutlined /></template>
        </a-button>
      </div>
    </div>

    <!-- 空结果 -->
    <div v-else class="analysis-empty">
      <a-empty description="没有找到需要分析的失败步骤" />
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { message as antMessage } from 'ant-design-vue'
import { RightOutlined, EditOutlined } from '@ant-design/icons-vue'
import { batchHealExecution, batchApplyHeal } from '@/api/execution'

interface AnalysisResult {
  heal_log_id: number
  step_index: number
  step_name: string
  heal_status: string
  original_locator: string
  suggested_locator: string
  suggested_locator_platform: { type: string; value: string } | null
  confidence: number
  reason: string
  selected: boolean
}

const props = defineProps<{
  visible: boolean
  executionId: number
  scriptId: number
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'applied', scriptId: number): void
}>()

const analyzing = ref(false)
const results = ref<AnalysisResult[]>([])
const applying = ref(false)
const analysisError = ref('')
const failedCount = ref(0)
const analyzedExecutionId = ref<number | null>(null)

// 动态加载提示
const loadingTips = [
  '正在采集页面元素信息...',
  '正在分析失败步骤的定位器...',
  'AI 正在思考最佳替代方案...',
  '正在验证推荐定位器的可行性...',
  '即将完成分析...',
]
const tipIndex = ref(0)
const dotIndex = ref(-1)
let tipTimer: ReturnType<typeof setInterval> | null = null
let dotTimer: ReturnType<typeof setInterval> | null = null

const loadingTip = computed(() => loadingTips[tipIndex.value % loadingTips.length])

function startLoadingAnimation() {
  tipIndex.value = 0
  dotIndex.value = -1
  tipTimer = setInterval(() => {
    tipIndex.value++
  }, 5000)
  dotTimer = setInterval(() => {
    dotIndex.value = (dotIndex.value + 1) % 3
  }, 400)
}

function stopLoadingAnimation() {
  if (tipTimer) { clearInterval(tipTimer); tipTimer = null }
  if (dotTimer) { clearInterval(dotTimer); dotTimer = null }
}

onBeforeUnmount(() => stopLoadingAnimation())

const successCount = computed(() => results.value.filter(r => r.heal_status === 'success').length)
const selectedCount = computed(() => results.value.filter(r => r.selected).length)
const isAllSuccessSelected = computed(() => {
  const successItems = results.value.filter(r => r.heal_status === 'success')
  return successItems.length > 0 && successItems.every(r => r.selected)
})
const isPartialSelected = computed(() => {
  const successItems = results.value.filter(r => r.heal_status === 'success')
  const selectedSuccess = successItems.filter(r => r.selected)
  return selectedSuccess.length > 0 && selectedSuccess.length < successItems.length
})

function toggleSelectAll() {
  const shouldSelect = !isAllSuccessSelected.value
  results.value.forEach(r => {
    if (r.heal_status === 'success') {
      r.selected = shouldSelect
    }
  })
}

function close() {
  emit('update:visible', false)
}

watch(() => props.executionId, (newExecutionId, oldExecutionId) => {
  if (newExecutionId === oldExecutionId) return
  analyzedExecutionId.value = null
  results.value = []
  analysisError.value = ''
  failedCount.value = 0
})

watch(() => props.visible, async (val) => {
  if (!val) return

  if (analyzedExecutionId.value === props.executionId && results.value.length > 0) {
    return
  }

  if (analyzing.value) return

  analyzing.value = true
  analysisError.value = ''
  results.value = []
  startLoadingAnimation()

  try {
    const res = await batchHealExecution(props.executionId)
    failedCount.value = res.analyzed_count
    results.value = res.analysis_results.map(r => ({
      ...r,
      selected: r.heal_status === 'success',
    }))
    analyzedExecutionId.value = props.executionId
  } catch (e: any) {
    analysisError.value = e?.response?.data?.error || e?.message || '分析失败，请稍后重试'
    analyzedExecutionId.value = props.executionId
  } finally {
    stopLoadingAnimation()
    analyzing.value = false
  }
})

async function handleApply() {
  const ids = results.value.filter(r => r.selected).map(r => r.heal_log_id)
  if (ids.length === 0) return

  applying.value = true
  try {
    const res = await batchApplyHeal(ids)
    antMessage.success(res.message || `已应用 ${res.applied_count} 条修复建议`)
    close()
    emit('applied', res.script_id)
  } catch (e: any) {
    antMessage.error(e?.response?.data?.error || '应用失败')
  } finally {
    applying.value = false
  }
}
</script>

<style scoped>
.analysis-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px 0;
}

.loading-icon-wrap {
  margin-bottom: 8px;
}

.loading-text {
  margin-top: 12px;
  font-size: 15px;
  font-weight: 500;
  color: #1677ff;
  min-height: 24px;
  transition: all 0.3s;
}

.loading-sub {
  margin-top: 8px;
  color: #999;
  font-size: 13px;
}

.loading-dots {
  display: flex;
  gap: 6px;
  margin-top: 16px;
}

.loading-dots .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d9d9d9;
  transition: all 0.3s ease;
}

.loading-dots .dot.active {
  background: #1677ff;
  transform: scale(1.3);
}

.analysis-results {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.results-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.results-summary {
  color: #999;
  font-size: 12px;
  margin-left: auto;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.result-item {
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 12px;
}

.result-success {
  border-color: rgba(82, 196, 26, 0.3);
  background: rgba(82, 196, 26, 0.02);
}

.result-failed {
  border-color: #f0f0f0;
  background: #fafafa;
}

.result-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-no-checkbox {
  width: 16px;
}

.result-step-name {
  font-weight: 500;
  flex: 1;
}

.result-detail {
  margin-top: 8px;
  padding-left: 24px;
}

.result-detail-failed {
  padding-left: 24px;
}

.locator-change {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.locator-old {
  background: rgba(255, 77, 79, 0.1);
  color: #cf1322;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 12px;
  text-decoration: line-through;
}

.locator-new {
  background: rgba(82, 196, 26, 0.1);
  color: #389e0d;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 12px;
}

.locator-arrow {
  color: #fa8c16;
  font-size: 10px;
}

.result-meta {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #666;
}

.confidence {
  color: #1890ff;
  font-weight: 500;
}

.reason {
  color: #999;
}

.failed-text {
  color: #999;
  font-size: 13px;
}

.results-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.analysis-empty {
  padding: 32px 0;
}
</style>
