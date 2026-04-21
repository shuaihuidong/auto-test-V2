# Auto Test Platform V2.0 - 部署文档

> **版本**: V2.0
> **更新日期**: 2026-04-21
> **适用范围**: Docker Compose 单机部署 / Kubernetes 集群部署

---

## 目录

- [架构概览](#架构概览)
- [环境要求](#环境要求)
- [部署方式一：Docker Compose (推荐)](#部署方式一docker-compose-推荐)
- [部署方式二：Kubernetes](#部署方式二kubernetes)
- [环境变量参考](#环境变量参考)
- [AI 服务配置](#ai-服务配置)
- [SSL/HTTPS 配置](#sslhttps-配置)
- [执行器调试模式](#执行器调试模式)
- [运维操作](#运维操作)
- [监控与日志](#监控与日志)
- [故障排查](#故障排查)
- [升级指南](#升级指南)

---

## 架构概览

V2.0 相比 V1.x 的核心变化：

| 变更项 | V1.x | V2.0 |
|--------|------|------|
| 测试引擎 | Selenium + PyQt6 桌面客户端 | Playwright + Docker 容器化执行器 |
| AI 能力 | 无 | LLM Gateway + NL2Script + Self-healing |
| 调试方式 | 本地 GUI | Trace 录制 + noVNC + CLI 工具 |
| 部署方案 | 手动部署 | Docker Compose / Kubernetes + Helm |
| 执行器扩展 | 手动添加 | HPA 自动伸缩 (K8s) / docker-compose scale |

### 系统架构图

```
                    ┌──────────────────────┐
                    │    Nginx / Ingress   │
                    │   (SSL 终止 + 路由)   │
                    └──────┬───────┬───────┘
                           │       │
               ┌───────────┘       └───────────┐
               ▼                               ▼
    ┌──────────────────┐             ┌──────────────────┐
    │   Frontend (Vue) │             │  Backend (Django) │
    │   Port 80/443    │             │  Port 8000        │
    │   Nginx 托管 SPA  │◄── /api ──►│  DRF + Channels   │
    └──────────────────┘             │  + AI Service     │
                                     └────┬────┬────────┘
                                          │    │
                              ┌───────────┘    └───────────┐
                              ▼                            ▼
                    ┌──────────────────┐        ┌──────────────────┐
                    │  Redis (缓存)     │        │  RabbitMQ (MQ)   │
                    │  Port 6379       │        │  Port 5672/15672 │
                    └──────────────────┘        └────────┬────────┘
                                                         │ 任务分发
                                          ┌──────────────┼──────────────┐
                                          ▼              ▼              ▼
                                   ┌────────────┐ ┌────────────┐ ┌────────────┐
                                   │ Executor-1 │ │ Executor-2 │ │ Executor-N │
                                   │ Playwright │ │ Playwright │ │ Playwright │
                                   │ HPA 自动伸缩│ │            │ │            │
                                   └────────────┘ └────────────┘ └────────────┘
```

### 组件清单

| 组件 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| frontend | `auto-test-frontend:latest` | 80, 443 | Vue3 SPA, Nginx 托管 |
| backend | `auto-test-backend:latest` | 8000 | Django + DRF + Channels |
| executor | `auto-test-executor:latest` | - | Playwright 执行引擎 |
| executor-debug | `auto-test-executor:latest` (debug build) | 6080 | 带 noVNC 的调试执行器 |
| redis | `redis:7-alpine` | 6379 | 缓存 + Channel 层 |
| rabbitmq | `rabbitmq:3.12-management` | 5672, 15672 | 消息队列 |

---

## 环境要求

### 硬件要求

| 部署规模 | CPU | 内存 | 磁盘 | 说明 |
|----------|-----|------|------|------|
| 最小 (体验) | 2 核 | 4 GB | 20 GB | 1 个执行器 |
| 标准 (团队) | 4 核 | 8 GB | 50 GB | 2-3 个执行器 |
| 生产 (企业) | 8 核+ | 16 GB+ | 100 GB+ | HPA 自动伸缩, 可达 10 个执行器 |

### 软件要求

| 软件 | Docker Compose | Kubernetes |
|------|---------------|------------|
| Docker | 20.10+ | - |
| Docker Compose | V2 (docker compose) | - |
| Kubernetes | - | 1.24+ |
| Helm | - | 3.8+ |
| kubectl | - | 匹配集群版本 |

---

## 部署方式一：Docker Compose (推荐)

### 1. 准备配置文件

```bash
cd auto-test-platform

# 复制环境变量模板
cp .env.example .env
```

编辑 `.env` 文件，修改以下关键配置：

```bash
# 必须修改
DJANGO_SECRET_KEY=your-random-secret-key-here    # 生成方式见下方

# 按需修改
DEBUG=False
CORS_ALLOWED_ORIGINS=https://your-domain.com
RABBITMQ_PUBLIC_HOST=your-server-ip              # 远程执行器连接地址

# AI 服务 (V2.0 新增, 按需配置)
# OPENAI_API_KEY=sk-xxx
# OPENAI_API_BASE=https://api.openai.com/v1
# OPENAI_MODEL=gpt-4o
# QWEN_API_KEY=xxx
# QWEN_MODEL=qwen-max
```

生成安全密钥：

```bash
# Django Secret Key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# RabbitMQ Encryption Key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. 配置 SSL 证书

将证书放置到 `ssl/` 目录：

```bash
mkdir -p ssl

# 方式 A: 使用已有证书
cp /path/to/your/cert.crt ssl/cert.crt
cp /path/to/your/cert.key ssl/cert.key

# 方式 B: 自签名证书 (仅用于测试)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/cert.key -out ssl/cert.crt \
  -subj "/CN=localhost"
```

### 3. 构建并启动所有服务

```bash
# 构建镜像
docker compose build

# 启动所有服务 (后台运行)
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

### 4. 初始化数据库

首次部署需要执行数据库迁移：

```bash
docker compose exec backend python manage.py migrate --noinput

# 创建管理员账户
docker compose exec backend python create_admin.py

# 收集静态文件 (Dockerfile 已内置, 通常无需手动执行)
docker compose exec backend python manage.py collectstatic --noinput
```

### 5. 验证部署

```bash
# 检查所有容器运行状态
docker compose ps

# 预期输出:
# auto-test-frontend   running   0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
# auto-test-backend    running   127.0.0.1:8000->8000/tcp
# auto-test-redis      running   127.0.0.1:6379->6379/tcp
# auto-test-rabbitmq   running   0.0.0.0:5672->5672/tcp, 127.0.0.1:15672->15672/tcp
# executor-1           running
# executor-2           running

# 健康检查
curl -k https://localhost/api/auth/login/ -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 6. 水平扩展执行器

```bash
# 扩展到 5 个执行器实例
EXECUTOR_REPLICAS=5 docker compose up -d --scale executor=5

# 或通过 .env 文件配置
echo "EXECUTOR_REPLICAS=5" >> .env
docker compose up -d
```

### 7. 启动调试执行器 (可选)

```bash
# 启动带 noVNC 可视化的调试执行器
docker compose --profile debug up -d executor-debug

# 通过浏览器访问 http://localhost:6080 观察浏览器操作
```

---

## 部署方式二：Kubernetes

### 方式 A: 使用原始 YAML

#### 1. 创建命名空间和 Secrets

```bash
# 创建命名空间
kubectl apply -f k8s/namespace.yaml

# 创建 Secrets (先修改密码!)
kubectl create secret generic platform-secrets \
  --namespace=auto-test \
  --from-literal=django-secret-key='YOUR_DJANGO_SECRET_KEY' \
  --from-literal=rabbitmq-password='YOUR_RABBITMQ_PASSWORD'

kubectl create secret generic ai-secrets \
  --namespace=auto-test \
  --from-literal=openai-api-key='YOUR_OPENAI_KEY' \
  --from-literal=qwen-api-key='YOUR_QWEN_KEY'
```

#### 2. 构建并推送镜像

```bash
# 构建镜像
docker build -t auto-test-backend:latest ./backend
docker build -t auto-test-frontend:latest ./frontend
docker build -t auto-test-executor:latest ./executor-docker

# 如果使用私有仓库
# docker tag auto-test-backend:latest your-registry/auto-test-backend:latest
# docker push your-registry/auto-test-backend:latest
```

#### 3. 部署基础设施

```bash
# 按顺序部署
kubectl apply -f k8s/infra.yaml      # Redis + RabbitMQ
kubectl apply -f k8s/backend.yaml    # 后端
kubectl apply -f k8s/executor.yaml   # 执行器 + HPA
kubectl apply -f k8s/frontend.yaml   # 前端 + Ingress

# 查看部署状态
kubectl get all -n auto-test
```

#### 4. 配置 Ingress TLS

```bash
# 创建 TLS 证书 Secret
kubectl create secret tls platform-tls \
  --namespace=auto-test \
  --cert=/path/to/cert.crt \
  --key=/path/to/cert.key

# 修改 k8s/frontend.yaml 中的 host 为你的域名
```

### 方式 B: 使用 Helm Chart (推荐)

#### 1. 基础安装

```bash
# 使用默认配置安装
helm install auto-test ./helm/auto-test-platform/

# 自定义命名空间和镜像仓库
helm install auto-test ./helm/auto-test-platform/ \
  --set global.namespace=auto-test \
  --set global.imageRegistry=your-registry.io
```

#### 2. 生产环境安装

```bash
# 复制并编辑生产环境配置
cp helm/auto-test-platform/values-production.yaml my-values.yaml

# 编辑 my-values.yaml, 修改:
# - secrets.djangoSecretKey
# - secrets.rabbitmqPassword
# - ingress.host
# - global.imageRegistry

helm install auto-test ./helm/auto-test-platform/ \
  -f my-values.yaml \
  --namespace auto-test --create-namespace
```

#### 3. 关键参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `global.imageRegistry` | `""` | 私有镜像仓库地址 |
| `backend.replicas` | `2` | 后端副本数 |
| `executor.hpa.enabled` | `true` | 启用 HPA 自动伸缩 |
| `executor.hpa.maxReplicas` | `10` | 执行器最大副本数 |
| `executor.hpa.targetCPUUtilization` | `70` | CPU 触发伸缩阈值 (%) |
| `ingress.host` | `test-platform.example.com` | 域名 |
| `ingress.tls.enabled` | `true` | 启用 HTTPS |
| `secrets.*` | 占位值 | **生产环境必须修改** |

#### 4. 升级与回滚

```bash
# 更新配置
helm upgrade auto-test ./helm/auto-test-platform/ -f my-values.yaml

# 回滚到上一版本
helm rollback auto-test

# 查看历史版本
helm history auto-test
```

---

## 环境变量参考

### 后端 (backend)

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `DJANGO_SECRET_KEY` | 是 | - | Django 密钥, 生产环境必须设置 |
| `DEBUG` | 否 | `False` | 调试模式 |
| `DJANGO_ALLOWED_HOSTS` | 否 | `*` | 允许的主机名 |
| `CORS_ALLOWED_ORIGINS` | 否 | `http://localhost` | CORS 允许的源 |
| `REDIS_HOST` | 否 | `redis` | Redis 地址 |
| `REDIS_PORT` | 否 | `6379` | Redis 端口 |
| `RABBITMQ_HOST` | 否 | `rabbitmq` | RabbitMQ 地址 |
| `RABBITMQ_PORT` | 否 | `5672` | RabbitMQ 端口 |
| `RABBITMQ_USER` | 否 | `guest` | RabbitMQ 用户名 |
| `RABBITMQ_PASSWORD` | 否 | `guest` | RabbitMQ 密码 |
| `RABBITMQ_ENCRYPTION_KEY` | 生产必填 | - | 密码加密密钥 |
| `RABBITMQ_PUBLIC_HOST` | 否 | - | 远程执行器连接地址 |

### 执行器 (executor)

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `BACKEND_URL` | 是 | `http://backend:8000` | 后端 API 地址 |
| `RABBITMQ_HOST` | 是 | `rabbitmq` | RabbitMQ 地址 |
| `RABBITMQ_USER` | 是 | `guest` | RabbitMQ 用户名 |
| `RABBITMQ_PASSWORD` | 是 | `guest` | RabbitMQ 密码 |
| `EXECUTOR_NAME` | 否 | `docker-executor` | 执行器名称 |
| `MAX_CONCURRENT` | 否 | `2` | 最大并发任务数 |
| `PLAYWRIGHT_HEADLESS` | 否 | `true` | 无头模式 |
| `TRACE_ENABLED` | 否 | `true` | 启用 Trace 录制 |
| `HEARTBEAT_INTERVAL` | 否 | `30` | 心跳间隔 (秒) |

---

## AI 服务配置

V2.0 新增 LLM Gateway, 支持 OpenAI 兼容接口和通义千问。AI 功能为可选配置, 不配置时平台正常运行, 仅 AI 相关功能不可用。

### 支持的 Provider

| Provider | 环境变量前缀 | 兼容服务 |
|----------|-------------|----------|
| OpenAI | `OPENAI_*` | OpenAI, DeepSeek, Azure OpenAI, 任何兼容接口 |
| Qwen | `QWEN_*` | 通义千问 |

### 配置方式

在 `.env` 文件或 K8s Secrets 中添加:

```bash
# Provider 选择
AI_PRIMARY_PROVIDER=openai          # 主 Provider
AI_FALLBACK_PROVIDER=qwen          # 备用 Provider (主 Provider 失败时切换)

# OpenAI 兼容配置
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE=https://api.openai.com/v1    # DeepSeek: https://api.deepseek.com/v1
OPENAI_MODEL=gpt-4o

# 通义千问配置
QWEN_API_KEY=sk-xxx
QWEN_MODEL=qwen-max

# 通用参数
AI_MAX_RETRIES=3                    # 最大重试次数
AI_RETRY_BASE_DELAY=1.0             # 重试基础延迟 (秒)
AI_TIMEOUT=60                       # 请求超时 (秒)
AI_DEFAULT_MAX_TOKENS=4096          # 默认最大 token 数
```

### AI 功能清单

| 功能 | API 端点 | 说明 |
|------|----------|------|
| NL2Script (单条) | `POST /api/scripts/nl2script/` | 自然语言转测试步骤 |
| NL2Script (批量) | `POST /api/scripts/nl2script_batch/` | 批量生成 (最多 50 条) |
| Self-healing 分析 | `POST /api/executions/{id}/heal/` | 智能定位器修复建议 |
| 查看修复日志 | `GET /api/executions/{id}/heal_logs/` | 查看修复历史 |
| 应用修复建议 | `POST /api/executions/heal_apply/` | 确认应用修复 |
| 沙盒验证 | `POST /api/scripts/sandbox_validate/` | 静态步骤校验 |

---

## SSL/HTTPS 配置

### Docker Compose 方式

SSL 证书通过 Volume 挂载到 frontend 容器:

```yaml
# docker-compose.yml 中已配置:
frontend:
  volumes:
    - ./ssl/cert.crt:/etc/nginx/ssl/cert.crt:ro
    - ./ssl/cert.key:/etc/nginx/ssl/cert.key:ro
```

将证书文件放到项目根目录的 `ssl/` 文件夹即可。

### Kubernetes / Helm 方式

```bash
# 创建 TLS Secret
kubectl create secret tls platform-tls \
  --namespace=auto-test \
  --cert=cert.crt --key=cert.key

# Helm 安装时指定
helm install auto-test ./helm/auto-test-platform/ \
  --set ingress.tls.secretName=platform-tls \
  --set ingress.host=your-domain.com
```

### Let's Encrypt (cert-manager)

如果集群安装了 cert-manager:

```bash
# 安装时自动签发证书
helm install auto-test ./helm/auto-test-platform/ \
  --set ingress.annotations."cert-manager\.io/cluster-issuer"=letsencrypt-prod \
  --set ingress.tls.secretName=platform-tls-auto
```

---

## 执行器调试模式

V2.0 提供三种调试方式, 均可独立使用:

### 方式 1: Playwright Trace 录制

每次执行自动录制 Trace 文件, 可离线回放:

```bash
# 下载 Trace 文件 (从 API 获取)
curl -k https://localhost/api/tasks/{task_id}/trace/ -o trace.zip

# 本地回放 (需要安装 playwright)
npx playwright show-trace trace.zip
```

### 方式 2: noVNC 实时观察

启动调试执行器, 通过浏览器实时观察 Playwright 操作:

```bash
# Docker Compose
docker compose --profile debug up -d executor-debug

# 访问 http://localhost:6080 即可看到浏览器画面
```

### 方式 3: 本地 CLI 调试工具

在本地运行调试器, 直接打开有界面的浏览器:

```bash
cd executor-docker

# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 运行调试 (指定后端地址和脚本 ID)
python debug.py --backend-url http://localhost:8000 --script-id 1
```

---

## 运维操作

### Docker Compose

```bash
# 查看服务状态
docker compose ps

# 查看某个服务日志
docker compose logs -f backend
docker compose logs -f executor

# 重启某个服务
docker compose restart backend

# 进入容器
docker compose exec backend bash

# 数据库迁移 (版本更新后)
docker compose exec backend python manage.py migrate --noinput

# 扩展执行器
docker compose up -d --scale executor=5

# 停止所有服务
docker compose down

# 停止并清除数据卷 (慎用!)
docker compose down -v
```

### Kubernetes / Helm

```bash
# 查看所有资源
kubectl get all -n auto-test

# 查看 Pod 日志
kubectl logs -f deployment/backend -n auto-test
kubectl logs -f deployment/executor -n auto-test --all-containers

# 进入容器
kubectl exec -it deployment/backend -n auto-test -- bash

# 数据库迁移
kubectl exec -it deployment/backend -n auto-test -- \
  python manage.py migrate --noinput

# 查看 HPA 状态
kubectl get hpa -n auto-test

# 手动伸缩执行器
kubectl scale deployment executor --replicas=5 -n auto-test

# 滚动重启
kubectl rollout restart deployment/backend -n auto-test
kubectl rollout restart deployment/executor -n auto-test

# 查看滚动更新状态
kubectl rollout status deployment/backend -n auto-test
```

---

## 监控与日志

### 日志位置

| 组件 | Docker Compose | Kubernetes |
|------|---------------|------------|
| Backend | `docker compose logs backend` | `kubectl logs deployment/backend -n auto-test` |
| Frontend | `docker compose logs frontend` | `kubectl logs deployment/frontend -n auto-test` |
| Executor | `docker compose logs executor` | `kubectl logs deployment/executor -n auto-test` |
| Redis | `docker compose logs redis` | `kubectl logs deployment/redis -n auto-test` |
| RabbitMQ | `docker compose logs rabbitmq` | `kubectl logs deployment/rabbitmq -n auto-test` |

### 健康检查

所有服务均配置了健康检查:

| 服务 | 检查方式 | 间隔 |
|------|----------|------|
| Backend | Socket 连接 8000 端口 | 30s |
| Redis | `redis-cli ping` | 10s |
| RabbitMQ | `rabbitmq-diagnostics ping` | 10s |

### 关键指标监控 (K8s)

```bash
# 查看 Pod 资源使用
kubectl top pods -n auto-test

# 查看 Node 资源使用
kubectl top nodes

# 查看 HPA 伸缩状态
kubectl describe hpa executor-hpa -n auto-test

# 查看事件
kubectl get events -n auto-test --sort-by='.lastTimestamp'
```

---

## 故障排查

### 常见问题

#### 1. Backend 启动失败: `RABBITMQ_ENCRYPTION_KEY not set`

```
ValueError: 生产环境必须设置 RABBITMQ_ENCRYPTION_KEY 环境变量！
```

**解决**: 在 `.env` 或环境变量中设置加密密钥:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# 将输出填入 RABBITMQ_ENCRYPTION_KEY
```

#### 2. 执行器无法连接 RabbitMQ

**检查步骤**:

```bash
# 检查 RabbitMQ 是否就绪
docker compose exec rabbitmq rabbitmq-diagnostics ping

# 检查执行器日志
docker compose logs executor | grep -i "rabbitmq\|amqp\|connection"

# 确认网络连通 (从执行器容器内)
docker compose exec executor python -c "
import socket
s = socket.socket()
s.connect(('rabbitmq', 5672))
print('RabbitMQ 可达')
s.close()
"
```

#### 3. 数据库迁移失败

```bash
# 查看迁移状态
docker compose exec backend python manage.py showmigrations

# 重新执行迁移
docker compose exec backend python manage.py migrate --noinput

# 如需重建 (会丢失数据!)
docker compose exec backend rm db/db.sqlite3
docker compose exec backend python manage.py migrate --noinput
```

#### 4. 前端无法连接后端 API

**检查清单**:
- Nginx 配置中 `/api` 和 `/ws` 的反向代理是否正确
- CORS 配置是否包含前端域名
- 后端健康检查是否通过: `docker compose exec backend python -c "import requests; print(requests.get('http://localhost:8000/api/auth/login/').status_code)"`

#### 5. K8s Pod CrashLoopBackOff

```bash
# 查看 Pod 错误日志
kubectl logs <pod-name> -n auto-test --previous

# 查看事件
kubectl describe pod <pod-name> -n auto-test

# 常见原因:
# - Secret 未创建: 先创建 platform-secrets 和 ai-secrets
# - 镜像不存在: 确认镜像已构建并推送到仓库
# - 资源不足: 调整 requests/limits 或增加节点
```

#### 6. HPA 无法获取指标

```bash
# 检查 metrics-server 是否安装
kubectl get pods -n kube-system | grep metrics-server

# 如未安装
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 验证
kubectl top nodes
kubectl top pods -n auto-test
```

---

## 升级指南

### 从 V1.x 升级到 V2.0

#### 1. 数据库迁移

V2.0 新增了 `HealLog` 模型和 `Script` 模型的字段变更:

```bash
# Docker Compose
docker compose exec backend python manage.py migrate --noinput

# Kubernetes
kubectl exec -it deployment/backend -n auto-test -- \
  python manage.py migrate --noinput
```

#### 2. 执行器切换

V2.0 执行器从 PyQt6 桌面客户端切换到 Docker 容器:

- 旧版 `executor-client/` (PyQt6) 不再是主要执行方式
- 新版 `executor-docker/` (Playwright) 通过 Docker 运行
- 两套执行器可以并存, 分别消费 MQ 任务

#### 3. 前端更新

V2.0 前端新增了 AI 相关组件:

- `NL2ScriptDialog.vue` - 自然语言生成脚本对话框
- `NL2ScriptBatchDialog.vue` - 批量生成对话框
- `HealLogPanel.vue` - 自修复日志面板
- ScriptList 和 ReportView 页面已集成上述组件

```bash
# 重新构建前端
docker compose build frontend
docker compose up -d frontend
```

#### 4. AI 功能 (可选)

AI 功能为可选升级, 不配置 API Key 时平台正常工作。按需在环境变量中添加 AI 配置即可启用。

---

## 默认账户

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 超级管理员 |

> **安全提示**: 生产环境部署后请立即修改默认密码。

---

## 文件结构参考

```
auto-test-platform/
├── .env                              # 环境变量 (Docker Compose)
├── docker-compose.yml                # Docker Compose 编排
├── ssl/                              # SSL 证书目录
│   ├── cert.crt
│   └── cert.key
├── k8s/                              # K8s 原始 YAML
│   ├── namespace.yaml
│   ├── secrets.yaml                  # 需手动创建, 未提供
│   ├── infra.yaml                    # Redis + RabbitMQ
│   ├── backend.yaml                  # 后端 Deployment + Service
│   ├── executor.yaml                 # 执行器 Deployment + HPA
│   └── frontend.yaml                 # 前端 Deployment + Ingress
├── helm/                             # Helm Chart
│   └── auto-test-platform/
│       ├── Chart.yaml
│       ├── values.yaml               # 默认配置
│       ├── values-production.yaml    # 生产环境覆盖
│       └── templates/                # 参数化模板
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── core/settings.py              # 含 AI_SERVICE 配置
│   └── ai_service/                   # V2.0 AI 服务模块
│       ├── client.py                 # LLM Gateway
│       ├── providers.py              # Provider 抽象
│       ├── nl2script.py              # NL2Script 服务
│       └── healing.py               # Self-healing 服务
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
├── executor-docker/                  # V2.0 容器化执行器
│   ├── Dockerfile                    # 生产镜像
│   ├── Dockerfile.debug              # 调试镜像 (含 noVNC)
│   ├── main.py                       # 入口
│   ├── executor.py                   # Playwright 引擎
│   ├── task_manager.py               # 异步任务管理
│   ├── debug.py                      # CLI 调试工具
│   ├── config.py
│   └── supervisord.conf              # 调试镜像进程管理
└── executor-client/                  # V1.x 桌面执行器 (仍可用)
```
