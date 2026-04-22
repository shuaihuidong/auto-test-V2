"""
执行机心跳 API

执行机通过 HTTP 定期（30秒）向平台上报心跳和状态
"""

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from apps.executors.models import Executor, ExecutorStatusLog

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def heartbeat_report(request):
    """
    执行机心跳上报

    请求体:
    {
        "executor_uuid": "uuid",
        "status": "online" | "idle" | "busy",
        "current_tasks": 0,
        "cpu_usage": 0.0,
        "memory_usage": 0.0,
        "disk_usage": 0.0,
        "message": ""
    }
    """
    try:
        data = request.data
        executor_uuid = data.get('executor_uuid')
        exec_status = data.get('status', 'online')
        current_tasks = data.get('current_tasks', 0)
        cpu_usage = data.get('cpu_usage')
        memory_usage = data.get('memory_usage')
        disk_usage = data.get('disk_usage')
        message = data.get('message', '')

        if not executor_uuid:
            return Response(
                {'error': '缺少 executor_uuid'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 查找执行机
        try:
            executor = Executor.objects.get(uuid=executor_uuid)
        except Executor.DoesNotExist:
            return Response(
                {'error': '执行机不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 更新执行机状态
        executor.status = exec_status
        executor.current_tasks = current_tasks
        executor.last_heartbeat = timezone.now()
        executor.save()

        # 记录状态日志
        ExecutorStatusLog.objects.create(
            executor=executor,
            status=exec_status,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
            current_tasks=current_tasks,
            message=message
        )

        logger.debug(
            f"收到心跳: executor={executor.name}, "
            f"status={exec_status}, tasks={current_tasks}"
        )

        return Response({
            'success': True,
            'server_time': timezone.now().isoformat(),
            'pending_tasks': _get_pending_tasks_count(executor)
        })

    except Exception as e:
        logger.error(f"处理心跳失败: {e}")
        return Response(
            {'error': f'服务器错误: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _get_pending_tasks_count(executor: Executor) -> int:
    """获取待处理任务数量"""
    from apps.executors.models import TaskQueue
    return TaskQueue.objects.filter(
        executor=executor,
        status='assigned'
    ).count()


@api_view(['POST'])
@permission_classes([AllowAny])
def executor_register(request):
    """
    执行机注册

    当执行机首次启动时调用，创建或更新执行机记录
    """
    try:
        data = request.data
        executor_uuid = data.get('executor_uuid')
        executor_name = data.get('executor_name', 'Unknown')
        platform = data.get('platform', 'Unknown')
        browser_types = data.get('browser_types', ['chrome'])
        owner_username = data.get('owner_username', '')

        if not executor_uuid:
            return Response(
                {'error': '缺少 executor_uuid'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 根据 owner_username 查找用户
        from django.contrib.auth import get_user_model
        User = get_user_model()
        owner = None

        # 优先使用已登录用户
        if request.user and request.user.is_authenticated:
            owner = request.user
        elif owner_username:
            try:
                owner = User.objects.get(username=owner_username)
            except User.DoesNotExist:
                logger.warning(f"用户不存在: {owner_username}")

        # 仍然支持 owner_id 字段（兼容旧版客户端）
        if not owner:
            owner_id = data.get('owner')
            if owner_id:
                try:
                    owner = User.objects.get(id=owner_id)
                except (User.DoesNotExist, ValueError):
                    logger.warning(f"用户不存在: {owner_id}")

        if not owner:
            return Response(
                {'error': '无法确定执行机所属用户，请提供 owner_username 或登录后注册'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 查找或创建执行机
        defaults = {
            'name': executor_name,
            'platform': platform,
            'browser_types': browser_types,
            'status': 'online',
            'max_concurrent': data.get('max_concurrent', 3),
            'scope': 'global',
            'owner': owner,
        }

        executor, created = Executor.objects.get_or_create(
            uuid=executor_uuid,
            defaults=defaults
        )

        if not created:
            # 更新现有执行机信息
            executor.name = executor_name
            executor.platform = platform
            executor.browser_types = browser_types
            executor.status = 'online'
            executor.last_heartbeat = timezone.now()
            executor.save()

        logger.info(f"执行机注册: {executor.name} (created={created})")

        return Response({
            'success': True,
            'executor_id': executor.id,
            'message': '注册成功'
        })

    except Exception as e:
        logger.error(f"执行机注册失败: {e}")
        return Response(
            {'error': f'服务器错误: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
