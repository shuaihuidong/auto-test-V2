/**
 * Step Configuration
 * Dynamic step library definitions for web, mobile, and API testing
 */

import type { StepCategory, StepDefinition, ScriptType } from '@/types/script-editor'
import {
  // Navigation Icons
  GlobalOutlined,
  ArrowDownOutlined,
  SwapOutlined,
  ReloadOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
  // Interaction Icons
  ControlOutlined,
  FormOutlined,
  CheckSquareOutlined,
  BorderOutlined,
  OrderedListOutlined,
  RocketOutlined,
  CameraOutlined,
  DragOutlined,
  DeleteOutlined,
  // Keyboard Icons
  CodeOutlined,
  ThunderboltOutlined,
  // Assertion Icons
  CheckCircleOutlined,
  FileTextOutlined,
  LinkOutlined,
  SearchOutlined,
  EyeOutlined,
  UnlockOutlined,
  // Wait Icons
  ClockCircleOutlined,
  HourglassOutlined,
  // File Icons
  UploadOutlined,
  DownloadOutlined,
  // Data Icons
  SaveFilled,
  ExportOutlined,
  CloudServerOutlined,
  // Advanced Icons
  PictureOutlined,
  PlusSquareOutlined,
  MinusSquareOutlined,
  // Mobile Icons
  MobileOutlined,
  TabletOutlined,
  PhoneOutlined,
  SyncOutlined,
  // API Icons
  ApiOutlined
} from '@ant-design/icons-vue'

// ============================================
// WEB STEP DEFINITIONS
// ============================================

const webStepCategories: StepCategory[] = [
  {
    name: 'navigation',
    label: '页面导航',
    icon: GlobalOutlined,
    steps: [
      {
        type: 'goto',
        label: '打开URL',
        icon: GlobalOutlined,
        defaultParams: { url: '' },
        description: '导航到指定URL地址',
        paramSchema: [
          { name: 'url', label: 'URL地址', type: 'text', required: true, placeholder: 'https://example.com' }
        ]
      },
      {
        type: 'refresh',
        label: '刷新页面',
        icon: ReloadOutlined,
        defaultParams: {},
        description: '重新加载当前页面'
      },
      {
        type: 'back',
        label: '后退',
        icon: ArrowLeftOutlined,
        defaultParams: {},
        description: '返回浏览器历史上一页'
      },
      {
        type: 'forward',
        label: '前进',
        icon: ArrowRightOutlined,
        defaultParams: {},
        description: '前进到浏览器历史下一页'
      },
      {
        type: 'scroll',
        label: '滚动页面',
        icon: ArrowDownOutlined,
        defaultParams: { scroll_type: 'position', x: 0, y: 0 },
        description: '滚动页面到指定位置',
        paramSchema: [
          { name: 'scroll_type', label: '滚动方式', type: 'select', required: true, options: [
            { label: '到指定坐标', value: 'position' },
            { label: '到元素位置', value: 'element' },
            { label: '到底部', value: 'bottom' }
          ]},
          { name: 'locator', label: '元素定位器', type: 'locator', showIf: (p) => p.scroll_type === 'element' },
          { name: 'x', label: 'X坐标', type: 'number', default: 0, showIf: (p) => p.scroll_type === 'position' },
          { name: 'y', label: 'Y坐标', type: 'number', default: 0, showIf: (p) => p.scroll_type === 'position' }
        ]
      }
    ]
  },
  {
    name: 'element',
    label: '元素操作',
    icon: ControlOutlined,
    steps: [
      {
        type: 'click',
        label: '点击',
        icon: ControlOutlined,
        defaultParams: { locator: { type: 'css', value: '' } },
        description: '单击指定元素',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator', required: true }
        ]
      },
      {
        type: 'double_click',
        label: '双击',
        icon: ControlOutlined,
        defaultParams: { locator: { type: 'css', value: '' } },
        description: '双击指定元素',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator', required: true }
        ]
      },
      {
        type: 'right_click',
        label: '右键点击',
        icon: ControlOutlined,
        defaultParams: { locator: { type: 'css', value: '' } },
        description: '右键点击指定元素',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator', required: true }
        ]
      },
      {
        type: 'hover',
        label: '悬停',
        icon: DragOutlined,
        defaultParams: { locator: { type: 'css', value: '' } },
        description: '鼠标悬停在指定元素上',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator', required: true }
        ]
      },
      {
        type: 'input',
        label: '输入文本',
        icon: FormOutlined,
        defaultParams: {
          locator: { type: 'css', value: '' },
          value: '',
          clear_first: true
        },
        description: '在输入框中输入文本',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator', required: true },
          { name: 'value', label: '输入内容', type: 'text', required: true },
          { name: 'clear_first', label: '输入前清空', type: 'checkbox', default: true }
        ]
      },
      {
        type: 'select',
        label: '下拉选择',
        icon: OrderedListOutlined,
        defaultParams: { locator: { type: 'css', value: '' }, value: '' },
        description: '在下拉列表中选择选项',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator', required: true },
          { name: 'value', label: '选项值', type: 'text', required: true }
        ]
      },
      {
        type: 'checkbox',
        label: '复选框',
        icon: CheckSquareOutlined,
        defaultParams: { locator: { type: 'css', value: '' }, checked: true },
        description: '勾选或取消勾选复选框',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator', required: true },
          { name: 'checked', label: '是否勾选', type: 'checkbox', default: true }
        ]
      },
      {
        type: 'radio',
        label: '单选框',
        icon: BorderOutlined,
        defaultParams: { locator: { type: 'css', value: '' } },
        description: '选择单选按钮',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator', required: true }
        ]
      }
    ]
  },
  {
    name: 'assertion',
    label: '断言验证',
    icon: CheckCircleOutlined,
    steps: [
      {
        type: 'assert_text',
        label: '文本校验',
        icon: SearchOutlined,
        defaultParams: {
          locator: { type: 'css', value: '' },
          text: ''
        },
        description: '验证页面或元素中是否包含指定文本',
        paramSchema: [
          { name: 'locator', label: '元素定位器(可选)', type: 'locator', description: '留空则验证整个页面' },
          { name: 'text', label: '期望文本', type: 'text', required: true }
        ]
      },
      {
        type: 'assert_element',
        label: '元素存在',
        icon: EyeOutlined,
        defaultParams: { locator: { type: 'css', value: '' } },
        description: '验证指定元素是否存在',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator', required: true }
        ]
      },
      {
        type: 'assert_visible',
        label: '可见性',
        icon: EyeOutlined,
        defaultParams: { locator: { type: 'css', value: '' } },
        description: '验证指定元素是否可见',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator', required: true }
        ]
      },
      {
        type: 'assert_enabled',
        label: '可用性',
        icon: UnlockOutlined,
        defaultParams: { locator: { type: 'css', value: '' }, enabled: true },
        description: '验证指定元素是否可用',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator', required: true },
          { name: 'enabled', label: '期望状态', type: 'select', required: true, options: [
            { label: '可用', value: true },
            { label: '不可用', value: false }
          ]}
        ]
      },
      {
        type: 'assert_title',
        label: '标题校验',
        icon: FileTextOutlined,
        defaultParams: { expected: '' },
        description: '验证页面标题',
        paramSchema: [
          { name: 'expected', label: '期望标题', type: 'text', required: true }
        ]
      },
      {
        type: 'assert_url',
        label: 'URL校验',
        icon: LinkOutlined,
        defaultParams: { expected: '' },
        description: '验证当前页面URL',
        paramSchema: [
          { name: 'expected', label: '期望URL', type: 'text', required: true, placeholder: 'https://example.com/page' }
        ]
      }
    ]
  },
  {
    name: 'wait',
    label: '等待',
    icon: ClockCircleOutlined,
    steps: [
      {
        type: 'wait',
        label: '固定等待',
        icon: ClockCircleOutlined,
        defaultParams: { wait_type: 'fixed', duration: 1 },
        description: '等待指定秒数',
        paramSchema: [
          { name: 'duration', label: '等待时间(秒)', type: 'number', required: true, default: 1, min: 0.1 }
        ]
      },
      {
        type: 'wait_element',
        label: '等待元素（通常不需要）',
        icon: HourglassOutlined,
        defaultParams: {
          locator: { type: 'css', value: '' },
          timeout: 10
        },
        description: '等待元素出现在页面上。注意：Playwright 的 click/input 等操作已内置自动等待，通常不需要手动添加此步骤',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator', required: true },
          { name: 'timeout', label: '超时时间(秒)', type: 'number', default: 10, min: 1 }
        ]
      },
      {
        type: 'wait_text',
        label: '等待文本',
        icon: SearchOutlined,
        defaultParams: {
          locator: { type: 'css', value: '' },
          text: '',
          timeout: 10
        },
        description: '等待文本出现在页面或元素中',
        paramSchema: [
          { name: 'locator', label: '元素定位器(可选)', type: 'locator', description: '留空则在整页中查找' },
          { name: 'text', label: '等待的文本', type: 'text', required: true },
          { name: 'timeout', label: '超时时间(秒)', type: 'number', default: 10, min: 1 }
        ]
      }
    ]
  },
  {
    name: 'window',
    label: '窗口/框架',
    icon: SwapOutlined,
    steps: [
      {
        type: 'switch_window',
        label: '切换窗口',
        icon: SwapOutlined,
        defaultParams: {
          switch_type: 'window',
          name_or_index: ''
        },
        description: '切换到指定窗口',
        paramSchema: [
          { name: 'name_or_index', label: '窗口名称或索引', type: 'text', required: true, placeholder: '窗口名称或数字索引' }
        ]
      },
      {
        type: 'switch_frame',
        label: '切换框架',
        icon: PictureOutlined,
        defaultParams: {
          switch_type: 'frame',
          name_or_index: ''
        },
        description: '切换到指定iframe',
        paramSchema: [
          { name: 'name_or_index', label: '框架名称或索引', type: 'text', required: true, placeholder: 'iframe名称或数字索引' }
        ]
      },
      {
        type: 'switch_default',
        label: '切换到主文档',
        icon: PlusSquareOutlined,
        defaultParams: { switch_type: 'default' },
        description: '切换回主文档'
      },
      {
        type: 'new_tab',
        label: '打开新标签',
        icon: PlusSquareOutlined,
        defaultParams: { url: '' },
        description: '在新标签页中打开URL',
        paramSchema: [
          { name: 'url', label: 'URL地址', type: 'text', placeholder: 'https://example.com' }
        ]
      },
      {
        type: 'close_tab',
        label: '关闭标签',
        icon: MinusSquareOutlined,
        defaultParams: {},
        description: '关闭当前标签页'
      }
    ]
  },
  {
    name: 'keyboard',
    label: '键盘操作',
    icon: CodeOutlined,
    steps: [
      {
        type: 'press_key',
        label: '按键',
        icon: CodeOutlined,
        defaultParams: { key: '' },
        description: '按下指定键',
        paramSchema: [
          { name: 'key', label: '按键', type: 'text', required: true, placeholder: 'ENTER, SPACE, TAB, A-Z 等' }
        ]
      },
      {
        type: 'press_keys',
        label: '组合键',
        icon: ThunderboltOutlined,
        defaultParams: { keys: '' },
        description: '按下组合键（如Ctrl+A）',
        paramSchema: [
          { name: 'keys', label: '组合键', type: 'text', required: true, placeholder: 'CTRL+A, SHIFT+TAB 等' }
        ]
      }
    ]
  },
  {
    name: 'file',
    label: '文件操作',
    icon: UploadOutlined,
    steps: [
      {
        type: 'upload',
        label: '上传文件',
        icon: UploadOutlined,
        defaultParams: {
          locator: { type: 'css', value: '' },
          file_path: ''
        },
        description: '上传文件到指定输入框',
        paramSchema: [
          { name: 'locator', label: '文件输入框定位器', type: 'locator', required: true },
          { name: 'file_path', label: '文件路径', type: 'text', required: true, placeholder: '/path/to/file.txt' }
        ]
      },
      {
        type: 'download',
        label: '下载文件',
        icon: DownloadOutlined,
        defaultParams: {
          url: '',
          save_path: '',
          wait_time: 5
        },
        description: '下载并验证文件',
        paramSchema: [
          { name: 'url', label: '下载链接', type: 'text', required: true },
          { name: 'save_path', label: '保存路径', type: 'text', placeholder: '/path/to/save/file.txt' },
          { name: 'wait_time', label: '等待时间(秒)', type: 'number', default: 5 }
        ]
      }
    ]
  },
  {
    name: 'data',
    label: '数据操作',
    icon: CloudServerOutlined,
    steps: [
      {
        type: 'set_variable',
        label: '设置变量',
        icon: SaveFilled,
        defaultParams: { name: '', value: '' },
        description: '设置一个测试变量的值',
        paramSchema: [
          { name: 'name', label: '变量名', type: 'text', required: true },
          { name: 'value', label: '变量值', type: 'text', required: true }
        ]
      },
      {
        type: 'extract_variable',
        label: '提取变量',
        icon: ExportOutlined,
        defaultParams: {
          name: '',
          locator: { type: 'css', value: '' },
          extract_type: 'text',
          attribute: '',
          pattern: ''
        },
        description: '从页面元素提取数据到变量',
        paramSchema: [
          { name: 'name', label: '变量名', type: 'text', required: true },
          { name: 'extract_type', label: '提取类型', type: 'select', required: true, options: [
            { label: '文本内容', value: 'text' },
            { label: '属性值', value: 'attribute' },
            { label: '输入值', value: 'value' },
            { label: 'URL', value: 'url' },
            { label: '页面标题', value: 'title' },
            { label: 'Cookie', value: 'cookie' }
          ]},
          { name: 'locator', label: '元素定位器', type: 'locator', showIf: (p) => ['text','attribute','value'].includes(p.extract_type) },
          { name: 'attribute', label: '属性名', type: 'text', showIf: (p) => p.extract_type === 'attribute' },
          { name: 'cookie_name', label: 'Cookie名称', type: 'text', showIf: (p) => p.extract_type === 'cookie' },
          { name: 'pattern', label: '正则提取', type: 'text', placeholder: '可选，如 [0-9]+' }
        ]
      }
    ]
  },
  {
    name: 'advanced',
    label: '高级操作',
    icon: RocketOutlined,
    steps: [
      {
        type: 'screenshot',
        label: '截图',
        icon: CameraOutlined,
        defaultParams: {
          filename: '',
          full_page: false
        },
        description: '截取当前页面或元素截图',
        paramSchema: [
          { name: 'filename', label: '文件名', type: 'text', placeholder: 'screenshot.png' },
          { name: 'full_page', label: '整页截图', type: 'checkbox', default: false }
        ]
      },
      {
        type: 'execute_script',
        label: '执行脚本',
        icon: CodeOutlined,
        defaultParams: { script: '' },
        description: '执行JavaScript代码',
        paramSchema: [
          { name: 'script', label: 'JavaScript代码', type: 'textarea', required: true, placeholder: 'return document.title;' }
        ]
      }
    ]
  }
]

// ============================================
// MOBILE STEP DEFINITIONS
// ============================================

const mobileStepCategories: StepCategory[] = [
  {
    name: 'device',
    label: '设备控制',
    icon: MobileOutlined,
    steps: [
      {
        type: 'swipe',
        label: '滑动屏幕',
        icon: ControlOutlined,
        defaultParams: {
          direction: 'up',
          duration_ms: 500
        },
        description: '在屏幕上滑动',
        paramSchema: [
          { name: 'direction', label: '滑动方向', type: 'select', required: true, options: [
            { label: '向上', value: 'up' },
            { label: '向下', value: 'down' },
            { label: '向左', value: 'left' },
            { label: '向右', value: 'right' }
          ]},
          { name: 'duration_ms', label: '持续时间(ms)', type: 'number', default: 500 }
        ]
      },
      {
        type: 'tap',
        label: '点击',
        icon: ControlOutlined,
        defaultParams: {
          locator: { type: 'css', value: '' },
          x: 0,
          y: 0
        },
        description: '点击屏幕或元素',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator' },
          { name: 'x', label: 'X坐标', type: 'number', default: 0, description: '不使用元素定位时有效' },
          { name: 'y', label: 'Y坐标', type: 'number', default: 0, description: '不使用元素定位时有效' }
        ]
      },
      {
        type: 'long_press',
        label: '长按',
        icon: ControlOutlined,
        defaultParams: {
          locator: { type: 'css', value: '' },
          duration_ms: 1000
        },
        description: '长按元素',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator', required: true },
          { name: 'duration_ms', label: '持续时间(ms)', type: 'number', default: 1000 }
        ]
      },
      {
        type: 'rotate',
        label: '横竖屏切换',
        icon: SyncOutlined,
        defaultParams: { orientation: 'portrait' },
        description: '切换设备屏幕方向',
        paramSchema: [
          { name: 'orientation', label: '屏幕方向', type: 'select', required: true, options: [
            { label: '竖屏', value: 'portrait' },
            { label: '横屏', value: 'landscape' }
          ]}
        ]
      },
      {
        type: 'shake',
        label: '摇一摇',
        icon: MobileOutlined,
        defaultParams: {},
        description: '模拟摇一摇操作'
      }
    ]
  },
  {
    name: 'app',
    label: '应用控制',
    icon: TabletOutlined,
    steps: [
      {
        type: 'launch_app',
        label: '启动应用',
        icon: RocketOutlined,
        defaultParams: {
          app_package: '',
          app_activity: ''
        },
        description: '启动指定应用',
        paramSchema: [
          { name: 'app_package', label: '应用包名', type: 'text', required: true, placeholder: 'com.example.app' },
          { name: 'app_activity', label: 'Activity', type: 'text', placeholder: 'com.example.app.MainActivity' }
        ]
      },
      {
        type: 'close_app',
        label: '关闭应用',
        icon: MinusSquareOutlined,
        defaultParams: {},
        description: '关闭当前应用'
      },
      {
        type: 'reset_app',
        label: '重置应用',
        icon: ReloadOutlined,
        defaultParams: {},
        description: '重置应用到初始状态'
      },
      {
        type: 'install_app',
        label: '安装应用',
        icon: DownloadOutlined,
        defaultParams: { app_path: '' },
        description: '安装应用到设备',
        paramSchema: [
          { name: 'app_path', label: '应用文件路径', type: 'text', required: true, placeholder: '/path/to/app.apk' }
        ]
      },
      {
        type: 'uninstall_app',
        label: '卸载应用',
        icon: DeleteOutlined,
        defaultParams: { app_package: '' },
        description: '从设备卸载应用',
        paramSchema: [
          { name: 'app_package', label: '应用包名', type: 'text', required: true, placeholder: 'com.example.app' }
        ]
      }
    ]
  },
  {
    name: 'context',
    label: '上下文切换',
    icon: SwapOutlined,
    steps: [
      {
        type: 'switch_context',
        label: '切换上下文',
        icon: SwapOutlined,
        defaultParams: { context: '' },
        description: '切换到NATIVE_APP或WEBVIEW',
        paramSchema: [
          { name: 'context', label: '上下文名称', type: 'select', required: true, options: [
            { label: '原生应用', value: 'NATIVE_APP' },
            { label: 'WebView (自动)', value: 'WEBVIEW' }
          ]}
        ]
      },
      {
        type: 'switch_to_web',
        label: '切换到Web',
        icon: GlobalOutlined,
        defaultParams: {},
        description: '切换到WebView上下文'
      },
      {
        type: 'switch_to_native',
        label: '切换到Native',
        icon: PhoneOutlined,
        defaultParams: {},
        description: '切换到原生应用上下文'
      }
    ]
  },
  {
    name: 'mobile_assertion',
    label: '断言验证',
    icon: CheckCircleOutlined,
    steps: [
      {
        type: 'assert_element',
        label: '元素存在',
        icon: EyeOutlined,
        defaultParams: { locator: { type: 'css', value: '' } },
        description: '验证元素是否存在',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator', required: true }
        ]
      },
      {
        type: 'assert_text',
        label: '文本校验',
        icon: SearchOutlined,
        defaultParams: {
          locator: { type: 'css', value: '' },
          text: ''
        },
        description: '验证文本内容',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator', required: true },
          { name: 'text', label: '期望文本', type: 'text', required: true }
        ]
      }
    ]
  },
  {
    name: 'mobile_wait',
    label: '等待',
    icon: ClockCircleOutlined,
    steps: [
      {
        type: 'wait',
        label: '固定等待',
        icon: ClockCircleOutlined,
        defaultParams: { wait_type: 'fixed', duration: 1 },
        description: '等待指定秒数',
        paramSchema: [
          { name: 'wait_type', label: '等待类型', type: 'select', required: true, options: [
            { label: '固定等待', value: 'fixed' },
            { label: '随机等待', value: 'random' }
          ]},
          { name: 'duration', label: '等待时长(秒)', type: 'number', required: true, default: 1, min: 0.1, max: 3600 }
        ]
      },
      {
        type: 'wait_element',
        label: '等待元素',
        icon: HourglassOutlined,
        defaultParams: {
          locator: { type: 'css', value: '' },
          timeout: 10
        },
        description: '等待元素出现',
        paramSchema: [
          { name: 'locator', label: '元素定位器', type: 'locator', required: true },
          { name: 'timeout', label: '超时时间(秒)', type: 'number', required: true, default: 10, min: 1, max: 300 }
        ]
      }
    ]
  }
]

// ============================================
// API STEP DEFINITIONS
// ============================================

const apiStepCategories: StepCategory[] = [
  {
    name: 'request',
    label: '请求配置',
    icon: ApiOutlined,
    steps: [
      {
        type: 'http_request',
        label: 'HTTP请求',
        icon: ApiOutlined,
        defaultParams: {
          method: 'GET',
          url: '',
          headers: {},
          body: null,
          query_params: {},
          timeout: 30
        },
        description: '发送HTTP/HTTPS请求',
        paramSchema: [
          { name: 'method', label: '请求方法', type: 'select', required: true, options: [
            { label: 'GET', value: 'GET' },
            { label: 'POST', value: 'POST' },
            { label: 'PUT', value: 'PUT' },
            { label: 'DELETE', value: 'DELETE' },
            { label: 'PATCH', value: 'PATCH' },
            { label: 'HEAD', value: 'HEAD' },
            { label: 'OPTIONS', value: 'OPTIONS' }
          ]},
          { name: 'url', label: '请求URL', type: 'text', required: true, placeholder: 'https://api.example.com/endpoint' },
          { name: 'headers', label: '请求头', type: 'json', rows: 4, placeholder: '{"Content-Type": "application/json"}' },
          { name: 'body', label: '请求体', type: 'json', rows: 6, placeholder: '{"key": "value"}' },
          { name: 'query_params', label: '查询参数', type: 'json', rows: 4, placeholder: '{"param": "value"}' },
          { name: 'timeout', label: '超时时间(秒)', type: 'number', default: 30, min: 1, max: 300 }
        ]
      },
      {
        type: 'graphql_request',
        label: 'GraphQL请求',
        icon: ApiOutlined,
        defaultParams: {
          url: '',
          query: '',
          variables: {},
          headers: {}
        },
        description: '发送GraphQL请求',
        paramSchema: [
          { name: 'url', label: 'GraphQL端点', type: 'text', required: true, placeholder: 'https://api.example.com/graphql' },
          { name: 'query', label: 'GraphQL查询', type: 'textarea', required: true, rows: 8, placeholder: 'query { user { id name } }' },
          { name: 'variables', label: '变量', type: 'json', rows: 4, placeholder: '{"userId": "123"}' },
          { name: 'headers', label: '请求头', type: 'json', rows: 4, placeholder: '{"Content-Type": "application/json"}' }
        ]
      }
    ]
  },
  {
    name: 'validation',
    label: '响应验证',
    icon: CheckCircleOutlined,
    steps: [
      {
        type: 'assert_status',
        label: '状态码校验',
        icon: CheckCircleOutlined,
        defaultParams: { status_code: 200, operator: 'eq' },
        description: '验证HTTP响应状态码',
        paramSchema: [
          { name: 'status_code', label: '期望状态码', type: 'number', required: true, default: 200 },
          { name: 'operator', label: '比较操作符', type: 'select', required: true, options: [
            { label: '等于', value: 'eq' },
            { label: '不等于', value: 'ne' },
            { label: '大于', value: 'gt' },
            { label: '小于', value: 'lt' },
            { label: '大于等于', value: 'ge' },
            { label: '小于等于', value: 'le' }
          ]}
        ]
      },
      {
        type: 'assert_jsonpath',
        label: 'JSONPath校验',
        icon: SearchOutlined,
        defaultParams: {
          json_path: '',
          expected: '',
          operator: 'eq'
        },
        description: '使用JSONPath验证响应数据',
        paramSchema: [
          { name: 'json_path', label: 'JSONPath表达式', type: 'text', required: true, placeholder: '$.data.user.name' },
          { name: 'expected', label: '期望值', type: 'text', required: true },
          { name: 'operator', label: '比较操作符', type: 'select', required: true, options: [
            { label: '等于', value: 'eq' },
            { label: '不等于', value: 'ne' },
            { label: '包含', value: 'contains' },
            { label: '不包含', value: 'not_contains' },
            { label: '大于', value: 'gt' },
            { label: '小于', value: 'lt' }
          ]}
        ]
      },
      {
        type: 'assert_header',
        label: '响应头校验',
        icon: FileTextOutlined,
        defaultParams: {
          header_name: '',
          header_value: '',
          operator: 'contains'
        },
        description: '验证响应头',
        paramSchema: [
          { name: 'header_name', label: '响应头名称', type: 'text', required: true, placeholder: 'Content-Type' },
          { name: 'header_value', label: '期望值', type: 'text', placeholder: 'application/json' },
          { name: 'operator', label: '比较操作符', type: 'select', options: [
            { label: '包含', value: 'contains' },
            { label: '不包含', value: 'not_contains' },
            { label: '等于', value: 'eq' },
            { label: '不等于', value: 'ne' }
          ]}
        ]
      },
      {
        type: 'assert_response_time',
        label: '响应时间断言',
        icon: ClockCircleOutlined,
        defaultParams: { response_time: 1000, operator: 'le' },
        description: '验证API响应时间',
        paramSchema: [
          { name: 'response_time', label: '最大响应时间(ms)', type: 'number', required: true, default: 1000 },
          { name: 'operator', label: '比较操作符', type: 'select', required: true, options: [
            { label: '小于', value: 'lt' },
            { label: '小于等于', value: 'le' },
            { label: '大于', value: 'gt' },
            { label: '大于等于', value: 'ge' }
          ]}
        ]
      },
      {
        type: 'assert_body_contains',
        label: '响应体包含',
        icon: SearchOutlined,
        defaultParams: { text: '' },
        description: '验证响应体是否包含指定文本',
        paramSchema: [
          { name: 'text', label: '包含的文本', type: 'text', required: true, placeholder: '期望在响应体中出现的文本' }
        ]
      },
      {
        type: 'assert_schema',
        label: 'JSON Schema校验',
        icon: FileTextOutlined,
        defaultParams: { schema: '{}' },
        description: '验证JSON响应结构',
        paramSchema: [
          { name: 'schema', label: 'JSON Schema', type: 'textarea', rows: 10, required: true, placeholder: '{"type": "object", "properties": {...}}' }
        ]
      }
    ]
  },
  {
    name: 'extraction',
    label: '数据提取',
    icon: ExportOutlined,
    steps: [
      {
        type: 'extract_jsonpath',
        label: 'JSONPath提取',
        icon: ExportOutlined,
        defaultParams: {
          variable_name: '',
          json_path: ''
        },
        description: '使用JSONPath从响应中提取数据',
        paramSchema: [
          { name: 'variable_name', label: '变量名', type: 'text', required: true, placeholder: 'myVariable' },
          { name: 'json_path', label: 'JSONPath表达式', type: 'text', required: true, placeholder: '$.data.user.name' }
        ]
      },
      {
        type: 'extract_header',
        label: '提取响应头',
        icon: FileTextOutlined,
        defaultParams: {
          variable_name: '',
          header_name: ''
        },
        description: '从响应头提取数据',
        paramSchema: [
          { name: 'variable_name', label: '变量名', type: 'text', required: true, placeholder: 'myVariable' },
          { name: 'header_name', label: '响应头名称', type: 'text', required: true, placeholder: 'Content-Type' }
        ]
      },
      {
        type: 'set_variable',
        label: '设置变量',
        icon: SaveFilled,
        defaultParams: {
          variable_name: '',
          value: ''
        },
        description: '设置测试变量',
        paramSchema: [
          { name: 'variable_name', label: '变量名', type: 'text', required: true, placeholder: 'myVariable' },
          { name: 'value', label: '变量值', type: 'text', required: true }
        ]
      }
    ]
  },
  {
    name: 'api_wait',
    label: '等待',
    icon: ClockCircleOutlined,
    steps: [
      {
        type: 'wait',
        label: '固定等待',
        icon: ClockCircleOutlined,
        defaultParams: { wait_type: 'fixed', duration: 1 },
        description: '等待指定秒数',
        paramSchema: [
          { name: 'wait_type', label: '等待类型', type: 'select', required: true, options: [
            { label: '固定等待', value: 'fixed' },
            { label: '随机等待', value: 'random' }
          ]},
          { name: 'duration', label: '等待时长(秒)', type: 'number', required: true, default: 1, min: 0.1, max: 3600 }
        ]
      }
    ]
  }
]

// ============================================
// STEP CATEGORIES MAP
// ============================================

/**
 * Get step categories by script type
 */
export function getStepCategories(scriptType: ScriptType): StepCategory[] {
  switch (scriptType) {
    case 'web':
      return webStepCategories
    case 'mobile':
      return mobileStepCategories
    case 'api':
      return apiStepCategories
    default:
      return webStepCategories
  }
}

/**
 * Get all step definitions for a script type
 */
export function getAllSteps(scriptType: ScriptType) {
  const categories = getStepCategories(scriptType)
  const allSteps: Record<string, StepDefinition> = {}

  for (const category of categories) {
    for (const step of category.steps) {
      allSteps[step.type] = step
    }
  }

  return allSteps
}

/**
 * Get step definition by type
 */
export function getStepByType(stepType: string, scriptType: ScriptType): StepDefinition | undefined {
  const allSteps = getAllSteps(scriptType)
  return allSteps[stepType]
}

/**
 * Get default parameters for a step type
 * Returns a deep copy to prevent shared references between step instances
 */
export function getDefaultParams(stepType: string, scriptType: ScriptType) {
  const step = getStepByType(stepType, scriptType)
  return step?.defaultParams ? JSON.parse(JSON.stringify(step.defaultParams)) : {}
}

/**
 * Get step icon component
 */
export function getStepIcon(stepType: string, scriptType: ScriptType) {
  const step = getStepByType(stepType, scriptType)
  return step?.icon || FileTextOutlined
}

/**
 * Check if step type is valid for script type
 */
export function isValidStepForType(stepType: string, scriptType: ScriptType): boolean {
  return !!getStepByType(stepType, scriptType)
}

// ============================================
// FRONTEND→BACKEND STEP MAPPING
// ============================================

/**
 * Convert frontend-friendly step names to backend format.
 * Called when saving/executing scripts to normalize the step type field.
 */
export function toBackendStep(step: Record<string, any>): Record<string, any> {
  const { type, params } = step
  const result: Record<string, any> = { ...step, params: { ...params } }

  switch (type) {
    // assert_text → assert (assert_type: 'text')
    case 'assert_text':
      result.type = 'assert'
      result.params = {
        ...result.params,
        assert_type: 'text',
        expected: params?.text ?? ''
      }
      break

    // assert_element → assert (assert_type: 'exists')
    case 'assert_element':
      result.type = 'assert'
      result.params = { ...result.params, assert_type: 'exists' }
      break

    // assert_visible → assert (assert_type: 'visible')
    case 'assert_visible':
      result.type = 'assert'
      result.params = { ...result.params, assert_type: 'visible' }
      break

    // assert_enabled → assert (assert_type: 'enabled')
    case 'assert_enabled':
      result.type = 'assert'
      result.params = { ...result.params, assert_type: 'enabled' }
      break

    // assert_title → assert (assert_type: 'title')
    case 'assert_title':
      result.type = 'assert'
      result.params = {
        ...result.params,
        assert_type: 'title',
        expected: params?.expected ?? ''
      }
      break

    // assert_url → assert (assert_type: 'url')
    case 'assert_url':
      result.type = 'assert'
      result.params = {
        ...result.params,
        assert_type: 'url',
        expected: params?.expected ?? ''
      }
      break

    // wait (固定) → wait (wait_type: 'fixed', duration: 秒×1000)
    case 'wait':
      result.params = {
        ...result.params,
        wait_type: result.params.wait_type || 'fixed',
        duration: (result.params.duration ?? 1) * 1000
      }
      break

    // wait_element → wait (wait_type: 'selector', duration: timeout×1000)
    case 'wait_element':
      result.type = 'wait'
      result.params = {
        ...result.params,
        wait_type: 'selector',
        duration: (result.params.timeout ?? 10) * 1000
      }
      break

    // checkbox → click
    case 'checkbox':
      result.type = 'click'
      break

    // radio → click
    case 'radio':
      result.type = 'click'
      break

    default:
      // 其他步骤直接透传
      break
  }

  return result
}

// ============================================
// EXPORTS
// ============================================

export { webStepCategories, mobileStepCategories, apiStepCategories }

// Script type labels
export const SCRIPT_TYPE_LABELS: Record<ScriptType, string> = {
  web: 'Web自动化',
  mobile: '移动端自动化',
  api: 'API接口测试'
}

// Framework labels
export const FRAMEWORK_LABELS: Record<string, string> = {
  playwright: 'Playwright',
  appium: 'Appium',
  httprunner: 'HttpRunner'
}

// Script type icons
export const SCRIPT_TYPE_ICONS: Record<ScriptType, string> = {
  web: 'global',
  mobile: 'mobile',
  api: 'api'
}
