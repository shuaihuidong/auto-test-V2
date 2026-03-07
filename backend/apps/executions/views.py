from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import datetime
from .models import Execution
from .serializers import ExecutionSerializer, ExecutionCreateSerializer
from apps.users.permissions import IsExecutionOwnerOrAdmin
import time
import logging

logger = logging.getLogger(__name__)


class ExecutionViewSet(viewsets.ModelViewSet):
    serializer_class = ExecutionSerializer
    permission_classes = [IsExecutionOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'plan', 'script', 'execution_type']
    search_fields = ['plan__name', 'script__name']
    ordering_fields = ['created_at', 'started_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """获取查询集 - 根据execution_type参数返回不同的执行记录"""
        queryset = Execution.objects.select_related('plan', 'script', 'created_by').filter(
            parent__isnull=True  # 只返回父执行记录或单个脚本执行
        )

        # 管理员和超级管理员可以看到所有执行记录
        user = self.request.user
        if user.role not in ['admin', 'super_admin']:
            queryset = queryset.filter(created_by=user)

        # 支持按名称筛选
        name = self.request.query_params.get('name', '')
        if name:
            queryset = queryset.filter(
                plan__name__icontains=name
            ) | queryset.filter(
                script__name__icontains=name
            )

        # 支持按时间范围筛选
        start_time = self.request.query_params.get('start_time', '')
        end_time = self.request.query_params.get('end_time', '')
        if start_time:
            queryset = queryset.filter(created_at__gte=start_time)
        if end_time:
            queryset = queryset.filter(created_at__lte=end_time)

        # 支持按执行类型筛选
        execution_type = self.request.query_params.get('execution_type', '')
        if execution_type:
            queryset = queryset.filter(execution_type=execution_type)

        return queryset

    def perform_create(self, serializer):
        """创建执行记录时自动设置创建者"""
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        # 权限检查 - guest 不能创建执行
        user = request.user
        if user.role == 'guest':
            return Response(
                {'error': '访客无权执行测试，请联系管理员升级权限'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ExecutionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan_id = serializer.validated_data.get('plan_id')
        script_id = serializer.validated_data.get('script_id')
        executor_id = serializer.validated_data.get('executor_id')
        execution_mode = serializer.validated_data.get('execution_mode', 'parallel')

        # 如果是计划执行，创建父子执行记录结构
        if plan_id and not script_id:
            from apps.plans.models import Plan
            try:
                plan = Plan.objects.get(id=plan_id)
            except Plan.DoesNotExist:
                return Response(
                    {'error': '计划不存在'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 获取计划中的所有脚本
            from apps.scripts.models import Script
            scripts = Script.objects.filter(id__in=plan.script_ids)

            if not scripts.exists():
                return Response(
                    {'error': '计划中没有有效的脚本'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 创建父执行记录（计划执行）
            parent_execution = Execution.objects.create(
                execution_type='plan',
                execution_mode=execution_mode,
                plan_id=plan_id,
                status='pending',
                created_by=request.user
            )

            # 【修复】为每个脚本创建子执行记录，先批量创建所有执行记录，确保 ID 连续
            child_executions = []

            # 准备计划中所有脚本的信息（用于执行机显示）
            plan_scripts_info = []
            scripts_list = list(scripts)  # 转换为列表以支持多次迭代
            for script in scripts_list:
                plan_scripts_info.append({
                    'id': script.id,
                    'name': script.name,
                    'type': script.type,
                    'framework': script.framework,
                    'step_count': len(script.steps) if script.steps else 0
                })

            # 第一阶段：创建所有子执行记录（不创建 TaskQueue）
            # 不预先生成 display_id，让 save() 方法自动生成（已有重试和锁机制）
            for index, script in enumerate(scripts_list):
                # 创建子执行记录，display_id 会在 save() 时自动生成
                child_execution = Execution(
                    execution_type='script',
                    parent=parent_execution,
                    plan_id=plan_id,
                    script_id=script.id,
                    status='pending',
                    created_by=request.user
                    # 注意：不设置 display_id，让 save() 方法自动生成
                )
                child_execution.save()
                child_executions.append(child_execution)

            # 第二阶段：为每个子执行创建任务
            from apps.executors.models import TaskQueue

            for index, script in enumerate(scripts_list):
                child_execution = child_executions[index]

                # 创建任务数据
                task_data = self._prepare_script_data(script)
                task_data['plan_id'] = plan.id
                task_data['plan_name'] = plan.name
                task_data['execution_id'] = child_execution.id
                task_data['parent_execution_id'] = parent_execution.id
                task_data['execution_mode'] = execution_mode
                # 添加完整的计划脚本信息
                task_data['plan_scripts'] = plan_scripts_info
                task_data['script_index'] = index  # 脚本在计划中的顺序
                task_data['total_scripts'] = len(scripts_list)  # 总脚本数

                # 根据执行模式设置优先级
                # 顺序执行：后面的任务优先级较低，确保按顺序执行
                # 并行执行：所有任务优先级相同
                priority = 'normal' if execution_mode == 'parallel' else 'low' if index > 0 else 'normal'

                # 如果指定了执行机，直接分配
                if executor_id:
                    TaskQueue.objects.create(
                        execution=child_execution,
                        executor_id=executor_id,
                        status='pending',
                        script_data=task_data,
                        priority=priority
                    )
                else:
                    # 否则让系统自动分配
                    TaskQueue.objects.create(
                        execution=child_execution,
                        status='pending',
                        script_data=task_data,
                        priority=priority
                    )

            # 触发任务分发
            from services.task_distributor import TaskDistributor
            TaskDistributor().distribute_tasks()

            return Response(
                ExecutionSerializer(parent_execution).data,
                status=status.HTTP_201_CREATED
            )

        # 单个脚本执行
        execution = Execution.objects.create(
            execution_type='script',
            plan_id=plan_id,
            script_id=script_id,
            status='pending',
            created_by=request.user
        )

        # 创建任务队列记录
        task_data = self._prepare_task_data(execution)
        from apps.executors.models import TaskQueue

        # 如果指定了执行机，直接分配
        if executor_id:
            TaskQueue.objects.create(
                execution=execution,
                executor_id=executor_id,
                status='pending',
                script_data=task_data,
                priority='normal'
            )
        else:
            # 否则让系统自动分配
            TaskQueue.objects.create(
                execution=execution,
                status='pending',
                script_data=task_data,
                priority='normal'
            )

        # 触发任务分发
        from services.task_distributor import TaskDistributor
        TaskDistributor().distribute_tasks()

        return Response(
            ExecutionSerializer(execution).data,
            status=status.HTTP_201_CREATED
        )

    def _prepare_task_data(self, execution):
        """准备任务数据（兼容旧代码）"""
        if execution.script:
            return self._prepare_script_data(execution.script)
        # 如果是计划执行但没有单个脚本，返回空数据
        return {}

    def _prepare_script_data(self, script):
        """准备单个脚本的任务数据"""
        from apps.scripts.models import Script

        if not isinstance(script, Script):
            try:
                script = Script.objects.get(id=script)
            except Script.DoesNotExist:
                return {}

        return {
            'script_id': script.id,
            'name': script.name,  # 执行机期望 'name' 字段
            'description': script.description,
            'type': script.type,
            'framework': script.framework,
            'steps': script.steps,
            'variables': script.variables or {},
            'timeout': script.timeout or 30000,
            'project_id': script.project_id,
        }

    def update(self, request, *args, **kwargs):
        """更新执行记录 - 权限检查"""
        execution = self.get_object()
        user = request.user

        # 管理员及以上有完全权限
        if user.role in ['admin', 'super_admin']:
            return super().update(request, *args, **kwargs)

        # 只能更新自己的执行记录
        if execution.created_by != user:
            return Response(
                {'error': '只能操作自己的执行记录'},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """删除执行记录 - 权限检查"""
        execution = self.get_object()
        user = request.user

        # 管理员及以上有完全权限
        if user.role in ['admin', 'super_admin']:
            execution.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # 只能删除自己的执行记录
        if execution.created_by != user:
            return Response(
                {'error': '只能删除自己的执行记录'},
                status=status.HTTP_403_FORBIDDEN
            )

        execution.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """停止执行"""
        execution = self.get_object()
        user = request.user

        # 权限检查
        if user.role not in ['admin', 'super_admin']:
            if execution.created_by != user:
                return Response(
                    {'error': '只能停止自己的执行记录'},
                    status=status.HTTP_403_FORBIDDEN
                )

        if execution.status not in ['pending', 'running', 'paused']:
            return Response(
                {'error': '只能停止等待中、执行中或已暂停的任务'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 保存原始状态，用于后续判断
        original_status = execution.status

        # 先更新父执行状态为stopped（这样任务分发时会检测到并跳过）
        execution.status = 'stopped'
        execution.completed_at = timezone.now()
        execution.save()

        # 取消所有子任务（包括 pending、assigned、running 状态）
        from services.task_distributor import TaskDistributor
        TaskDistributor().cancel_all_child_tasks(execution.id)

        # 如果是计划执行，更新所有子执行的状态
        if execution.execution_type == 'plan':
            # 获取所有未完成的子执行
            unfinished_children = Execution.objects.filter(
                parent_id=execution.id,
                status__in=['pending', 'running', 'paused']
            )

            for child in unfinished_children:
                # 将子执行状态更新为stopped
                child.status = 'stopped'
                child.completed_at = timezone.now()
                # 更新 result 字段，添加停止原因
                if not child.result:
                    child.result = {}
                child.result['success'] = False
                child.result['message'] = '用户已停止执行'
                child.result['error'] = '用户已停止执行'
                child.result['stopped_at'] = timezone.now().isoformat()
                child.save()

        return Response({'message': '已停止执行'})

    @action(detail=True, methods=['get'], permission_classes=[])
    def status_check(self, request, pk=None):
        """
        检查执行状态（轻量级接口，用于执行机验证任务是否有效）

        返回执行状态，执行机根据状态决定是否接收任务
        只有 running 状态的执行才是有效的

        注意：此接口允许执行机（无认证）访问，用于停止检查逻辑
        """
        # 直接查询，避免使用 self.get_object() 导致的权限问题
        from apps.executions.models import Execution
        try:
            execution = Execution.objects.get(pk=pk)
        except Execution.DoesNotExist:
            return Response({'error': '执行不存在'}, status=404)

        return Response({
            'status': execution.status,
            'is_valid': execution.status == 'running'
        })

    @action(detail=True, methods=['post'])
    def debug(self, request, pk=None):
        """启动调试模式"""
        execution = self.get_object()
        user = request.user

        # 权限检查
        if user.role not in ['admin', 'super_admin']:
            if execution.created_by != user:
                return Response(
                    {'error': '只能调试自己的执行记录'},
                    status=status.HTTP_403_FORBIDDEN
                )

        if execution.status != 'pending':
            return Response(
                {'error': '只能在等待状态下启动调试模式'},
                status=status.HTTP_400_BAD_REQUEST
            )

        execution.debug_mode = True
        execution.save()

        # 创建任务队列记录
        task_data = self._prepare_task_data(execution)
        task_data['debug_mode'] = True
        from apps.executors.models import TaskQueue
        TaskQueue.objects.create(
            execution=execution,
            status='pending',
            script_data=task_data,
            priority='high'  # 调试模式使用高优先级
        )

        # 触发任务分发
        from services.task_distributor import TaskDistributor
        TaskDistributor().distribute_tasks()

        return Response(
            ExecutionSerializer(execution).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """暂停执行"""
        execution = self.get_object()
        user = request.user

        # 权限检查
        if user.role not in ['admin', 'super_admin']:
            if execution.created_by != user:
                return Response(
                    {'error': '只能暂停自己的执行记录'},
                    status=status.HTTP_403_FORBIDDEN
                )

        if execution.status != 'running':
            return Response(
                {'error': '只能暂停执行中的任务'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not execution.debug_mode:
            return Response(
                {'error': '只能在调试模式下暂停'},
                status=status.HTTP_400_BAD_REQUEST
            )

        execution.status = 'paused'
        execution.save()

        # 通过 WebSocket 通知执行机暂停
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'execution_{execution.id}',
            {
                'type': 'pause_execution',
                'data': {'execution_id': execution.id}
            }
        )

        return Response({'message': '已暂停执行'})

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """恢复执行"""
        execution = self.get_object()
        user = request.user

        # 权限检查
        if user.role not in ['admin', 'super_admin']:
            if execution.created_by != user:
                return Response(
                    {'error': '只能恢复自己的执行记录'},
                    status=status.HTTP_403_FORBIDDEN
                )

        if execution.status != 'paused':
            return Response(
                {'error': '只能恢复已暂停的任务'},
                status=status.HTTP_400_BAD_REQUEST
            )

        execution.status = 'running'
        execution.save()

        # 通过 WebSocket 通知执行机恢复
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'execution_{execution.id}',
            {
                'type': 'resume_execution',
                'data': {'execution_id': execution.id}
            }
        )

        return Response({'message': '已恢复执行'})

    @action(detail=True, methods=['post'])
    def step(self, request, pk=None):
        """单步执行"""
        execution = self.get_object()
        user = request.user

        # 权限检查
        if user.role not in ['admin', 'super_admin']:
            if execution.created_by != user:
                return Response(
                    {'error': '只能操作自己的执行记录'},
                    status=status.HTTP_403_FORBIDDEN
                )

        if execution.status != 'paused':
            return Response(
                {'error': '只能在暂停状态下单步执行'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not execution.debug_mode:
            return Response(
                {'error': '只能在调试模式下单步执行'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 通过 WebSocket 通知执行机单步执行
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'execution_{execution.id}',
            {
                'type': 'step_execution',
                'data': {'execution_id': execution.id}
            }
        )

        return Response({'message': '执行下一步'})

    @action(detail=True, methods=['post'])
    def breakpoint(self, request, pk=None):
        """设置/移除断点"""
        execution = self.get_object()
        user = request.user

        # 权限检查
        if user.role not in ['admin', 'super_admin']:
            if execution.created_by != user:
                return Response(
                    {'error': '只能操作自己的执行记录'},
                    status=status.HTTP_403_FORBIDDEN
                )

        step_index = request.data.get('step_index')
        action_type = request.data.get('action', 'add')  # add or remove

        if step_index is None:
            return Response(
                {'error': '缺少step_index参数'},
                status=status.HTTP_400_BAD_REQUEST
            )

        breakpoints = execution.breakpoints or []

        if action_type == 'add':
            if step_index not in breakpoints:
                breakpoints.append(step_index)
                breakpoints.sort()
        elif action_type == 'remove':
            if step_index in breakpoints:
                breakpoints.remove(step_index)
        else:
            return Response(
                {'error': '无效的action，应为add或remove'},
                status=status.HTTP_400_BAD_REQUEST
            )

        execution.breakpoints = breakpoints
        execution.save()

        return Response({
            'message': f'断点已{("添加" if action_type == "add" else "移除")}',
            'breakpoints': breakpoints
        })

    @action(detail=True, methods=['get'])
    def variables(self, request, pk=None):
        """获取当前变量"""
        execution = self.get_object()
        return Response({
            'variables': execution.variables_snapshot
        })

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """获取执行日志"""
        execution = self.get_object()
        # 从result中提取日志
        logs = execution.result.get('logs', []) if execution.result else []
        return Response({'logs': logs})

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取执行统计"""
        total = self.get_queryset().count()
        running = self.get_queryset().filter(status='running').count()
        completed = self.get_queryset().filter(status='completed').count()
        failed = self.get_queryset().filter(status='failed').count()

        return Response({
            'total': total,
            'running': running,
            'completed': completed,
            'failed': failed,
            'success_rate': round(completed / total * 100, 2) if total > 0 else 0
        })

    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        """获取子执行记录"""
        execution = self.get_object()
        if execution.execution_type != 'plan':
            return Response(
                {'error': '只有计划执行记录才有子任务'},
                status=status.HTTP_400_BAD_REQUEST
            )

        children = execution.children.select_related('script', 'created_by').all()
        serializer = ExecutionSerializer(children, many=True)
        return Response(serializer.data)
