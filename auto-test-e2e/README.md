# auto-test-e2e

auto-test-platform E2E 测试套件 — 独立运行，通过 HTTP API 回归验证。

## 测试范围

- **API 测试** (89+): 认证、脚本 CRUD、AI 设置、NL2Script、执行器调度、全链路集成
- **UI 测试**: 登录、权限控制、脚本编辑器、AI 设置页面、NL2Script 对话框

## 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

## 运行测试

### API 测试 (无需前端)

```bash
pytest tests/ -v --tb=short -k "not ui"
```

需要后端服务运行在 `http://localhost:8000`。

### 全部测试 (含 UI)

```bash
pytest tests/ -v --tb=short
```

需要同时运行:
- 后端: `http://localhost:8000`
- 前端: `http://localhost:5173`

### 无头模式

```bash
pytest tests/ -v --tb=short --browser chromium
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `API_URL` | `http://localhost:8000` | 后端 API 地址 |
| `BASE_URL` | `http://localhost:5173` | 前端地址 |
| `DB_ENGINE` | `sqlite3` | 数据库引擎 |

## 测试账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| super_admin | admin | admin123 |
| admin | admin2 | admin123 |
| tester | tester1 | test123456 |
| guest | guest1 | guest123456 |

## 项目结构

```
auto-test-e2e/
├── conftest.py           # pytest 配置和全局 fixture
├── pytest.ini            # pytest 运行参数
├── requirements.txt      # Python 依赖
├── pages/                # Playwright Page Object Model
├── mocks/                # Mock 服务 (RabbitMQ, Executor, LLM)
└── tests/                # 测试用例
    ├── test_auth.py          # 登录与权限
    ├── test_script.py        # 脚本 CRUD 与编辑器
    ├── test_ai_settings.py   # AI 设置管理
    ├── test_ai.py            # NL2Script + Self-healing
    ├── test_executor_flow.py # 执行器全链路
    └── test_v2_fixes.py      # V2.0 修复验证 (API)
```

## 与主项目关系

本目录是 `auto-test-platform` 的独立 E2E 测试模块，通过 HTTP 调用后端 API 进行回归测试，不依赖主项目源码文件。
