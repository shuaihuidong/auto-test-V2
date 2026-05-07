import { get, post, put, del } from './request'
import instance from './request'
import type { Script, ScriptForm } from '@/types/script'

export async function getScriptList(projectId: number, params?: any): Promise<{ results: Script[]; count: number }> {
  return get(`/scripts/`, { project: projectId, ...params })
}

export async function getScript(id: number): Promise<Script> {
  return get(`/scripts/${id}/`)
}

export async function createScript(data: ScriptForm): Promise<Script> {
  return post('/scripts/', data)
}

export async function updateScript(id: number, data: Partial<ScriptForm>): Promise<Script> {
  return put(`/scripts/${id}/`, data)
}

export async function deleteScript(id: number): Promise<void> {
  return del(`/scripts/${id}/`)
}

export async function getScriptModules(params?: any): Promise<Script[]> {
  return get('/scripts/modules/', params)
}

export async function duplicateScript(id: number): Promise<Script> {
  return post(`/scripts/${id}/duplicate/`)
}

// ==================== V2.0 AI 功能 ====================

/** 自然语言转 Playwright 脚本（仅生成，不自动保存） */
export async function nl2script(data: {
  prompt: string
  context?: string
}): Promise<{
  steps: any[]
  raw_steps: any[]
  token_usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number }
  model: string
  provider: string
}> {
  return post('/scripts/nl2script/', data)
}

/** 保存 AI 生成的脚本（用户确认后调用） */
export async function nl2scriptSave(data: {
  steps: any[]
  project_id: number
  script_name: string
  prompt: string
}): Promise<{ script_id: number }> {
  return post('/scripts/nl2script_save/', data)
}

/** 批量自然语言转脚本（仅生成，不自动保存） */
export async function nl2scriptBatch(data: {
  prompts: string[]
  context?: string
  max_concurrency?: number
}): Promise<{
  results: any[]
  total: number
  success_count: number
  failed_count: number
  total_tokens: number
}> {
  return post('/scripts/nl2script_batch/', data)
}

/** AI 审查生成的脚本质量 */
export async function nl2scriptReview(items: { prompt: string; steps: any[] }[]): Promise<{
  reviews: { quality_score: number; intent_match: number; suggestions: string[]; passed: boolean }[]
}> {
  return post('/scripts/nl2script_review/', { items })
}

/** 批量保存用户确认的脚本 */
export async function nl2scriptBatchSave(data: {
  project_id: number
  scripts: { prompt: string; steps: any[]; script_name: string; description?: string; tags?: string[] }[]
}): Promise<{ saved_ids: number[] }> {
  return post('/scripts/nl2script_batch_save/', data)
}

/** 解析上传的 Excel/CSV 文件，返回列和行数据 */
export async function nl2scriptBatchParseFile(file: File): Promise<{
  columns: string[]
  rows: Record<string, any>[]
  total_rows: number
  file_name: string
}> {
  const formData = new FormData()
  formData.append('file', file)
  return instance.post('/scripts/nl2script_batch_parse_file/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
}

/** 沙盒验证步骤 */
export async function sandboxValidate(data: {
  steps: any[]
  url?: string
}): Promise<{
  valid: boolean
  error_count: number
  warning_count: number
  errors: { step_index: number; field: string; message: string }[]
  warnings: { step_index: number; message: string }[]
}> {
  return post('/scripts/sandbox_validate/', data)
}

/** 沙盒执行步骤（在服务端直接运行 Playwright） */
export async function sandboxExecute(data: {
  steps: any[]
  browser?: string
  headless?: boolean
}): Promise<{
  success: boolean
  results: {
    total: number
    passed: number
    failed: number
    steps: any[]
    logs: any[]
  }
  error?: string
}> {
  return instance.post('/scripts/sandbox_execute/', data, { timeout: 120000 })
}

// ==================== 批量任务中心 ====================

/** 批量任务信息 */
export interface BatchTaskInfo {
  id: number
  name: string
  status: 'pending' | 'running' | 'reviewing' | 'completed' | 'failed'
  total_count: number
  completed_count: number
  failed_count: number
  results: BatchTaskResult[]
  error_message: string
  created_by: number
  created_by_name: string
  created_at: string
  updated_at: string
}

export interface BatchTaskResult {
  index: number
  prompt: string
  success: boolean
  steps: any[]
  error: string
  token_usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number }
  review?: {
    quality_score: number
    intent_match: number
    suggestions: string[]
    passed: boolean
  }
}

/** 创建批量生成任务 */
export async function createBatchTask(data: {
  name: string
  prompts: string[]
  context?: string
}): Promise<BatchTaskInfo> {
  return post('/scripts/batch_tasks/', data)
}

/** 获取批量任务列表 */
export async function getBatchTaskList(): Promise<BatchTaskInfo[]> {
  return get('/scripts/batch_tasks/')
}

/** 获取批量任务详情 */
export async function getBatchTask(id: number): Promise<BatchTaskInfo> {
  return get(`/scripts/batch_tasks/${id}/`)
}

/** 删除批量任务 */
export async function deleteBatchTask(id: number): Promise<void> {
  return del(`/scripts/batch_tasks/${id}/`)
}

/** 保存选中的生成结果为脚本 */
export async function saveBatchTaskScripts(taskId: number, data: {
  project_id: number
  items: { index: number; script_name: string; steps: any[] }[]
}): Promise<{ saved_ids: number[] }> {
  return post(`/scripts/batch_tasks/${taskId}/save_scripts/`, data)
}

/** 删除选中的任务结果条目 */
export async function deleteBatchTaskResults(taskId: number, data: {
  indexes: number[]
}): Promise<BatchTaskInfo> {
  return post(`/scripts/batch_tasks/${taskId}/delete_results/`, data)
}

/** 重新生成选中的任务结果 */
export async function regenerateBatchTaskResults(taskId: number, data: {
  indexes: number[]
}): Promise<{ message: string }> {
  return post(`/scripts/batch_tasks/${taskId}/regenerate_results/`, data)
}

// 导出 API 对象供组件使用
export const scriptApi = {
  getList: (projectId: number, params?: any) => getScriptList(projectId, params),
  get: getScript,
  create: createScript,
  update: updateScript,
  delete: deleteScript,
  getModules: getScriptModules,
  duplicate: duplicateScript,
  nl2script,
  nl2scriptSave,
  nl2scriptBatch,
  nl2scriptReview,
  nl2scriptBatchSave,
  nl2scriptBatchParseFile,
  sandboxValidate,
  sandboxExecute,
  createBatchTask,
  getBatchTaskList,
  getBatchTask,
  deleteBatchTask,
  saveBatchTaskScripts,
  deleteBatchTaskResults,
  regenerateBatchTaskResults,
}
