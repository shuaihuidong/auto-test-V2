import json
import logging
from typing import Any, Dict, List

from asgiref.sync import async_to_sync
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ai_service.client import LLMGateway
from ai_service.healing import (
    HealingService,
    _extract_original_locator_info,
    _suggested_locator_to_platform,
)
from apps.settings.resolver import get_ai_config
from apps.users.permissions import IsExecutionOwnerOrAdmin
from apps.scripts.models import Script
from .services import start_plan_execution, start_script_execution, _script_steps
from .models import Execution, HealLog
from .serializers import (
    ExecutionCreateSerializer,
    ExecutionSerializer,
    HealLogSerializer,
)

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
        queryset = Execution.objects.select_related('plan', 'script', 'created_by')

        # 仅列表页隐藏计划下的子执行，详情/动作接口仍需能访问子执行，
        # 否则报告页里的 AI 自愈会把子执行当成 404。
        if self.action == 'list':
            queryset = queryset.filter(parent__isnull=True)

        user = self.request.user
        if user.role not in ['admin', 'super_admin']:
            queryset = queryset.filter(created_by=user)

        name = self.request.query_params.get('name', '')
        if name:
            queryset = queryset.filter(plan__name__icontains=name) | queryset.filter(
                script__name__icontains=name
            )

        start_time = self.request.query_params.get('start_time', '')
        end_time = self.request.query_params.get('end_time', '')
        if start_time:
            queryset = queryset.filter(created_at__gte=start_time)
        if end_time:
            queryset = queryset.filter(created_at__lte=end_time)

        execution_type = self.request.query_params.get('execution_type', '')
        if execution_type:
            queryset = queryset.filter(execution_type=execution_type)

        return queryset

    def create(self, request, *args, **kwargs):
        user = request.user
        if user.role == 'guest':
            return Response(
                {'error': 'Guest users cannot create executions.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ExecutionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan_id = serializer.validated_data.get('plan_id')
        script_id = serializer.validated_data.get('script_id')
        execution_mode = serializer.validated_data.get('execution_mode', 'parallel')

        if plan_id and not script_id:
            try:
                from apps.plans.models import Plan

                plan = Plan.objects.get(id=plan_id)
            except Plan.DoesNotExist:
                return Response({'error': 'Plan does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                parent_execution = start_plan_execution(
                    plan=plan,
                    user=user,
                    execution_mode=execution_mode,
                )
            except ValueError as exc:
                return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

            return Response(ExecutionSerializer(parent_execution).data, status=status.HTTP_201_CREATED)

        try:
            from apps.scripts.models import Script

            script = Script.objects.get(id=script_id)
        except Script.DoesNotExist:
            return Response({'error': 'Script does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

        plan = None
        if plan_id:
            from apps.plans.models import Plan

            plan = Plan.objects.filter(id=plan_id).first()

        execution = start_script_execution(script=script, user=user, plan=plan)

        return Response(ExecutionSerializer(execution).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        execution = self.get_object()
        user = request.user

        if user.role not in ['admin', 'super_admin'] and execution.created_by != user:
            return Response(
                {'error': 'You can only stop your own executions.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if execution.status not in ['pending', 'running', 'paused']:
            return Response(
                {'error': 'Execution is not pending, running, or paused.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from services.execution_runner import ExecutionRunner

        execution.status = 'stopped'
        execution.completed_at = timezone.now()
        execution.save(update_fields=['status', 'completed_at'])

        if execution.execution_type == 'plan':
            unfinished = Execution.objects.filter(
                parent_id=execution.id,
                status__in=['pending', 'running', 'paused'],
            )
            for child in unfinished:
                ExecutionRunner.cancel(child.id)
                child.status = 'stopped'
                child.completed_at = timezone.now()
                result = dict(child.result or {})
                result['success'] = False
                result['message'] = 'Stopped by user.'
                result['error'] = 'Stopped by user.'
                result['stopped_at'] = timezone.now().isoformat()
                child.result = result
                child.save(update_fields=['status', 'completed_at', 'result'])
        else:
            ExecutionRunner.cancel(execution.id)

        return Response({'message': 'Execution stopped.'})

    @action(detail=True, methods=['get'])
    def status_check(self, request, pk=None):
        execution = self.get_object()
        return Response(
            {
                'status': execution.status,
                'is_valid': execution.status == 'running',
            }
        )

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        execution = self.get_object()
        user = request.user

        if user.role not in ['admin', 'super_admin'] and execution.created_by != user:
            return Response(
                {'error': 'You can only pause your own executions.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if execution.status != 'running':
            return Response({'error': 'Execution is not running.'}, status=status.HTTP_400_BAD_REQUEST)

        if not execution.debug_mode:
            return Response({'error': 'Pause is only allowed in debug mode.'}, status=status.HTTP_400_BAD_REQUEST)

        execution.status = 'paused'
        execution.save(update_fields=['status'])
        return Response({'message': 'Execution paused.'})

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        execution = self.get_object()
        user = request.user

        if user.role not in ['admin', 'super_admin'] and execution.created_by != user:
            return Response(
                {'error': 'You can only resume your own executions.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if execution.status != 'paused':
            return Response({'error': 'Execution is not paused.'}, status=status.HTTP_400_BAD_REQUEST)

        if not execution.debug_mode:
            return Response({'error': 'Resume is only allowed in debug mode.'}, status=status.HTTP_400_BAD_REQUEST)

        execution.status = 'running'
        execution.save(update_fields=['status'])
        return Response({'message': 'Execution resumed.'})

    @action(detail=True, methods=['get'])
    def heal_logs(self, request, pk=None):
        execution = self.get_object()
        logs = HealLog.objects.filter(execution=execution).order_by('-created_at')
        return Response(HealLogSerializer(logs, many=True).data)

    @action(detail=False, methods=['post'])
    def heal_apply(self, request):
        user = request.user
        if user.role == 'guest':
            return Response({'error': 'Guest users cannot use healing.'}, status=status.HTTP_403_FORBIDDEN)

        heal_log_id = request.data.get('heal_log_id')
        if not heal_log_id:
            return Response({'error': 'heal_log_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            heal_log = HealLog.objects.select_related('script', 'execution').get(id=heal_log_id)
        except HealLog.DoesNotExist:
            return Response({'error': 'Heal log does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        if user.role not in ['admin', 'super_admin'] and heal_log.execution.created_by != user:
            return Response({'error': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)

        if heal_log.auto_applied:
            return Response({'error': 'This suggestion was already applied.'}, status=status.HTTP_400_BAD_REQUEST)

        if heal_log.heal_status != 'success':
            return Response({'error': 'Only successful suggestions can be applied.'}, status=status.HTTP_400_BAD_REQUEST)

        script = heal_log.script
        steps = _script_steps(script)
        if heal_log.step_index >= len(steps):
            return Response({'error': 'Step index out of range.'}, status=status.HTTP_400_BAD_REQUEST)

        suggested_platform = _suggested_locator_to_platform(
            heal_log.suggested_locator,
            heal_log.locator_type,
        )
        step_payload = steps[heal_log.step_index]
        params = step_payload.setdefault('params', {})
        params['locator'] = suggested_platform
        script.steps = steps
        script.save(update_fields=['steps', 'updated_at'])

        heal_log.auto_applied = True
        heal_log.save(update_fields=['auto_applied'])

        return Response(
            {
                'message': 'Healing suggestion applied.',
                'script_id': script.id,
                'step_index': heal_log.step_index,
                'new_locator': suggested_platform,
            }
        )

    @action(detail=True, methods=['post'])
    def batch_heal(self, request, pk=None):
        user = request.user
        if user.role == 'guest':
            return Response({'error': 'Guest users cannot use healing.'}, status=status.HTTP_403_FORBIDDEN)

        execution = self.get_object()
        if not execution.script_id:
            return Response({'error': 'Execution is not linked to a script.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            script = Script.objects.get(id=execution.script_id)
        except Script.DoesNotExist:
            return Response({'error': 'Script does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        steps_data = (execution.result or {}).get('steps', [])
        failed_steps = [step for step in steps_data if not step.get('success') and step.get('dom_snapshot')]
        if not failed_steps:
            return Response(
                {
                    'execution_id': execution.id,
                    'script_id': script.id,
                    'analysis_results': [],
                    'analyzed_count': 0,
                    'total_tokens': 0,
                }
            )

        config = get_ai_config()
        if not (config.get('OPENAI_API_KEY', '').strip() or config.get('QWEN_API_KEY', '').strip()):
            return Response(
                {'error': 'AI service is not configured.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        gateway = LLMGateway.from_config(config)
        service = HealingService(gateway)
        analysis_results: List[Dict[str, Any]] = []
        total_tokens = 0

        for step in failed_steps:
            step_index = int(step.get('index', 0))
            step_name = step.get('name', '')
            error_message = step.get('error', '')
            dom_snapshot = step.get('dom_snapshot', '')

            if step_index >= len(script.steps or []):
                continue

            original_locator = script.steps[step_index].get('params', {}).get('locator', {})

            try:
                result = async_to_sync(service.analyze)(
                    original_locator=original_locator,
                    error_message=error_message,
                    dom_snapshot=dom_snapshot,
                    step_name=step_name,
                    step_index=step_index,
                )
                total_tokens += result.get('token_usage', {}).get('total_tokens', 0)
                suggested_platform = result.get('suggested_locator_platform', {})
                heal_log = HealLog.objects.create(
                    script=script,
                    execution=execution,
                    step_index=step_index,
                    step_name=step_name,
                    original_locator=result.get('original_locator', ''),
                    suggested_locator=result.get('suggested_locator', ''),
                    locator_type=result.get('locator_type', 'css'),
                    heal_status=result.get('heal_status', 'failed'),
                    heal_strategy=result.get('heal_strategy', 'llm_recommend'),
                    confidence=result.get('confidence', 0.0),
                    reason=result.get('reason', ''),
                    dom_snapshot=dom_snapshot[:5000],
                    llm_provider=result.get('provider', ''),
                    token_consumed=result.get('token_usage', {}).get('total_tokens', 0),
                    auto_applied=False,
                )
                analysis_results.append(
                    {
                        'heal_log_id': heal_log.id,
                        'step_index': step_index,
                        'step_name': step_name,
                        'heal_status': result.get('heal_status', 'failed'),
                        'original_locator': result.get('original_locator', ''),
                        'suggested_locator': result.get('suggested_locator', ''),
                        'suggested_locator_platform': suggested_platform,
                        'confidence': result.get('confidence', 0.0),
                        'reason': result.get('reason', ''),
                    }
                )
            except Exception as exc:
                logger.exception('batch_heal failed for execution %s step %s', execution.id, step_index)
                heal_log = HealLog.objects.create(
                    script=script,
                    execution=execution,
                    step_index=step_index,
                    step_name=step_name,
                    original_locator=_extract_original_locator_info(original_locator),
                    suggested_locator='',
                    locator_type='css',
                    heal_status='failed',
                    heal_strategy='llm_recommend',
                    confidence=0.0,
                    reason=str(exc),
                    dom_snapshot=dom_snapshot[:5000],
                    llm_provider='',
                    token_consumed=0,
                    auto_applied=False,
                )
                analysis_results.append(
                    {
                        'heal_log_id': heal_log.id,
                        'step_index': step_index,
                        'step_name': step_name,
                        'heal_status': 'failed',
                        'original_locator': _extract_original_locator_info(original_locator),
                        'suggested_locator': '',
                        'suggested_locator_platform': None,
                        'confidence': 0.0,
                        'reason': str(exc),
                    }
                )

        return Response(
            {
                'execution_id': execution.id,
                'script_id': script.id,
                'analysis_results': analysis_results,
                'analyzed_count': len(analysis_results),
                'total_tokens': total_tokens,
            }
        )

    @action(detail=False, methods=['post'])
    def heal_batch_apply(self, request):
        user = request.user
        if user.role == 'guest':
            return Response({'error': 'Guest users cannot use healing.'}, status=status.HTTP_403_FORBIDDEN)

        heal_log_ids = request.data.get('heal_log_ids', [])
        if not isinstance(heal_log_ids, list) or not heal_log_ids:
            return Response({'error': 'heal_log_ids must be a non-empty list.'}, status=status.HTTP_400_BAD_REQUEST)

        heal_logs = list(HealLog.objects.select_related('script', 'execution').filter(id__in=heal_log_ids))
        if not heal_logs:
            return Response({'error': 'No heal logs found.'}, status=status.HTTP_404_NOT_FOUND)

        if user.role not in ['admin', 'super_admin']:
            if any(log.execution.created_by != user for log in heal_logs):
                return Response({'error': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)

        script_ids = {log.script_id for log in heal_logs}
        if len(script_ids) != 1:
            return Response({'error': 'Selected heal logs must belong to the same script.'}, status=status.HTTP_400_BAD_REQUEST)

        script = heal_logs[0].script
        steps = _script_steps(script)
        applied_count = 0

        for heal_log in heal_logs:
            if heal_log.heal_status != 'success' or heal_log.auto_applied:
                continue
            if heal_log.step_index >= len(steps):
                continue

            suggested_platform = _suggested_locator_to_platform(
                heal_log.suggested_locator,
                heal_log.locator_type,
            )
            step_payload = steps[heal_log.step_index]
            params = step_payload.setdefault('params', {})
            params['locator'] = suggested_platform
            heal_log.auto_applied = True
            heal_log.save(update_fields=['auto_applied'])
            applied_count += 1

        if applied_count:
            script.steps = steps
            script.save(update_fields=['steps', 'updated_at'])

        return Response(
            {
                'message': f'Applied {applied_count} healing suggestions.',
                'script_id': script.id,
                'applied_count': applied_count,
            }
        )
