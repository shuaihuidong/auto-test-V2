<template>
  <a-modal
    v-model:open="visible"
    title="AI 生成测试脚本"
    :width="680"
    :footer="null"
    :destroy-on-close="true"
    @cancel="handleClose"
  >
    <!-- 输入区 -->
    <div v-if="!result" class="nl-input-area">
      <a-textarea
        v-model:value="prompt"
        placeholder="描述你想要执行的测试操作，例如：&#10;打开百度首页，在搜索框输入 playwright，点击搜索按钮"
        :rows="4"
        :disabled="loading"
        @pressEnter="handleGenerate"
      />

      <!-- AI 生成中的友好提示 -->
      <div v-if="loading" class="nl-generating">
        <div class="nl-generating-inner">
          <a-spin size="small" />
          <span class="nl-generating-text">{{ generatingTip }}</span>
        </div>
        <div class="nl-generating-dots">
          <span class="gdot" :class="{ active: genDotIdx >= 0 }"></span>
          <span class="gdot" :class="{ active: genDotIdx >= 1 }"></span>
          <span class="gdot" :class="{ active: genDotIdx >= 2 }"></span>
        </div>
      </div>

      <div class="nl-actions">
        <a-space>
          <a-select
            v-if="projects.length > 0"
            v-model:value="selectedProject"
            placeholder="保存到项目"
            style="width: 200px"
            :disabled="loading"
          >
            <a-select-option v-for="p in projects" :key="p.id" :value="p.id">
              {{ p.name }}
            </a-select-option>
          </a-select>
          <a-button
            type="primary"
            :loading="loading"
            :disabled="!prompt.trim()"
            @click="handleGenerate"
          >
            <template #icon><ThunderboltOutlined /></template>
            生成脚本
          </a-button>
        </a-space>
      </div>
    </div>

    <!-- 结果预览区 -->
    <div v-if="result" class="nl-result-area">
      <a-divider>生成结果</a-divider>

      <div class="nl-meta">
        <a-space>
          <a-tag color="blue">{{ result.model }}</a-tag>
          <a-tag color="green">{{ result.provider }}</a-tag>
          <span class="nl-token-info">
            Token: {{ result.token_usage?.total_tokens || 0 }}
          </span>
        </a-space>
      </div>

      <!-- 步骤预览 -->
      <div class="nl-steps">
        <div
          v-for="(step, idx) in result.steps"
          :key="idx"
          class="nl-step-item"
        >
          <span class="nl-step-index">{{ idx + 1 }}</span>
          <span class="nl-step-type">
            <a-tag :color="stepColor(step.type)">{{ step.type }}</a-tag>
          </span>
          <span class="nl-step-name">{{ step.name }}</span>
          <span v-if="step.params?.locator" class="nl-step-locator">
            {{ formatLocator(step.params.locator) }}
          </span>
          <span v-if="step.params?.value" class="nl-step-value">
            "{{ truncate(step.params.value, 30) }}"
          </span>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="nl-result-actions">
        <a-select
          v-if="projects.length > 1"
          v-model:value="selectedProject"
          placeholder="选择保存到的项目"
          style="width: 220px"
        >
          <a-select-option v-for="p in projects" :key="p.id" :value="p.id">
            {{ p.name }}
          </a-select-option>
        </a-select>
        <a-space>
          <a-button @click="handleCopyJSON">复制 JSON</a-button>
          <a-button @click="handleDiscard">丢弃</a-button>
          <a-button
            v-if="!savedScriptId"
            type="primary"
            :loading="saving"
            @click="handleSave"
          >
            保存
          </a-button>
          <a-button
            v-if="savedScriptId"
            type="primary"
            @click="handleEdit"
          >
            编辑脚本
          </a-button>
        </a-space>
      </div>
    </div>

    <!-- 错误提示 -->
    <a-alert
      v-if="errorMsg"
      :message="errorMsg"
      type="error"
      show-icon
      closable
      class="nl-error"
    />
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from 'vue'
import { message as antMessage } from 'ant-design-vue'
import { ThunderboltOutlined } from '@ant-design/icons-vue'
import { nl2script, nl2scriptSave } from '@/api/script'

const props = defineProps<{
  projects: { id: number; name: string }[]
}>()

const emit = defineEmits<{
  (e: 'saved', scriptId: number): void
  (e: 'edit', scriptId: number): void
}>()

const visible = ref(false)
const prompt = ref('')
const loading = ref(false)
const saving = ref(false)
const result = ref<any>(null)
const errorMsg = ref('')
const selectedProject = ref<number | undefined>(undefined)
const savedScriptId = ref<number | null>(null)

// 动态加载提示
const generatingTips = [
  'AI 正在理解您的测试需求...',
  '正在规划测试步骤和操作流程...',
  '正在为每个操作匹配最佳定位器...',
  '正在生成完整的测试脚本...',
  '即将完成，请稍候...',
]
const genTipIdx = ref(0)
const genDotIdx = ref(-1)
let genTipTimer: ReturnType<typeof setInterval> | null = null
let genDotTimer: ReturnType<typeof setInterval> | null = null

const generatingTip = computed(() => generatingTips[genTipIdx.value % generatingTips.length])

function startGenAnimation() {
  genTipIdx.value = 0
  genDotIdx.value = -1
  genTipTimer = setInterval(() => { genTipIdx.value++ }, 4000)
  genDotTimer = setInterval(() => { genDotIdx.value = (genDotIdx.value + 1) % 3 }, 400)
}

function stopGenAnimation() {
  if (genTipTimer) { clearInterval(genTipTimer); genTipTimer = null }
  if (genDotTimer) { clearInterval(genDotTimer); genDotTimer = null }
}

onBeforeUnmount(() => stopGenAnimation())

function open() {
  visible.value = true
  result.value = null
  errorMsg.value = ''
  prompt.value = ''
  savedScriptId.value = null
  // 当只有一个项目时自动选中
  if (props.projects.length === 1) {
    selectedProject.value = props.projects[0].id
  }
}

function handleClose() {
  visible.value = false
}

async function handleGenerate() {
  if (!prompt.value.trim()) return
  loading.value = true
  errorMsg.value = ''
  result.value = null
  savedScriptId.value = null
  startGenAnimation()

  try {
    result.value = await nl2script({ prompt: prompt.value })
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.error || 'AI 生成失败，请检查网络或 API Key 配置'
  } finally {
    stopGenAnimation()
    loading.value = false
  }
}

async function handleSave() {
  if (!result.value?.steps) return
  if (!selectedProject.value) {
    antMessage.warning('请先选择一个项目')
    return
  }
  saving.value = true
  try {
    const res = await nl2scriptSave({
      steps: result.value.steps,
      project_id: selectedProject.value,
      script_name: `AI生成 - ${prompt.value.slice(0, 20)}`,
      prompt: prompt.value,
    })
    savedScriptId.value = res.script_id
    antMessage.success('脚本已保存')
    emit('saved', res.script_id)
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.error || '保存失败'
  } finally {
    saving.value = false
  }
}

function handleEdit() {
  if (savedScriptId.value) {
    emit('edit', savedScriptId.value)
    handleClose()
  }
}

function handleDiscard() {
  result.value = null
  savedScriptId.value = null
  errorMsg.value = ''
}

function handleCopyJSON() {
  if (!result.value?.steps) return
  navigator.clipboard.writeText(JSON.stringify(result.value.steps, null, 2))
  antMessage.success('已复制到剪贴板')
}

function stepColor(type: string): string {
  const colors: Record<string, string> = {
    goto: 'blue', click: 'orange', input: 'green',
    assert_text: 'purple', wait: 'cyan', screenshot: 'geekblue',
    scroll: 'magenta', refresh: 'gold',
  }
  return colors[type] || 'default'
}

function formatLocator(locator: any): string {
  if (!locator) return ''
  if (typeof locator === 'string') return locator
  const { type, value } = locator
  if (type === 'xpath') return `xpath=${value}`
  if (type === 'id') return `#${value}`
  return value || ''
}

function truncate(str: string, len: number): string {
  return str.length > len ? str.slice(0, len) + '...' : str
}

defineExpose({ open })
</script>

<style scoped>
.nl-input-area {
  margin-bottom: 16px;
}
.nl-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
.nl-generating {
  margin-top: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #e6f4ff 0%, #f0f5ff 100%);
  border-radius: 8px;
  border: 1px solid #bae0ff;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.nl-generating-inner {
  display: flex;
  align-items: center;
  gap: 8px;
}
.nl-generating-text {
  font-size: 13px;
  color: #1677ff;
  font-weight: 500;
}
.nl-generating-dots {
  display: flex;
  gap: 5px;
}
.nl-generating-dots .gdot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #d9d9d9;
  transition: all 0.3s ease;
}
.nl-generating-dots .gdot.active {
  background: #1677ff;
  transform: scale(1.4);
}
.nl-result-area {
  max-height: 400px;
  overflow-y: auto;
}
.nl-meta {
  margin-bottom: 12px;
}
.nl-token-info {
  color: #999;
  font-size: 12px;
}
.nl-steps {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.nl-step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: #fafafa;
  border-radius: 4px;
  font-size: 13px;
}
.nl-step-index {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #e6f4ff;
  color: #1677ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}
.nl-step-name {
  font-weight: 500;
}
.nl-step-locator {
  color: #666;
  font-family: monospace;
  font-size: 12px;
}
.nl-step-value {
  color: #52c41a;
  font-family: monospace;
  font-size: 12px;
}
.nl-result-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.nl-error {
  margin-top: 12px;
}
</style>
