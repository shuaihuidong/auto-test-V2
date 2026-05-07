"""
ExecutionRunner - 轻量化后台线程执行引擎

职责：
1. 使用全局 ThreadPoolExecutor 管理并发，限制同时运行的浏览器数
2. 在后台线程中运行 PlaywrightEngine，逐步推送步骤结果到 WebSocket
3. 步骤失败时如实记录结果和 DOM 快照，供后续手动 AI 分析使用
4. 支持优雅停机（取消排队任务、等待运行中任务完成或超时）
"""

import threading
import time
import logging
import json
import os
import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Any, List, Optional

from django.utils import timezone
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

# ==================== 并发控制 ====================

# 全局配置：最大同时执行数（即可同时启动的 Playwright 浏览器实例数）
# 优先读环境变量，否则默认 3
MAX_CONCURRENT_EXECUTIONS = int(os.getenv('MAX_CONCURRENT_EXECUTIONS', '3'))


def _ensure_windows_proactor_event_loop_policy() -> None:
    """
    Playwright 在 Windows 上需要支持 subprocess 的 event loop policy.

    ThreadPoolExecutor 里的 worker 线程有时会拿到不支持 subprocess 的
    SelectorEventLoop，导致 sync_playwright() 启动时抛 NotImplementedError。
    """
    if sys.platform != 'win32':
        return

    policy = asyncio.get_event_loop_policy()
    if not isinstance(policy, asyncio.WindowsProactorEventLoopPolicy):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def _get_max_workers() -> int:
    """
    获取最大并发工作线程数。

    优先级：数据库 settings_ai_setting > Django settings > 环境变量 > 默认值 3
    """
    # 1. 尝试从数据库读取（与 AI 配置走同一套机制）
    try:
        from apps.settings.models import AISetting
        row = AISetting.objects.filter(key='MAX_CONCURRENT_EXECUTIONS').first()
        if row and row.value:
            val = int(row.value)
            if val >= 1:
                return val
    except Exception:
        pass

    # 2. Django settings
    try:
        from django.conf import settings
        cfg = getattr(settings, 'EXECUTION_RUNNER', {})
        val = cfg.get('max_workers')
        if val:
            return int(val)
    except Exception:
        pass

    # 3. 环境变量 / 默认值
    return MAX_CONCURRENT_EXECUTIONS


class _ExecutionPool:
    """
    全局执行线程池（单例）

    - 控制最大并发浏览器数
    - 记录每个 execution_id 对应的 Future，用于取消和查询状态
    - 提供优雅停机
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        max_workers = _get_max_workers()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix='exec-runner',
        )
        self._futures: Dict[int, Future] = {}  # execution_id -> Future
        self._futures_lock = threading.Lock()
        logger.info(f'ExecutionPool initialized, max_workers={max_workers}')

    @property
    def max_workers(self) -> int:
        return self._executor._max_workers

    def submit(self, execution_id: int, fn, *args, **kwargs) -> Future:
        """提交任务到线程池"""
        future = self._executor.submit(fn, *args, **kwargs)
        with self._futures_lock:
            self._futures[execution_id] = future
        future.add_done_callback(lambda f: self._remove_future(execution_id))
        return future

    def _remove_future(self, execution_id: int):
        with self._futures_lock:
            self._futures.pop(execution_id, None)

    def cancel(self, execution_id: int) -> bool:
        """
        尝试取消指定执行。

        - 如果任务还在排队（未开始），直接取消，返回 True
        - 如果已经在运行中，无法中断线程，返回 False
        """
        with self._futures_lock:
            future = self._futures.get(execution_id)
        if future and future.cancel():
            self._remove_future(execution_id)
            logger.info(f'Execution {execution_id} cancelled (was queued)')
            return True
        return False

    def active_count(self) -> int:
        """当前正在运行的任务数"""
        with self._futures_lock:
            return sum(1 for f in self._futures.values() if f.running())

    def queued_count(self) -> int:
        """当前排队等待的任务数"""
        with self._futures_lock:
            return sum(1 for f in self._futures.values() if not f.running() and not f.done())

    def shutdown(self, wait: bool = True, timeout: float = 30):
        """
        优雅关闭线程池。

        wait=True  时会阻塞等待运行中任务完成（最多 timeout 秒）
        wait=False 时立即返回，运行中任务继续到完成
        """
        logger.info('ExecutionPool shutting down...')
        # 尝试取消所有排队中的任务
        with self._futures_lock:
            for eid, future in list(self._futures.items()):
                future.cancel()
        self._executor.shutdown(wait=wait)


def get_pool() -> _ExecutionPool:
    """获取全局线程池单例"""
    return _ExecutionPool()


# ==================== ExecutionRunner ====================

class ExecutionRunner:
    """
    轻量化执行运行器

    使用全局 ThreadPoolExecutor + Playwright 引擎执行测试脚本，
    通过 Django Channels WebSocket 逐步推送结果。
    """

    @staticmethod
    def start(
        execution_id: int,
        steps: List[Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None,
    ) -> Future:
        """
        提交执行任务到线程池。

        如果线程池已满，任务会排队等待，执行状态保持 pending 直到轮到执行。
        """
        pool = get_pool()
        future = pool.submit(
            execution_id,
            ExecutionRunner._run,
            execution_id, steps, config,
        )
        logger.info(
            f'Execution {execution_id} submitted. '
            f'active={pool.active_count()}, queued={pool.queued_count()}, '
            f'max_workers={pool.max_workers}'
        )
        return future

    @staticmethod
    def cancel(execution_id: int) -> bool:
        """
        取消执行。

        - 排队中的任务：直接移除
        - 运行中的任务：标记 stopped（线程无法强制中断，但会在下一个步骤检查时退出）
        """
        pool = get_pool()
        cancelled = pool.cancel(execution_id)

        if not cancelled:
            # 运行中 → 标记 stopped，_run 循环里会检查
            from apps.executions.models import Execution
            try:
                execution = Execution.objects.get(id=execution_id)
                if execution.status in ('running', 'pending'):
                    execution.status = 'stopped'
                    execution.completed_at = timezone.now()
                    execution.save(update_fields=['status', 'completed_at'])
                    logger.info(f'Execution {execution_id} marked as stopped')
                    return True
            except Exception:
                pass

        return cancelled

    @staticmethod
    def get_status() -> Dict[str, int]:
        """获取线程池状态"""
        pool = get_pool()
        return {
            'max_workers': pool.max_workers,
            'active': pool.active_count(),
            'queued': pool.queued_count(),
        }

    @staticmethod
    def _run(execution_id: int, steps: List[Dict[str, Any]], config: Optional[Dict[str, Any]] = None):
        """在后台线程中执行所有步骤"""
        _ensure_windows_proactor_event_loop_policy()
        # Playwright sync_api 内部会启动一个 asyncio event loop，
        # 导致 Django 误判当前处于 async context 而拒绝同步 DB 操作。
        # 此线程实际是同步线程，标记允许即可。
        os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

        from apps.executions.models import Execution
        from engine.playwright_engine import PlaywrightEngine

        channel_layer = get_channel_layer()
        group_name = f'execution_{execution_id}'

        engine = None

        try:
            execution = Execution.objects.get(id=execution_id)
        except Execution.DoesNotExist:
            logger.error(f'Execution {execution_id} not found')
            return

        try:
            # 0. 检查是否已被取消
            execution.refresh_from_db()
            if execution.status == 'stopped':
                logger.info(f'Execution {execution_id} was stopped before starting')
                return

            # 1. 更新状态为 running
            execution.status = 'running'
            execution.started_at = timezone.now()
            execution.save(update_fields=['status', 'started_at'])

            # 2. 初始化 Playwright 引擎
            engine_config = config or {}
            engine_config.setdefault('headless', True)
            engine_config.setdefault('screenshot_on_failure', True)

            # 截图目录：每次执行独立一个文件夹
            from django.conf import settings as django_settings
            ts = timezone.now().strftime('%Y%m%d_%H%M%S')
            exec_folder = f'exec_{execution_id}_{ts}'
            engine_config['screenshot_dir'] = os.path.join(django_settings.SCREENSHOTS_ROOT, exec_folder)

            engine = PlaywrightEngine(engine_config)
            if not engine.setup():
                raise RuntimeError('Playwright 引擎初始化失败')

            # 3. 推送 execution_started 事件
            _push_event(channel_layer, group_name, {
                'type': 'execution_started',
                'total': len(steps),
                'execution_id': execution_id,
            })

            passed = 0
            failed = 0
            step_results = []

            # 4. 逐步执行
            for i, step in enumerate(steps):
                # ---- 停止检查 ----
                execution.refresh_from_db(fields=['status'])
                if execution.status == 'stopped':
                    logger.info(f'Execution {execution_id} stopped at step {i}')
                    # 把剩余步骤标记为 skipped
                    for j in range(i, len(steps)):
                        step_results.append({
                            'index': j,
                            'name': steps[j].get('name', ''),
                            'type': steps[j].get('type', ''),
                            'success': False,
                            'error': '用户已停止执行',
                            'duration': 0,
                        })
                        failed += 1
                        _push_event(channel_layer, group_name, {
                            'type': 'step_result',
                            'index': j,
                            'name': steps[j].get('name', ''),
                            'step_type': steps[j].get('type', ''),
                            'success': False,
                            'error': '用户已停止执行',
                            'duration': 0,
                        })
                    break

                step_copy = json.loads(json.dumps(step))  # deep copy
                engine.current_step_index = i

                # 解析变量
                resolved_step = engine.resolve_variables(step_copy)

                step_result = engine.execute_step(resolved_step)

                # 4.1 每步执行后自动截图（如果步骤本身没有产生截图）
                if not step_result.get('screenshot'):
                    try:
                        auto_screenshot = engine._take_screenshot(f'step_{i}', full_page=False)
                        if auto_screenshot:
                            step_result['screenshot'] = auto_screenshot
                    except Exception:
                        pass  # 截图失败不影响执行

                # 5. 构建步骤结果
                result_data = {
                    'type': 'step_result',
                    'index': i,
                    'name': step.get('name', ''),
                    'step_type': step.get('type', ''),
                    'success': step_result.get('success', False),
                    'duration': step_result.get('duration', 0),
                    'message': step_result.get('message', ''),
                }

                if not step_result.get('success'):
                    result_data['error'] = step_result.get('error', '')
                    failed += 1
                else:
                    passed += 1

                if step_result.get('screenshot'):
                    result_data['screenshot'] = step_result['screenshot']

                # 推送单步结果
                _push_event(channel_layer, group_name, result_data)

                # 记录步骤结果
                step_results.append({
                    'index': i,
                    'name': step.get('name', ''),
                    'type': step.get('type', ''),
                    'success': step_result.get('success', False),
                    'message': step_result.get('message', ''),
                    'error': step_result.get('error', ''),
                    'duration': step_result.get('duration', 0),
                    'screenshot': step_result.get('screenshot'),
                    'dom_snapshot': step_result.get('dom_snapshot', '')[:50000],
                })

            # 6. 保存最终结果
            # 重新读取，防止 stopped 被覆盖
            execution.refresh_from_db(fields=['status'])
            final_status = execution.status
            if final_status != 'stopped':
                final_status = 'completed' if failed == 0 else 'failed'

            execution.status = final_status
            execution.completed_at = timezone.now()
            execution.result = {
                'total': len(steps),
                'passed': passed,
                'failed': failed,
                'steps': step_results,
            }
            execution.save(update_fields=['status', 'completed_at', 'result'])

            # 7. 推送 execution_completed 事件
            if final_status != 'stopped':
                _push_event(channel_layer, group_name, {
                    'type': 'execution_completed',
                    'status': final_status,
                    'result': {
                        'total': len(steps),
                        'passed': passed,
                        'failed': failed,
                    },
                    'execution_id': execution_id,
                })

            # 8. 自动生成报告
            try:
                from apps.reports.generators import ReportGenerator
                generator = ReportGenerator(execution)
                generator.generate()
                logger.info(f'Report auto-generated for execution {execution_id}')
            except Exception as report_err:
                logger.warning(f'Failed to auto-generate report for execution {execution_id}: {report_err}')

        except Exception as e:
            logger.error(f'Execution {execution_id} failed with error: {e}', exc_info=True)

            # 更新执行状态为 failed
            try:
                execution.status = 'failed'
                execution.completed_at = timezone.now()
                execution.result = {
                    'total': len(steps),
                    'passed': 0,
                    'failed': 0,
                    'error': str(e),
                    'steps': [],
                }
                execution.save(update_fields=['status', 'completed_at', 'result'])
            except Exception:
                pass

            # 推送 execution_error 事件
            _push_event(channel_layer, group_name, {
                'type': 'execution_error',
                'error': str(e),
                'execution_id': execution_id,
            })

        finally:
            # 清理引擎资源
            if engine:
                try:
                    engine.teardown()
                except Exception:
                    pass

            # 更新父执行记录状态（如果是计划执行中的子执行）
            _update_parent_execution(execution_id)

            # 为父执行自动生成报告
            try:
                execution.refresh_from_db()
                if execution.parent_id:
                    from apps.reports.generators import ReportGenerator
                    parent = execution.parent
                    if parent.status in ('completed', 'failed'):
                        generator = ReportGenerator(parent)
                        generator.generate()
                        logger.info(f'Report auto-generated for parent execution {parent.id}')
            except Exception as e:
                logger.warning(f'Failed to generate parent report: {e}')


# ==================== 辅助函数 ====================

def _push_event(channel_layer, group_name: str, data: Dict[str, Any]):
    """推送事件到 Channel Layer"""
    try:
        # Playwright sync_api 在当前线程中运行了 asyncio event loop，
        # 导致 async_to_sync / asyncio.new_event_loop 均不可用。
        # 在独立线程中执行异步推送来规避这一限制。
        import asyncio

        async def _send():
            await channel_layer.group_send(
                group_name,
                {
                    'type': 'execution_message',
                    'data': data,
                }
            )

        t = threading.Thread(
            target=lambda: asyncio.run(_send()),
            daemon=True,
        )
        t.start()
        t.join(timeout=2)  # 最多等2秒，Redis不可用时快速跳过
    except Exception as e:
        logger.debug(f'Failed to push event to {group_name}: {e}')


def _update_parent_execution(execution_id: int):
    """更新父执行记录状态（如果当前执行是计划执行的子执行）"""
    from apps.executions.models import Execution

    try:
        execution = Execution.objects.get(id=execution_id)
        if not execution.parent_id:
            return

        parent = execution.parent
        children = parent.children.all()

        # 检查是否所有子执行都已完成
        all_done = all(
            child.status in ('completed', 'failed', 'stopped')
            for child in children
        )

        if all_done:
            passed_count = children.filter(status='completed').count()
            failed_count = children.filter(status='failed').count()

            parent.status = 'failed' if failed_count > 0 else 'completed'
            parent.completed_at = timezone.now()
            parent.result = {
                'total': children.count(),
                'passed': passed_count,
                'failed': failed_count,
            }
            parent.save(update_fields=['status', 'completed_at', 'result'])

            # 推送父执行完成事件
            channel_layer = get_channel_layer()
            _push_event(channel_layer, f'execution_{parent.id}', {
                'type': 'execution_completed',
                'status': parent.status,
                'result': {
                    'total': children.count(),
                    'passed': passed_count,
                    'failed': failed_count,
                },
                'execution_id': parent.id,
            })

    except Exception as e:
        logger.error(f'Failed to update parent execution for {execution_id}: {e}')
