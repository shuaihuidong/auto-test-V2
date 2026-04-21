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
    <div class="nl-input-area">
      <a-textarea
        v-model:value="prompt"
        placeholder="描述你想要执行的测试操作，例如：&#10;打开百度首页，在搜索框输入 playwright，点击搜索按钮"
        :rows="4"
        :disabled="loading"
        @pressEnter="handleGenerate"
      />
      <div class="nl-actions">
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

    <!-- 结果区 -->
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
        <a-space>
          <a-button @click="handleCopyJSON">复制 JSON</a-button>
          <a-button
            v-if="selectedProject && !result.script_id"
            type="primary"
            @click="handleSave"
          >
            保存为脚本
          </a-button>
          <a-button
            v-if="result.script_id"
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
import { ref } from 'vue'
import { message as antMessage } from 'ant-design-vue'
import { ThunderboltOutlined } from '@ant-design/icons-vue'
import { nl2script } from '@/api/script'
import { useRouter } from 'vue-router'

const props = defineProps<{
  projects: { id: number; name: string }[]
}>()

const emit = defineEmits<{
  (e: 'saved', scriptId: number): void
}>()

const router = useRouter()

const visible = ref(false)
const prompt = ref('')
const loading = ref(false)
const result = ref<any>(null)
const errorMsg = ref('')
const selectedProject = ref<number | undefined>(undefined)

function open() {
  visible.value = true
  result.value = null
  errorMsg.value = ''
  prompt.value = ''
}

function handleClose() {
  visible.value = false
}

async function handleGenerate() {
  if (!prompt.value.trim()) return
  loading.value = true
  errorMsg.value = ''
  result.value = null

  try {
    const data: any = { prompt: prompt.value }
    if (selectedProject.value) {
      data.save_to_project = selectedProject.value
      data.script_name = `AI生成 - ${prompt.value.slice(0, 20)}`
    }
    result.value = await nl2script(data)
    if (result.value.script_id) {
      antMessage.success('脚本已自动保存')
    }
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.error || 'AI 生成失败，请检查网络或 API Key 配置'
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!selectedProject.value || !result.value) return
  loading.value = true
  try {
    const res = await nl2script({
      prompt: prompt.value,
      save_to_project: selectedProject.value,
      script_name: `AI生成 - ${prompt.value.slice(0, 20)}`,
    })
    if (res.script_id) {
      antMessage.success('脚本已保存')
      emit('saved', res.script_id)
      result.value = res
    }
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.error || '保存失败'
  } finally {
    loading.value = false
  }
}

function handleEdit() {
  if (result.value?.script_id) {
    router.push(`/script/edit/${result.value.script_id}`)
    handleClose()
  }
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
