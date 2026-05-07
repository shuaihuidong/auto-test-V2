from __future__ import annotations

from typing import Any, Dict, List, Optional

from django.db import transaction

from apps.executions.models import Execution
from apps.plans.models import Plan
from apps.scripts.models import Script
from services.execution_runner import ExecutionRunner


def _script_steps(script: Script) -> List[Dict[str, Any]]:
    return list(script.steps or [])


def _normalize_script_ids(script_ids) -> List[int]:
    normalized: List[int] = []
    for script_id in script_ids or []:
        try:
            normalized.append(int(script_id))
        except (TypeError, ValueError):
            continue
    return normalized


def start_script_execution(script: Script, user, plan: Optional[Plan] = None) -> Execution:
    """Create a script execution record and dispatch it to the runner."""
    execution = Execution.objects.create(
        execution_type='script',
        plan=plan,
        script=script,
        status='pending',
        created_by=user,
    )
    ExecutionRunner.start(execution_id=execution.id, steps=_script_steps(script))
    return execution


def start_plan_execution(plan: Plan, user, execution_mode: Optional[str] = None) -> Execution:
    """
    Create a plan execution record and dispatch all child script executions.

    The current runner executes children independently; this helper preserves
    the plan's script order when creating child executions.
    """
    script_ids = _normalize_script_ids(plan.script_ids)
    script_map = Script.objects.in_bulk(script_ids)
    scripts = [script_map[script_id] for script_id in script_ids if script_id in script_map]

    if not scripts:
        raise ValueError('Plan does not contain any valid scripts.')

    execution_mode = execution_mode or plan.execution_mode or 'parallel'
    child_payloads: List[Dict[str, Any]] = []

    with transaction.atomic():
        parent_execution = Execution.objects.create(
            execution_type='plan',
            execution_mode=execution_mode,
            plan=plan,
            status='running',
            created_by=user,
        )

        for script in scripts:
            child_execution = Execution.objects.create(
                execution_type='script',
                parent=parent_execution,
                plan=plan,
                script=script,
                status='pending',
                created_by=user,
            )
            child_payloads.append(
                {
                    'execution_id': child_execution.id,
                    'steps': _script_steps(script),
                }
            )

    for payload in child_payloads:
        ExecutionRunner.start(
            execution_id=payload['execution_id'],
            steps=payload['steps'],
        )

    return parent_execution
