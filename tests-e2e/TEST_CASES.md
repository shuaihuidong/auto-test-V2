# Auto Test Platform V2.0 — 全链路 E2E 测试用例清单

> **测试对象**: 平台自身 (前端 Vue3 + 后端 Django + 执行器 + AI)
> **测试框架**: Python + Playwright + Pytest
> **优先级**: P0 (阻塞) / P1 (核心) / P2 (边界)

---

## 维度一：前端 UI 与交互

### 1.1 登录与权限

| 用例ID | 模块 | 测试场景 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|------|----------|----------|----------|----------|--------|
| UI-AUTH-001 | 登录 | 正常登录 | 平台运行中，存在 admin/admin123 | 1. 访问 /login 2. 输入 admin/admin123 3. 点击登录 | 跳转到 /projects，页面显示项目列表 | P0 |
| UI-AUTH-002 | 登录 | 错误密码 | 平台运行中 | 1. 访问 /login 2. 输入 admin/wrong 3. 点击登录 | 提示错误，停留在登录页 | P0 |
| UI-AUTH-003 | 登录 | 空表单提交 | 平台运行中 | 1. 访问 /login 2. 不填任何内容 3. 点击登录 | 表单校验提示必填 | P1 |
| UI-AUTH-004 | 登录 | Token 过期跳转 | 已登录但 Token 过期 | 1. 手动设置过期 Token 2. 访问任意页面 | 自动跳转到 /login | P1 |
| UI-AUTH-005 | 权限 | 超管可见所有菜单 | 以 admin 登录 | 1. 检查侧边栏菜单项 | 可见：用户管理、账号角色管理、执行器管理 | P0 |
| UI-AUTH-006 | 权限 | 测试人员隐藏管理菜单 | 以 tester1 登录 | 1. 检查侧边栏菜单项 | 不可见：用户管理、账号角色管理 | P0 |
| UI-AUTH-007 | 权限 | 访客只读 | 以 guest1 登录 | 1. 进入任意项目 2. 查看脚本列表 | 无"新建脚本"、"删除"按钮 | P1 |
| UI-AUTH-008 | 权限 | 访客访问 /account-role 被拒 | 以 guest1 登录 | 1. 浏览器直接访问 /account-role | 被路由守卫拦截，跳转到首页或提示无权限 | P1 |

### 1.2 项目管理

| 用例ID | 模块 | 测试场景 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|------|----------|----------|----------|----------|--------|
| UI-PROJ-001 | 项目 | 创建 Web 项目 | 以 admin 登录 | 1. 点击"新建项目" 2. 填写名称 3. 选择类型 Web 4. 提交 | 项目列表出现新项目，卡片显示 Web 标签 | P0 |
| UI-PROJ-002 | 项目 | 创建 API 项目 | 以 admin 登录 | 同上，类型选 API | 项目列表出现 API 标签项目 | P1 |
| UI-PROJ-003 | 项目 | 删除项目 | 存在一个测试项目 | 1. 点击项目卡片删除按钮 2. 确认删除 | 项目从列表消失 | P1 |

### 1.3 脚本编辑器

| 用例ID | 模块 | 测试场景 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|------|----------|----------|----------|----------|--------|
| UI-EDIT-001 | 编辑器 | 新建 Playwright 脚本 | 存在一个 Web 项目 | 1. 进入脚本列表 2. 点击"新建脚本" 3. 选择 Web + Playwright 4. 填写名称 5. 保存 | 脚本创建成功，步骤画布为空 | P0 |
| UI-EDIT-002 | 编辑器 | 拖拽步骤到画布 | 存在一个空脚本 | 1. 从左侧步骤面板找到"打开页面" 2. 拖拽到画布 | 画布出现"打开页面"步骤卡片 | P0 |
| UI-EDIT-003 | 编辑器 | 编辑步骤属性 | 画布上有一个"打开页面"步骤 | 1. 点击步骤 2. 在右侧属性面板输入 URL 3. 保存 | 步骤属性更新为输入的 URL | P0 |
| UI-EDIT-004 | 编辑器 | 删除步骤 | 画布上有至少一个步骤 | 1. 选中步骤 2. 点击删除 | 步骤从画布移除 | P1 |
| UI-EDIT-005 | 编辑器 | JSON 模式编辑 | 存在一个脚本 | 1. 切换到 JSON 编辑模式 2. 修改步骤 JSON 3. 切回可视化模式 | 可视化画布反映 JSON 修改 | P1 |
| UI-EDIT-006 | 编辑器 | 未保存提示 | 编辑过脚本但未保存 | 1. 修改步骤 2. 点击"调试"按钮 | 弹出提示"有未保存的修改，是否先保存？" | P1 |

### 1.4 AI 助手交互

| 用例ID | 模块 | 测试场景 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|------|----------|----------|----------|----------|--------|
| UI-AI-001 | NL2Script | 单条生成 | Mock LLM 就绪，存在一个项目 | 1. 点击"AI 生成"按钮 2. 输入"打开百度首页搜索playwright" 3. 点击生成 | 显示步骤预览列表，包含打开页面+输入+点击步骤 | P0 |
| UI-AI-002 | NL2Script | 生成后保存 | 步骤已生成 | 1. 选择目标项目 2. 填写脚本名 3. 点击"保存" | 脚本列表出现新脚本，标记 ai_generated=True | P0 |
| UI-AI-003 | NL2Script | 批量生成 | Mock LLM 就绪 | 1. 点击"批量生成" 2. 输入多行描述 3. 点击生成 | 进度条推进，每条描述对应一组步骤 | P1 |
| UI-AI-004 | NL2Script | LLM 错误处理 | Mock LLM 返回异常 | 1. 触发 NL2Script 请求 | 前端显示友好错误提示 | P1 |
| UI-AI-005 | 沙盒验证 | 静态校验 | 存在一个脚本 | 1. 调用沙盒验证 API | 返回校验结果（步骤格式/定位器合法性） | P2 |

---

## 维度二：后端 API 与数据流转

### 2.1 脚本 CRUD

| 用例ID | 模块 | 测试场景 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|------|----------|----------|----------|----------|--------|
| API-SCR-001 | 脚本 | 创建脚本 | 已登录，存在项目 | POST /api/scripts/ {name, project, type, framework, steps} | 201, 返回脚本对象, framework 默认为 playwright | P0 |
| API-SCR-002 | 脚本 | 获取脚本列表 | 存在多个脚本 | GET /api/scripts/?project={id} | 200, 返回分页列表 | P0 |
| API-SCR-003 | 脚本 | 更新脚本 | 存在一个脚本 | PATCH /api/scripts/{id}/ {steps: [...]} | 200, steps 更新 | P0 |
| API-SCR-004 | 脚本 | 删除脚本 | 存在一个脚本 | DELETE /api/scripts/{id}/ | 204 | P0 |
| API-SCR-005 | 脚本 | 复制脚本 | 存在一个脚本 | POST /api/scripts/{id}/duplicate/ | 201, 新脚本名称含"副本" | P1 |
| API-SCR-006 | 脚本 | 导出脚本代码 | 存在一个 Playwright 脚本 | GET /api/scripts/{id}/export_code/ | 200, 返回 Python Playwright async 代码 | P1 |
| API-SCR-007 | 脚本 | 导入脚本 | 准备合法的 JSON 脚本文件 | POST /api/scripts/import_script/ (multipart) | 201, framework 自动设为 playwright | P1 |
| API-SCR-008 | 脚本 | ai_generated 字段 | 创建脚本时 | POST /api/scripts/ {ai_generated: true, ...} | 响应中 ai_generated=true | P1 |
| API-SCR-009 | 脚本 | heal_enabled 字段 | 存在一个脚本 | PATCH /api/scripts/{id}/ {heal_enabled: true} | 200, heal_enabled=true | P1 |

### 2.2 执行触发与状态

| 用例ID | 模块 | 测试场景 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|------|----------|----------|----------|----------|--------|
| API-EXE-001 | 执行 | 触发脚本执行 | 存在一个脚本，有在线执行器 | POST /api/executions/ {script_id} | 201, status=pending, MQ 收到任务消息 | P0 |
| API-EXE-002 | 执行 | 触发计划执行 | 存在一个测试计划 | POST /api/executions/ {plan_id} | 201, 生成子执行记录 | P1 |
| API-EXE-003 | 执行 | 查询执行状态 | 存在一个 pending 执行 | GET /api/executions/{id}/ | 200, status 字段正确 | P0 |
| API-EXE-004 | 执行 | 停止执行 | 存在一个 running 执行 | POST /api/executions/{id}/stop/ | 200, status 变为 stopped | P0 |
| API-EXE-005 | 执行 | 获取执行统计 | 存在多条执行记录 | GET /api/executions/statistics/ | 200, 包含 total/pass/fail 统计 | P2 |

### 2.3 自愈闭环 API

| 用例ID | 模块 | 测试场景 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|------|----------|----------|----------|----------|--------|
| API-HEAL-001 | 自愈 | 触发修复分析 | 存在一个 failed 执行，Mock LLM | POST /api/executions/{id}/heal/ {step_index, dom_snapshot} | 200, 返回 suggested_locator, confidence | P0 |
| API-HEAL-002 | 自愈 | 查询修复日志 | 执行过 heal 分析 | GET /api/executions/{id}/heal_logs/ | 200, 返回 HealLog 列表 | P0 |
| API-HEAL-003 | 自愈 | 手动应用修复 | 存在 pending 状态的 HealLog | POST /api/executions/heal_apply/ {heal_log_id} | 200, 脚本步骤定位器被更新 | P0 |
| API-HEAL-004 | 自愈 | 高置信度自动应用 | heal_enabled=True, confidence>=0.8 | 触发 heal 分析 | HealLog.auto_applied=True, 脚本自动更新 | P1 |
| API-HEAL-005 | 自愈 | 低置信度不自动应用 | heal_enabled=True, confidence<0.8 | 触发 heal 分析 | HealLog.auto_applied=False, 需手动确认 | P1 |

### 2.4 执行器注册与心跳

| 用例ID | 模块 | 测试场景 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|------|----------|----------|----------|----------|--------|
| API-EXC-001 | 执行器 | 注册执行器 | 平台运行中 | POST /api/executor/register/ {name, ...} | 200, 返回 executor_uuid | P0 |
| API-EXC-002 | 执行器 | 心跳上报 | 执行器已注册 | POST /api/executor/heartbeat/ {executor_uuid, ...} | 200, 更新 last_heartbeat | P0 |
| API-EXC-003 | 执行器 | 心跳超时离线 | 执行器已注册，模拟超时 | 1. 注册执行器 2. 不发送心跳 3. 等待超时判定 | 执行器状态变为 offline | P1 |
| API-EXC-004 | 执行器 | 获取在线列表 | 存在多个执行器 | GET /api/executors/online/ | 200, 只返回 is_online=True 的执行器 | P1 |

---

## 维度三：异步调度与执行层

### 3.1 任务全链路

| 用例ID | 模块 | 测试场景 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|------|----------|----------|----------|----------|--------|
| FLOW-001 | 全链路 | 脚本执行闭环 | Mock MQ + Mock 执行器 | 1. 创建脚本 2. 触发执行 3. Mock 消费任务 4. Mock 上报结果 | 执行状态: pending → running → completed | P0 |
| FLOW-002 | 全链路 | 执行失败闭环 | Mock MQ + Mock 执行器 | 1. 创建脚本 2. 触发执行 3. Mock 执行器返回失败 | 执行状态变为 failed, 错误信息正确 | P0 |
| FLOW-003 | 调度 | 无可用执行器时排队 | 无在线执行器 | 1. 触发执行 | status=pending, 任务在队列中等待 | P1 |
| FLOW-004 | 调度 | 执行器上线后自动消费 | 任务排队中 | 1. 执行器上线 2. 心跳上报 | 任务被分发，状态变为 running | P1 |

### 3.2 心跳保活

| 用例ID | 模块 | 测试场景 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|------|----------|----------|----------|----------|--------|
| FLOW-HB-001 | 心跳 | 正常心跳保活 | 执行器已注册 | 1. 每 30s 发送心跳 (连续 3 次) | 执行器始终保持 online | P0 |
| FLOW-HB-002 | 心跳 | 心跳停止后离线 | 执行器 online | 1. 停止心跳 2. 等待超过超时阈值 | 执行器变为 offline | P1 |
| FLOW-HB-003 | 心跳 | 心跳恢复后重新上线 | 执行器 offline | 1. 重新发送心跳 | 执行器恢复 online | P1 |

### 3.3 结果回传

| 用例ID | 模块 | 测试场景 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|------|----------|----------|----------|----------|--------|
| FLOW-RES-001 | 结果 | 上报执行结果 | 任务处于 running | POST /api/tasks/{id}/result/ {status, steps_results} | 200, 执行状态更新 | P0 |
| FLOW-RES-002 | 结果 | 上报截图 | 任务处于 running | POST /api/tasks/{id}/screenshot/ (multipart) | 200, 截图保存 | P1 |
| FLOW-RES-003 | 结果 | 上传 Trace | 任务已完成 | POST /api/tasks/{id}/trace/ (multipart) | 200, trace 文件保存到 /media/traces/ | P1 |

---

## 维度四：AI 智能化功能

### 4.1 NL2Script

| 用例ID | 模块 | 测试场景 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|------|----------|----------|----------|----------|--------|
| AI-NL2S-001 | NL2Script | 基本生成 | Mock LLM 返回固定步骤 JSON | POST /api/scripts/nl2script/ {prompt} | 200, steps 格式正确, 包含 type/name/params | P0 |
| AI-NL2S-002 | NL2Script | 生成并保存 | Mock LLM 就绪 | POST /api/scripts/nl2script/ {prompt, save: true, script_name, project} | 201, 脚本已入库, ai_generated=True | P0 |
| AI-NL2S-003 | NL2Script | 定位器解析 | Mock LLM 返回含定位器的步骤 | 触发生成 | locator 解析为 {type, value} 格式 | P0 |
| AI-NL2S-004 | NL2Script | 批量生成 (≤50) | Mock LLM 就绪 | POST /api/scripts/nl2script_batch/ {prompts: [...50条]} | 200, 返回 50 组结果 | P1 |
| AI-NL2S-005 | NL2Script | 批量生成超限 | — | POST /api/scripts/nl2script_batch/ {prompts: [...51条]} | 400, 提示超出上限 | P1 |
| AI-NL2S-006 | NL2Script | LLM 降级 | 主 Provider 失败, 备用可用 | 触发生成 | 自动切换 fallback provider, 返回结果 | P1 |
| AI-NL2S-007 | NL2Script | LLM 全部不可用 | 主备 Provider 均 Mock 为失败 | 触发生成 | 返回 503 错误, 含重试耗尽信息 | P1 |

### 4.2 智能自愈

| 用例ID | 模块 | 测试场景 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|------|----------|----------|----------|----------|--------|
| AI-HEAL-001 | 自愈 | 触发分析 | 存在 failed 执行, Mock LLM 返回建议定位器 | POST heal API | 返回 suggested_locator, confidence, strategy | P0 |
| AI-HEAL-002 | 自愈 | 生成 HealLog | 分析完成 | 查询 heal_logs | 存在 pending 状态的 HealLog 记录, 含 original/suggested 对比 | P0 |
| AI-HEAL-003 | 自愈 | 手动应用 | HealLog status=success | POST heal_apply {heal_log_id} | 脚本步骤定位器更新, HealLog 标记为 applied | P0 |
| AI-HEAL-004 | 自愈 | 自动应用 (≥0.8) | heal_enabled=True, Mock LLM 返回 confidence=0.9 | 触发分析 | auto_applied=True, 脚本自动更新, 无需手动确认 | P1 |
| AI-HEAL-005 | 自愈 | 不自动应用 (<0.8) | heal_enabled=True, Mock LLM 返回 confidence=0.6 | 触发分析 | auto_applied=False, 需手动确认 | P1 |
| AI-HEAL-006 | 自愈 | heal_enabled=False | 脚本未启用自愈 | 触发分析 | 仅记录 HealLog, 不自动修改脚本 | P1 |
| AI-HEAL-007 | 自愈 | DOM 快照记录 | 触发分析时传入 dom_snapshot | 查询 heal_logs | HealLog.dom_snapshot 有值 | P2 |
| AI-HEAL-008 | 自愈 | Token 消耗记录 | Mock LLM 消耗 token | 查询 heal_logs | HealLog.token_consumed > 0 | P2 |

---

## 汇总统计

| 维度 | P0 | P1 | P2 | 合计 |
|------|-----|-----|-----|------|
| 一：前端 UI 与交互 | 7 | 9 | 1 | 17 |
| 二：后端 API 与数据流转 | 9 | 8 | 1 | 18 |
| 三：异步调度与执行层 | 5 | 6 | 0 | 11 |
| 四：AI 智能化功能 | 6 | 7 | 2 | 15 |
| **合计** | **27** | **30** | **4** | **61** |
