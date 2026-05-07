from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.executions.services import start_plan_execution
from apps.plans.models import Plan

from .models import ScheduledTask, ScheduledTaskLog

logger = logging.getLogger(__name__)


def _build_schedule_config(plan: Plan) -> dict:
    return {
        'cron': (plan.cron_expression or '').strip(),
    }


def sync_plan_schedule(plan: Plan) -> ScheduledTask:
    """
    Keep one scheduler row in sync with a plan.

    Manual plans are persisted as disabled tasks so enabling cron later is
    a simple update rather than a row creation.
    """
    schedule_enabled = bool(plan.schedule_enabled and plan.schedule_type == 'cron' and plan.cron_expression.strip())
    defaults = {
        'project': plan.project,
        'name': plan.name,
        'description': plan.description or '',
        'script': None,
        'schedule_type': 'cron',
        'schedule_config': _build_schedule_config(plan),
        'status': 'enabled' if schedule_enabled else 'disabled',
        'created_by': plan.created_by,
    }

    task, _ = ScheduledTask.objects.update_or_create(plan=plan, defaults=defaults)

    if schedule_enabled:
        try:
            task.calculate_next_execution()
        except Exception as exc:
            task.status = 'disabled'
            task.next_execution = None
            task.save(update_fields=['status', 'next_execution', 'updated_at'])
            raise ValueError(f'Invalid cron expression: {exc}') from exc
        task.save(update_fields=['next_execution', 'status', 'updated_at'])
    else:
        if task.next_execution is not None or task.status != 'disabled':
            task.next_execution = None
            task.status = 'disabled'
            task.save(update_fields=['next_execution', 'status', 'updated_at'])

    return task


def execute_scheduled_task(task: ScheduledTask) -> ScheduledTaskLog:
    """
    Dispatch a scheduled task once and write a scheduler log entry.

    The execution engine is asynchronous, so this function records launch
    success/failure rather than the eventual script result.
    """
    start_time = timezone.now()
    log_entry = ScheduledTaskLog.objects.create(
        scheduled_task=task,
        status='skipped',
        message='Task was not dispatched yet.',
    )

    try:
        if not task.plan_id or task.plan is None:
            raise ValueError('Scheduled task is not linked to a plan.')

        execution = start_plan_execution(
            plan=task.plan,
            user=task.created_by,
            execution_mode=task.plan.execution_mode if task.plan else None,
        )
    except Exception as exc:
        task.mark_executed(success=False, executed_at=start_time)
        log_entry.status = 'failed'
        log_entry.message = str(exc)
        log_entry.completed_at = timezone.now()
        log_entry.duration = int((log_entry.completed_at - log_entry.started_at).total_seconds())
        log_entry.save(update_fields=['status', 'message', 'completed_at', 'duration', 'updated_at'])
        logger.exception('Scheduled task %s failed to dispatch', task.id)
        return log_entry

    task.mark_executed(success=True, executed_at=start_time)
    log_entry.execution = execution
    log_entry.status = 'success'
    log_entry.message = f'Execution {execution.display_id} started successfully.'
    log_entry.completed_at = timezone.now()
    log_entry.duration = int((log_entry.completed_at - log_entry.started_at).total_seconds())
    log_entry.save(update_fields=['execution', 'status', 'message', 'completed_at', 'duration', 'updated_at'])
    return log_entry


def run_due_scheduled_tasks(now: Optional[datetime] = None) -> int:
    """
    Run all due scheduled tasks once.

    Returns the number of dispatch attempts made.
    """
    now = now or timezone.now()
    dispatched = 0

    due_tasks = (
        ScheduledTask.objects.select_related('plan', 'created_by')
        .filter(status='enabled', plan__isnull=False, next_execution__isnull=False, next_execution__lte=now)
        .order_by('next_execution', 'id')
    )

    for task in due_tasks:
        with transaction.atomic():
            locked_task = ScheduledTask.objects.select_for_update().get(pk=task.pk)
            if (
                locked_task.status != 'enabled'
                or locked_task.plan_id is None
                or locked_task.next_execution is None
                or locked_task.next_execution > now
            ):
                continue

            execute_scheduled_task(locked_task)
            dispatched += 1

    return dispatched
