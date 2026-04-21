import { get, post, put, del } from './request'
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

/** 自然语言转 Playwright 脚本 */
export async function nl2script(data: {
  prompt: string
  context?: string
  save_to_project?: number
  script_name?: string
}): Promise<{
  steps: any[]
  raw_steps: any[]
  token_usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number }
  model: string
  provider: string
  script_id: number | null
}> {
  return post('/scripts/nl2script/', data)
}

/** 批量自然语言转脚本 */
export async function nl2scriptBatch(data: {
  prompts: string[]
  context?: string
  save_to_project?: number
  max_concurrency?: number
}): Promise<{
  results: any[]
  total: number
  success_count: number
  failed_count: number
  total_tokens: number
  saved_ids: number[]
}> {
  return post('/scripts/nl2script_batch/', data)
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
  nl2scriptBatch,
  sandboxValidate,
}
