# 系统架构文档

> **文档状态（2026-08-31 对照源码修订）**  
> 当前代码的执行链路是 **Django 进程内 `ExecutionRunner` + Playwright**。  
> 下文从「任务分发机制」起，大量描述 RabbitMQ、`executor-docker`、TaskDistributor、独立执行机，那是早期 V2 设计，**已不适用于本仓库**：
>
> - `backend/core/urls.py`：`executors` 仅变量管理，旧 Executor / TaskQueue / RabbitMQ 已移除  
> - `backend/apps/executions/services.py`：创建执行后直接 `ExecutionRunner.start()`  
> - `backend/apps/executors/consumers_v2.py`：任务下发已迁移到轻量化执行引擎  
> - 仓库中 **不存在** `executor-docker/`、`task_distributor.py`

## 目录

1. [当前架构（以代码为准）](#当前架构以代码为准)
2. [任务分发机制](#任务分发机制)（历史方案，已废弃）
3. [执行模式详解](#执行模式详解)（历史方案）
4. [关键问题与解决方案](#关键问题与解决方案)
5. [数据流详解](#数据流详解)
6. [通信协议](#通信协议)
7. [部署架构](#部署架构)

---

## 当前架构（以代码为准）

### 设计原则

| 原则 | 说明 | 实现方式 |
|------|------|----------|
| 进程内执行 | 不单独部署执行机 | `ExecutionRunner` 线程池调用 `PlaywrightEngine` |
| 并发可控 | 限制同时打开的浏览器数 | `MAX_CONCURRENT_EXECUTIONS`（环境变量 / 系统设置，默认 3） |
| 实时反馈 | 步骤结果推到页面 | Django Channels WebSocket |
| 可选基础设施 | 本地尽量零依赖 | 本地 `CHANNEL_LAYER_BACKEND=inmemory` + SQLite；生产用 Redis |

### 分层

```
┌─────────────────────────────────────────┐
│  Vue 3 前端（HTTP + WebSocket）          │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│  Django + DRF + Channels                │
│  executions.services → ExecutionRunner  │
│  ai_service（NL2Script / Healing）      │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│  engine/playwright_engine.py            │
│  本机或后端容器内的 Chromium             │
└─────────────────────────────────────────┘
```

不经过 RabbitMQ，也没有「执行器注册 / 心跳 / 专属队列」。

### 当前执行流程

```
用户点击「执行测试」
        │
        ▼
POST /api/executions/
        │
        ▼
start_script_execution() / start_plan_execution()
  - 创建 Execution（status=pending）
  - ExecutionRunner.start(execution_id, steps)
        │
        ▼
全局 ThreadPoolExecutor
  - 有空闲 worker：立即 _run()
  - 已满：排队，记录保持 pending
        │
        ▼
PlaywrightEngine.setup() → execute_steps()
  - 逐步写回结果
  - Channels 推送步骤状态
  - 失败时采集元素摘要，供 AI 分析
        │
        ▼
Execution status = completed / failed / cancelled
```

计划执行会为每个脚本建子 Execution，当前 runner **各自独立提交**，计划上的 sequential/parallel 字段保留，但并发实际上由线程池 `max_workers` 限制。

### 核心代码（当前）

| 文件 | 职责 |
|------|------|
| `backend/services/execution_runner.py` | 线程池、提交/取消、跑 Playwright |
| `backend/apps/executions/services.py` | 创建执行记录并 dispatch |
| `backend/engine/playwright_engine.py` | 步骤执行 |
| `backend/apps/executors/models.py` | 仅 Variable，不是执行机模型 |
| `backend/core/settings.py` | Channel 层：redis 或 inmemory |

### 和「只装浏览器驱动」的关系

V1 是桌面客户端 + Selenium 驱动。  
当前 V2 代码等价于：**后端所在环境装好 Playwright 浏览器**（`playwright install chromium`），即可跑用例。  
不需要再买一台执行机，也不需要 `executor-docker` 容器。

若把后端放进 Docker，浏览器必须打进 **backend 镜像**，而不是再起一个 executor 容器。

---

## 任务分发机制

> 以下至文末多数内容为早期「RabbitMQ + 独立执行器」方案存档，与当前代码不符。


### 完整任务分发流程

```
用户点击"执行测试"
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 创建执行记录                                        │
│ POST /api/executions/                                        │
│ - 创建 Execution 记录 (parent_id = plan_execution_id)        │
│ - 为计划中的每个脚本创建 TaskQueue 记录                      │
│ - 状态: pending                                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: TaskDistributor 扫描待分配任务                       │
│ backend/services/task_distributor.py                         │
│                                                              │
│ def distribute_pending_tasks():                              │
│     tasks = TaskQueue.objects.filter(status='pending')       │
│     for task in tasks:                                       │
│         executor = select_available_executor(task)           │
│         publish_to_mq(task, executor)                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 选择执行机                                           │
│                                                              │
│ 选择逻辑:                                                    │
│ 1. 过滤在线执行机 (status='online')                          │
│ 2. 过滤匹配项目/标签                                         │
│ 3. 过滤未达到并发上限的执行机                                 │
│    running_count < max_concurrent                            │
│ 4. 选择 running_count 最少的执行机 (负载均衡)                │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 发布到 RabbitMQ                                      │
│                                                              │
│ channel.basic_publish(                                       │
│     exchange='executor_tasks',                               │
│     routing_key=f'executor.{executor.uuid}',                │
│     body=json.dumps({                                        │
│         'task_id': task.id,                                  │
│         'script_data': {...},                                │
│         'execution_id': execution.id,                        │
│         'execution_mode': 'parallel'  // 或 'sequential'     │
│     })                                                       │
│ )                                                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: 执行机接收任务                                       │
│ executor-docker/task_manager.py                              │
│                                                              │
│ def on_message(ch, method, properties, body):               │
│     task_data = json.loads(body)                             │
│     result = self.task_manager.execute_task(task_data)       │
│     if result:                                               │
│         ch.basic_ack(delivery_tag)                           │
│     else:                                                    │
│         ch.basic_nack(delivery_tag, requeue=True)            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 6: 执行任务并上报结果                                   │
│ executor-docker/task_manager.py                              │
│                                                              │
│ 1. 启动执行线程                                               │
│ 2. 执行测试脚本                                               │
│ 3. 收集结果                                                   │
│ 4. HTTP POST 上报结果                                        │
│    POST /api/tasks/{task_id}/result/                         │
└─────────────────────────────────────────────────────────────┘
```

### 执行机选择算法

**代码位置**: `backend/apps/executors/services.py`

```python
def select_available_executor(project_id: int, tags: list = None) -> Optional[Executor]:
    """
    选择可用执行机

    算法流程:
    1. 查询在线执行机
    2. 过滤项目匹配
    3. 过滤标签匹配 (如果有)
    4. 过滤未达到并发上限
    5. 按运行任务数升序排序 (选择最空闲的)
    """
    executors = Executor.objects.filter(status='online')

    # 项目匹配
    executors = executors.filter(project_id=project_id)

    # 标签匹配
    if tags:
        executors = executors.filter(tags__overlap=tags)

    # 并发控制
    available_executors = []
    for executor in executors:
        running_count = TaskQueue.objects.filter(
            assigned_executor=executor,
            status__in=['assigned', 'running']
        ).count()

        if running_count < executor.max_concurrent:
            available_executors.append((executor, running_count))

    # 选择最空闲的
    if available_executors:
        return min(available_executors, key=lambda x: x[1])[0]
    return None
```

---

## 执行模式详解

### 顺序执行 (Sequential Execution)

**关键特征**: 由**后端控制**任务分发顺序

#### 控制逻辑

**代码位置**: `backend/services/task_distributor.py:59-96`

```python
# 如果是顺序执行，检查前一个脚本是否已完成
if execution_mode == 'sequential' and parent_execution_id:
    script_index = task.script_data.get('script_index', 0)

    if script_index > 0:
        with transaction.atomic():
            task = TaskQueue.objects.select_for_update().get(id=task.id)
            if task.status != 'pending':
                continue

            # 查询同父执行的所有子任务，按 id 排序
            sibling_executions = Execution.objects.filter(
                parent_id=parent_execution_id
            ).order_by('id')

            if script_index <= len(sibling_executions):
                prev_execution = sibling_executions[script_index - 1]

                # 核心判断: 前一个脚本必须完成
                if prev_execution.status not in ['completed', 'failed', 'stopped']:
                    logger.info(f"任务 {task.id} 等待前一个脚本完成")
                    continue  # 跳过此任务，等待下次分发
```

#### 顺序执行流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                    用户触发顺序执行计划                          │
│                       (4个脚本: A,B,C,D)                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Step 1: 创建4个 TaskQueue 记录                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │Task A    │  │Task B    │  │Task C    │  │Task D    │        │
│  │index=0   │  │index=1   │  │index=2   │  │index=3   │        │
│  │status:   │  │status:   │  │status:   │  │status:   │        │
│  │pending   │  │pending   │  │pending   │  │pending   │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Step 2: TaskDistributor 分发任务 A                  │
│                                                              │
│  检查: script_index=0，无需检查前序任务                         │
│  动作: 立即分发到执行机                                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Step 3: TaskDistributor 尝试分发任务 B              │
│                                                              │
│  检查: script_index=1，检查 Execution[0] 状态                   │
│  状态: Execution[0].status = 'running'                         │
│  动作: 跳过，等待下次扫描                                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ 等待...
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Step 4: 任务 A 完成，上报结果                       │
│                                                              │
│  Execution[0].status = 'completed'                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Step 5: TaskDistributor 再次扫描，分发任务 B        │
│                                                              │
│  检查: script_index=1，检查 Execution[0] 状态                   │
│  状态: Execution[0].status = 'completed' ✓                     │
│  动作: 立即分发到执行机                                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
                       ... 依次类推 ...
```

### 并发执行 (Parallel Execution)

**关键特征**: 由**执行机控制**并发数量

#### 控制逻辑

**代码位置**: `executor-docker/task_manager.py`

```python
def execute_task(self, task_data: dict) -> bool:
    """
    执行任务 - 并发控制核心逻辑

    返回: True-接收任务, False-拒绝任务
    """

    # 【关键】先加入 running_tasks，再检查并发限制
    # 避免竞态条件：多个任务同时到达时都能看到对方的占用
    execution_id = task_data.get("execution_id")
    self.running_tasks[task_id] = {
        "execution_id": execution_id,
        "script_name": script_name,
        "status": "starting",
    }

    # 现在检查并发限制
    current_tasks = len(self.running_tasks)
    if current_tasks > self.config.max_concurrent:
        # 超过限制，拒绝任务
        del self.running_tasks[task_id]
        return False  # 返回 False 导致 NACK + requeue=True

    # 启动执行线程
    threading.Thread(target=self._run_task, args=(...)).start()
    return True
```

#### 并发执行流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                    用户触发并发执行计划                          │
│                       (4个脚本: A,B,C,D)                         │
│                    max_concurrent = 3                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Step 1: TaskDistributor 分发所有任务                │
│                                                              │
│  顺序执行模式下会等待，但并发模式下立即分发所有任务               │
│  所有4个任务都被推送到 RabbitMQ 队列                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Step 2: 执行机消费任务                              │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  MessageQueueClient 从队列消费消息                       │    │
│  │  队列中有4个消息，逐个调用 TaskManager.execute_task()   │    │
│  └────────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Step 3: 并发控制 - 执行机端                        │
│                                                              │
│  任务A到达:                                                    │
│    running_tasks = {A: {...}}                                   │
│    len(running_tasks) = 1 ≤ 3 ✓ 接受                           │
│                                                              │
│  任务B到达:                                                    │
│    running_tasks = {A: {...}, B: {...}}                        │
│    len(running_tasks) = 2 ≤ 3 ✓ 接受                           │
│                                                              │
│  任务C到达:                                                    │
│    running_tasks = {A, B, C}                                   │
│    len(running_tasks) = 3 ≤ 3 ✓ 接受                           │
│                                                              │
│  任务D到达:                                                    │
│    running_tasks = {A, B, C}                                   │
│    len(running_tasks) = 3, 尝试添加 D                          │
│    len(running_tasks) = 4 > 3 ✗ 拒绝                           │
│    从 running_tasks 移除 D                                     │
│    返回 False → NACK + requeue=True                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Step 4: 任务 D 重新入队                            │
│                                                              │
│  RabbitMQ 将任务 D 重新放回队列末尾                             │
│  执行机继续处理队列中的其他任务...                               │
│  等待 A/B/C 中任意一个完成后，任务 D 将被成功接受               │
└─────────────────────────────────────────────────────────────────┘
```

### 两种执行模式对比

| 特性 | 顺序执行 | 并发执行 |
|------|----------|----------|
| **控制位置** | 后端 (TaskDistributor) | 执行机 (TaskManager) |
| **控制机制** | 检查前序任务完成状态 | running_tasks 数量限制 |
| **分发时机** | 前序任务完成后才分发 | 立即分发所有任务 |
| **并发保证** | 同时只有1个任务运行 | 最多 max_concurrent 个任务 |
| **代码位置** | `task_distributor.py:59-96` | `executor-docker/task_manager.py` |
| **拒绝处理** | 跳过，等待下次扫描 | NACK + requeue=True |

---

## 关键问题与解决方案

### 问题1: 并发执行竞态条件 (Race Condition)

#### 问题描述

当多个任务几乎同时到达执行机时，如果先检查并发限制再添加到 running_tasks，会导致所有任务都看到 "当前只有0个任务在运行"，从而全部通过检查。

#### 错误代码示例

```python
# ❌ 错误的实现 - 先检查后添加
def execute_task_wrong(self, task_data: dict) -> bool:
    current_tasks = len(self.running_tasks)

    # 竞态窗口: 多个线程可能同时执行到这里
    if current_tasks >= self.config.max_concurrent:
        return False  # 拒绝

    # 多个线程都会执行到这里
    self.running_tasks[task_id] = {...}
    return True
```

#### 时序分析

```
时间轴 →
─────────────────────────────────────────────────────────────

任务A                    任务B                    任务C
│                        │                        │
▼                        ▼                        ▼
check: len=0 ✓          check: len=0 ✓          check: len=0 ✓
│                        │                        │
│                        │                        │
▼                        ▼                        ▼
add A→len=1             add B→len=2             add C→len=3

结果: max_concurrent=2，但有3个任务同时运行!
```

#### 正确实现

```python
# ✓ 正确的实现 - 先添加后检查
def execute_task_correct(self, task_data: dict) -> bool:
    task_id = task_data.get("task_id")

    # 【关键】先加入 running_tasks
    self.running_tasks[task_id] = {
        "execution_id": task_data.get("execution_id"),
        "script_name": task_data.get("script_name"),
        "status": "starting",
    }

    # 【关键】再检查并发限制
    current_tasks = len(self.running_tasks)
    if current_tasks > self.config.max_concurrent:
        # 超过限制，移除并拒绝
        del self.running_tasks[task_id]
        return False

    # 启动执行线程
    threading.Thread(target=self._run_task, args=(...)).start()
    return True
```

#### 时序分析

```
时间轴 →
─────────────────────────────────────────────────────────────

任务A                    任务B                    任务C
│                        │                        │
▼                        ▼                        ▼
add A→len=1             add B→len=2             add C→len=3
│                        │                        │
check: 1≤2 ✓            check: 2≤2 ✓            check: 3>2 ✗
│                        │                        │
│                        │                        ▼
keep A                   keep B                  remove C
拒绝任务C

结果: 严格保证最多2个任务同时运行!
```

#### 相关代码

| 文件 | 行号 | 说明 |
|------|------|------|
| `executor-docker/task_manager.py` | - | 并发控制核心逻辑 |
| `executor-docker/task_manager.py` | - | NACK + requeue 处理 |

### 问题2: JSON 数据截断导致 HTTP 400

#### 问题描述

执行结果上报时，使用 `data=json_data` 参数导致 `requests` 库无法正确设置 `Content-Length` 头，大 JSON 被截断。

#### 错误代码

```python
# ❌ 错误实现
response = requests.post(
    result_url,
    data=json.dumps(result),  # 错误: 使用 data 参数
    headers={'Content-Type': 'application/json'},
    timeout=10
)
```

#### 正确实现

```python
# ✓ 正确实现
response = requests.post(
    result_url,
    json=result,  # 正确: 使用 json 参数，requests 自动序列化
    timeout=10
)
```

#### 相关代码

| 文件 | 行号 | 说明 |
|------|------|------|
| `executor-docker/task_manager.py` | - | JSON 序列化修复 |

### 问题3: 执行机注册重试机制

#### 问题描述

执行机启动时，后端服务可能尚未就绪，导致注册失败。

#### 解决方案

实现指数退避重试机制。

```python
def _register_executor(self, max_retries: int = 5, initial_delay: float = 2.0) -> bool:
    """
    注册执行机到平台（带重试机制）
    """
    import time
    api_base = self.config.server_url.rstrip('/')
    register_url = f"{api_base}/api/executor/register/"

    for attempt in range(max_retries):
        try:
            response = requests.post(register_url, json={...}, timeout=10)
            if response.status_code == 200:
                logger.info("执行机注册成功")
                return True
        except Exception as e:
            logger.warning(f"执行机注册异常 (尝试 {attempt + 1}/{max_retries}): {e}")

        if attempt < max_retries - 1:
            delay = initial_delay * (2 ** attempt)  # 指数退避
            logger.info(f"等待 {delay:.1f} 秒后重试注册...")
            time.sleep(delay)

    return False
```

#### 重试时间表

| 尝试次数 | 等待时间 | 累计时间 |
|----------|----------|----------|
| 1 | 0s | 0s |
| 2 | 2s | 2s |
| 3 | 4s | 6s |
| 4 | 8s | 14s |
| 5 | 16s | 30s |

---

## 数据流详解

### 完整数据流 - 从用户点击到测试执行

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户操作                                    │
│                   点击"执行测试"按钮                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   前端 Vue.js                                   │
│  POST /api/executions/                                          │
│  {                                                              │
│    "plan_id": 7,                                                │
│    "execution_mode": "parallel",  // 或 "sequential"            │
│    "env": "test"                                                │
│  }                                                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP 201 Created
                           │ 返回 execution_id
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  后端 Django REST API                           │
│  ExecutionSerializer.create()                                   │
│  1. 创建 Execution 记录 (status='pending')                       │
│  2. 创建子 Execution 记录 (每个脚本一条)                         │
│  3. 创建 TaskQueue 记录 (每个脚本一条，status='pending')         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              TaskDistributor (后台服务)                         │
│  每5秒扫描一次待分配任务                                         │
│                                                              │
│  distribute_pending_tasks():                                    │
│      tasks = TaskQueue.objects.filter(status='pending')         │
│      for task in tasks:                                         │
│          # 顺序执行检查                                          │
│          if execution_mode == 'sequential':                     │
│              if not check_previous_completed(task):             │
│                  continue  # 跳过，等待                          │
│          # 选择执行机                                            │
│          executor = select_available_executor(task)             │
│          # 发布到 MQ                                            │
│          publish_to_mq(task, executor)                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   RabbitMQ                                      │
│  Exchange: executor_tasks                                       │
│  Routing Key: executor.{executor_uuid}                          │
│  Message:                                                       │
│  {                                                              │
│    "task_id": 123,                                              │
│    "script_data": {...},                                        │
│    "execution_id": 456,                                         │
│    "execution_mode": "parallel"                                 │
│  }                                                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│            AsyncTaskManager (执行机)                            │
│  on_message(ch, method, properties, body):                      │
│      task_data = json.loads(body)                               │
│      result = task_manager.execute_task(task_data)              │
│      if result:                                                 │
│          ch.basic_ack(delivery_tag)                             │
│      else:                                                      │
│          ch.basic_nack(delivery_tag, requeue=True)              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              AsyncTaskManager (执行机)                          │
│  execute_task(task_data):                                       │
│      # 1. 并发控制检查                                          │
│      if not check_concurrent_limit(task_data):                  │
│          return False  # 拒绝任务                               │
│      # 2. 启动执行线程                                          │
│      thread = threading.Thread(target=_run_task, ...)           │
│      thread.start()                                             │
│      return True                                                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                 测试引擎                                        │
│  Selenium / Playwright / Appium / HttpRunner                   │
│  1. 初始化驱动/客户端                                           │
│  2. 执行测试步骤                                                 │
│  3. 收集结果                                                     │
│  4. 清理资源                                                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              上报执行结果                                        │
│  POST /api/tasks/{task_id}/result/                              │
│  {                                                              │
│    "status": "completed",  // 或 "failed"                       │
│    "result_data": {...},                                        │
│    "start_time": "...",                                         │
│    "end_time": "...",                                           │
│    "error": null                                                │
│  }                                                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP 200 OK
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│            后端处理结果                                          │
│  1. 更新 TaskQueue.status = 'completed'                         │
│  2. 更新 Execution.status = 'completed'                         │
│  3. 触发 WebSocket 通知                                         │
│  4. 调用 TaskDistributor 继续分发下一批任务                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│            WebSocket 实时推送                                    │
│  /ws/executor-status/                                           │
│  前端接收状态更新，刷新 UI                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 通信协议

### HTTP API

#### 执行机注册

```http
POST /api/executor/register/ HTTP/1.1
Content-Type: application/json

{
  "executor_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "测试执行机-01",
  "project_id": 7,
  "max_concurrent": 3,
  "tags": ["chrome", "windows"],
  "ip_address": "192.168.1.100",
  "system_info": {
    "os": "Windows 11",
    "cpu_cores": 8,
    "memory_gb": 16
  }
}

HTTP/1.1 200 OK
{"status": "registered"}
```

#### 执行机心跳

```http
POST /api/executor/heartbeat/ HTTP/1.1
Content-Type: application/json

{
  "executor_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "cpu_usage": 25.5,
  "memory_usage": 45.2,
  "disk_usage": 60.0,
  "running_tasks": 2
}

HTTP/1.1 200 OK
{"status": "ok"}
```

#### 上报执行结果

```http
POST /api/tasks/123/result/ HTTP/1.1
Content-Type: application/json

{
  "task_id": 123,
  "execution_id": 456,
  "status": "completed",
  "start_time": "2026-02-10T03:57:00Z",
  "end_time": "2026-02-10T03:58:30Z",
  "result_data": {
    "total_steps": 10,
    "passed_steps": 10,
    "failed_steps": 0,
    "skipped_steps": 0,
    "screenshots": ["screenshot1.png"],
    "logs": "Test execution log..."
  }
}

HTTP/1.1 200 OK
{"status": "result_recorded"}
```

### RabbitMQ 消息格式

#### 任务消息

```json
{
  "task_id": 123,
  "execution_id": 456,
  "parent_execution_id": 789,
  "script_data": {
    "script_id": 5,
    "script_name": "登录测试",
    "script_type": "web",
    "test_framework": "selenium",
    "steps": [...],
    "variables": {...}
  },
  "execution_mode": "parallel",
  "env": "test",
  "browser": "chrome",
  "project_id": 7
}
```

### WebSocket 消息

#### 执行机状态更新

```json
{
  "type": "executor_status",
  "data": {
    "executor_id": 1,
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "name": "测试执行机-01",
    "status": "online",
    "running_tasks": 2,
    "max_concurrent": 3,
    "cpu_usage": 25.5,
    "memory_usage": 45.2
  }
}
```

#### 执行状态更新

```json
{
  "type": "execution_status",
  "data": {
    "execution_id": 456,
    "status": "running",
    "progress": 50,
    "current_script": "登录测试"
  }
}
```

---

## 部署架构

### 单机开发环境

```
┌─────────────────────────────────────────────────────────────┐
│                       本地机器                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  浏览器                                                │  │
│  │  http://localhost:5173                                 │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Django 后端 (daphne)                                  │  │
│  │  http://0.0.0.0:8000                                   │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  RabbitMQ                                             │  │
│  │  amqp://guest:guest@localhost:5672                    │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  执行器 (Playwright Docker)                            │  │
│  │  docker compose up -d executor                        │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 生产环境分布式部署

```
┌─────────────────────────────────────────────────────────────────┐
│                         负载均衡器                                │
│                            Nginx                                 │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Web 服务器集群                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Nginx + Vue │  │  Nginx + Vue │  │  Nginx + Vue │          │
│  │   前端静态    │  │   前端静态    │  │   前端静态    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API 服务器集群                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Django     │  │   Django     │  │   Django     │          │
│  │  (Daphne)    │  │  (Daphne)    │  │  (Daphne)    │          │
│  │   :8000      │  │   :8001      │  │   :8002      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      共享存储                                     │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │ PostgreSQL   │  │   RabbitMQ   │                             │
│  │   数据库      │  │   消息队列    │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    执行机集群 (多台机器)                          │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │  执行机节点 A     │  │  执行机节点 B     │                     │
│  │  - Windows 11    │  │  - Linux         │                     │
│  │  - Chrome        │  │  - Firefox       │                     │
│  │  - max_concur=3  │  │  - max_concur=5  │                     │
│  └──────────────────┘  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 附录

### 核心代码文件索引

**当前有效：**

| 文件路径 | 核心功能 |
|----------|----------|
| `backend/services/execution_runner.py` | 线程池执行引擎 |
| `backend/apps/executions/services.py` | 创建并提交执行 |
| `backend/engine/playwright_engine.py` | Playwright 步骤引擎 |
| `backend/apps/executions/models.py` | Execution / HealLog |

**以下文件在本仓库中已不存在或已改职责（早期方案）：**

| 文件路径 | 说明 |
|----------|------|
| `backend/services/task_distributor.py` | 不存在 |
| `executor-docker/` | 不存在 |
| `backend/apps/tasks/models.py` | 不存在 |
| `backend/apps/executors/` | 现仅变量 API |

### 数据库关系图

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Project    │1       n│    Script    │1       n│     Plan     │
│──────────────│─────────│──────────────│─────────│──────────────│
│ id           │         │ id           │         │ id           │
│ name         │         │ project_id   │         │ project_id   │
│ type         │         │ name         │         │ name         │
└──────────────┘         │ script_type  │         │ scripts(m2m) │
                         └──────────────┘         └──────────────┘
                                  │                         │
                                  │                         │n
                                  │1                        │
                                  ▼                         ▼
                         ┌──────────────┐         ┌──────────────┐
                         │  Execution   │1       1│  Execution   │
                         │ (脚本执行)    │─────────│  (计划执行)   │
                         │──────────────│         │──────────────│
                         │ id           │         │ id           │
                         │ script_id    │         │ plan_id      │
                         │ status       │         │ execution_   │
                         │ parent_id    │         │   mode       │
                         └──────────────┘         └──────────────┘
                                  │1
                                  │
                                  │n
                         ┌──────────────┐
                         │  TaskQueue   │
                         │──────────────│
                         │ id           │
                         │ execution_id │
                         │ status       │
                         │ assigned_    │
                         │   executor   │
                         └──────────────┘
                                  │1
                                  │
                                  │n
                         ┌──────────────┐
                         │  Executor    │
                         │──────────────│
                         │ uuid         │
                         │ max_concurrent│
                         │ status       │
                         └──────────────┘
```

---

**文档版本**: v1.0
**最后更新**: 2026-02-10
**维护者**: Auto Test Platform Team
