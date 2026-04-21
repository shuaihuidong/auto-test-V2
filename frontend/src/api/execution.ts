import { get, post } from './request'
import type { Execution, ExecutionCreateForm } from '@/types/execution'

export async function getExecutionList(params?: any): Promise<{ results: Execution[]; count: number }> {
  return get('/executions/', params)
}

export async function getExecution(id: number): Promise<Execution> {
  return get(`/executions/${id}/`)
}

export async function createExecution(data: ExecutionCreateForm): Promise<Execution> {
  return post('/executions/', data)
}

export async function stopExecution(id: number): Promise<{ message: string }> {
  return post(`/executions/${id}/stop/`)
}

export async function getExecutionLogs(id: number): Promise<{ logs: any[] }> {
  return get(`/executions/${id}/logs/`)
}

export async function getExecutionStatistics(): Promise<any> {
  return get('/executions/statistics/')
}

// ==================== V2.0 自愈 & Trace ====================

/** 触发智能自愈分析 */
export async function healExecution(
  executionId: number,
  data: { script_id: number; step_index: number; error_message: string; dom_snapshot?: string }
): Promise<{
  heal_status: string
  original_locator: string
  suggested_locator: string
  suggested_locator_platform: { type: string; value: string }
  locator_type: string
  confidence: number
  reason: string
  auto_applied: boolean
  heal_log_id: number
  token_usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number }
}> {
  return post(`/executions/${executionId}/heal/`, data)
}

/** 获取执行的自愈日志 */
export async function getHealLogs(executionId: number): Promise<any[]> {
  const res = await get(`/executions/${executionId}/heal_logs/`)
  return Array.isArray(res) ? res : []
}

/** 手动应用自愈建议 */
export async function applyHeal(healLogId: number): Promise<{
  message: string
  script_id: number
  step_index: number
  new_locator: { type: string; value: string }
}> {
  return post('/executions/heal_apply/', { heal_log_id: healLogId })
}

// 导出 API 对象供组件使用
export const executionApi = {
  getList: getExecutionList,
  get: getExecution,
  create: createExecution,
  stop: stopExecution,
  getLogs: getExecutionLogs,
  getStatistics: getExecutionStatistics,
  heal: healExecution,
  getHealLogs,
  applyHeal,
}
