export interface Execution {
  id: number
  execution_type: 'plan' | 'script'
  execution_type_display: string
  parent: number | null
  plan: number | null
  plan_name: string | null
  script: number | null
  script_name: string | null
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped'
  status_display: string
  result: ExecutionResult
  duration: number
  passed_count: number
  failed_count: number
  total_count: number
  children_count: number
  children?: Execution[]
  childrenLoading?: boolean
  started_at: string | null
  completed_at: string | null
  created_by: number
  created_by_name: string
  created_at: string
}

export interface ExecutionResult {
  total: number
  passed: number
  failed: number
  steps: StepResult[]
  logs: LogEntry[]
  screenshots: ScreenshotEntry[]
  error?: string
}

export interface StepResult {
  index: number
  name: string
  type: string
  success: boolean
  message: string
  duration: number
  error?: string
}

export interface LogEntry {
  step: number
  message: string
  level: 'info' | 'error' | 'warning'
  timestamp: string
}

export interface ScreenshotEntry {
  step: number
  path: string
}

export interface ExecutionCreateForm {
  plan_id?: number
  script_id?: number
  executor_id?: number
  concurrent?: number
  execution_mode?: string
}
