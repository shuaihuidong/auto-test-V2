<template>
  <div class="help-center">
    <div class="page-header">
      <h2>帮助中心</h2>
    </div>

    <a-row :gutter="24">
      <a-col :span="6">
        <a-menu
          v-model:selectedKeys="selectedKeys"
          mode="inline"
          theme="dark"
          @click="handleMenuClick"
          style="border-right: none;"
        >
          <a-menu-item key="quickstart">
            <RocketOutlined /> 新手入门
          </a-menu-item>
          <a-menu-item key="script">
            <CodeOutlined /> 脚本编辑
          </a-menu-item>
          <a-menu-item key="ai">
            <ThunderboltOutlined /> AI 功能
          </a-menu-item>
          <a-menu-item key="playwright">
            <LaptopOutlined /> Playwright 引擎
          </a-menu-item>
          <a-menu-item key="plan">
            <ScheduleOutlined /> 测试计划
          </a-menu-item>
          <a-menu-item key="execution">
            <PlayCircleOutlined /> 执行测试
          </a-menu-item>
          <a-menu-item key="report">
            <BarChartOutlined /> 测试报告
          </a-menu-item>
          <a-menu-item key="faq">
            <QuestionCircleOutlined /> 常见问题
          </a-menu-item>
        </a-menu>
      </a-col>

      <a-col :span="18">
        <a-card class="content-card">

          <!-- 新手入门 -->
          <div v-if="currentSection === 'quickstart'" class="help-content">
            <h3>新手入门</h3>
            <p>四步快速上手自动化测试平台。</p>

            <a-timeline>
              <a-timeline-item color="green">
                <template #dot><span class="timeline-number">1</span></template>
                <div class="timeline-content">
                  <h4>创建项目</h4>
                  <p>进入「项目管理」页面，点击「新建项目」，填写项目名称和类型。</p>
                </div>
              </a-timeline-item>

              <a-timeline-item>
                <template #dot><span class="timeline-number">2</span></template>
                <div class="timeline-content">
                  <h4>创建测试脚本</h4>
                  <p>进入项目详情，点击「新建脚本」，通过以下两种方式创建：</p>
                  <a-row :gutter="16">
                    <a-col :span="12">
                      <a-card size="small" title="可视化编辑">
                        <p>从左侧拖拽步骤到画布，点击步骤配置参数，适合精确控制每一步操作。</p>
                      </a-card>
                    </a-col>
                    <a-col :span="12">
                      <a-card size="small" title="AI 生成">
                        <p>用自然语言描述测试操作，AI 自动生成脚本步骤，适合快速创建。</p>
                      </a-card>
                    </a-col>
                  </a-row>
                </div>
              </a-timeline-item>

              <a-timeline-item>
                <template #dot><span class="timeline-number">3</span></template>
                <div class="timeline-content">
                  <h4>执行测试</h4>
                  <p>脚本保存后，点击「执行」按钮，系统启动浏览器按步骤自动执行。</p>
                </div>
              </a-timeline-item>

              <a-timeline-item color="gray">
                <template #dot><span class="timeline-number">4</span></template>
                <div class="timeline-content">
                  <h4>查看结果</h4>
                  <p>执行完成后查看报告：</p>
                  <ul>
                    <li>每个步骤的通过/失败状态</li>
                    <li>失败步骤的自动截图</li>
                    <li>测试统计数据和耗时分析</li>
                    <li>失败步骤可点击「AI 智能分析」获取修复建议</li>
                  </ul>
                </div>
              </a-timeline-item>
            </a-timeline>
          </div>

          <!-- 脚本编辑 -->
          <div v-if="currentSection === 'script'" class="help-content">
            <h3>脚本编辑</h3>
            <p>基于 Playwright 引擎，通过拖拽方式创建测试脚本。</p>

            <a-divider>编辑器布局</a-divider>

            <div class="editor-layout">
              <div class="layout-panel left">
                <div class="panel-header">步骤面板</div>
                <p>左侧：分类展示所有可用步骤</p>
              </div>
              <div class="layout-panel center">
                <div class="panel-header">画布</div>
                <p>中间：拖入步骤，按执行顺序排列</p>
              </div>
              <div class="layout-panel right">
                <div class="panel-header">属性面板</div>
                <p>右侧：点击步骤配置参数</p>
              </div>
            </div>

            <a-divider>步骤分类</a-divider>

            <a-row :gutter="[16, 16]">
              <a-col :span="8">
                <a-card title="页面导航" size="small">
                  <ul class="step-list">
                    <li><strong>打开URL</strong> - 访问指定网址</li>
                    <li><strong>刷新 / 后退 / 前进</strong> - 浏览器导航</li>
                    <li><strong>滚动页面</strong> - 滚到底部/元素/坐标</li>
                  </ul>
                </a-card>
              </a-col>
              <a-col :span="8">
                <a-card title="元素操作" size="small">
                  <ul class="step-list">
                    <li><strong>点击 / 双击 / 右键 / 悬停</strong></li>
                    <li><strong>输入文本</strong> - 填写表单</li>
                    <li><strong>下拉选择 / 复选框 / 单选框</strong></li>
                  </ul>
                </a-card>
              </a-col>
              <a-col :span="8">
                <a-card title="断言验证" size="small">
                  <ul class="step-list">
                    <li><strong>文本校验</strong> - 检查页面/元素文字</li>
                    <li><strong>元素存在 / 可见性 / 可用性</strong></li>
                    <li><strong>标题校验 / URL校验</strong></li>
                  </ul>
                </a-card>
              </a-col>
            </a-row>
            <a-row :gutter="[16, 16]" style="margin-top: 16px;">
              <a-col :span="8">
                <a-card title="等待" size="small">
                  <ul class="step-list">
                    <li><strong>固定等待</strong> - 等待指定秒数</li>
                    <li><strong>等待元素</strong> - 等待元素出现</li>
                    <li><strong>等待文本</strong> - 等待文本出现</li>
                  </ul>
                </a-card>
              </a-col>
              <a-col :span="8">
                <a-card title="窗口/框架" size="small">
                  <ul class="step-list">
                    <li><strong>切换窗口 / 切换框架</strong></li>
                    <li><strong>打开新标签 / 关闭标签</strong></li>
                    <li><strong>切换到主文档</strong></li>
                  </ul>
                </a-card>
              </a-col>
              <a-col :span="8">
                <a-card title="高级操作" size="small">
                  <ul class="step-list">
                    <li><strong>截图</strong> - 支持整页截图</li>
                    <li><strong>按键 / 组合键</strong></li>
                    <li><strong>上传/下载文件</strong></li>
                    <li><strong>执行 JavaScript</strong></li>
                  </ul>
                </a-card>
              </a-col>
            </a-row>

            <a-divider>定位器类型</a-divider>

            <a-card size="small">
              <a-table :columns="locatorColumns" :data-source="locatorData" :pagination="false" size="small" />
              <p style="margin-top: 12px; color: #666;">Playwright 推荐：优先使用 CSS Selector 和 ID，稳定性更高。</p>
            </a-card>

            <a-divider>常用技巧</a-divider>

            <a-collapse>
              <a-collapse-panel key="1" header="如何获取元素定位器？">
                <ol>
                  <li>在浏览器中按 F12 打开开发者工具</li>
                  <li>点击左上角的元素选择器图标</li>
                  <li>点击页面上的目标元素</li>
                  <li>右键代码高亮行 → Copy → Copy selector</li>
                </ol>
              </a-collapse-panel>
              <a-collapse-panel key="2" header="页面加载慢导致失败？">
                <p>Playwright 默认会自动等待元素可操作。如果仍失败，可添加「等待元素」步骤，设置更长的超时时间。</p>
              </a-collapse-panel>
              <a-collapse-panel key="3" header="如何复用变量？">
                <p>在「数据操作」中使用「设置变量」和「提取变量」步骤。在参数值中填写 <code>${变量名}</code> 即可引用。</p>
              </a-collapse-panel>
              <a-collapse-panel key="4" header="如何在 iframe 中操作？">
                <p>先添加「切换框架」步骤进入 iframe，操作完成后添加「切换到主文档」步骤返回。</p>
              </a-collapse-panel>
            </a-collapse>
          </div>

          <!-- AI 功能 -->
          <div v-if="currentSection === 'ai'" class="help-content">
            <h3>AI 功能</h3>
            <p>平台集成了 AI 能力，帮助更高效地创建和维护测试脚本。</p>

            <a-divider>AI 生成测试脚本</a-divider>

            <p>用自然语言描述测试操作，AI 自动生成完整的脚本步骤。</p>

            <a-card title="使用方法" size="small" style="margin-bottom: 16px;">
              <a-steps direction="vertical" :current="4" size="small">
                <a-step title="打开 AI 生成">
                  在脚本列表页，点击「AI 生成脚本」按钮
                </a-step>
                <a-step title="描述测试操作">
                  <p>用自然语言描述你要执行的测试，例如：</p>
                  <a-alert type="info" show-icon style="margin-top: 8px;">
                    <template #message>
                      "打开百度首页，在搜索框输入 playwright，点击搜索按钮，验证页面包含 playwright 相关结果"
                    </template>
                  </a-alert>
                </a-step>
                <a-step title="选择保存项目">
                  选择将生成的脚本保存到哪个项目下
                </a-step>
                <a-step title="审核并保存">
                  AI 生成后展示步骤预览，确认后点击「保存」。也可「复制 JSON」手动调整。
                </a-step>
              </a-steps>
            </a-card>

            <a-alert type="warning" show-icon style="margin-bottom: 24px;">
              <template #message>
                AI 生成的脚本建议先执行一次验证效果。描述越具体，生成效果越好。
              </template>
            </a-alert>

            <a-divider>AI 智能分析</a-divider>

            <p>当测试步骤因定位器失效而失败时，AI 可以分析页面元素并推荐替代定位器。</p>

            <a-card title="使用流程" size="small" style="margin-bottom: 16px;">
              <a-steps direction="vertical" :current="5" size="small">
                <a-step title="执行脚本">
                  正常执行测试脚本，失败步骤会自动采集页面元素摘要
                </a-step>
                <a-step title="打开报告页">
                  点击执行记录进入报告页面
                </a-step>
                <a-step title="点击 AI 智能分析">
                  在「问题分析与建议」区域，点击「AI 智能分析」按钮
                </a-step>
                <a-step title="审核结果">
                  <p>弹窗展示每个失败步骤的分析结果：</p>
                  <ul>
                    <li><strong>原定位器 → 建议定位器</strong>：AI 推荐的替代方案</li>
                    <li><strong>置信度</strong>：对推荐结果的把握程度</li>
                    <li><strong>修复原因</strong>：为什么推荐这个定位器</li>
                  </ul>
                </a-step>
                <a-step title="应用建议">
                  勾选要采纳的建议，点击「应用并编辑脚本」，定位器自动更新并跳转到编辑页
                </a-step>
              </a-steps>
            </a-card>

            <a-row :gutter="16">
              <a-col :span="12">
                <a-card title="适用场景" size="small">
                  <ul>
                    <li>页面改版后 ID / Class 发生变化</li>
                    <li>元素名称或位置调整导致定位器失效</li>
                  </ul>
                </a-card>
              </a-col>
              <a-col :span="12">
                <a-card title="注意事项" size="small">
                  <ul>
                    <li>需在系统设置中配置 LLM API Key</li>
                    <li>分析结果仅供参考，建议审核后应用</li>
                    <li>重复分析同一记录会复用上次结果</li>
                  </ul>
                </a-card>
              </a-col>
            </a-row>
          </div>

          <!-- Playwright 引擎 -->
          <div v-if="currentSection === 'playwright'" class="help-content">
            <h3>Playwright 引擎</h3>
            <p>了解平台底层测试引擎的工作原理，帮助你更好地编写和调试测试脚本。</p>

            <a-divider>什么是 Playwright</a-divider>

            <a-card size="small" style="margin-bottom: 16px;">
              <p>Playwright 是微软开源的浏览器自动化框架，本平台基于它执行测试。相比 Selenium：</p>
              <a-row :gutter="16">
                <a-col :span="8">
                  <p><strong>自动等待</strong></p>
                  <p>操作元素前自动等待其可交互，无需手动加 sleep</p>
                </a-col>
                <a-col :span="8">
                  <p><strong>多浏览器</strong></p>
                  <p>原生支持 Chromium、Firefox、WebKit 三大内核</p>
                </a-col>
                <a-col :span="8">
                  <p><strong>更稳定</strong></p>
                  <p>基于浏览器 DevTools Protocol，不存在 WebDriver 兼容性问题</p>
                </a-col>
              </a-row>
            </a-card>

            <a-divider>执行流程</a-divider>

            <a-card title="一个脚本是如何被执行的" size="small" style="margin-bottom: 16px;">
              <a-steps direction="vertical" :current="5" size="small">
                <a-step title="启动浏览器">
                  <template #description>
                    <p>系统在服务器端启动一个真实的 Chromium 浏览器实例（默认非无头模式，可看到浏览器窗口）。整个过程对用户透明，无需本地安装浏览器。</p>
                  </template>
                </a-step>
                <a-step title="按顺序执行步骤">
                  <template #description>
                    <p>脚本中的步骤按从上到下的顺序依次执行。每一步都会：</p>
                    <ol>
                      <li>解析步骤类型（点击、输入、验证...）</li>
                      <li>如果需要操作元素，先用定位器找到目标元素</li>
                      <li>Playwright 自动等待元素可见且可交互</li>
                      <li>执行操作并记录结果</li>
                    </ol>
                  </template>
                </a-step>
                <a-step title="失败处理">
                  <template #description>
                    <p>某个步骤失败时：</p>
                    <ul>
                      <li>自动截取当前页面截图</li>
                      <li>采集页面元素摘要（供后续 AI 分析使用）</li>
                      <li>记录错误信息</li>
                      <li>跳过剩余步骤，标记脚本为「已失败」</li>
                    </ul>
                  </template>
                </a-step>
                <a-step title="生成报告">
                  <template #description>
                    <p>所有步骤执行完毕后，汇总每步的执行结果、耗时、截图，生成完整报告。</p>
                  </template>
                </a-step>
                <a-step title="关闭浏览器">
                  <template #description>
                    <p>执行结束后关闭浏览器实例，释放资源。</p>
                  </template>
                </a-step>
              </a-steps>
            </a-card>

            <a-divider>定位器详解</a-divider>

            <p>定位器（Locator）告诉 Playwright 在页面上找到哪个元素。平台支持以下定位方式：</p>

            <a-table
              :columns="locatorDetailColumns"
              :data-source="locatorDetailData"
              :pagination="false"
              size="small"
              style="margin-bottom: 16px;"
            />

            <a-alert type="info" show-icon style="margin-bottom: 16px;">
              <template #message>
                <strong>选择建议：</strong>优先使用 CSS Selector（最灵活）和 ID（最稳定）。文本类定位器适合动态内容的页面。避免依赖容易变化的 Class 名称。
              </template>
            </a-alert>

            <a-divider>自动等待机制</a-divider>

            <a-card title="Playwright 的 Auto-Wait" size="small" style="margin-bottom: 16px;">
              <p>Playwright 在执行每个操作（点击、输入等）之前，会<strong>自动</strong>进行一系列检查：</p>
              <ol>
                <li>元素已附加到 DOM（页面中存在）</li>
                <li>元素可见（没有被隐藏或 display:none）</li>
                <li>元素稳定（不在动画或移动中）</li>
                <li>元素可交互（没有被其他元素遮挡）</li>
                <li>元素已启用（没有被 disabled）</li>
              </ol>
              <p>如果以上检查在超时时间内未通过，才会报错。默认超时为 10 秒。</p>
              <a-alert type="success" show-icon style="margin-top: 12px;">
                <template #message>
                  这意味着大部分情况下你<strong>不需要手动添加等待步骤</strong>。Playwright 会自动处理页面加载和元素出现的时机。
                </template>
              </a-alert>
            </a-card>

            <a-divider>什么时候需要手动等待</a-divider>

            <a-row :gutter="16">
              <a-col :span="12">
                <a-card title="需要手动等待的场景" size="small">
                  <ul>
                    <li>AJAX 请求返回后内容才渲染（超过默认 10 秒）</li>
                    <li>元素需要特定的动画完成后才能操作</li>
                    <li>页面有懒加载，滚动后才出现元素</li>
                    <li>需要等待特定文本出现</li>
                  </ul>
                </a-card>
              </a-col>
              <a-col :span="12">
                <a-card title="对应的解决方案" size="small">
                  <ul>
                    <li>添加「等待元素」步骤，设置更长的超时</li>
                    <li>添加「固定等待」步骤</li>
                    <li>先「滚动页面」，再「等待元素」</li>
                    <li>添加「等待文本」步骤</li>
                  </ul>
                </a-card>
              </a-col>
            </a-row>
          </div>

          <!-- 测试计划 -->
          <div v-if="currentSection === 'plan'" class="help-content">
            <h3>测试计划</h3>
            <p>把多个脚本组合起来，一键批量执行。</p>

            <a-divider>执行模式</a-divider>

            <a-row :gutter="16">
              <a-col :span="12">
                <a-card title="并行执行" size="small">
                  <p>所有脚本同时开始，执行时间短，适合无依赖关系的测试。</p>
                </a-card>
              </a-col>
              <a-col :span="12">
                <a-card title="顺序执行" size="small">
                  <p>按顺序逐个执行，确保执行顺序，适合有前后依赖的测试。</p>
                </a-card>
              </a-col>
            </a-row>

            <a-divider>创建步骤</a-divider>

            <a-steps direction="vertical" :current="-1">
              <a-step title="填写基本信息">
                <template #description>
                  <p>计划名称、所属项目、描述。</p>
                </template>
              </a-step>
              <a-step title="选择脚本">
                <template #description>
                  <p>勾选要包含的脚本，可拖拽调整执行顺序。</p>
                </template>
              </a-step>
              <a-step title="配置参数">
                <template #description>
                  <ul>
                    <li><strong>执行模式</strong>：并行或顺序</li>
                    <li><strong>失败后继续</strong>：某脚本失败后是否继续执行其他脚本</li>
                  </ul>
                </template>
              </a-step>
              <a-step title="执行">
                <template #description>
                  <p>点击「运行」按钮，系统自动执行所有脚本。</p>
                </template>
              </a-step>
            </a-steps>
          </div>

          <!-- 执行测试 -->
          <div v-if="currentSection === 'execution'" class="help-content">
            <h3>执行测试</h3>

            <a-divider>执行方式</a-divider>

            <a-row :gutter="16">
              <a-col :span="12">
                <a-card title="单脚本执行" hoverable>
                  <p>在脚本列表页，点击脚本右侧的「执行」按钮，立即开始执行。</p>
                </a-card>
              </a-col>
              <a-col :span="12">
                <a-card title="计划执行" hoverable>
                  <p>在测试计划页，点击计划的「运行」按钮，按配置批量执行。</p>
                </a-card>
              </a-col>
            </a-row>

            <a-divider>状态说明</a-divider>

            <a-descriptions bordered :column="1">
              <a-descriptions-item label="等待中">任务已创建，排队等待执行</a-descriptions-item>
              <a-descriptions-item label="执行中">脚本正在执行中</a-descriptions-item>
              <a-descriptions-item label="已完成">执行成功</a-descriptions-item>
              <a-descriptions-item label="已失败">执行失败，可查看日志和截图</a-descriptions-item>
              <a-descriptions-item label="已停止">被手动停止</a-descriptions-item>
            </a-descriptions>
          </div>

          <!-- 测试报告 -->
          <div v-if="currentSection === 'report'" class="help-content">
            <h3>测试报告</h3>

            <a-divider>报告内容</a-divider>

            <a-row :gutter="16">
              <a-col :span="12">
                <a-card title="测试概览" size="small">
                  <ul>
                    <li>总步骤数、通过数、失败数</li>
                    <li>通过率和总耗时</li>
                    <li>各步骤执行时间线</li>
                  </ul>
                </a-card>
              </a-col>
              <a-col :span="12">
                <a-card title="图表展示" size="small">
                  <ul>
                    <li>状态分布饼图</li>
                    <li>步骤耗时趋势图</li>
                  </ul>
                </a-card>
              </a-col>
            </a-row>

            <a-divider>报告功能</a-divider>

            <a-row :gutter="16">
              <a-col :span="8">
                <a-card title="查看截图" size="small">
                  <p>失败步骤自动截图，帮助定位问题。</p>
                </a-card>
              </a-col>
              <a-col :span="8">
                <a-card title="AI 智能分析" size="small">
                  <p>点击「AI 智能分析」按钮，AI 分析失败步骤并推荐替代定位器。</p>
                </a-card>
              </a-col>
              <a-col :span="8">
                <a-card title="导出报告" size="small">
                  <p>导出为 HTML 文件，可在浏览器中打开分享。</p>
                </a-card>
              </a-col>
            </a-row>
          </div>

          <!-- 常见问题 -->
          <div v-if="currentSection === 'faq'" class="help-content">
            <h3>常见问题</h3>

            <a-collapse accordion>
              <a-collapse-panel key="1" header="执行失败怎么排查？">
                <ol>
                  <li>查看报告中的错误信息和失败截图</li>
                  <li>检查定位器是否正确（页面可能已改版）</li>
                  <li>Playwright 默认自动等待，如果仍超时，添加「等待元素」步骤</li>
                  <li>点击「AI 智能分析」让 AI 推荐替代定位器</li>
                </ol>
              </a-collapse-panel>

              <a-collapse-panel key="2" header="页面加载慢导致失败？">
                <p>Playwright 默认会在操作前自动等待元素。如果页面特别慢，可添加「固定等待」或「等待元素」步骤并设置更长的超时时间。</p>
              </a-collapse-panel>

              <a-collapse-panel key="3" header="如何在 iframe 中操作？">
                <p>添加「切换框架」步骤进入 iframe，完成后添加「切换到主文档」步骤返回。详见脚本编辑 → 常用技巧。</p>
              </a-collapse-panel>

              <a-collapse-panel key="4" header="AI 生成/分析不可用？">
                <p>需要在「系统设置」中配置 LLM API Key。支持 OpenAI 兼容接口（智谱、通义千问等）。</p>
              </a-collapse-panel>
            </a-collapse>
          </div>

        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  RocketOutlined,
  CodeOutlined,
  ThunderboltOutlined,
  LaptopOutlined,
  ScheduleOutlined,
  PlayCircleOutlined,
  BarChartOutlined,
  QuestionCircleOutlined
} from '@ant-design/icons-vue'

const selectedKeys = ref(['quickstart'])
const currentSection = ref('quickstart')

const locatorColumns = [
  { title: '定位器', dataIndex: 'locator', key: 'locator' },
  { title: '稳定性', dataIndex: 'stability', key: 'stability' },
  { title: '推荐指数', dataIndex: 'stars', key: 'stars' }
]

const locatorData = [
  { key: '1', locator: 'CSS Selector', stability: '推荐', stars: '★★★★★' },
  { key: '2', locator: 'ID', stability: '推荐', stars: '★★★★★' },
  { key: '3', locator: 'XPath', stability: '很稳定', stars: '★★★★' },
  { key: '4', locator: '文本内容', stability: '较稳定', stars: '★★★' },
  { key: '5', locator: 'aria 标签', stability: '较稳定', stars: '★★★' },
]

const locatorDetailColumns = [
  { title: '定位方式', dataIndex: 'method', key: 'method', width: 120 },
  { title: '说明', dataIndex: 'desc', key: 'desc' },
  { title: '示例', dataIndex: 'example', key: 'example', width: 220 },
]

const locatorDetailData = [
  { key: '1', method: 'CSS', desc: '通过 CSS 选择器定位，最灵活通用', example: '#login-btn、.submit、form > button' },
  { key: '2', method: 'ID', desc: '通过元素 id 属性定位，简洁稳定', example: 'username（匹配 id="username"）' },
  { key: '3', method: 'XPath', desc: '通过 XPath 路径定位，适合复杂结构', example: '//button[@type="submit"]' },
  { key: '4', method: '文本内容', desc: '通过按钮/链接的显示文字定位', example: '登录、Submit、Search' },
  { key: '5', method: 'Label', desc: '通过关联的 label 文字定位表单元素', example: '用户名（匹配 label 包含"用户名"的 input）' },
  { key: '6', method: 'Placeholder', desc: '通过输入框的 placeholder 文字定位', example: '请输入密码' },
  { key: '7', method: 'Role', desc: '通过 ARIA 角色定位，符合无障碍标准', example: 'button[name="Submit"]' },
  { key: '8', method: 'Test ID', desc: '通过 data-testid 属性定位，最可靠', example: 'login-button（匹配 data-testid="login-button"）' },
]

function handleMenuClick({ key }: { key: string }) {
  currentSection.value = key
  selectedKeys.value = [key]
}
</script>

<style scoped>
.help-center {
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

.content-card {
  min-height: 600px;
}

.help-content h3 {
  margin-bottom: 24px;
  font-size: 20px;
  color: rgba(0, 0, 0, 0.85);
  font-weight: 600;
}

.help-content h4 {
  margin: 12px 0;
  font-size: 16px;
  color: rgba(0, 0, 0, 0.75);
  font-weight: 500;
}

.help-content p {
  margin: 8px 0;
  color: #333;
}

.help-content ul,
.help-content ol {
  margin: 12px 0;
  padding-left: 24px;
}

.help-content li {
  margin: 8px 0;
  color: #555;
}

.help-content code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Consolas', monospace;
  color: #c7254e;
}

.step-detail {
  padding: 8px 0;
}

.step-detail ol,
.step-detail ul {
  padding-left: 20px;
}

.step-detail li {
  margin: 8px 0;
}

.editor-layout {
  display: flex;
  gap: 16px;
  margin: 16px 0;
}

.layout-panel {
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.layout-panel .panel-header {
  font-weight: bold;
  margin-bottom: 12px;
  color: #1890ff;
  font-size: 16px;
}

.layout-panel.left { flex: 1; }
.layout-panel.center { flex: 2; }
.layout-panel.right { flex: 1.5; }

.step-list {
  margin: 0;
  padding-left: 20px;
}

.step-list li {
  margin: 8px 0;
}

.timeline-number {
  display: inline-block;
  width: 24px;
  height: 24px;
  line-height: 24px;
  text-align: center;
  background: #1890ff;
  color: white;
  border-radius: 50%;
  font-weight: bold;
}

.timeline-content {
  padding: 8px 0;
}

.timeline-content h4 {
  margin-bottom: 8px;
}

.timeline-content ul,
.timeline-content ol {
  padding-left: 20px;
}

.timeline-content li {
  margin: 6px 0;
}
</style>
