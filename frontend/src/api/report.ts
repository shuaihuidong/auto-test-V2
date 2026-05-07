import { get, post } from './request'

export interface Report {
  id: number
  execution: number
  execution_status: string
  execution_type?: string
  execution_plan_name: string | null
  execution_script_name: string | null
  summary: ReportSummary
  html_report: string | null
  pdf_report: string | null
  charts_data: ChartsData
  pass_rate: number
  total_duration: number
  created_at: string
}

export interface ReportSummary {
  execution_type?: string
  // 脚本报告字段
  total?: number
  step_types?: Record<string, any>
  // 计划报告字段
  total_scripts?: number
  total_cases?: number
  script_status?: Record<string, number>
  // 通用字段
  passed: number
  failed: number
  pass_rate: number
  total_duration: number
  execution_id?: number
  script_id?: number
  script_name?: string
  plan_name?: string
  started_at?: string
  completed_at?: string
}

export interface ChartsData {
  // 脚本报告字段
  trend?: ChartDataPoint[]
  distribution?: DistributionDataPoint[]
  failure_analysis?: FailureDataPoint[]
  // 计划报告字段
  scripts?: ScriptReportData[]
  status_distribution?: StatusDistributionPoint[]
  failed_scripts?: FailedScriptData[]
}

export interface ScriptReportData {
  id: number
  execution_id?: number
  name: string
  status: string
  total_count: number
  passed_count: number
  failed_count: number
  duration: number
  success: boolean
}

export interface StatusDistributionPoint {
  status: string
  count: number
}

export interface FailedScriptData {
  name: string
  execution_id?: number
  reason: string
}

export interface ChartDataPoint {
  index: number
  name: string
  duration: number
  success: boolean
  error?: string
  message?: string
}

export interface DistributionDataPoint {
  range: string
  count: number
}

export interface FailureDataPoint {
  reason: string
  count: number
}

export interface Screenshot {
  id: number
  execution: number
  step_index: number
  step_name: string
  image_path: string
  thumbnail_path?: string
  is_error: boolean
  error_message?: string
  timestamp: string
}

export interface TrendDataPoint {
  execution_id: number
  date: string
  time: string
  status: string
  pass_rate: number
  total: number
  passed: number
  failed: number
  duration: number
}

export interface TrendAnalysis {
  trend: TrendDataPoint[]
  summary: {
    total_executions: number
    successful_executions: number
    avg_pass_rate: number
    avg_duration: number
  }
}

export async function getReport(executionId: number): Promise<{ results: Report[] }> {
  return get(`/reports/?execution=${executionId}`)
}

export async function downloadHtmlReport(reportId: number): Promise<Blob> {
  const response = await fetch(`/api/reports/${reportId}/html/`, {
    credentials: 'include'
  })
  return response.blob()
}

export async function downloadPdfReport(reportId: number): Promise<Blob> {
  const response = await fetch(`/api/reports/${reportId}/pdf/`, {
    credentials: 'include'
  })
  return response.blob()
}

export async function getChartsData(): Promise<any> {
  return get('/reports/charts/')
}

export async function generateReport(executionId: number): Promise<Report> {
  return post('/reports/generate/', { execution_id: executionId })
}

export async function getTrendAnalysis(params: {
  script_id?: number
  project_id?: number
  days?: number
}): Promise<TrendAnalysis> {
  const query = new URLSearchParams()
  if (params.script_id) query.append('script_id', params.script_id.toString())
  if (params.project_id) query.append('project_id', params.project_id.toString())
  if (params.days) query.append('days', params.days.toString())
  return get(`/reports/trend_analysis/?${query.toString()}`)
}

export async function getExecutionScreenshots(executionId: number): Promise<Screenshot[]> {
  return get(`/executions/${executionId}/screenshots/`)
}
