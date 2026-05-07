/**
 * Script Editor Type Definitions
 * Comprehensive types for the multi-platform script editor
 */

// ============================================
// Script Type & Framework
// ============================================

/**
 * Supported script types for testing
 */
export type ScriptType = 'web' | 'mobile' | 'api'

/**
 * Supported testing frameworks
 */
export type Framework = 'playwright' | 'appium' | 'httprunner'

/**
 * Framework options available for each script type
 */
export const FRAMEWORK_MAP: Record<ScriptType, Framework[]> = {
  web: ['playwright'],
  mobile: ['appium'],
  api: ['httprunner']
}

// ============================================
// Locator Types
// ============================================

/**
 * Element locator strategies
 */
export type LocatorType =
  | 'css'
  | 'xpath'
  | 'id'
  | 'name'
  | 'class'
  | 'tag'
  | 'link_text'
  | 'text'
  | 'label'
  | 'placeholder'
  | 'role'
  | 'test_id'

/**
 * Element locator definition
 */
export interface Locator {
  type: LocatorType
  value: string
}

// ============================================
// Step Types
// ============================================

/**
 * All available step types across platforms
 */
export type StepType =
  // Web - Navigation
  | 'goto' | 'refresh' | 'back' | 'forward' | 'scroll'
  // Web - Element Interaction
  | 'click' | 'double_click' | 'right_click' | 'hover' | 'input' | 'clear'
  | 'select' | 'checkbox' | 'radio'
  // Web - Form Interaction
  | 'submit' | 'reset'
  // Web - Assertion
  | 'assert' | 'assert_text' | 'assert_element' | 'assert_visible' | 'assert_enabled'
  | 'assert_title' | 'assert_url' | 'assert_attribute' | 'assert_value'
  // Web - Wait
  | 'wait' | 'wait_element' | 'wait_text' | 'wait_url' | 'wait_title'
  // Web - Window/Frame
  | 'switch' | 'switch_window' | 'switch_frame' | 'switch_default' | 'new_tab' | 'close_tab'
  // Web - Screenshot
  | 'screenshot'
  // Web - Keyboard
  | 'press_key' | 'press_keys'
  // Web - File Operations
  | 'upload' | 'download'
  // Web - Storage & Cookies
  | 'get_cookie' | 'set_cookie' | 'delete_cookie'
  | 'get_storage' | 'set_storage' | 'delete_storage'
  // Web - Data Extraction
  | 'extract' | 'extract_json' | 'extract_table'
  // Web - Advanced
  | 'execute_script' | 'execute_async_script' | 'drag_and_drop'
  // Mobile - Device Control
  | 'swipe' | 'tap' | 'long_press' | 'rotate' | 'shake'
  // Mobile - App Control
  | 'install_app' | 'uninstall_app' | 'launch_app' | 'close_app' | 'reset_app'
  // Mobile - Device Actions
  | 'lock' | 'unlock' | 'push_file' | 'pull_file'
  // Mobile - Mobile Web
  | 'switch_context' | 'switch_to_web' | 'switch_to_native'
  // API - Request
  | 'request' | 'http_request' | 'graphql_request'
  // API - Validation
  | 'assert_status' | 'assert_jsonpath' | 'assert_header' | 'assert_response_time'
  | 'assert_schema' | 'assert_body_contains'
  // API - Data Processing
  | 'extract_jsonpath' | 'extract_header' | 'set_variable' | 'extract_variable'
  // Flow Control
  | 'if' | 'loop' | 'retry' | 'skip'
  // Module
  | 'module'

// ============================================
// Step Parameters
// ============================================

/**
 * Base parameter interface - all params extend this
 */
export interface StepParams {
  [key: string]: any

  // Common parameters
  timeout?: number
  description?: string
  enabled?: boolean

  // Navigation
  url?: string
  scroll_type?: 'top' | 'bottom' | 'custom' | 'element' | 'position'
  x?: number
  y?: number

  // Element interaction
  locator?: Locator
  value?: string
  values?: string[]
  text?: string
  clear_first?: boolean

  // Form interaction
  checked?: boolean
  selected?: string

  // Assertion
  expected?: string | number | boolean
  operator?: 'eq' | 'ne' | 'gt' | 'lt' | 'ge' | 'le' | 'contains' | 'matches' | 'not_contains'
  attribute?: string

  // Wait
  wait_type?: 'fixed' | 'random'
  duration?: number

  // Window/Frame
  switch_type?: 'window' | 'frame' | 'default' | 'context'
  name_or_index?: string | number

  // Keyboard
  key?: string
  keys?: string

  // File operations
  file_path?: string
  save_path?: string
  filename?: string
  full_page?: boolean

  // Storage/Cookies
  storage_type?: 'localStorage' | 'sessionStorage'
  cookie_name?: string
  cookie_value?: string
  cookie_domain?: string
  cookie_path?: string
  storage_key?: string

  // Data extraction
  extract_source?: 'text' | 'attribute' | 'value' | 'json' | 'table'
  variable_name?: string
  json_path?: string

  // Script execution
  script?: string
  args?: any[]

  // Drag and drop
  source_locator?: Locator
  target_locator?: Locator

  // Mobile specific
  direction?: 'up' | 'down' | 'left' | 'right'
  duration_ms?: number
  orientation?: 'portrait' | 'landscape'
  app_package?: string
  app_activity?: string
  context?: string

  // API specific
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'HEAD' | 'OPTIONS'
  headers?: Record<string, string>
  body?: any
  form_data?: Record<string, string>
  query_params?: Record<string, string>

  // Assertions (API)
  status_code?: number
  response_time?: number
  header_name?: string
  header_value?: string

  // Flow control
  condition?: string
  loop_count?: number
  loop_variable?: string
  retry_count?: number
  retry_delay?: number

  // Module
  module_id?: number
  module_name?: string
  module_params?: Record<string, any>
}

// ============================================
// Assertion Types
// ============================================

/**
 * Assertion operator types
 */
export type AssertionOperator =
  | 'eq'      // equals
  | 'ne'      // not equals
  | 'gt'      // greater than
  | 'lt'      // less than
  | 'ge'      // greater or equal
  | 'le'      // less or equal
  | 'contains'   // contains substring
  | 'not_contains' // does not contain
  | 'matches'     // regex matches
  | 'not_matches' // regex does not match
  | 'exists'      // element exists
  | 'not_exists'  // element does not exist
  | 'visible'     // element is visible
  | 'not_visible' // element is not visible
  | 'enabled'     // element is enabled
  | 'not_enabled' // element is not enabled
  | 'empty'       // value is empty
  | 'not_empty'   // value is not empty

/**
 * Assertion definition
 */
export interface Assertion {
  type: 'text' | 'attribute' | 'value' | 'url' | 'title' | 'status' | 'jsonpath' | 'header' | 'response_time'
  expected?: any
  operator?: AssertionOperator
  locator?: Locator
  attribute?: string
  json_path?: string
  header_name?: string
  timeout?: number
}

// ============================================
// Test Step
// ============================================

/**
 * Single test step definition
 */
export interface TestStep {
  id: string
  type: StepType
  name: string
  params: StepParams
  description?: string
  enabled?: boolean
  children?: TestStep[]  // For flow control steps (if, loop, retry)
}

// ============================================
// Script Definition
// ============================================

/**
 * Full script definition
 */
export interface Script {
  id?: number
  project: number
  project_name?: string
  name: string
  description?: string
  type: ScriptType
  framework: Framework
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
  created_by?: number
  created_by_name?: string
  step_count?: number
  created_at?: string
  updated_at?: string
}

/**
 * Script form data for create/update
 */
export interface ScriptForm {
  project: number
  name: string
  description: string
  type: ScriptType
  framework: Framework
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

// ============================================
// Canvas State
// ============================================

/**
 * Editor canvas state
 */
export interface CanvasState {
  steps: TestStep[]
  selectedStepId: string | null
  scriptType: ScriptType
  framework: Framework
  editorMode: 'visual' | 'json'
  clipboard: TestStep | null
  history: TestStep[][]
  historyIndex: number
}

// ============================================
// Step Category & Definition
// ============================================

/**
 * Component type (Vue component)
 */
export type Component = any

/**
 * Parameter schema for step configuration
 */
export interface ParamSchema {
  name: string
  label: string
  type: 'text' | 'number' | 'select' | 'checkbox' | 'radio' | 'textarea' | 'locator' | 'json'
  required?: boolean
  default?: any
  placeholder?: string
  options?: Array<{ label: string; value: any }>
  min?: number
  max?: number
  step?: number
  rows?: number
  description?: string
  showIf?: (params: StepParams) => boolean
}

/**
 * Step definition for palette
 */
export interface StepDefinition {
  type: StepType
  label: string
  icon: Component
  defaultParams: StepParams
  paramSchema?: ParamSchema[]
  description?: string
  platforms?: ScriptType[]
  frameworks?: Framework[]
}

/**
 * Step category in palette
 */
export interface StepCategory {
  name: string
  label: string
  icon: Component
  steps: StepDefinition[]
}

// ============================================
// Script Type & Framework Options
// ============================================

/**
 * Script type option
 */
export interface ScriptTypeOption {
  value: ScriptType
  label: string
  icon: string
  description: string
}

/**
 * Framework option
 */
export interface FrameworkOption {
  value: Framework
  label: string
  icon: string
  description?: string
}

/**
 * Complete script type selection
 */
export interface ScriptTypeSelection {
  type: ScriptType
  framework: Framework
}

// ============================================
// Flow Control Steps
// ============================================

/**
 * If condition step
 */
export interface IfStep extends TestStep {
  type: 'if'
  params: StepParams & {
    condition: string
  }
  children: TestStep[]
}

/**
 * Loop step
 */
export interface LoopStep extends TestStep {
  type: 'loop'
  params: StepParams & {
    loop_type: 'count' | 'while' | 'foreach'
    loop_count?: number
    loop_condition?: string
    loop_variable?: string
    loop_items?: string[]
  }
  children: TestStep[]
}

/**
 * Retry step
 */
export interface RetryStep extends TestStep {
  type: 'retry'
  params: StepParams & {
    retry_count: number
    retry_delay?: number
    stop_on_failure?: boolean
  }
  children: TestStep[]
}

// ============================================
// Module Reference
// ============================================

/**
 * Module call step
 */
export interface ModuleStep extends TestStep {
  type: 'module'
  params: StepParams & {
    module_id: number
    module_name: string
    module_params?: Record<string, any>
  }
}

// ============================================
// Execution Result Types
// ============================================

/**
 * Step execution status
 */
export type StepStatus = 'pending' | 'running' | 'passed' | 'failed' | 'skipped' | 'error'

/**
 * Step execution result
 */
export interface StepResult {
  stepId: string
  status: StepStatus
  startTime?: string
  endTime?: string
  duration?: number
  error?: string
  screenshot?: string
  logs?: string[]
  children?: StepResult[]
}

/**
 * Script execution result
 */
export interface ScriptResult {
  scriptId: number
  status: StepStatus
  startTime: string
  endTime: string
  duration: number
  steps: StepResult[]
  summary: {
    total: number
    passed: number
    failed: number
    skipped: number
  }
}

// ============================================
// Validation Types
// ============================================

/**
 * Validation result
 */
export interface ValidationResult {
  valid: boolean
  error?: string
  field?: string
}

// ============================================
// Drag & Drop Types
// ============================================

/**
 * Drag data transfer format
 */
export interface DragData {
  type: StepType
  label: string
  category: string
}

// ============================================
// Export/Import Types
// ============================================

/**
 * Export format options
 */
export type ExportFormat = 'json' | 'yaml' | 'python' | 'java' | 'javascript'

/**
 * Export options
 */
export interface ExportOptions {
  format: ExportFormat
  includeComments?: boolean
  includeScreenshots?: boolean
  indent?: number
}

/**
 * Import options
 */
export interface ImportOptions {
  format: ExportFormat
  overwrite?: boolean
  merge?: boolean
}

// ============================================
// Type Guards
// ============================================

/**
 * Check if step has children (flow control)
 */
export function isFlowControlStep(step: TestStep): step is IfStep | LoopStep | RetryStep {
  return ['if', 'loop', 'retry'].includes(step.type)
}

/**
 * Check if step is a module call
 */
export function isModuleStep(step: TestStep): step is ModuleStep {
  return step.type === 'module'
}

/**
 * Check if script type supports framework
 */
export function isFrameworkSupported(scriptType: ScriptType, framework: Framework): boolean {
  return FRAMEWORK_MAP[scriptType].includes(framework)
}

/**
 * Get step category for a step type
 */
export function getStepCategoryForType(type: StepType): string {
  const categoryMap: Partial<Record<StepType, string>> = {
    goto: 'navigation',
    refresh: 'navigation',
    back: 'navigation',
    forward: 'navigation',
    scroll: 'navigation',
    click: 'interaction',
    input: 'interaction',
    assert_text: 'assertion',
    assert_element: 'assertion',
    wait: 'wait',
    screenshot: 'advanced',
    http_request: 'request',
    assert_status: 'validation',
    swipe: 'device',
    tap: 'device'
  }
  return categoryMap[type] || 'other'
}
