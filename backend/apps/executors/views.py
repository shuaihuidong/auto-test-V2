from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
import logging

from .models import Executor, ExecutorGroup, ExecutorTag, ExecutorStatusLog, Variable, TaskQueue
from .serializers import (
    ExecutorSerializer, ExecutorGroupSerializer, ExecutorTagSerializer,
    ExecutorStatusLogSerializer, VariableSerializer, TaskQueueSerializer,
    ExecutorHeartbeatSerializer, ExecutorRegisterSerializer, TaskExecutionSerializer
)

logger = logging.getLogger(__name__)


class ExecutorViewSet(viewsets.ModelViewSet):
    """执行机管理视图集"""
    serializer_class = ExecutorSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'scope', 'platform', 'is_enabled']
    search_fields = ['name', 'uuid']
    ordering_fields = ['created_at', 'last_heartbeat', 'name']
    ordering = ['-created_at']

    def update(self, request, *args, **kwargs):
        """更新执行机（带错误日志）"""
        try:
            response = super().update(request, *args, **kwargs)
            executor = self.get_object()

            # 如果修改了并发数，通过WebSocket通知执行机更新配置
            if hasattr(request, 'data') and 'max_concurrent' in request.data:
                self._notify_executor_config_update(executor, {'max_concurrent': request.data['max_concurrent']})

            return response
        except Exception as e:
            logger.error(f"更新执行机失败: {e}", exc_info=True)
            return Response(
                {'error': str(e), 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _notify_executor_config_update(self, executor, config_changes):
        """通过WebSocket通知执行机更新配置"""
        from channels.layers import get_channel_layer

        # 构造配置更新消息
        message = {
            'type': 'config_update',
            'data': config_changes
        }

        # 发送给执行机
        try:
            import asyncio
            from asgiref.sync import async_to_sync

            async def send_notification():
                await get_channel_layer().group_send(
                    f'executor_{executor.uuid}',
                    {
                        'type': 'config_update',
                        'data': config_changes
                    }
                )

            async_to_sync(send_notification)()
            logger.info(f"已通知执行机 {executor.name} 更新配置: {config_changes}")
        except Exception as e:
            logger.warning(f"通知执行机配置更新失败: {e}")

    def get_queryset(self):
        """获取查询集 - 只返回当前用户的执行机"""
        queryset = Executor.objects.filter(owner=self.request.user)

        # 项目创建者可以看到项目内的全局执行机
        user_created_projects = self.request.user.created_projects.all()
        for project in user_created_projects:
            project_executors = Executor.objects.filter(
                Q(bound_projects=project) | Q(scope='global')
            )
            queryset = queryset | project_executors

        return queryset.distinct()

    @action(detail=False, methods=['get'])
    def online(self, request):
        """获取在线执行机列表"""
        queryset = self.get_queryset().filter(status='online')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def available(self, request):
        """获取可用执行机列表（在线且未达并发上限）"""
        import logging
        logger = logging.getLogger(__name__)

        project_id = request.query_params.get('project_id')
        logger.info(f"查询可用执行机 - project_id={project_id}")

        queryset = self.get_queryset().filter(is_enabled=True)
        logger.info(f"已启用执行机数量: {queryset.count()}")

        # 如果指定了项目，过滤可用执行机
        if project_id:
            global_executors = queryset.filter(scope='global')
            project_executors = queryset.filter(scope='project', bound_projects__id=project_id)
            queryset = global_executors | project_executors
        else:
            queryset = queryset.filter(scope='global')

        logger.info(f"作用域过滤后执行机数量: {queryset.count()}")

        # 输出每个执行机的状态
        for e in queryset:
            logger.info(f"执行机: {e.name}, is_online={e.is_online}, is_enabled={e.is_enabled}, "
                       f"current_tasks={e.current_tasks}, max_concurrent={e.max_concurrent}, "
                       f"is_available={e.is_available}, last_heartbeat={e.last_heartbeat}")

        # 过滤可用执行机
        available_executors = [e for e in queryset if e.is_available]
        logger.info(f"最终可用执行机数量: {len(available_executors)}")

        serializer = self.get_serializer(available_executors, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def heartbeat(self, request, pk=None):
        """执行机心跳"""
        executor = self.get_object()

        # 验证执行机所有者
        if executor.owner != request.user:
            return Response(
                {'error': '无权操作此执行机'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ExecutorHeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 更新执行机状态
        data = serializer.validated_data
        executor.status = data.get('status', 'online')
        # 不再用心跳覆盖 current_tasks，因为后端在任务分配/完成时会正确更新
        # 只有当执行机报告的任务数与后端不一致时才更新（用于修正异常情况）
        reported_tasks = data.get('current_tasks', 0)
        # 仅当报告数大于后端记录数时更新（防止任务完成后未及时减少）
        if reported_tasks > executor.current_tasks:
            executor.current_tasks = reported_tasks
        executor.last_heartbeat = timezone.now()
        executor.save()

        # 记录状态日志
        ExecutorStatusLog.objects.create(
            executor=executor,
            status=executor.status,
            cpu_usage=data.get('cpu_usage'),
            memory_usage=data.get('memory_usage'),
            disk_usage=data.get('disk_usage'),
            current_tasks=executor.current_tasks,
            message=data.get('message', '')
        )

        return Response({'message': '心跳更新成功', 'server_time': timezone.now()})

    @action(detail=True, methods=['get'])
    def status_logs(self, request, pk=None):
        """获取执行机状态日志"""
        executor = self.get_object()
        logs = executor.status_logs.all()[:100]  # 最近100条
        serializer = ExecutorStatusLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def config(self, request, pk=None):
        """获取执行机配置信息"""
        executor = self.get_object()

        if executor.owner != request.user:
            return Response(
                {'error': '无权查看此执行机配置'},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response({
            'uuid': str(executor.uuid),
            'name': executor.name,
            'max_concurrent': executor.max_concurrent,
            'browser_types': executor.browser_types,
            'platform': executor.platform,
        })


class ExecutorGroupViewSet(viewsets.ModelViewSet):
    """执行机分组视图集"""
    queryset = ExecutorGroup.objects.all()
    serializer_class = ExecutorGroupSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['sort_order', 'created_at']
    ordering = ['sort_order', '-created_at']


class ExecutorTagViewSet(viewsets.ModelViewSet):
    """执行机标签视图集"""
    queryset = ExecutorTag.objects.all()
    serializer_class = ExecutorTagSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['sort_order', 'created_at']
    ordering = ['sort_order', '-created_at']


class VariableViewSet(viewsets.ModelViewSet):
    """变量管理视图集"""
    serializer_class = VariableSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['scope', 'type', 'is_sensitive']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['scope', 'project', 'script', 'name']

    def get_queryset(self):
        """获取查询集"""
        queryset = Variable.objects.all()
        user = self.request.user

        # 管理员和超级管理员可以看到所有变量
        if user.role in ['admin', 'super_admin']:
            return queryset

        # 其他用户只能看到自己创建的项目的变量
        user_created_projects = user.created_projects.all()
        queryset = queryset.filter(
            Q(project__in=user_created_projects) | Q(script__project__in=user_created_projects)
        )

        return queryset.distinct()

    @action(detail=False, methods=['get'])
    def by_project(self, request):
        """获取项目变量"""
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response({'error': '缺少project_id参数'}, status=status.HTTP_400_BAD_REQUEST)

        variables = self.get_queryset().filter(scope='project', project_id=project_id)
        serializer = self.get_serializer(variables, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_script(self, request):
        """获取脚本变量（包含项目变量）"""
        script_id = request.query_params.get('script_id')
        if not script_id:
            return Response({'error': '缺少script_id参数'}, status=status.HTTP_400_BAD_REQUEST)

        # 获取脚本所属项目
        script = get_object_or_404(Script, id=script_id)

        # 获取项目变量
        project_variables = self.get_queryset().filter(scope='project', project_id=script.project.id)

        # 获取脚本级变量
        script_variables = self.get_queryset().filter(scope='script', script_id=script_id)

        # 合并变量（脚本级优先）
        all_variables = list(project_variables) + list(script_variables)
        serializer = self.get_serializer(all_variables, many=True)
        return Response(serializer.data)


class TaskQueueViewSet(viewsets.ModelViewSet):
    """任务队列视图集"""
    serializer_class = TaskQueueSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'executor']
    search_fields = ['execution__script__name']
    ordering_fields = ['created_at', 'priority']
    ordering = ['-priority', '-created_at']

    def get_queryset(self):
        """获取查询集 - 只返回当前用户的任务"""
        return TaskQueue.objects.filter(
            execution__created_by=self.request.user
        ).distinct()

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """获取待处理任务队列（执行机调用）"""
        executor_id = request.query_params.get('executor_id')
        if not executor_id:
            return Response({'error': '缺少executor_id参数'}, status=status.HTTP_400_BAD_REQUEST)

        executor = get_object_or_404(Executor, id=executor_id)

        # 验证执行机所有者
        if executor.owner != request.user:
            return Response(
                {'error': '无权操作此执行机'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 获取待分配或已分配给该执行机的任务
        tasks = TaskQueue.objects.filter(
            status='pending'
        ) | TaskQueue.objects.filter(
            executor=executor,
            status='assigned'
        )

        # 限制返回数量
        tasks = tasks[:10]
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """分配任务到执行机"""
        task = self.get_object()
        executor_id = request.data.get('executor_id')

        if not executor_id:
            return Response({'error': '缺少executor_id参数'}, status=status.HTTP_400_BAD_REQUEST)

        executor = get_object_or_404(Executor, id=executor_id)

        # 验证执行机所有者
        if executor.owner != request.user:
            return Response(
                {'error': '无权操作此执行机'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 分配任务
        task.executor = executor
        task.status = 'assigned'
        task.assigned_at = timezone.now()
        task.save()

        return Response({'message': '任务已分配', 'executor': executor.name})

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """开始执行任务"""
        task = self.get_object()

        if task.status != 'assigned':
            return Response(
                {'error': '任务状态不正确，只有已分配的任务可以开始'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 检查执行记录状态，如果已停止则不允许开始
        if task.execution and task.execution.status == 'stopped':
            return Response(
                {'error': '任务已被停止，无法开始执行'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 检查父任务状态（如果存在），如果父任务已停止则不允许开始
        if task.execution and task.execution.parent:
            parent_status = task.execution.parent.status
            if parent_status == 'stopped':
                return Response(
                    {'error': '父任务已被停止，子任务无法开始执行'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        task.status = 'running'
        task.started_at = timezone.now()
        task.save()

        # 更新执行机当前任务数
        if task.executor:
            task.executor.current_tasks += 1
            task.executor.save()

        # 更新执行记录状态
        if task.execution:
            # 再次检查执行记录状态（双重检查）
            if task.execution.status == 'stopped':
                # 任务已被停止，回退状态
                task.status = 'cancelled'
                task.completed_at = timezone.now()
                task.save()
                if task.executor:
                    task.executor.current_tasks = max(0, task.executor.current_tasks - 1)
                    task.executor.save()
                return Response(
                    {'error': '任务已被停止，无法开始执行'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            task.execution.status = 'running'
            task.execution.started_at = timezone.now()
            task.execution.save()

            # 如果有父任务（计划执行），更新父任务状态
            if task.execution.parent and task.execution.parent.status == 'pending':
                task.execution.parent.status = 'running'
                task.execution.parent.started_at = timezone.now()
                task.execution.parent.save()

        return Response({'message': '任务已开始执行'})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """完成任务"""
        task = self.get_object()

        if task.status != 'running':
            return Response(
                {'error': '任务状态不正确'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = TaskExecutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # 更新任务状态
        task.status = 'completed' if data['result'].get('failed', 0) == 0 else 'failed'
        task.completed_at = timezone.now()
        task.save()

        # 更新执行机当前任务数
        if task.executor:
            task.executor.current_tasks = max(0, task.executor.current_tasks - 1)
            task.executor.save()

        # 更新执行记录
        if task.execution:
            task.execution.result = data['result']
            task.execution.status = task.status
            task.execution.completed_at = timezone.now()
            task.execution.save()

            # 如果有父任务（计划执行），更新父任务状态
            if task.execution.parent:
                self._update_parent_execution_status(task.execution.parent)

        return Response({'message': '任务已完成'})

    def _update_parent_execution_status(self, parent_execution):
        """更新父执行记录的状态"""
        from django.db.models import Q

        # 获取所有子任务的状态
        children = parent_execution.children.all()
        if not children.exists():
            return

        # 统计子任务状态
        total = children.count()
        completed = children.filter(status='completed').count()
        failed = children.filter(status='failed').count()
        running = children.filter(status__in=['pending', 'running']).count()

        # 更新父任务状态
        if running == 0:
            # 所有子任务都已完成/失败
            if failed == 0:
                parent_execution.status = 'completed'
            elif completed == 0:
                parent_execution.status = 'failed'
            else:
                parent_execution.status = 'failed'  # 部分失败也算失败
            parent_execution.completed_at = timezone.now()

            # 计划执行完成后，自动生成报告
            try:
                from apps.reports.generators import ReportGenerator
                generator = ReportGenerator(parent_execution)
                generator.generate()
                logger.info(f"计划执行报告已自动生成: execution_id={parent_execution.id}")
            except Exception as e:
                logger.warning(f"自动生成计划执行报告失败: {e}")
        else:
            # 还有子任务在运行
            parent_execution.status = 'running'
            if not parent_execution.started_at:
                parent_execution.started_at = timezone.now()

        parent_execution.save()

    @action(detail=True, methods=['post'], permission_classes=[])
    def result(self, request, pk=None):
        """接收执行器上报的任务结果"""
        # 不使用 get_queryset()，直接通过 task ID 获取
        task = get_object_or_404(TaskQueue, pk=pk)

        data = request.data
        result_status = data.get('status', 'completed')
        result_message = data.get('message', '')
        result_steps = data.get('steps', [])
        result_duration = data.get('duration', 0)
        result_logs = data.get('logs', [])  # 获取日志数据

        # 确定最终状态
        if result_status == 'completed':
            task.status = 'completed'
        elif result_status == 'failed':
            task.status = 'failed'
        else:
            task.status = result_status

        # 如果 started_at 未设置，根据执行时长推算开始时间
        if not task.started_at:
            if result_duration > 0:
                task.started_at = timezone.now() - timezone.timedelta(seconds=result_duration)
            else:
                task.started_at = task.created_at

        task.completed_at = timezone.now()
        task.error_message = result_message if result_status == 'failed' else ''
        task.save()

        # 更新执行机当前任务数
        if task.executor:
            task.executor.current_tasks = max(0, task.executor.current_tasks - 1)
            task.executor.save()

        # 更新执行记录
        if task.execution:
            # 如果 started_at 未设置，根据执行时长推算开始时间
            if not task.execution.started_at:
                if result_duration > 0:
                    # 使用执行器上报的时长推算开始时间
                    task.execution.started_at = timezone.now() - timezone.timedelta(seconds=result_duration)
                else:
                    # 如果没有时长信息，使用任务创建时间作为开始时间
                    task.execution.started_at = task.created_at

            # 构建结果数据
            total_steps = len(result_steps)
            passed_steps = sum(1 for s in result_steps if s.get('success', False))
            failed_steps = total_steps - passed_steps

            execution_result = {
                'total': total_steps,
                'passed': passed_steps,
                'failed': failed_steps,
                'steps': result_steps,
                'duration': result_duration,
                'message': result_message,
                'logs': result_logs  # 保存日志数据
            }

            task.execution.result = execution_result
            task.execution.status = task.status
            task.execution.completed_at = timezone.now()
            task.execution.save()

            # 如果有父任务（计划执行），更新父任务状态
            if task.execution.parent:
                self._update_parent_execution_status(task.execution.parent)

            # 自动生成报告
            try:
                from apps.reports.generators import ReportGenerator
                generator = ReportGenerator(task.execution)
                generator.generate()  # 自动生成报告
                logger.info(f"报告已自动生成: execution_id={task.execution.id}")
            except Exception as e:
                logger.warning(f"自动生成报告失败: {e}")

        # 任务完成后，自动触发任务分发（处理等待中的任务）
        try:
            from services.task_distributor import TaskDistributor
            distributor = TaskDistributor()
            distributed = distributor.distribute_tasks(limit=10)
            logger.info(f"任务 {task.id} 完成，自动分发检查: 分发了 {distributed} 个任务")
            if distributed > 0:
                logger.info(f"✓ 自动分发了 {distributed} 个等待中的任务")
        except Exception as e:
            logger.error(f"自动任务分发失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

        logger.info(f"任务 {task.id} 结果已上报: status={task.status}")

        return Response({
            'message': '任务结果已记录',
            'task_id': task.id,
            'status': task.status
        })

    @action(detail=True, methods=['post'], permission_classes=[])
    def screenshot(self, request, pk=None):
        """接收执行器上报的截图"""
        # 不使用 get_queryset()，直接通过 task ID 获取
        task = get_object_or_404(TaskQueue, pk=pk)

        image_data = request.data.get('image_data')
        is_failure = request.data.get('is_failure', True)

        if not image_data:
            return Response(
                {'error': '缺少 image_data 参数'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            import base64
            from django.core.files.base import ContentFile
            import os
            from django.conf import settings

            # 解码 base64 图片数据
            if image_data.startswith('data:image'):
                # 移除 data URL 前缀 (如 "data:image/png;base64,")
                image_data = image_data.split(',', 1)[1]

            image_bytes = base64.b64decode(image_data)

            # 保存截图文件
            filename = f"task_{task.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.png"
            screenshots_dir = os.path.join(settings.MEDIA_ROOT, 'screenshots')
            os.makedirs(screenshots_dir, exist_ok=True)

            file_path = os.path.join(screenshots_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(image_bytes)

            # 可以将截图路径保存到任务的 result 中
            if task.execution:
                if not task.execution.result:
                    task.execution.result = {}
                task.execution.result['screenshot'] = f"/media/screenshots/{filename}"
                if is_failure:
                    task.execution.result['failure_screenshot'] = f"/media/screenshots/{filename}"
                task.execution.save()

            logger.info(f"任务 {task.id} 截图已保存: {filename}")

            return Response({
                'message': '截图已保存',
                'path': f"/media/screenshots/{filename}"
            })

        except Exception as e:
            logger.error(f"保存截图失败: {e}")
            return Response(
                {'error': f'保存截图失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], permission_classes=[])
    def trace(self, request, pk=None):
        """
        接收执行器上报的 Playwright Trace 文件

        执行器通过 multipart/form-data 上传 trace.zip，
        保存到 /media/traces/ 目录，路径记录到执行结果中。
        """
        task = get_object_or_404(TaskQueue, pk=pk)

        trace_file = request.FILES.get('trace')
        if not trace_file:
            return Response(
                {'error': '缺少 trace 文件'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            import os
            from django.conf import settings

            traces_dir = os.path.join(settings.MEDIA_ROOT, 'traces')
            os.makedirs(traces_dir, exist_ok=True)

            filename = f"task_{task.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.zip"
            file_path = os.path.join(traces_dir, filename)

            with open(file_path, 'wb') as f:
                for chunk in trace_file.chunks():
                    f.write(chunk)

            # 将 trace 路径保存到执行结果中
            if task.execution:
                if not task.execution.result:
                    task.execution.result = {}
                task.execution.result['trace'] = f"/media/traces/{filename}"
                task.execution.save(update_fields=['result'])

            logger.info(f"任务 {task.id} Trace 已保存: {filename}")

            return Response({
                'message': 'Trace 已保存',
                'path': f"/media/traces/{filename}",
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"保存 Trace 失败: {e}")
            return Response(
                {'error': f'保存 Trace 失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消任务"""
        task = self.get_object()

        if task.status in ['completed', 'failed', 'cancelled']:
            return Response(
                {'error': '任务已结束，无法取消'},
                status=status.HTTP_400_BAD_REQUEST
            )

        task.status = 'cancelled'
        task.completed_at = timezone.now()
        task.save()

        # 更新执行机当前任务数
        if task.executor and task.status == 'running':
            task.executor.current_tasks = max(0, task.executor.current_tasks - 1)
            task.executor.save()

        # 更新执行记录
        if task.execution:
            task.execution.status = 'stopped'
            task.execution.completed_at = timezone.now()
            task.execution.save()

        return Response({'message': '任务已取消'})

    @action(detail=False, methods=['post'], permission_classes=[])
    def distribute(self, request):
        """
        手动触发任务分发

        用于执行器在任务完成后主动请求新任务
        """
        try:
            from services.task_distributor import TaskDistributor
            distributor = TaskDistributor()
            distributed = distributor.distribute_tasks(limit=10)

            logger.info(f"手动触发任务分发: 分发了 {distributed} 个任务")

            return Response({
                'message': '任务分发完成',
                'distributed_count': distributed
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"手动任务分发失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

            return Response({
                'error': f'任务分发失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
