<template>
  <a-modal
    v-model:open="visible"
    title="批量 AI 生成脚本"
    :width="720"
    :footer="null"
    :destroy-on-close="true"
    @cancel="handleClose"
  >
    <!-- 阶段一：输入生成 -->
    <div v-if="results.length === 0" class="batch-input-area">
      <!-- 输入模式切换 -->
      <a-radio-group v-model:value="inputMode" style="margin-bottom: 12px" :disabled="loading">
        <a-radio-button value="text">手动输入</a-radio-button>
        <a-radio-button value="file">文件导入</a-radio-button>
      </a-radio-group>

      <!-- 手动输入模式 -->
      <template v-if="inputMode === 'text'">
        <a-alert type="info" show-icon style="margin-bottom: 12px">
          <template #message>每行一条测试描述，最多 50 条。生成后可预览、审查、选择保存。</template>
        </a-alert>
        <a-textarea
          v-model:value="promptsText"
          placeholder="打开百度搜索关键词自动化测试&#10;登录系统验证用户名密码&#10;在商品列表页添加购物车&#10;..."
          :rows="8"
          :disabled="loading"
        />
        <div class="batch-meta">
          <span>{{ promptLines.length }} 条描述</span>
          <a-button type="primary" :loading="loading" :disabled="promptLines.length === 0" @click="handleGenerate">
            <template #icon><ThunderboltOutlined /></template>
            批量生成 ({{ promptLines.length }})
          </a-button>
        </div>
      </template>

      <!-- 文件导入模式 -->
      <template v-if="inputMode === 'file'">
        <a-upload-dragger
          :before-upload="handleFileSelect"
          :show-upload-list="false"
          accept=".csv,.xlsx,.xls"
          :disabled="uploading"
        >
          <p class="ant-upload-drag-icon">
            <inbox-outlined />
          </p>
          <p class="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p class="ant-upload-hint">支持 .xlsx / .xls / .csv 文件，最多 50 行，10MB 以内</p>
        </a-upload-dragger>

        <a-spin :spinning="uploading" tip="正在解析文件...">
          <!-- 文件信息 & 列映射 -->
          <template v-if="parsedFile">
            <div class="file-info">
              <a-tag color="blue">{{ parsedFile.file_name }}</a-tag>
              <span>{{ parsedFile.total_rows }} 行 &times; {{ parsedFile.columns.length }} 列</span>
              <a-tag v-if="parsedFile.total_rows > 50" color="orange">仅取前 50 行</a-tag>
            </div>

            <!-- 列映射表 -->
            <div class="column-mapping">
              <div class="mapping-title">列映射 (请为每列选择角色)</div>
              <a-table
                :columns="mappingTableColumns"
                :data-source="mappingTableData"
                :pagination="false"
                size="small"
                row-key="column"
                bordered
              >
                <template #bodyCell="{ column: col, record }">
                  <template v-if="col.key === 'role'">
                    <a-select
                      v-model:value="columnMapping[record.column]"
                      style="width: 140px"
                      @change="onMappingChange"
                    >
                      <a-select-option value="ignore">忽略</a-select-option>
                      <a-select-option value="prompt">
                        <span style="color: #1677ff">测试描述</span>
                        <span style="color: #999; font-size: 11px"> (必选)</span>
                      </a-select-option>
                      <a-select-option value="name">脚本名称</a-select-option>
                      <a-select-option value="description">描述</a-select-option>
                      <a-select-option value="tags">标签</a-select-option>
                    </a-select>
                  </template>
                </template>
              </a-table>
            </div>

            <!-- 映射验证 -->
            <a-alert
              v-if="!hasPromptMapping"
              type="warning"
              show-icon
              style="margin-top: 12px"
              message="请至少将一列映射为「测试描述」角色"
            />

            <!-- 数据预览 -->
            <div v-if="previewPrompts.length > 0" class="data-preview">
              <div class="mapping-title">数据预览 (前 {{ Math.min(5, previewPrompts.length) }} 条)</div>
              <div v-for="(p, i) in previewPrompts.slice(0, 5)" :key="i" class="preview-item">
                <span class="preview-idx">{{ i + 1 }}</span>
                <span>{{ truncate(String(p), 80) }}</span>
              </div>
            </div>

            <div class="batch-meta">
              <span>{{ filePromptCount }} 条描述</span>
              <a-button
                type="primary"
                :loading="loading"
                :disabled="filePromptCount === 0 || !hasPromptMapping"
                @click="handleGenerateFromFile"
              >
                <template #icon><ThunderboltOutlined /></template>
                批量生成 ({{ filePromptCount }})
              </a-button>
            </div>
          </template>
        </a-spin>
      </template>
    </div>

    <!-- 进度条 -->
    <a-progress v-if="loading" :percent="progress" status="active" style="margin: 16px 0" />

    <!-- 阶段二：结果列表（可滚动） -->
    <div v-if="results.length > 0 && !loading" class="batch-results">
      <a-divider>
        生成结果: {{ summary.success }} 成功 / {{ summary.failed }} 失败
        (Token: {{ summary.totalTokens }})
      </a-divider>

      <div class="batch-list">
        <div
          v-for="(r, idx) in results"
          :key="idx"
          class="batch-item"
          :class="{
            'batch-failed': !r.success,
            'batch-unchecked': !checked[idx] && r.success,
          }"
        >
          <div class="batch-item-header">
            <a-checkbox
              v-if="r.success && r.steps?.length"
              :checked="checked[idx]"
              @change="(e: any) => toggleCheck(idx, e.target.checked)"
            />
            <span class="batch-item-index">#{{ idx + 1 }}</span>
            <a-tag v-if="r.success" color="green">{{ r.steps?.length || 0 }} 步</a-tag>
            <a-tag v-else color="red">失败</a-tag>
            <span class="batch-item-prompt">{{ truncate(r.prompt, 50) }}</span>

            <!-- AI 审查标签 -->
            <template v-if="reviews[idx]">
              <a-tooltip :title="`质量: ${reviews[idx].quality_score} / 意图匹配: ${reviews[idx].intent_match}`">
                <a-tag :color="scoreColor(reviews[idx].quality_score)">
                  Q: {{ reviews[idx].quality_score }}
                </a-tag>
              </a-tooltip>
              <a-tooltip :title="`意图匹配: ${reviews[idx].intent_match}`">
                <a-tag :color="scoreColor(reviews[idx].intent_match)">
                  I: {{ reviews[idx].intent_match }}
                </a-tag>
              </a-tooltip>
              <a-tooltip v-if="reviews[idx].suggestions?.length" placement="left">
                <template #title>
                  <div v-for="(s, si) in reviews[idx].suggestions" :key="si">{{ s }}</div>
                </template>
                <a-tag color="orange">{{ reviews[idx].suggestions.length }} 条建议</a-tag>
              </a-tooltip>
            </template>

            <div class="batch-item-actions">
              <a-button v-if="r.success" size="small" type="link" @click="toggleExpand(idx)">
                {{ expanded[idx] ? '收起' : '展开' }}
              </a-button>
              <a-button
                size="small"
                type="link"
                :loading="regeneratingIdx === idx"
                @click="handleRegenerate(idx)"
              >
                重新生成
              </a-button>
            </div>
          </div>

          <!-- 步骤详情 -->
          <div v-if="expanded[idx] && r.steps" class="batch-item-steps">
            <div v-for="(step, si) in r.steps" :key="si" class="batch-step">
              <span class="batch-step-idx">{{ si + 1 }}</span>
              <a-tag :color="stepColor(step.type)" size="small">{{ step.type }}</a-tag>
              <span>{{ step.name }}</span>
            </div>
          </div>

          <!-- 审查建议详情 -->
          <div v-if="expanded[idx] && reviews[idx]?.suggestions?.length" class="batch-review-detail">
            <div v-for="(s, si) in reviews[idx].suggestions" :key="si" class="batch-suggestion">
              - {{ s }}
            </div>
          </div>

          <div v-if="!r.success" class="batch-item-error">{{ r.error }}</div>
        </div>
      </div>
    </div>

    <!-- 底部工具栏（始终固定在滚动区外） -->
    <div v-if="results.length > 0 && !loading" class="batch-toolbar">
      <a-select
        v-if="projects.length > 0"
        v-model:value="selectedProject"
        placeholder="选择保存到项目"
        allow-clear
        style="width: 200px"
      >
        <a-select-option v-for="p in projects" :key="p.id" :value="p.id">
          {{ p.name }}
        </a-select-option>
      </a-select>
      <a-space>
        <a-button
          :loading="reviewing"
          :disabled="successfulItems.length === 0"
          @click="handleReview"
        >
          <template #icon><SafetyCertificateOutlined /></template>
          AI 审查
        </a-button>
        <a-button @click="handleBack">返回输入</a-button>
        <a-button
          type="primary"
          :loading="saving"
          :disabled="checkedCount === 0"
          @click="handleBatchSave"
        >
          保存选中的 ({{ checkedCount }})
        </a-button>
      </a-space>
    </div>

    <!-- 重新生成弹窗 -->
    <a-modal
      v-model:open="regenDialogVisible"
      title="重新生成"
      :width="500"
      :confirm-loading="regenConfirming"
      @ok="confirmRegenerate"
      @cancel="regenDialogVisible = false"
    >
      <a-textarea
        v-model:value="regenPrompt"
        :rows="4"
        placeholder="编辑描述后重新生成"
      />
    </a-modal>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { message as antMessage } from 'ant-design-vue'
import { ThunderboltOutlined, SafetyCertificateOutlined, InboxOutlined } from '@ant-design/icons-vue'
import { nl2script, nl2scriptReview, nl2scriptBatchSave, nl2scriptBatchParseFile, createBatchTask } from '@/api/script'

// @ts-ignore
defineProps<{
  projects: { id: number; name: string }[]
}>()

const emit = defineEmits<{
  (e: 'saved'): void
  (e: 'goToTask', taskId: number): void
}>()

const visible = ref(false)
const promptsText = ref('')
const loading = ref(false)
const results = ref<any[]>([])
const selectedProject = ref<number | undefined>(undefined)
const expanded = ref<Record<number, boolean>>({})
const checked = ref<Record<number, boolean>>({})
const progress = ref(0)

// AI 审查
const reviews = ref<Record<number, { quality_score: number; intent_match: number; suggestions: string[]; passed: boolean }>>({})
const reviewing = ref(false)

// 保存
const saving = ref(false)

// 重新生成
const regeneratingIdx = ref<number | null>(null)
const regenDialogVisible = ref(false)
const regenPrompt = ref('')
const regenTargetIdx = ref<number | null>(null)
const regenConfirming = ref(false)

// 文件导入相关
const inputMode = ref<'text' | 'file'>('text')
const parsedFile = ref<{ columns: string[]; rows: Record<string, any>[]; total_rows: number; file_name: string } | null>(null)
const columnMapping = ref<Record<string, string>>({})
const enrichedFileData = ref<any[]>([])
const uploading = ref(false)

const promptLines = computed(() =>
  promptsText.value.split('\n').map(l => l.trim()).filter(l => l.length > 0)
)

const summary = computed(() => ({
  success: results.value.filter(r => r.success).length,
  failed: results.value.filter(r => !r.success).length,
  totalTokens: results.value.reduce((sum, r) => sum + (r.token_usage?.total_tokens || 0), 0),
}))

const successfulItems = computed(() =>
  results.value
    .map((r, i) => ({ ...r, idx: i }))
    .filter(r => r.success && r.steps?.length)
)

const checkedCount = computed(() =>
  Object.values(checked.value).filter(Boolean).length
)

// --- 文件导入 computed ---

const hasPromptMapping = computed(() =>
  Object.values(columnMapping.value).some(v => v === 'prompt')
)

const previewPrompts = computed(() => {
  if (!parsedFile.value) return []
  const promptCol = Object.entries(columnMapping.value).find(([, v]) => v === 'prompt')?.[0]
  if (!promptCol) return []
  return parsedFile.value.rows
    .map(r => r[promptCol])
    .filter(v => v !== '' && v !== null && v !== undefined)
})

const filePromptCount = computed(() => previewPrompts.value.length)

// 列映射表格列定义
const mappingTableColumns = [
  { title: '列名', dataIndex: 'column', key: 'column', width: 150 },
  { title: '示例数据 (前3行)', dataIndex: 'sample', key: 'sample' },
  { title: '角色', key: 'role', width: 160 },
]

const mappingTableData = computed(() => {
  if (!parsedFile.value) return []
  return parsedFile.value.columns.map(col => ({
    column: col,
    sample: parsedFile.value!.rows.slice(0, 3)
      .map(r => truncate(String(r[col] ?? ''), 30))
      .join(' / '),
  }))
})

// --- 自动检测列映射 ---
function autoDetectMapping(columns: string[]): Record<string, string> {
  const mapping: Record<string, string> = {}
  for (const col of columns) {
    mapping[col] = 'ignore'
  }
  for (const col of columns) {
    const lower = col.toLowerCase()
    if (/描述|用例描述|测试描述|步骤|prompt|test\s*desc|description/.test(lower)) {
      mapping[col] = 'prompt'
    } else if (/名称|用例名|脚本名|name|title/.test(lower)) {
      mapping[col] = 'name'
    } else if (/标签|tag/.test(lower)) {
      mapping[col] = 'tags'
    }
  }
  // 如果没有匹配到 prompt，尝试将第一列非空文本列设为 prompt
  if (!Object.values(mapping).includes('prompt') && columns.length > 0) {
    mapping[columns[0]] = 'prompt'
  }
  return mapping
}

function onMappingChange() {
  // 触发 computed 重新计算
  columnMapping.value = { ...columnMapping.value }
}

// --- 文件上传处理 ---
async function handleFileSelect(file: File) {
  uploading.value = true
  parsedFile.value = null
  columnMapping.value = {}
  enrichedFileData.value = []

  try {
    const res = await nl2scriptBatchParseFile(file)
    parsedFile.value = res
    columnMapping.value = autoDetectMapping(res.columns)

    if (res.total_rows > 50) {
      antMessage.warning(`文件共 ${res.total_rows} 行，仅取前 50 行`)
    }
  } catch (e: any) {
    antMessage.error(e?.response?.data?.error || '文件解析失败')
  } finally {
    uploading.value = false
  }

  // 阻止 ant-design 自动上传
  return false
}

// --- 从文件构建批量数据 ---
function buildFileBatchData() {
  if (!parsedFile.value) return { prompts: [], enrichedRows: [] }

  const mapping = columnMapping.value
  const promptCol = Object.entries(mapping).find(([, v]) => v === 'prompt')?.[0]
  const nameCol = Object.entries(mapping).find(([, v]) => v === 'name')?.[0]
  const descCol = Object.entries(mapping).find(([, v]) => v === 'description')?.[0]
  const tagsCol = Object.entries(mapping).find(([, v]) => v === 'tags')?.[0]

  const prompts: string[] = []
  const enrichedRows: any[] = []

  for (const row of parsedFile.value.rows) {
    const promptVal = promptCol ? String(row[promptCol] ?? '').trim() : ''
    if (!promptVal) continue

    prompts.push(promptVal)
    enrichedRows.push({
      prompt: promptVal,
      script_name: nameCol ? String(row[nameCol] ?? '').trim() : '',
      description: descCol ? String(row[descCol] ?? '').trim() : '',
      tags: tagsCol ? parseTagsValue(row[tagsCol]) : [],
    })
  }

  return { prompts, enrichedRows }
}

/** 解析标签值：支持逗号、分号、空格分隔 */
function parseTagsValue(val: any): string[] {
  if (Array.isArray(val)) return val.map(String)
  if (val === '' || val === null || val === undefined) return []
  return String(val).split(/[,;，；\s]+/).map(t => t.trim()).filter(Boolean)
}

// --- 文件模式批量生成 ---
async function handleGenerateFromFile() {
  const { prompts } = buildFileBatchData()
  if (prompts.length === 0) {
    antMessage.warning('没有可生成的描述')
    return
  }

  loading.value = true
  progress.value = 10

  try {
    const res = await createBatchTask({
      name: '',
      prompts,
    })
    antMessage.success('任务已创建，正在后台生成')
    handleClose()
    emit('goToTask', res.id)
  } catch (e: any) {
    antMessage.error(e?.response?.data?.error || '创建任务失败')
  } finally {
    loading.value = false
    progress.value = 0
  }
}

function open() {
  visible.value = true
  results.value = []
  promptsText.value = ''
  expanded.value = {}
  checked.value = {}
  reviews.value = {}
  progress.value = 0
  // 重置文件导入状态
  inputMode.value = 'text'
  parsedFile.value = null
  columnMapping.value = {}
  enrichedFileData.value = []
  uploading.value = false
}

function handleClose() {
  visible.value = false
}

function toggleExpand(idx: number) {
  expanded.value[idx] = !expanded.value[idx]
}

function toggleCheck(idx: number, val: boolean) {
  checked.value[idx] = val
}

async function handleGenerate() {
  const lines = promptLines.value
  if (lines.length === 0) return

  loading.value = true
  progress.value = 10

  try {
    const res = await createBatchTask({
      name: '',
      prompts: lines,
    })
    antMessage.success('任务已创建，正在后台生成')
    handleClose()
    emit('goToTask', res.id)
  } catch (e: any) {
    antMessage.error(e?.response?.data?.error || '创建任务失败')
  } finally {
    loading.value = false
    progress.value = 0
  }
}

async function handleReview() {
  const items = successfulItems.value.map(r => ({
    prompt: r.prompt,
    steps: r.steps,
  }))
  if (items.length === 0) return

  reviewing.value = true
  try {
    const res = await nl2scriptReview(items)
    const reviewList = res.reviews || []

    const successfulIndices = successfulItems.value.map(r => r.idx)
    successfulIndices.forEach((origIdx, i) => {
      if (reviewList[i]) {
        reviews.value[origIdx] = reviewList[i]
        if (!reviewList[i].passed) {
          checked.value[origIdx] = false
        }
      }
    })

    antMessage.success('AI 审查完成')
  } catch (e: any) {
    antMessage.error(e?.response?.data?.error || 'AI 审查失败')
  } finally {
    reviewing.value = false
  }
}

async function handleBatchSave() {
  if (!selectedProject.value) {
    antMessage.warning('请先选择一个项目')
    return
  }

  const scripts: { prompt: string; steps: any[]; script_name: string; description?: string; tags?: string[] }[] = []
  results.value.forEach((r, i) => {
    if (checked.value[i] && r.success && r.steps?.length) {
      const enriched = r._enriched
      const scriptName = enriched?.script_name || `AI生成 - ${(r.prompt || '').slice(0, 20)}`
      scripts.push({
        prompt: r.prompt,
        steps: r.steps,
        script_name: scriptName,
        description: enriched?.description || '',
        tags: enriched?.tags || [],
      })
    }
  })

  if (scripts.length === 0) return

  saving.value = true
  try {
    const res = await nl2scriptBatchSave({
      project_id: selectedProject.value,
      scripts,
    })
    antMessage.success(`已保存 ${res.saved_ids.length} 个脚本`)
    emit('saved')
    handleClose()
  } catch (e: any) {
    antMessage.error(e?.response?.data?.error || '批量保存失败')
  } finally {
    saving.value = false
  }
}

function handleRegenerate(idx: number) {
  regenTargetIdx.value = idx
  regenPrompt.value = results.value[idx]?.prompt || ''
  regenDialogVisible.value = true
}

async function confirmRegenerate() {
  if (regenTargetIdx.value === null || !regenPrompt.value.trim()) return

  const idx = regenTargetIdx.value
  regenConfirming.value = true
  regeneratingIdx.value = idx

  try {
    const res = await nl2script({ prompt: regenPrompt.value })
    // 替换原位置的结果，保留 _enriched
    const enriched = results.value[idx]?._enriched || null
    results.value[idx] = {
      ...results.value[idx],
      success: true,
      steps: res.steps,
      token_usage: res.token_usage,
      prompt: regenPrompt.value,
      error: undefined,
      _enriched: enriched,
    }
    checked.value[idx] = true
    delete reviews.value[idx]

    antMessage.success(`第 ${idx + 1} 条已重新生成`)
    regenDialogVisible.value = false
  } catch (e: any) {
    antMessage.error(e?.response?.data?.error || '重新生成失败')
  } finally {
    regenConfirming.value = false
    regeneratingIdx.value = null
    regenTargetIdx.value = null
  }
}

function handleBack() {
  results.value = []
  reviews.value = {}
  checked.value = {}
  expanded.value = {}
  enrichedFileData.value = []
}

function scoreColor(score: number): string {
  if (score >= 80) return 'green'
  if (score >= 60) return 'orange'
  return 'red'
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
.batch-results { max-height: 420px; overflow-y: auto }
.batch-list { display: flex; flex-direction: column; gap: 8px }
.batch-item {
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 8px 12px;
  transition: border-color 0.2s;
}
.batch-item.batch-failed { border-color: #ffccc7; background: #fff2f0 }
.batch-item.batch-unchecked { border-color: #d9d9d9; opacity: 0.7 }
.batch-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.batch-item-index { font-weight: 600; color: #1677ff; min-width: 28px }
.batch-item-prompt { flex: 1; font-size: 13px; min-width: 100px }
.batch-item-actions {
  margin-left: auto;
  display: flex;
  gap: 4px;
}
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
.batch-review-detail {
  margin-top: 6px;
  padding-left: 36px;
  font-size: 12px;
  color: #d48806;
}
.batch-suggestion {
  padding: 2px 0;
}
.batch-toolbar {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
/* 文件导入相关 */
.file-info {
  margin: 12px 0 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #666;
}
.column-mapping { margin-top: 12px }
.mapping-title {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}
.data-preview {
  margin-top: 12px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 8px 12px;
}
.preview-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
  color: #555;
}
.preview-idx {
  min-width: 20px;
  color: #1677ff;
  font-weight: 600;
}
</style>
