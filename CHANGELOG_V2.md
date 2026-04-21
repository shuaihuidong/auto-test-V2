# Auto Test Platform V2.0 - 开发变更日志

> 本文档记录 V2.0 升级过程中的所有代码变更，供后续 Bug 修复和维护参考。
> 格式：每条记录包含日期、变更文件、变更内容、关键代码位置。

---

## 2026-04-21 — V2.0 全量升级 (初始提交)

**提交哈希**: `847ef70`
**变更统计**: 54 files, +6391 / -55

---

### 一、Phase 1 — 基础架构升级

#### 1.1 数据库模型升级 (Task 6)

**`backend/apps/scripts/models.py`** — Script 模型
- 移除 `'selenium'` 选项 (FRAMEWORK_CHOICES 中删除)
- `framework` 字段增加 `default='playwright'`
- 新增 `ai_generated = BooleanField(default=False)` — 标记脚本是否由 AI 生成
- 新增 `heal_enabled = BooleanField(default=False)` — 控制该脚本是否启用智能自愈

**`backend/apps/executions/models.py`** — 新增 HealLog 模型
- 整个 `HealLog` 类新增在文件末尾（Execution 类之后）
- 字段：script(FK), execution(FK), step_index, step_name, original_locator, suggested_locator, locator_type(css/xpath/data-testid/id/text), heal_status(success/failed/pending), heal_strategy(llm_recommend/dom_analysis/rule_based), confidence(float), reason, dom_snapshot, llm_provider, token_consumed, auto_applied
- 索引：`(script, heal_status)`, `(execution, step_index)`
- **注意**：HealLog 必须定义在 Execution 之后，因为 FK 引用了 Execution

**迁移文件**:
- `backend/apps/scripts/migrations/0007_v2_add_ai_fields_and_heallog.py` — Script 模型的 ai_generated, heal_enabled 字段
- `backend/apps/executions/migrations/0007_v2_add_ai_fields_and_heallog.py` — HealLog 整个模型

**`backend/apps/scripts/serializers.py`**
- ScriptSerializer 的 fields 列表新增 `'ai_generated'`, `'heal_enabled'`

**`backend/apps/executions/serializers.py`**
- 新增 `HealLogSerializer` — 完整字段只读序列化
- 新增 `HealLogCreateSerializer` — 创建时使用，含 script/execution/step_index 必填校验

---

#### 1.2 Playwright 引擎 + Docker 容器化执行器 (Task 2)

**`executor-docker/`** — 全新目录，替代 executor-client/ 的 PyQt6 桌面客户端

| 文件 | 说明 |
|------|------|
| `config.py` | ExecutorConfig dataclass，从环境变量加载配置，自动生成 UUID |
| `executor.py` | PlaywrightStepExecutor: 20+ 步骤类型实现，定位器转换 (`_locator_to_pw()`)，变量替换；PlaywrightScriptExecutor: 浏览器生命周期、Trace 录制、sandbox 模式 (5s 超时) |
| `task_manager.py` | AsyncTaskManager: aio-pika 异步消费 RabbitMQ，httpx 异步上报结果，完整生命周期 (register→consume→execute→result→heartbeat) |
| `main.py` | 入口，优雅关闭 (SIGINT/SIGTERM) |
| `debug.py` | CLI 调试工具：从后端 API 获取脚本 → 本地 headed 模式 + Inspector 运行 |
| `requirements.txt` | playwright>=1.49.0, httpx>=0.27.0, aio-pika>=9.4.0, loguru>=0.7.0 |
| `Dockerfile` | 基于 `mcr.microsoft.com/playwright/python:v1.49.0-noble`，非 root 用户，entrypoint.sh |
| `Dockerfile.debug` | 在生产镜像基础上增加 Xvfb + noVNC + fluxbox + supervisor |
| `supervisord.conf` | 管理 xvfb, fluxbox, novnc, x11vnc, executor 五个进程 |
| `entrypoint.sh` | 创建 /app/traces 和 /app/logs 目录后启动 main.py |

**executor.py 步骤类型映射**:
```
open_page, click, double_click, right_click, input_text, clear_input,
select_option, check, uncheck, hover, screenshot, scroll_page,
wait_element, wait_text, wait_time, verify_title, verify_url,
verify_text, verify_element, keyboard_press, execute_script,
handle_dialog, upload_file, download_file, get_cookie, set_cookie,
set_storage, switch_frame, switch_window, open_tab, close_tab,
refresh_page, go_back, go_forward, extract_data
```

**定位器转换 (`_locator_to_pw`)**:
```
xpath   → xpath=...
css     → 直接使用
id      → #...
name    → [name=...]
text    → text=...
class   → .xxx (CSS class selector)
tag     → 直接使用标签名
data-testid → [data-testid=...]
```

**`docker-compose.yml`** — 新增两个服务
- `executor` 服务: 生产执行器，默认 replicas=2，CPU 1核/内存 2G，无固定 container_name 支持 scale
- `executor-debug` 服务: 调试执行器，Dockerfile.debug 构建，noVNC 端口 6080，profiles: [debug]

---

### 二、Phase 2 — AI 能力集成

#### 2.1 LLM Gateway (Task 5)

**`backend/ai_service/`** — 全新 AI 服务模块

| 文件 | 说明 |
|------|------|
| `__init__.py` | 暴露 `get_llm_gateway()` 单例，延迟初始化 |
| `exceptions.py` | AIServiceError, AIProviderError, AIRetryExhaustedError, AIResponseParseError |
| `providers.py` | LLMResponse dataclass; BaseLLMProvider(ABC); OpenAIProvider (/v1/chat/completions); QwenProvider (/compatible-mode/v1/chat/completions); PROVIDER_REGISTRY dict |
| `client.py` | LLMGateway: `call()` 文本调用, `call_json()` JSON 结构化调用, `from_settings()` 工厂方法, `_retry_loop()` 指数退避 (base * 2^attempt)，primary→fallback 降级 |

**`backend/core/settings.py`** — 新增 AI_SERVICE 配置块
- 12 个环境变量: AI_PRIMARY_PROVIDER, AI_FALLBACK_PROVIDER, OPENAI_API_KEY/BASE/MODEL, QWEN_API_KEY/MODEL, AI_MAX_RETRIES, AI_RETRY_BASE_DELAY, AI_TIMEOUT, AI_DEFAULT_MAX_TOKENS

**`backend/requirements.txt`** — 新增依赖
- `httpx>=0.27.0` — 异步 HTTP 客户端 (替代 requests 调用 LLM API)
- `loguru>=0.7.0` — 结构化日志

---

#### 2.2 NL2Script — 自然语言生成测试脚本 (Task 3)

**`backend/ai_service/nl2script.py`** — 全新
- `NL2SCRIPT_SYSTEM_PROMPT`: 系统提示词，定义 16 种步骤类型和 2 个完整示例
- `_parse_locator_string(locator_str)`: 解析 LLM 返回的定位器字符串 → `{type, value}` dict
- `_convert_llm_step_to_platform(llm_step)`: LLM 输出格式 → 平台步骤格式转换
- `NL2ScriptService.generate(prompt, script_name)`: 单条生成
- `NL2ScriptService.batch_generate(prompts, max_concurrent)`: 批量生成，asyncio.Semaphore 控制并发，最多 50 条

**`backend/apps/scripts/views.py`** — 新增 3 个 API 端点
- `nl2script` action: `POST /api/scripts/nl2script/` — prompt → steps → 可选保存为脚本
- `nl2script_batch` action: `POST /api/scripts/nl2script_batch/` — prompts 列表批量生成
- `sandbox_validate` action: `POST /api/scripts/sandbox_validate/` — 静态步骤校验 (不启动浏览器)

**`backend/apps/scripts/views.py`** — 改写 `_generate_python_code()`
- 原 f-string 方式有 `{{name}}` 转义 Bug，改用 `lines` 列表 + `append()` + `'\n'.join()`
- 新增 `_locator_to_playwright()` 静态方法: 平台定位器格式 → Playwright locator 字符串
- 输出 Playwright async Python 代码 (非 Selenium)

**`backend/apps/scripts/views.py`** — 修改 `import_script()`
- 默认 framework 从 `'selenium'` 改为 `'playwright'`

---

#### 2.3 Self-healing — 智能定位器修复 (Task 4)

**`backend/ai_service/healing.py`** — 全新
- `HEAL_SYSTEM_PROMPT`: 自修复系统提示词，要求 LLM 分析 DOM 快照并推荐替代定位器
- `_extract_original_locator_info(step)`: 从步骤中提取原始定位器信息
- `_suggested_locator_to_platform(suggestion)`: LLM 推荐格式 → 平台定位器格式
- `HealingService.analyze(execution, step_index, dom_snapshot)`: 分析失败步骤，返回修复建议
- `HealingService.auto_heal_script(execution, heal_log)`: 置信度 >= 0.8 且 heal_enabled=True 时自动应用修复

**`backend/apps/executions/views.py`** — 新增 3 个 API 端点
- `heal` action: `POST /api/executions/{id}/heal/` — 触发自修复分析
- `heal_logs` action: `GET /api/executions/{id}/heal_logs/` — 查询修复日志
- `heal_apply` action: `POST /api/executions/heal_apply/` — 手动确认应用修复

**`backend/apps/executors/views.py`** — 新增 Trace 上传端点
- `trace` action: `POST /api/tasks/{id}/trace/` — multipart 文件上传，保存到 /media/traces/

---

### 三、Phase 2 收尾 + 前端集成

#### 3.1 前端 API 层

**`frontend/src/api/script.ts`** — 新增 3 个 API 方法
- `nl2script(data)`: POST /api/scripts/nl2script/
- `nl2scriptBatch(data)`: POST /api/scripts/nl2script_batch/
- `sandboxValidate(data)`: POST /api/scripts/sandbox_validate/

**`frontend/src/api/execution.ts`** — 新增 3 个 API 方法
- `healExecution(id)`: POST /api/executions/{id}/heal/
- `getHealLogs(id)`: GET /api/executions/{id}/heal_logs/
- `applyHeal(data)`: POST /api/executions/heal_apply/

#### 3.2 前端组件

**`frontend/src/components/AI/NL2ScriptDialog.vue`** — 全新 (300 行)
- Modal 对话框: textarea 输入自然语言 → 调用 nl2script API → 步骤 JSON 预览
- 显示 token 消耗和 LLM Provider 信息
- 操作：保存为新脚本 / 复制 JSON / 编辑后再保存

**`frontend/src/components/AI/NL2ScriptBatchDialog.vue`** — 全新 (214 行)
- 多行输入 (每行一条描述)，调用 nl2script_batch API
- 进度条展示批量生成进度
- 结果列表支持展开/折叠查看每条生成详情

**`frontend/src/components/AI/HealLogPanel.vue`** — 全新 (209 行)
- 展示某次执行的所有修复日志
- 对比显示：原始定位器 vs 推荐替代定位器
- 操作：一键应用修复建议

#### 3.3 前端页面集成

**`frontend/src/views/ScriptList.vue`** — 修改
- 新增 "AI 生成" 按钮 → 打开 NL2ScriptDialog
- 新增 "批量生成" 按钮 → 打开 NL2ScriptBatchDialog
- 引入 ThunderboltOutlined 图标

**`frontend/src/views/ReportView.vue`** — 修改
- 在报告底部新增 HealLogPanel 卡片，展示该执行的自修复日志

---

### 四、Phase 3 — 高级特性

#### 4.1 沙盒验证

**`backend/apps/scripts/views.py`** — `sandbox_validate` action
- 静态校验步骤 JSON: 检查必填字段、定位器格式、参数合法性
- 不启动浏览器，纯后端验证

**`executor-docker/executor.py`** — PlaywrightScriptExecutor
- 新增 `sandbox=True` 模式：使用更短超时 (5s)，不录制 Trace，仅验证步骤可执行性

#### 4.2 K8s 云原生化部署

**`k8s/`** — 原始 YAML 清单

| 文件 | 内容 |
|------|------|
| `namespace.yaml` | Namespace: auto-test |
| `backend.yaml` | Deployment (2 副本, secrets, liveness/readiness probe) + ClusterIP Service :8000 |
| `executor.yaml` | Deployment (2 副本, emptyDir volumes) + HPA (min 2, max 10, CPU 70%, Mem 80%) |
| `frontend.yaml` | Deployment (2 副本) + ClusterIP Service :80 + Ingress (TLS, / → frontend, /api → backend, /ws → backend) |
| `infra.yaml` | Redis (PVC + Deployment + Service) + RabbitMQ (PVC + Deployment + Service) |

**`helm/auto-test-platform/`** — Helm Chart

| 文件 | 内容 |
|------|------|
| `Chart.yaml` | apiVersion: v2, appVersion: 2.0.0 |
| `values.yaml` | 全部可配置参数 (后端/前端/执行器/Redis/RabbitMQ/Ingress/Secrets) |
| `values-production.yaml` | 生产环境覆盖值 (3 副本, 更高资源, HPA max 20) |
| `templates/_helpers.tpl` | 通用 helper: name, fullname, labels, image (支持 registry 前缀) |
| `templates/namespace.yaml` | 参数化 Namespace |
| `templates/secrets.yaml` | platform-secrets + ai-secrets |
| `templates/backend.yaml` | 参数化 Deployment + Service |
| `templates/frontend.yaml` | 参数化 Deployment + Service |
| `templates/executor.yaml` | 参数化 Deployment + HPA (可开关) |
| `templates/infra.yaml` | 参数化 Redis + RabbitMQ (PVC + Deployment + Service) |
| `templates/ingress.yaml` | 参数化 Ingress (TLS 可开关) |

**Helm Chart 关键设计**:
- `auto-test.image` helper 接受 `repository`, `tag`, `registry` 三个参数，显式传入 `registry`
- 所有组件都有 `enabled` 开关，可独立禁用
- HPA 可通过 `executor.hpa.enabled: false` 关闭
- PVC 的 `storageClass` 留空时使用集群默认

---

### 五、部署文档

**`DEPLOYMENT_V2.md`** — 全新 (820 行)
- 架构概览 (V1 vs V2 对照表, 架构图)
- Docker Compose 部署完整流程
- Kubernetes 部署 (原始 YAML + Helm Chart 两种方式)
- 环境变量参考表 (后端 + 执行器)
- AI 服务配置指南
- SSL/HTTPS 配置 (手动/Let's Encrypt/K8s Secret)
- 三种调试模式使用说明
- 运维操作命令速查
- 故障排查 (6 个常见问题)
- V1.x → V2.0 升级步骤

---

### 六、Git & 仓库配置

- 新增 SSH key: `~/.ssh/id_ed25519_v2` → 添加到 GitHub 账号级别
- SSH config: `~/.ssh/config` 配置两个 Host 别名 (github-original / github-v2)
- 新增 remote `v2`: `git@github-v2:shuaihuidong/auto-test-V2.git`
- 推送到新仓库: https://github.com/shuaihuidong/auto-test-V2

---

### Bug 修复记录

| 问题 | 文件 | 修复方式 |
|------|------|----------|
| HealLog 定义在 Execution 之前导致 FK 引用失败 | `executions/models.py` | 将整个 HealLog 类移到 Execution 类定义之后 |
| `_generate_python_code()` 中 f-string `{{name}}` 输出为 `{name}` 而非变量值 | `scripts/views.py` | 整个方法改用 `lines = []` + `lines.append()` + `'\n'.join(lines)` |
| `import_script` 默认 framework 为 `'selenium'` | `scripts/views.py` | 改为 `default='playwright'` |
| Helm helper `auto-test.image` 中 `$.Values` 在 include dict 上下文中无法访问 | `templates/_helpers.tpl` | 改为显式传入 `registry` 参数，helper 内使用 `.registry` |

---

### 已知待办 / 潜在风险点

1. **数据库**: 当前使用 SQLite，生产环境建议切换 PostgreSQL
2. **Secrets 管理**: K8s Secrets 和 docker-compose .env 中的密钥为明文，生产应使用 Vault/External Secrets
3. **AI 服务未配置时不影响平台运行**，但 NL2Script / Self-healing 相关 API 会返回错误
4. **executor-client/ (PyQt6)** 未删除，仍可与 V2.0 并存消费 MQ 任务
5. **Playwright Trace 文件** 存储在 emptyDir (K8s) 或 Docker volume 中，Pod 重启后丢失，需对接对象存储

---

## 变更日志索引 (后续追加)

> 格式：日期 | 模块 | 文件 | 描述

| 日期 | 模块 | 文件 | 描述 |
|------|------|------|------|
| 2026-04-21 | 全量 | 54 files | V2.0 初始提交，详见上方各章节 |
| | | | |
