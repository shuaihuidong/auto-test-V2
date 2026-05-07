import { get, post, put, del } from './request'

// ==================== AI 配置 ====================

export interface AISettingItem {
  id: number
  key: string
  value: string
  category: string
  description: string
  is_secret: boolean
  updated_at: string
}

export interface AIConfigCheck {
  configured: boolean
  primary_provider: string
  fallback_provider: string
}

export async function getAISettings(): Promise<AISettingItem[]> {
  return get('/settings/ai/')
}

export async function updateAISettings(settings: { key: string; value: string }[]): Promise<AISettingItem[]> {
  return put('/settings/ai/', { settings })
}

export async function checkAIConfig(): Promise<AIConfigCheck> {
  return get('/settings/ai/check/')
}

// ==================== 执行引擎 ====================

export interface ExecutionEngineStatus {
  max_workers: number
  active: number
  queued: number
  db_config_value: number
  needs_restart: boolean
}

export async function getExecutionEngineStatus(): Promise<ExecutionEngineStatus> {
  return get('/settings/execution/status/')
}

// ==================== Prompt 模板 ====================

export interface PromptTemplate {
  id: number
  service: 'healing' | 'nl2script'
  scenario: 'strict' | 'relaxed' | 'custom'
  name: string
  system_prompt: string
  description: string
  is_active: boolean
  temperature: number
  updated_at: string
}

export async function getPromptTemplates(params?: { service?: string }): Promise<PromptTemplate[]> {
  return get('/settings/prompts/', params)
}

export async function createPromptTemplate(data: Partial<PromptTemplate>): Promise<PromptTemplate> {
  return post('/settings/prompts/', data)
}

export async function updatePromptTemplate(id: number, data: Partial<PromptTemplate>): Promise<PromptTemplate> {
  return put(`/settings/prompts/${id}/`, data)
}

export async function activatePromptTemplate(id: number): Promise<PromptTemplate> {
  return put(`/settings/prompts/${id}/activate/`)
}

export async function deletePromptTemplate(id: number): Promise<void> {
  return del(`/settings/prompts/${id}/`)
}

// 导出 API 对象
export const settingsApi = {
  getAISettings,
  updateAISettings,
  checkAIConfig,
  getPromptTemplates,
  createPromptTemplate,
  updatePromptTemplate,
  activatePromptTemplate,
  deletePromptTemplate,
}
