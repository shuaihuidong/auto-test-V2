# 自动化测试管理平台

<div align="center">

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Django](https://img.shields.io/badge/Django-4.2.7-green)
![Vue](https://img.shields.io/badge/Vue-3.3.8-brightgreen)
![Playwright](https://img.shields.io/badge/Playwright-1.49+-orange)
![License](https://img.shields.io/badge/license-MIT-orange)

基于 Vue3 + Django + Playwright 的自动化测试管理平台，通过可视化拖拉拽方式创建和管理测试脚本。

</div>

## 功能特性

- **可视化脚本编辑器** - 拖拉拽创建测试步骤，可视化/JSON 双模式编辑，50+ 步骤类型
- **Playwright 引擎** - 支持 Chromium/Firefox/WebKit，Docker 容器化执行器可水平扩展
- **AI 辅助生成 (NL2Script)** - 自然语言描述自动生成测试脚本，支持单个和批量生成
- **AI 智能分析** - 手动触发分析失败步骤，LLM 推荐替代定位器，审核后一键应用并跳转编辑页
- **智能元素提取** - 失败步骤自动采集结构化页面元素摘要（JSON），体积仅为原始 DOM 的 1-2%
- **测试报告** - ECharts 图表展示，步骤时间线，WebSocket 实时状态
- **消息队列架构** - RabbitMQ 任务分发，多执行机负载均衡
- **权限分级** - 超级管理员 / 管理员 / 测试人员 / 访客 四级角色
- **参数化测试** - 项目级/脚本级变量，数据驱动
- **执行隔离** - 每次执行独立截图目录，避免跨执行覆盖

## 技术栈

Vue 3 + TypeScript + Ant Design Vue | Django + DRF + Channels | Playwright | RabbitMQ | Redis | SQLite / PostgreSQL

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
│   │   └── settings/           # 系统设置 (AI 配置)
│   ├── ai_service/             # AI 服务 (NL2Script, Healing, LLM Gateway)
│   ├── services/               # ExecutionRunner, 消息队列, 任务分发
│   └── engine/                 # Playwright 引擎 (本地执行)
├── frontend/
│   └── src/
│       ├── components/ScriptEditor/   # 可视化脚本编辑器
│       ├── components/AI/             # AI 智能分析弹窗、NL2Script
│       └── views/                     # 页面视图
└── executor-docker/                   # 容器化执行器
```

## 系统架构

```
浏览器 (Vue3) ──HTTP+WebSocket──▶ Django 后端
                                    ├─ ExecutionRunner (线程池 + Playwright)
                                    ├─ AI Service (NL2Script / Healing)
                                    └─ TaskDistributor ──▶ RabbitMQ ──▶ Docker 执行器
```

**执行模式**: 本地执行 (线程池，适合调试) | 远程执行 (RabbitMQ + Docker，适合生产)

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

- 步骤失败时采集结构化元素摘要（tag / role / name / attrs），体积约 5-20KB
- 支持 LLM 限流自动重试（429 状态码 + 超时重试，最多 3 次）
- 分析过程中展示动态友好提示，告知用户当前进度

## 快速开始

### 环境要求

Python 3.9+ | Node.js 16+ | Playwright 1.49+ (本地执行时)

### 后端

```bash
cd backend
pip install -r requirements.txt
playwright install chromium          # 本地执行需要
python manage.py migrate
python create_admin.py               # 创建管理员

# 启动 (daphne 支持 WebSocket)
daphne -b 0.0.0.0 -p 8000 core.asgi:application

# 或 runserver 调试 (不支持 WebSocket)
DB_PATH=db/db.sqlite3 python manage.py runserver 0.0.0.0:8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

### Docker 执行器

```bash
docker compose up -d
docker compose up -d --scale executor=5   # 水平扩展
```

### AI 服务配置

超级管理员登录 → 系统设置 → 配置 LLM API Key / API Base URL / 模型名称

支持主备 Provider 切换，兼容 OpenAI / 智谱 / 通义千问等 OpenAI 兼容接口。

## 默认账户

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 超级管理员 |
| admin2 | admin123 | 管理员 |
| tester1 | test123 | 测试人员 |
| guest1 | guest123 | 访客 |

## 使用流程

```
创建项目 → 新建脚本 (可视化编辑 或 AI 生成) → 配置步骤参数 → 执行
                                                              ↓
                                              查看报告 → 失败时点击「AI 智能分析」→ 应用修复 → 编辑页
```

## 文档

| 文档 | 说明 |
|------|------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 系统架构 - 任务分发、执行模式详解 |
| [CHANGELOG.md](./CHANGELOG.md) | V1.x 变更日志 |
| [CHANGELOG_V2.md](./CHANGELOG_V2.md) | V2.0 开发变更日志 |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | 生产环境部署指南 |
| [DEPLOYMENT_V2.md](./DEPLOYMENT_V2.md) | V2.0 部署 (Docker Compose + Kubernetes) |
| [SECURITY.md](./SECURITY.md) | 安全性说明 |

## 许可证

MIT License
