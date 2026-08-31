# 自动化测试管理平台

<div align="center">

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Django](https://img.shields.io/badge/Django-4.2.7-green)
![Vue](https://img.shields.io/badge/Vue-3.3.8-brightgreen)
![Playwright](https://img.shields.io/badge/Playwright-1.40-orange)
![License](https://img.shields.io/badge/license-MIT-orange)

基于 Vue3 + Django + Playwright 的自动化测试管理平台，通过可视化拖拉拽方式创建和管理测试脚本。

</div>

> **当前执行模型（以代码为准）**  
> 点击「执行」后，后端 `ExecutionRunner` 在进程内用线程池启动 Playwright。  
> **不需要独立执行机，也不需要 `executor-docker`。**  
> 本机开发：安装 Python / Node / Chromium 即可。  
> 仓库里的 `docker-compose.yml`、K8s/Helm 仍含 RabbitMQ 与 `executor` 服务，属于早期方案残留，与当前后端路由不一致。

## 功能特性

- **可视化脚本编辑器** - 拖拉拽创建测试步骤，可视化/JSON 双模式编辑，50+ 步骤类型
- **Playwright 引擎** - 支持 Chromium / Firefox / WebKit，由后端线程池并发执行（`MAX_CONCURRENT_EXECUTIONS`，默认 3）
- **AI 辅助生成 (NL2Script)** - 自然语言描述自动生成测试脚本，支持单个和批量生成
- **AI 智能分析** - 手动触发分析失败步骤，LLM 推荐替代定位器，审核后一键应用并跳转编辑页
- **智能元素提取** - 失败步骤自动采集结构化页面元素摘要（JSON）
- **测试报告** - ECharts 图表展示，步骤时间线，WebSocket 实时状态
- **权限分级** - 超级管理员 / 管理员 / 测试人员 / 访客 四级角色
- **参数化测试** - 项目级/脚本级变量，数据驱动
- **执行隔离** - 每次执行独立截图目录，避免跨执行覆盖

## 技术栈

Vue 3 + TypeScript + Ant Design Vue | Django + DRF + Channels | Playwright | Redis（生产 Channel 层，本地可用内存） | SQLite / PostgreSQL

## 项目结构

```
auto-test-platform/
├── backend/
│   ├── core/                   # Django 核心配置
│   ├── apps/                   # 应用模块
│   │   ├── users/              # 用户与权限
│   │   ├── projects/           # 项目管理
│   │   ├── scripts/            # 脚本管理
│   │   ├── plans/              # 测试计划
│   │   ├── executions/         # 执行管理 + HealLog
│   │   ├── reports/            # 报告生成
│   │   ├── executors/          # 现仅变量管理（旧 Executor 模型已移除）
│   │   └── settings/           # 系统设置 (AI 配置)
│   ├── ai_service/             # AI 服务 (NL2Script, Healing, LLM Gateway)
│   ├── services/
│   │   ├── execution_runner.py # 当前唯一执行入口（线程池 + Playwright）
│   │   └── storage.py
│   └── engine/                 # Playwright / Selenium / API 引擎
├── frontend/
│   └── src/
│       ├── components/ScriptEditor/
│       ├── components/AI/
│       └── views/
├── start-all.ps1 / start-all.cmd   # 本机一键启动（推荐）
└── docker-compose.yml              # 含早期 executor/rabbitmq，部署前请对照 DEPLOYMENT_V2.md
```

当前仓库 **没有** `executor-docker/` 目录。`backend/core/urls.py` 已注明：旧 Executor / TaskQueue / RabbitMQ 分发已移除。

## 系统架构

```
浏览器 (Vue3) ──HTTP + WebSocket──▶ Django 后端
                                      ├─ ExecutionRunner（线程池）
                                      │     └─ PlaywrightEngine（本进程内开浏览器）
                                      ├─ AI Service（NL2Script / Healing）
                                      └─ Redis（生产环境 Channel 层；本地可 inmemory）
```

**执行路径**

1. 前端 `POST /api/executions/`
2. `apps.executions.services.start_script_execution` 创建记录
3. `ExecutionRunner.start()` 提交到线程池
4. 线程内 `PlaywrightEngine` 逐步执行，结果经 Channels 推到前端

不经过 RabbitMQ，也不注册外部执行器。

### AI 智能分析流程

```
执行脚本 → 失败步骤自动采集页面元素摘要（结构化 JSON，非原始 DOM）
    ↓
报告页面 → 点击「AI 智能分析」按钮
    ↓
弹窗展示分析结果：原定位器 → 建议定位器，置信度，修复原因
    ↓
勾选要采纳的建议 → 点击「应用并编辑脚本」→ 脚本定位器自动更新并跳转编辑页
```

## 快速开始

### 环境要求

Python 3.9+ | Node.js 16+ | Playwright（需执行 `playwright install chromium`）

### 本机一键启动（推荐，与日常开发一致）

```powershell
.\start-all.ps1 -Mode local
```

脚本会使用 SQLite、`CHANNEL_LAYER_BACKEND=inmemory`，不依赖 Redis / RabbitMQ。

### 后端（手动）

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
python manage.py migrate
python create_admin.py

daphne -b 0.0.0.0 -p 8000 core.asgi:application
```

### 前端（手动）

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

### 生产 / 服务器

见 [DEPLOYMENT_V2.md](./DEPLOYMENT_V2.md)。要点：后端进程（或后端容器）内必须能启动 Chromium；不要再按「先起 executor 容器」来部署。

### AI 服务配置

超级管理员登录 → 系统设置 → 配置 LLM API Key / API Base URL / 模型名称。  
不配置 Key 时平台可正常执行脚本，仅 AI 功能不可用。

## 默认账户

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 超级管理员 |
| admin2 | admin123 | 管理员 |
| tester1 | test123 | 测试人员 |
| guest1 | guest123 | 访客 |

生产环境请立即修改默认密码。

## 使用流程

```
创建项目 → 新建脚本 (可视化编辑 或 AI 生成) → 配置步骤参数 → 执行
                                                              ↓
                                              查看报告 → 失败时点击「AI 智能分析」→ 应用修复 → 编辑页
```

## 文档

| 文档 | 说明 |
|------|------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 当前执行架构 + 早期 RabbitMQ 方案（已废弃，仅存档） |
| [DEPLOYMENT_V2.md](./DEPLOYMENT_V2.md) | 部署说明（以 ExecutionRunner 为准） |
| [CHANGELOG.md](./CHANGELOG.md) | V1.x 变更日志 |
| [CHANGELOG_V2.md](./CHANGELOG_V2.md) | V2.0 开发变更日志 |
| [SECURITY.md](./SECURITY.md) | 安全性说明 |
| [QUICK_START_SECURITY.md](./QUICK_START_SECURITY.md) | 安全快速检查 |

## 许可证

MIT License
