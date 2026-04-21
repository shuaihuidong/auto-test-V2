<template>
  <a-modal
    v-model:open="visible"
    title="批量 AI 生成脚本"
    :width="720"
    :footer="null"
    :destroy-on-close="true"
    @cancel="handleClose"
  >
    <!-- 输入区 -->
    <div class="batch-input-area">
      <a-alert type="info" show-icon style="margin-bottom: 12px">
        <template #message>每行一条测试描述，最多 50 条。生成后可选保存到项目。</template>
      </a-alert>
      <a-textarea
        v-model:value="promptsText"
        placeholder="打开百度搜索关键词自动化测试&#10;登录系统验证用户名密码&#10;在商品列表页添加购物车&#10;..."
        :rows="8"
        :disabled="loading"
      />
      <div class="batch-meta">
        <span>{{ promptLines.length }} 条描述</span>
        <a-space>
          <a-select
            v-if="projects.length > 0"
            v-model:value="selectedProject"
            placeholder="保存到项目（可选）"
            allow-clear
            style="width: 200px"
            :disabled="loading"
          >
            <a-select-option v-for="p in projects" :key="p.id" :value="p.id">
              {{ p.name }}
            </a-select-option>
          </a-select>
          <a-button type="primary" :loading="loading" :disabled="promptLines.length === 0" @click="handleGenerate">
            <template #icon><ThunderboltOutlined /></template>
            批量生成 ({{ promptLines.length }})
          </a-button>
        </a-space>
      </div>
    </div>

    <!-- 进度条 -->
    <a-progress v-if="loading" :percent="progress" status="active" style="margin: 16px 0" />

    <!-- 结果区 -->
    <div v-if="results.length > 0" class="batch-results">
      <a-divider>
        生成结果: {{ summary.success }} 成功 / {{ summary.failed }} 失败
        (Token: {{ summary.totalTokens }})
      </a-divider>

      <div class="batch-list">
        <div v-for="(r, idx) in results" :key="idx" class="batch-item" :class="{ 'batch-failed': !r.success }">
          <div class="batch-item-header">
            <span class="batch-item-index">#{{ idx + 1 }}</span>
            <a-tag v-if="r.success" color="green">{{ r.steps?.length || 0 }} 步</a-tag>
            <a-tag v-else color="red">失败</a-tag>
            <span class="batch-item-prompt">{{ truncate(r.prompt, 60) }}</span>
            <a-button v-if="r.success && r.steps?.length" size="small" type="link" @click="toggleExpand(idx)">
              {{ expanded[idx] ? '收起' : '展开' }}
            </a-button>
          </div>
          <div v-if="expanded[idx] && r.steps" class="batch-item-steps">
            <div v-for="(step, si) in r.steps" :key="si" class="batch-step">
              <span class="batch-step-idx">{{ si + 1 }}</span>
              <a-tag :color="stepColor(step.type)" size="small">{{ step.type }}</a-tag>
              <span>{{ step.name }}</span>
            </div>
          </div>
          <div v-if="!r.success" class="batch-item-error">{{ r.error }}</div>
        </div>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { message as antMessage } from 'ant-design-vue'
import { ThunderboltOutlined } from '@ant-design/icons-vue'
import { nl2scriptBatch } from '@/api/script'

const props = defineProps<{
  projects: { id: number; name: string }[]
}>()

const emit = defineEmits<{
  (e: 'saved'): void
}>()

const visible = ref(false)
const promptsText = ref('')
const loading = ref(false)
const results = ref<any[]>([])
const selectedProject = ref<number | undefined>(undefined)
const expanded = ref<Record<number, boolean>>({})
const progress = ref(0)

const promptLines = computed(() =>
  promptsText.value.split('\n').map(l => l.trim()).filter(l => l.length > 0)
)

const summary = computed(() => ({
  success: results.value.filter(r => r.success).length,
  failed: results.value.filter(r => !r.success).length,
  totalTokens: results.value.reduce((sum, r) => sum + (r.token_usage?.total_tokens || 0), 0),
}))

function open() {
  visible.value = true
  results.value = []
  promptsText.value = ''
  expanded.value = {}
  progress.value = 0
}

function handleClose() { visible.value = false }

function toggleExpand(idx: number) {
  expanded.value[idx] = !expanded.value[idx]
}

async function handleGenerate() {
  const lines = promptLines.value
  if (lines.length === 0) return

  loading.value = true
  progress.value = 10
  results.value = []

  try {
    const data: any = { prompts: lines }
    if (selectedProject.value) {
      data.save_to_project = selectedProject.value
    }

    // 模拟进度
    const timer = setInterval(() => {
      if (progress.value < 90) progress.value += 5
    }, 500)

    const res = await nl2scriptBatch(data)
    clearInterval(() => {})
    progress.value = 100

    results.value = res.results || []

    if (res.saved_ids?.length) {
      antMessage.success(`已保存 ${res.saved_ids.length} 个脚本`)
      emit('saved')
    }
  } catch (e: any) {
    antMessage.error(e?.response?.data?.error || '批量生成失败')
  } finally {
    loading.value = false
    setTimeout(() => { progress.value = 0 }, 500)
  }
}

function stepColor(type: string): string {
  const colors: Record<string, string> = {
    goto: 'blue', click: 'orange', input: 'green',
    assert_text: 'purple', wait: 'cyan', screenshot: 'geekblue',
  }
  return colors[type] || 'default'
}

function truncate(str: string, len: number): string {
  return (str || '').length > len ? str.slice(0, len) + '...' : (str || '')
}

defineExpose({ open })
</script>

<style scoped>
.batch-input-area { margin-bottom: 16px }
.batch-meta {
  margin-top: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #666;
  font-size: 13px;
}
.batch-results { max-height: 450px; overflow-y: auto }
.batch-list { display: flex; flex-direction: column; gap: 8px }
.batch-item {
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 8px 12px;
}
.batch-item.batch-failed { border-color: #ffccc7; background: #fff2f0 }
.batch-item-header { display: flex; align-items: center; gap: 8px }
.batch-item-index { font-weight: 600; color: #1677ff; min-width: 28px }
.batch-item-prompt { flex: 1; font-size: 13px }
.batch-item-steps {
  margin-top: 8px;
  padding-left: 36px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.batch-step { display: flex; align-items: center; gap: 6px; font-size: 12px }
.batch-step-idx {
  width: 18px; height: 18px;
  border-radius: 50%;
  background: #e6f4ff; color: #1677ff;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600; flex-shrink: 0;
}
.batch-item-error { color: #cf1322; font-size: 12px; margin-top: 4px }
</style>
