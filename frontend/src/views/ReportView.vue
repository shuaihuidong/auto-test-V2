<template>
  <div class="report-view">
    <div class="page-header">
      <a-space>
        <a-button @click="goBack">
          <ArrowLeftOutlined /> 返回
        </a-button>
        <h2>{{ pageTitle }}</h2>
      </a-space>
      <a-space>
        <a-button @click="refreshReport">
          <ReloadOutlined /> 刷新
        </a-button>
        <a-button type="primary" @click="downloadReport">
          <DownloadOutlined /> 下载HTML
        </a-button>
      </a-space>
    </div>

    <a-spin :spinning="loading">
      <!-- 计划执行报告 -->
      <div v-if="report && isPlanReport" class="report-content">
        <!-- 概览卡片 -->
        <a-row :gutter="16" class="summary-cards">
          <a-col :span="5">
            <a-card>
              <a-statistic title="脚本总数" :value="report.summary.total_scripts || 0" />
            </a-card>
          </a-col>
          <a-col :span="5">
            <a-card>
              <a-statistic title="已完成" :value="report.summary.script_status?.completed || 0" :value-style="{ color: '#52c41a' }" />
            </a-card>
          </a-col>
          <a-col :span="5">
            <a-card>
              <a-statistic title="失败" :value="report.summary.script_status?.failed || 0" :value-style="{ color: '#f5222d' }" />
            </a-card>
          </a-col>
          <a-col :span="5">
            <a-card>
              <a-statistic title="待执行" :value="(report.summary.script_status?.pending || 0) + (report.summary.script_status?.running || 0)" :value-style="{ color: '#1890ff' }" />
            </a-card>
          </a-col>
          <a-col :span="4">
            <a-card>
              <a-statistic
                title="总耗时"
                :value="report.summary.total_duration"
                suffix="秒"
              />
            </a-card>
          </a-col>
        </a-row>

        <!-- 状态分布图表 -->
        <a-row :gutter="16" class="charts-section">
          <a-col :span="12">
            <a-card title="脚本状态分布" :body-style="{ height: '350px' }">
              <div ref="statusChartRef" class="chart"></div>
            </a-card>
          </a-col>
          <a-col :span="12">
            <a-card title="问题分析与建议" :body-style="{ height: '350px', padding: '16px', overflow: 'auto' }">
              <div class="plan-failure-analysis">
                <!-- 失败原因标签 -->
                <div v-if="getFailureReasons().length > 0" class="analysis-section">
                  <div class="section-title">
                    <ExperimentOutlined style="margin-right: 6px; color: #1890ff; font-size: 14px;" />
                    <span>失败原因</span>
                  </div>
                  <div class="failure-reason-tags">
                    <a-tag v-for="(reason, index) in getFailureReasons()" :key="index" color="error">
                      {{ reason.name }} ({{ reason.count }})
                    </a-tag>
                  </div>
                </div>

                <!-- 改进建议 - 从失败原因中汇总 -->
                <div v-if="getPlanSuggestions().length > 0" class="analysis-section">
                  <div class="section-title">
                    <BulbOutlined style="color: #faad14; margin-right: 6px; font-size: 14px;" />
                    <span>改进建议</span>
                  </div>
                  <div class="suggestion-list">
                    <div v-for="(suggestion, index) in getPlanSuggestions()" :key="index" class="suggestion-item">
                      <span class="suggestion-bullet">•</span>
                      <span class="suggestion-text">{{ suggestion }}</span>
                    </div>
                  </div>
                </div>

                <!-- 无失败时的展示 -->
                <div v-if="getFailureReasons().length === 0 && getPlanSuggestions().length === 0" class="no-failure-state">
                  <CheckCircleOutlined style="font-size: 40px; color: #52c41a; margin-bottom: 8px;" />
                  <div class="no-failure-text">测试全部通过</div>
                  <div class="no-failure-sub">所有脚本均执行成功</div>
                </div>
              </div>
            </a-card>
          </a-col>
        </a-row>

        <!-- 脚本执行详情 -->
        <a-card title="脚本执行详情" class="steps-section">
          <a-table
            :columns="scriptColumns"
            :data-source="scripts"
            :pagination="{ pageSize: 20 }"
            row-key="id"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'status'">
                <a-tag :color="getStatusTagColor(record.status)">
                  {{ getStatusText(record.status) }}
                </a-tag>
              </template>
            <template v-else-if="column.key === 'error_reason'">
              <span v-if="record.error_reason" class="error-text">{{ record.error_reason }}</span>
              <span v-else>-</span>
            </template>
            <template v-else-if="column.key === 'detail'">
              <a-button type="link" size="small" @click="openExecutionDetail(record)">
                详情
              </a-button>
            </template>
          </template>
        </a-table>
        </a-card>
      </div>

      <!-- 脚本执行报告 -->
      <div v-else-if="report" class="report-content">
        <!-- 概览卡片 -->
        <a-row :gutter="16" class="summary-cards">
          <a-col :span="4">
            <a-card>
              <a-statistic title="步骤总数" :value="report.summary.total || 0" />
            </a-card>
          </a-col>
          <a-col :span="4">
            <a-card>
              <a-statistic title="通过步骤" :value="report.summary.passed || 0" :value-style="{ color: '#52c41a' }" />
            </a-card>
          </a-col>
          <a-col :span="4">
            <a-card>
              <a-statistic title="失败步骤" :value="report.summary.failed || 0" :value-style="{ color: '#f5222d' }" />
            </a-card>
          </a-col>
          <a-col :span="4">
            <a-card>
              <a-statistic
                title="通过率"
                :value="report.summary.pass_rate || 0"
                suffix="%"
                :value-style="{ color: (report.summary.pass_rate || 0) >= 80 ? '#52c41a' : '#f5222d' }"
              />
            </a-card>
          </a-col>
          <a-col :span="4">
            <a-card>
              <a-statistic
                title="总耗时"
                :value="report.summary.total_duration || 0"
                suffix="秒"
              />
            </a-card>
          </a-col>
          <a-col :span="4">
            <a-card>
              <a-statistic
                title="执行状态"
                :value-style="{ color: getStatusColor(report.execution_status) }"
              >
                <template #formatter>
                  {{ getStatusText(report.execution_status) }}
                </template>
              </a-statistic>
            </a-card>
          </a-col>
        </a-row>

        <!-- 图表区域 -->
        <a-row :gutter="16" class="charts-section">
          <a-col :span="12">
            <a-card title="执行趋势" :body-style="{ height: '350px' }">
              <div ref="trendChartRef" class="chart"></div>
            </a-card>
          </a-col>
          <a-col :span="12">
            <a-card title="问题分析与建议" :body-style="{ height: '350px', padding: '16px', overflow: 'auto' }">
              <div class="script-failure-analysis">
                <!-- 失败原因标签 -->
                <div v-if="getStepFailureReasons().length > 0" class="analysis-section">
                  <div class="section-title">
                    <ExperimentOutlined style="margin-right: 6px; color: #1890ff; font-size: 14px;" />
                    <span>失败原因</span>
                  </div>
                  <div class="failure-reason-tags">
                    <a-tag v-for="(reason, index) in getStepFailureReasons()" :key="index" color="error">
                      {{ reason.name }} ({{ reason.count }})
                    </a-tag>
                  </div>
                </div>

                <!-- 改进建议 -->
                <div v-if="getStepSuggestions().length > 0" class="analysis-section">
                  <div class="section-title">
                    <BulbOutlined style="color: #faad14; margin-right: 6px; font-size: 14px;" />
                    <span>改进建议</span>
                  </div>
                  <div class="suggestion-list">
                    <div v-for="(suggestion, index) in getStepSuggestions()" :key="index" class="suggestion-item">
                      <span class="suggestion-bullet">•</span>
                      <span class="suggestion-text">{{ suggestion }}</span>
                    </div>
                  </div>
                </div>

                <!-- 无失败时的展示 -->
                <div v-if="getStepFailureReasons().length === 0 && getStepSuggestions().length === 0" class="no-failure-state">
                  <CheckCircleOutlined style="font-size: 40px; color: #52c41a; margin-bottom: 8px;" />
                  <div class="no-failure-text">全部通过</div>
                  <div class="no-failure-sub">所有步骤执行成功</div>
                </div>

                <!-- AI 智能分析按钮 -->
                <div v-if="steps.some(s => !s.success)" class="ai-analysis-trigger">
                  <a-button type="primary" ghost @click="showAIModal = true">
                    <ThunderboltOutlined /> AI 智能分析
                  </a-button>
                </div>
              </div>
            </a-card>
          </a-col>
        </a-row>

        <!-- 步骤详情 - Playwright 风格时间线 -->
        <a-card title="步骤详情" class="steps-section">
          <template v-if="getRemainingStepsCount() > 0" #extra>
            <a-tag color="warning" style="margin-right: 8px;">
              <WarningOutlined style="margin-right: 4px;" />
              脚本中途失败，还有 {{ getRemainingStepsCount() }} 个步骤未执行
            </a-tag>
          </template>

          <div class="step-timeline">
            <div
              v-for="step in steps"
              :key="step.index"
              class="step-row"
              :class="{
                'step-passed': step.success,
                'step-failed': !step.success,
              }"
            >
              <!-- 左侧：状态指示器 -->
              <div class="step-indicator">
                <CheckCircleFilled v-if="step.success" class="icon-pass" />
                <CloseCircleFilled v-else class="icon-fail" />
              </div>

              <!-- 中间：步骤内容 -->
              <div class="step-content">
                <!-- 步骤头部 -->
                <div class="step-header">
                  <span class="step-index">#{{ step.index }}</span>
                  <span class="step-name">{{ step.name }}</span>
                  <a-tag v-if="step.type" size="small" class="step-type-tag">{{ step.type }}</a-tag>
                  <span class="step-duration" :class="{ 'duration-slow': step.duration > 3000 }">
                    {{ formatDuration(step.duration) }}
                  </span>
                </div>

                <!-- 消息 -->
                <div v-if="step.message && step.message !== '执行成功'" class="step-message">
                  {{ step.message }}
                </div>

                <!-- 错误信息 -->
                <div v-if="step.error" class="step-error">
                  <ExclamationCircleOutlined /> {{ step.error }}
                </div>

                <!-- 截图 -->
                <div v-if="step.screenshot" class="step-screenshot">
                  <a-image
                    :src="step.screenshot"
                    :width="200"
                    :preview="{ src: step.screenshot }"
                    class="screenshot-thumb"
                  />
                </div>
              </div>

              <!-- 右侧：耗时条 -->
              <div class="step-duration-bar">
                <div
                  class="duration-fill"
                  :class="{
                    'fill-pass': step.success,
                    'fill-fail': !step.success,
                  }"
                  :style="{ width: getDurationPercent(step.duration) + '%' }"
                />
              </div>
            </div>
          </div>

          <!-- 汇总统计 -->
          <div class="step-summary">
            <a-space :size="24">
              <span>
                <CheckCircleFilled style="color: #52c41a; margin-right: 4px;" />
                {{ steps.filter(s => s.success).length }} 通过
              </span>
              <span v-if="steps.some(s => !s.success)">
                <CloseCircleFilled style="color: #ff4d4f; margin-right: 4px;" />
                {{ steps.filter(s => !s.success).length }} 失败
              </span>
              <span style="color: #999;">
                总耗时 {{ formatDuration(steps.reduce((a, s) => a + s.duration, 0)) }}
              </span>
            </a-space>
          </div>
        </a-card>
      </div>

      <a-empty v-else description="暂无报告数据" />
    </a-spin>

    <!-- AI 智能分析弹窗 -->
    <AIAnalysisModal
      v-model:visible="showAIModal"
      :execution-id="executionId"
      :script-id="report?.summary?.script_id || 0"
      @applied="handleAIApplied"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import {
  ArrowLeftOutlined,
  ReloadOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  ExclamationCircleOutlined,
  BulbOutlined,
  ExperimentOutlined,
  WarningOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons-vue'
import { getReport, downloadHtmlReport, generateReport } from '@/api/report'
import type { Report } from '@/api/report'
import AIAnalysisModal from '@/components/AI/AIAnalysisModal.vue'

const router = useRouter()
const route = useRoute()
const executionId = parseInt(route.params.executionId as string)

const loading = ref(false)
const report = ref<Report | null>(null)

const trendChartRef = ref<HTMLElement>()
const statusChartRef = ref<HTMLElement>()

let trendChart: echarts.ECharts | null = null
let statusChart: echarts.ECharts | null = null

// 是否为计划报告
const isPlanReport = computed(() => {
  if (!report.value) return false
  // 优先从 execution_type 字段获取，如果没有则从 summary.execution_type 获取
  const type = report.value.execution_type || report.value.summary?.execution_type
  return type === 'plan'
})

// 页面标题
const pageTitle = computed(() => isPlanReport.value ? '测试计划报告' : '测试报告')

// 脚本执行报告的步骤列
// 计划报告的脚本列
const scriptColumns = [
  { title: 'ID', key: 'id', dataIndex: 'id', width: 80 },
  { title: '脚本名称', key: 'name', dataIndex: 'name', width: 300 },
  { title: '状态', key: 'status', width: 100 },
  { title: '耗时(秒)', key: 'duration', dataIndex: 'duration', width: 100 },
  { title: '失败原因', key: 'error_reason', width: 300 },
  { title: '详情', key: 'detail', width: 100 }
]

const steps = ref<any[]>([])
const scripts = ref<any[]>([])
const showAIModal = ref(false)

async function loadReport() {
  loading.value = true
  try {
    let reports = await getReport(executionId)

    // 如果报告不存在，自动生成
    if (!reports.results || reports.results.length === 0) {
      await generateReport(executionId)
      reports = await getReport(executionId)
    }

    if (reports.results?.length > 0) {
      report.value = reports.results[0]

      // 调试日志
      console.log('报告数据:', report.value)
      console.log('execution_type:', report.value!.execution_type)
      console.log('summary.execution_type:', report.value!.summary?.execution_type)
      console.log('charts_data:', report.value!.charts_data)

      // 如果是计划报告，处理脚本数据
      if (isPlanReport.value && report.value!.charts_data?.scripts) {
        scripts.value = report.value!.charts_data.scripts.map((script: any) => ({
          ...script,
          error_reason: script.error_reason || (script.status === 'failed' ? '执行失败' : '')
        }))
        console.log('脚本数据:', scripts.value)
      } else {
        // 脚本报告，处理步骤数据
        if (report.value!.charts_data?.trend) {
          steps.value = report.value!.charts_data.trend.map((item: any, index: number) => ({
            index: index + 1,
            name: item.name || `步骤${index + 1}`,
            type: item.type || 'unknown',
            success: item.success,
            duration: item.duration || 0,
            message: item.message || (item.success ? '执行成功' : '执行失败'),
            error: item.success ? '' : (item.error || item.message || '执行失败'),
            screenshot: item.screenshot || '',
          }))
        }
        console.log('步骤数据:', steps.value)
      }

      await nextTick()
      renderCharts()
    }
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

async function refreshReport() {
  await generateReport(executionId)
  await loadReport()
  message.success('报告已刷新')
}

async function downloadReport() {
  if (!report.value) return
  try {
    const blob = await downloadHtmlReport(report.value.id)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${executionId}.html`
    a.click()
    window.URL.revokeObjectURL(url)
    message.success('下载成功')
  } catch (error) {
    message.error('下载失败')
  }
}

function goBack() {
  const returnTo = route.query.returnTo
  if (typeof returnTo === 'string' && returnTo) {
    window.location.assign(returnTo)
    return
  }

  // Fallback: return to the executions page that opened this report.
  if (isPlanReport.value) {
    router.push({ path: '/executions', query: { tab: 'plan' } })
  } else {
    router.push({ path: '/executions', query: { tab: 'script' } })
  }
}

function handleAIApplied(scriptId: number) {
  router.push({ name: 'ScriptEdit', params: { id: scriptId } })
}

function openExecutionDetail(record: any) {
  const detailExecutionId = record.execution_id || record.id
  const target = router.resolve({
    name: 'ReportView',
    params: { executionId: String(detailExecutionId) },
    query: { returnTo: route.fullPath },
  })
  window.location.assign(target.href)
}

function renderCharts() {
  if (!report.value) return

  // 如果是计划报告，渲染状态分布图
  if (isPlanReport.value) {
    if (statusChartRef.value) {
      statusChart = echarts.init(statusChartRef.value)

      // 定义状态颜色映射
      const statusColors: Record<string, string> = {
        '已完成': '#52c41a',  // 绿色
        '失败': '#f5222d',    // 红色
        '等待中': '#faad14',  // 黄色
        '执行中': '#faad14',  // 黄色
        '已停止': '#d9d9d9'   // 灰色
      }

      // 只显示有数据的状态
      const filteredData = (report.value.charts_data.status_distribution || [])
        .filter((item: any) => item.count > 0)
        .map((item: any) => ({
          name: item.status === 'running' ? '执行中' :
                 item.status === 'pending' ? '待执行' :
                 item.status === 'stopped' ? '已停止' :
                 getStatusText(item.status),
          value: item.count,
          itemStyle: {
            color: statusColors[
              item.status === 'running' ? '执行中' :
              item.status === 'pending' ? '待执行' :
              item.status === 'stopped' ? '已停止' :
              getStatusText(item.status)
            ] || '#d9d9d9'
          }
        }))

      const statusOption: EChartsOption = {
        tooltip: {
          trigger: 'item',
          formatter: '{a} <br/>{b}: {c} ({d}%)'
        },
        legend: {
          orient: 'vertical',
          right: 10,
          top: 'center'
        },
        series: [{
          name: '脚本状态',
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['40%', '50%'],
          data: filteredData,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          },
          label: {
            formatter: '{b}: {c}'
          }
        }]
      }
      statusChart.setOption(statusOption)
    }
    return
  }

  // 脚本报告：渲染趋势图
  if (trendChartRef.value) {
    trendChart = echarts.init(trendChartRef.value)
    const trendOption: EChartsOption = {
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const param = params[0]
          const item = report.value!.charts_data.trend?.[param.dataIndex]
          return `${param.name}<br/>耗时: ${item?.duration}ms<br/>状态: ${item?.success ? '成功' : '失败'}`
        }
      },
      xAxis: {
        type: 'category',
        data: report.value!.charts_data.trend?.map((item: any) => `步骤${item.index}`) || [],
        axisLabel: { rotate: 45 }
      },
      yAxis: { type: 'value', name: '耗时(ms)' },
      series: [{
        type: 'line',
        smooth: true,
        data: report.value!.charts_data.trend?.map((item: any) => ({
          value: item.duration,
          itemStyle: { color: item.success ? '#52c41a' : '#f5222d' }
        })) || [],
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(82, 196, 26, 0.3)' },
              { offset: 1, color: 'rgba(82, 196, 26, 0.05)' }
            ]
          }
        }
      }]
    }
    trendChart.setOption(trendOption)
  }
}

function getStatusColor(status: string) {
  const colors: Record<string, string> = {
    completed: '#52c41a',
    failed: '#f5222d',
    running: '#1890ff',
    pending: '#999',
    stopped: '#faad14'
  }
  return colors[status] || '#999'
}

function getStatusTagColor(status: string) {
  const colors: Record<string, string> = {
    completed: 'success',
    failed: 'error',
    running: 'processing',
    pending: 'default',
    stopped: 'warning'
  }
  return colors[status] || 'default'
}

function getStatusText(status: string) {
  const texts: Record<string, string> = {
    completed: '已完成',
    failed: '失败',
    running: '执行中',
    pending: '等待中',
    stopped: '已停止'
  }
  return texts[status] || status
}

// 获取失败原因分析（增强版）
function getFailureReasons() {
  if (!report.value || !report.value.charts_data?.scripts) return []

  // 统计失败原因（从脚本维度），同时记录失败的脚本
  const reasonMap = new Map<string, { count: number; scripts: any[]; examples: string[] }>()
  const failedScripts = report.value.charts_data.scripts.filter((s: any) => s.status === 'failed')

  failedScripts.forEach((script: any) => {
    const errorMsg = script.error_reason || script.error_message || '未知错误'
    const reason = classifyFailureReason(errorMsg)

    if (!reasonMap.has(reason)) {
      reasonMap.set(reason, {
        count: 0,
        scripts: [],
        examples: []
      })
    }

    const info = reasonMap.get(reason)!
    info.count++
    info.scripts.push({
      id: script.id,
      name: script.name,
      error: errorMsg.substring(0, 100) // 保存前100个字符作为示例
    })

    // 提取核心错误信息（去掉"步骤 X [名称]:"前缀）
    let coreError = errorMsg
    if (errorMsg.includes(']:')) {
      // 从 "步骤 7 [点击]: 未找到元素" 中提取 "未找到元素"
      coreError = errorMsg.split(']:')[1]?.trim() || errorMsg
    }
    // 保存最多2个不同的核心错误示例
    if (info.examples.length < 2 && !info.examples.includes(coreError.substring(0, 60))) {
      info.examples.push(coreError.substring(0, 60))
    }
  })

  // 如果没有失败原因但有失败的脚本，返回通用原因
  if (reasonMap.size === 0 && failedScripts.length > 0) {
    return [{
      name: '脚本执行失败',
      count: failedScripts.length,
      scripts: failedScripts.map((s: any) => ({
        id: s.id,
        name: s.name,
        error: (s.error_reason || s.error_message || '未知错误').substring(0, 100)
      })),
      examples: ['脚本执行过程中发生错误，请查看详细日志'],
      suggestions: ['检查测试环境配置和脚本逻辑', '查看详细日志定位具体问题']
    }]
  }

  // 转换为数组并排序，添加建议
  return Array.from(reasonMap.entries())
    .map(([name, info]) => ({
      name,
      count: info.count,
      scripts: info.scripts,
      examples: info.examples,
      suggestions: getSuggestionsForReason(name)
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 3) // 只显示前3个
}

// 根据失败原因获取针对性建议
function getSuggestionsForReason(reasonName: string): string[] {
  const suggestionMap: Record<string, string[]> = {
    '执行超时': [
      '检查网络连接和页面加载速度',
      '增加脚本执行超时时间',
      '使用显式等待替代固定等待时间'
    ],
    '元素定位失败': [
      '检查元素选择器是否正确',
      '确认元素是否在iframe中，需要先切换',
      '确保页面完全加载后再操作元素',
      '尝试使用更稳定的定位方式（如CSS选择器）'
    ],
    '网络连接问题': [
      '检查网络连接和服务器状态',
      '增加重试机制处理网络波动',
      '检查防火墙和代理设置'
    ],
    '断言验证失败': [
      '检查断言条件和测试数据是否匹配',
      '验证页面结构是否发生变化',
      '确认测试数据的正确性'
    ],
    '浏览器相关问题': [
      '检查浏览器驱动版本是否匹配',
      '尝试使用不同的浏览器或浏览器版本',
      '确认浏览器是否正常启动'
    ],
    'JavaScript错误': [
      '检查页面控制台是否有JS错误',
      '验证页面脚本是否正常加载',
      '联系开发人员修复页面JS问题'
    ],
    '权限问题': [
      '检查用户权限和访问控制配置',
      '确保测试账号有足够的操作权限',
      '验证登录状态是否正常'
    ],
    '数据异常': [
      '检查测试数据是否正确配置',
      '验证数据源是否可用',
      '确认变量引用是否正确'
    ],
    '其他错误': [
      '检查测试环境配置和脚本逻辑',
      '查看详细日志定位具体问题',
      '联系技术支持获取帮助'
    ]
  }

  return suggestionMap[reasonName] || ['检查测试环境配置', '查看详细日志定位问题']
}

// 分类失败原因（脚本级别）
function classifyFailureReason(errorMsg: string): string {
  if (!errorMsg) return '未知错误'

  const lowerMsg = errorMsg.toLowerCase()

  // 超时相关
  if (lowerMsg.includes('timeout') || lowerMsg.includes('超时') || lowerMsg.includes('timed out')) {
    return '执行超时'
  }

  // 元素定位相关
  if (lowerMsg.includes('element') || lowerMsg.includes('元素') ||
      lowerMsg.includes('locator') || lowerMsg.includes('定位') ||
      lowerMsg.includes('not found') || lowerMsg.includes('找不到') ||
      lowerMsg.includes('no such')) {
    return '元素定位失败'
  }

  // 网络相关
  if (lowerMsg.includes('network') || lowerMsg.includes('网络') ||
      lowerMsg.includes('connection') || lowerMsg.includes('连接') ||
      lowerMsg.includes('unreachable') || lowerMsg.includes('无法访问')) {
    return '网络连接问题'
  }

  // 断言相关
  if (lowerMsg.includes('assert') || lowerMsg.includes('断言') ||
      lowerMsg.includes('expected') || lowerMsg.includes('期望') ||
      lowerMsg.includes('match') || lowerMsg.includes('匹配')) {
    return '断言验证失败'
  }

  // 浏览器相关
  if (lowerMsg.includes('browser') || lowerMsg.includes('浏览器') ||
      lowerMsg.includes('driver') || lowerMsg.includes('驱动') ||
      lowerMsg.includes('chrome') || lowerMsg.includes('firefox')) {
    return '浏览器相关问题'
  }

  // JavaScript错误
  if (lowerMsg.includes('javascript') || lowerMsg.includes('js error') ||
      lowerMsg.includes('script error') || lowerMsg.includes('语法')) {
    return 'JavaScript错误'
  }

  // 权限相关
  if (lowerMsg.includes('permission') || lowerMsg.includes('权限') ||
      lowerMsg.includes('access') || lowerMsg.includes('访问') ||
      lowerMsg.includes('unauthorized') || lowerMsg.includes('未授权')) {
    return '权限问题'
  }

  // 数据相关
  if (lowerMsg.includes('data') || lowerMsg.includes('数据') ||
      lowerMsg.includes('null') || lowerMsg.includes('undefined') ||
      lowerMsg.includes('空值')) {
    return '数据异常'
  }

  return '其他错误'
}

// 获取步骤失败原因分析
function getStepFailureReasons() {
  if (!report.value || !report.value.charts_data?.trend) return []

  // 统计失败原因（从步骤维度）
  const reasonMap = new Map<string, number>()
  const failedSteps = report.value.charts_data.trend.filter((s: any) => !s.success && (s.error || s.message))

  failedSteps.forEach((step: any) => {
    const errorMsg = step.error || step.message || '未知错误'
    const reason = classifyStepFailureReason(errorMsg)
    reasonMap.set(reason, (reasonMap.get(reason) || 0) + 1)
  })

  // 如果没有失败原因但有失败的步骤，返回通用原因
  if (reasonMap.size === 0) {
    const failedCount = report.value.charts_data.trend.filter((s: any) => !s.success).length
    if (failedCount > 0) {
      return [{ name: '步骤执行失败', count: failedCount }]
    }
  }

  // 转换为数组并排序
  return Array.from(reasonMap.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 3)
}

// 分类步骤失败原因
function classifyStepFailureReason(errorMsg: string): string {
  if (!errorMsg) return '未知错误'

  const lowerMsg = errorMsg.toLowerCase()

  // 超时相关
  if (lowerMsg.includes('timeout') || lowerMsg.includes('超时') || lowerMsg.includes('timed out')) {
    return '步骤超时'
  }

  // 元素定位相关
  if (lowerMsg.includes('element') || lowerMsg.includes('元素') ||
      lowerMsg.includes('locator') || lowerMsg.includes('定位') ||
      lowerMsg.includes('not found') || lowerMsg.includes('找不到') ||
      lowerMsg.includes('no such')) {
    return '元素定位失败'
  }

  // 网络相关
  if (lowerMsg.includes('network') || lowerMsg.includes('网络') ||
      lowerMsg.includes('connection') || lowerMsg.includes('连接')) {
    return '网络连接问题'
  }

  // 断言相关
  if (lowerMsg.includes('assert') || lowerMsg.includes('断言') ||
      lowerMsg.includes('expected') || lowerMsg.includes('期望')) {
    return '断言验证失败'
  }

  // JavaScript错误
  if (lowerMsg.includes('javascript') || lowerMsg.includes('js error')) {
    return 'JavaScript错误'
  }

  return '其他错误'
}

// 获取步骤改进建议
function getStepSuggestions() {
  if (!report.value || !report.value.charts_data?.trend) return []

  const failureReasons = getStepFailureReasons()
  const suggestions: string[] = []
  const steps = report.value.charts_data.trend

  // 检查脚本是否从中间失败（有未执行的步骤）
  const totalSteps = report.value.summary.total || 0
  const executedSteps = steps.length
  const failedStep = steps.find((s: any) => !s.success)

  // 如果脚本从中间失败
  if (failedStep && executedSteps < totalSteps) {
    const remainingSteps = totalSteps - executedSteps
    suggestions.push(`脚本在步骤${failedStep.index || executedSteps}失败，还有${remainingSteps}个步骤未执行`)

    // 根据失败原因给出针对性建议
    const errorMsg = failedStep.error || failedStep.message || ''
    if (errorMsg.toLowerCase().includes('timeout') || errorMsg.includes('超时')) {
      suggestions.push('该步骤超时导致脚本中断，建议增加超时时间或优化页面加载')
    } else if (errorMsg.toLowerCase().includes('element') || errorMsg.includes('元素') || errorMsg.includes('定位')) {
      suggestions.push('元素定位失败导致脚本中断，建议检查页面结构和元素选择器')
    } else {
      suggestions.push('步骤失败导致脚本中断，建议查看详细错误日志并修复问题步骤')
    }

    suggestions.push('考虑在脚本中添加异常处理，提高脚本健壮性')
  } else if (failureReasons.length > 0) {
    // 正常失败处理
    failureReasons.forEach(reason => {
      switch (reason.name) {
        case '步骤超时':
          suggestions.push('增加该步骤的等待时间')
          suggestions.push('检查页面加载速度')
          break
        case '元素定位失败':
          suggestions.push('检查元素定位器是否正确')
          suggestions.push('确保元素已加载完成')
          break
        case '网络连接问题':
          suggestions.push('检查网络连接稳定性')
          break
        case '断言验证失败':
          suggestions.push('检查断言条件和测试数据')
          break
        case 'JavaScript错误':
          suggestions.push('检查页面是否有JavaScript错误')
          break
        default:
          suggestions.push('查看详细日志定位问题')
      }
    })
  }

  // 如果没有失败原因，提供通用的建议
  if (suggestions.length === 0) {
    suggestions.push('定期维护测试用例，保持测试数据更新')
    suggestions.push('优化等待策略，提高脚本稳定性')
  }

  // 去重并限制数量
  return Array.from(new Set(suggestions)).slice(0, 4)
}

// 获取计划执行改进建议
function getPlanSuggestions() {
  if (!report.value) return []

  const failureReasons = getFailureReasons()
  const suggestions: string[] = []

  // 从失败原因中提取建议
  failureReasons.forEach(reason => {
    if (reason.suggestions && Array.isArray(reason.suggestions)) {
      suggestions.push(...reason.suggestions)
    }
  })

  // 如果没有失败原因，提供通用建议
  if (failureReasons.length === 0) {
    suggestions.push('定期维护测试用例，保持测试数据更新')
    suggestions.push('优化等待策略，提高脚本稳定性')
  }

  // 去重并限制数量
  return Array.from(new Set(suggestions)).slice(0, 4)
}

// 获取未执行的步骤数
function getRemainingStepsCount() {
  if (!report.value || !report.value.charts_data?.trend) return 0

  const totalSteps = report.value.summary.total || 0
  const executedSteps = report.value.charts_data.trend.length

  // 如果已执行步骤数小于总步骤数，说明有未执行的步骤
  if (executedSteps < totalSteps) {
    return totalSteps - executedSteps
  }

  return 0
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function getDurationPercent(ms: number): number {
  if (!steps.value.length) return 0
  const maxDuration = Math.max(...steps.value.map(s => s.duration), 1)
  return Math.max(Math.round((ms / maxDuration) * 100), 2)
}


onMounted(() => {
  loadReport()
})
</script>

<style scoped>
.report-view {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  color: rgba(255, 255, 255, 0.9);
}

.summary-cards {
  margin-bottom: 16px;
}

.charts-section {
  margin-bottom: 16px;
}

.chart {
  width: 100%;
  height: 300px;
}

.steps-section {
  margin-top: 16px;
}

/* Step timeline - Playwright style */
.step-timeline {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.step-row {
  display: flex;
  align-items: flex-start;
  padding: 10px 12px;
  border-radius: 6px;
  transition: background 0.2s;
  position: relative;
}

.step-row:hover {
  background: rgba(255, 255, 255, 0.04);
}

.step-passed {
  border-left: 3px solid #52c41a;
}

.step-failed {
  border-left: 3px solid #ff4d4f;
  background: rgba(255, 77, 79, 0.04);
}

.step-indicator {
  width: 20px;
  flex-shrink: 0;
  margin-right: 10px;
  margin-top: 2px;
}

.icon-pass {
  color: #52c41a;
  font-size: 16px;
}

.icon-fail {
  color: #ff4d4f;
  font-size: 16px;
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.step-index {
  color: #999;
  font-size: 12px;
  font-family: monospace;
}

.step-name {
  font-weight: 500;
  font-size: 14px;
}

.step-type-tag {
  font-size: 11px;
  opacity: 0.7;
}

.step-duration {
  font-family: monospace;
  font-size: 12px;
  color: #999;
  margin-left: auto;
  white-space: nowrap;
}

.duration-slow {
  color: #fa8c16;
}

.step-message {
  font-size: 12px;
  color: #aaa;
  margin-top: 4px;
  padding-left: 4px;
}

.step-error {
  font-size: 12px;
  color: #ff7875;
  margin-top: 4px;
  padding: 4px 8px;
  background: rgba(255, 77, 79, 0.08);
  border-radius: 4px;
}

.step-screenshot {
  margin-top: 6px;
}

.screenshot-thumb {
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.step-duration-bar {
  width: 80px;
  flex-shrink: 0;
  height: 4px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 2px;
  margin-top: 8px;
  margin-left: 12px;
}

.duration-fill {
  height: 100%;
  border-radius: 2px;
  min-width: 2px;
  transition: width 0.3s;
}

.fill-pass {
  background: #52c41a;
}

.fill-fail {
  background: #ff4d4f;
}

.step-summary {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 13px;
}

.failure-analysis {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto;  /* 添加滚动支持 */
  padding-right: 4px;  /* 滚动条间距 */
}

.failure-reason-group {
  background: rgba(0, 0, 0, 0.02);
  border-radius: 8px;
  padding: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  margin-bottom: 10px;
}

.failure-reason-group:last-child {
  margin-bottom: 0;
}

.failure-reason-header {
  display: flex;
  align-items: center;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  margin-bottom: 8px;
}

.failure-reason-header .reason-name {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.85);
}

.failure-reason-header .reason-count {
  font-size: 13px;
  font-weight: 600;
  color: #f5222d;
  background: rgba(245, 34, 45, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.error-examples {
  margin-bottom: 8px;
}

.error-example {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.55);
  background: rgba(245, 34, 45, 0.05);
  padding: 6px 10px;
  border-radius: 4px;
  margin-bottom: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  line-height: 1.4;
}

.error-example:last-child {
  margin-bottom: 0;
}

.failed-scripts {
  margin-bottom: 8px;
}

.failed-script-item {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.65);
  padding: 4px 0 4px 16px;
  position: relative;
}

.failed-script-item::before {
  content: '•';
  position: absolute;
  left: 4px;
  color: rgba(0, 0, 0, 0.3);
}

.script-name {
  color: rgba(0, 0, 0, 0.75);
}

.more-scripts {
  font-size: 11px;
  color: rgba(0, 0, 0, 0.4);
  padding-left: 16px;
  font-style: italic;
}

.reason-suggestions {
  display: flex;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px dashed rgba(0, 0, 0, 0.06);
}

.suggestion-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.suggestion-list {
  flex: 1;
}

.suggestion-text {
  font-size: 12px;
  color: rgba(250, 173, 20, 0.85);
  line-height: 1.5;
  padding: 3px 0;
}

.no-failure {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.no-failure-content {
  text-align: center;
}

.no-failure-text {
  font-size: 16px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.85);
  margin-bottom: 4px;
}

.no-failure-sub {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.45);
}

.suggestion-item:last-child {
  margin-bottom: 0;
}

/* 脚本执行记录 - 问题分析与建议优化样式 */
.script-failure-analysis {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.analysis-section {
  background: rgba(0, 0, 0, 0.02);
  border-radius: 8px;
  padding: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.section-title {
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.85);
  margin-bottom: 10px;
}

.failure-reason-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.suggestion-list .suggestion-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: rgba(0, 0, 0, 0.75);
  line-height: 1.6;
  margin: 0;
}

.suggestion-bullet {
  color: #faad14;
  flex-shrink: 0;
}

.suggestion-list .suggestion-text {
  flex: 1;
  word-break: break-word;
}

.no-failure-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 20px 0;
}

.no-failure-state .no-failure-text {
  font-size: 15px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.85);
  margin-top: 8px;
}

.no-failure-state .no-failure-sub {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.45);
  margin-top: 4px;
}

/* 计划执行报告 - 问题分析与建议优化样式 */
.plan-failure-analysis {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* AI 智能分析按钮 */
.ai-analysis-trigger {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed rgba(255, 255, 255, 0.1);
  text-align: center;
}
</style>
