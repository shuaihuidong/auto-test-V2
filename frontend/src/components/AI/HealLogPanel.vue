<template>
  <div class="heal-panel">
    <a-spin :spinning="loading">
      <div v-if="logs.length === 0 && !loading" class="heal-empty">
        <a-empty description="暂无自愈记录" />
      </div>

      <div v-else class="heal-list">
        <div v-for="log in logs" :key="log.id" class="heal-item">
          <div class="heal-header">
            <a-space>
              <a-tag :color="statusColor(log.heal_status)">
                {{ statusLabel(log.heal_status) }}
              </a-tag>
              <span class="heal-step">步骤 {{ log.step_index + 1 }}: {{ log.step_name }}</span>
            </a-space>
            <span class="heal-time">{{ formatTime(log.created_at) }}</span>
          </div>

          <div class="heal-body">
            <div class="heal-locator-row">
              <span class="heal-label">原始定位器</span>
              <code class="heal-locator old">{{ log.original_locator }}</code>
            </div>
            <div v-if="log.suggested_locator" class="heal-locator-row">
              <span class="heal-label">推荐替代</span>
              <code class="heal-locator new">{{ log.suggested_locator }}</code>
            </div>
            <div class="heal-details">
              <a-space :size="16">
                <span>策略: <a-tag size="small">{{ strategyLabel(log.heal_strategy) }}</a-tag></span>
                <span>置信度: {{ (log.confidence * 100).toFixed(0) }}%</span>
                <span v-if="log.llm_provider">Provider: {{ log.llm_provider }}</span>
                <span v-if="log.token_consumed">Token: {{ log.token_consumed }}</span>
              </a-space>
            </div>
            <div v-if="log.reason" class="heal-reason">{{ log.reason }}</div>
          </div>

          <div v-if="log.heal_status === 'success' && !log.auto_applied" class="heal-actions">
            <a-button size="small" type="primary" @click="handleApply(log)">
              应用此建议
            </a-button>
          </div>
          <div v-if="log.auto_applied" class="heal-applied">
            <CheckCircleOutlined /> 已自动应用
          </div>
        </div>
      </div>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { message as antMessage } from 'ant-design-vue'
import { CheckCircleOutlined } from '@ant-design/icons-vue'
import { getHealLogs, applyHeal } from '@/api/execution'

const props = defineProps<{
  executionId: number
}>()

const emit = defineEmits<{
  (e: 'applied', logId: number): void
}>()

const logs = ref<any[]>([])
const loading = ref(false)

async function fetchLogs() {
  if (!props.executionId) return
  loading.value = true
  try {
    logs.value = await getHealLogs(props.executionId)
  } catch {
    logs.value = []
  } finally {
    loading.value = false
  }
}

async function handleApply(log: any) {
  try {
    await applyHeal(log.id)
    antMessage.success('自愈建议已应用到脚本')
    log.auto_applied = true
    emit('applied', log.id)
  } catch (e: any) {
    antMessage.error(e?.response?.data?.error || '应用失败')
  }
}

function statusColor(status: string): string {
  return status === 'success' ? 'green' : status === 'failed' ? 'red' : 'orange'
}

function statusLabel(status: string): string {
  return status === 'success' ? '修复成功' : status === 'failed' ? '修复失败' : '待审核'
}

function strategyLabel(strategy: string): string {
  const labels: Record<string, string> = {
    llm_recommend: 'LLM推荐',
    dom_analysis: 'DOM分析',
    rule_based: '规则匹配',
  }
  return labels[strategy] || strategy
}

function formatTime(dateStr: string): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

onMounted(fetchLogs)
watch(() => props.executionId, fetchLogs)

defineExpose({ refresh: fetchLogs })
</script>

<style scoped>
.heal-panel {
  min-height: 100px;
}
.heal-empty {
  padding: 24px;
}
.heal-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.heal-item {
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 12px;
}
.heal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.heal-step {
  font-weight: 500;
}
.heal-time {
  color: #999;
  font-size: 12px;
}
.heal-body {
  font-size: 13px;
}
.heal-locator-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.heal-label {
  color: #666;
  width: 72px;
  flex-shrink: 0;
}
.heal-locator {
  font-family: monospace;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.heal-locator.old {
  background: #fff2f0;
  color: #cf1322;
  text-decoration: line-through;
}
.heal-locator.new {
  background: #f6ffed;
  color: #389e0d;
}
.heal-details {
  margin-top: 8px;
  color: #666;
  font-size: 12px;
}
.heal-reason {
  margin-top: 6px;
  padding: 6px 8px;
  background: #fafafa;
  border-radius: 3px;
  color: #666;
  font-size: 12px;
}
.heal-actions {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}
.heal-applied {
  margin-top: 8px;
  text-align: right;
  color: #52c41a;
  font-size: 13px;
}
</style>
