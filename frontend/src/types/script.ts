export interface Locator {
  type: 'xpath' | 'id' | 'name' | 'class' | 'css' | 'tag' | 'link_text'
  value: string
}

export interface TestStep {
  id: string
  type: StepType
  name: string
  params: StepParams
  description?: string
}

export type StepType =
  | 'goto'
  | 'click'
  | 'input'
  | 'assert'
  | 'wait'
  | 'scroll'
  | 'switch'
  | 'screenshot'
  | 'execute_script'
  | 'module'
  | 'request'
  | 'extract'
  | 'set_variable'
  | 'extract_variable'
  | 'if'
  | 'loop'
  | 'retry'
  | 'skip'

export interface StepParams {
  [key: string]: any
  locator?: Locator
  url?: string
  value?: string
  expected?: any
  timeout?: number
  duration?: number
  script?: string
  module_id?: number
  method?: string
  headers?: Record<string, string>
  body?: any
  variable_name?: string
  json_path?: string
}

export interface Script {
  id: number
  project: number
  project_name: string
  name: string
  description: string
  type: 'web' | 'mobile' | 'api'
  framework: 'playwright' | 'appium' | 'httprunner'
  steps: TestStep[]
  variables?: Record<string, any>
  timeout?: number
  retry_count?: number
  tags?: string[]
  is_module: boolean
  module_name?: string
  data_source?: number
  data_source_name?: string
  data_driven: boolean
  created_by: number
  created_by_name: string
  step_count: number
  created_at: string
  updated_at: string
}

export interface ScriptForm {
  project: number
  name: string
  description: string
  type: 'web' | 'mobile' | 'api'
  framework: 'playwright' | 'appium' | 'httprunner'
  steps: TestStep[]
  variables?: Record<string, any>
  timeout?: number
  retry_count?: number
  tags?: string[]
  is_module: boolean
  module_name?: string
  data_source?: number
  data_driven: boolean
}

// Flow control step types
export interface FlowControlStep extends TestStep {
  children?: TestStep[]
}

// Assertion types
export type AssertionType =
  | 'text'
  | 'exists'
  | 'attribute'
  | 'url'
  | 'title'
  | 'contains'
  | 'not_contains'
  | 'regex'
  | 'numeric_compare'
  | 'page_contains'

// Variable extraction types
export type ExtractType =
  | 'text'
  | 'attribute'
  | 'value'
  | 'url'
  | 'title'
  | 'cookie'
