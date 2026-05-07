from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class ScheduledTask(models.Model):
    STATUS_CHOICES = [
        ('enabled', 'Enabled'),
        ('disabled', 'Disabled'),
        ('running', 'Running'),
        ('paused', 'Paused'),
    ]

    SCHEDULE_TYPE_CHOICES = [
        ('interval', 'Interval'),
        ('cron', 'Cron'),
        ('once', 'Once'),
    ]

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='scheduled_tasks',
        verbose_name='Project',
    )
    name = models.CharField(max_length=200, verbose_name='Task name')
    description = models.TextField(blank=True, verbose_name='Description')

    script = models.ForeignKey(
        'scripts.Script',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='scheduled_tasks',
        verbose_name='Script',
    )
    plan = models.ForeignKey(
        'plans.Plan',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='scheduled_tasks',
        verbose_name='Plan',
    )

    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_TYPE_CHOICES,
        default='interval',
        verbose_name='Schedule type',
    )
    schedule_config = models.JSONField(default=dict, verbose_name='Schedule config')

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='enabled',
        verbose_name='Status',
    )

    execute_on_failure = models.BooleanField(default=False, verbose_name='Notify on failure')
    notification_config = models.JSONField(default=dict, verbose_name='Notification config')

    last_execution = models.DateTimeField(null=True, blank=True, verbose_name='Last execution')
    next_execution = models.DateTimeField(null=True, blank=True, verbose_name='Next execution')
    total_executions = models.IntegerField(default=0, verbose_name='Total executions')
    successful_executions = models.IntegerField(default=0, verbose_name='Successful executions')
    failed_executions = models.IntegerField(default=0, verbose_name='Failed executions')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_scheduled_tasks',
        verbose_name='Created by',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')

    class Meta:
        db_table = 'scheduler_scheduledtask'
        verbose_name = 'Scheduled task'
        verbose_name_plural = 'Scheduled tasks'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.name

    def calculate_next_execution(self):
        """Calculate the next run time and store it on the instance."""
        now = timezone.now()

        if self.schedule_type == 'interval':
            config = self.schedule_config or {}
            interval = int(config.get('interval', 3600))
            unit = config.get('unit', 'seconds')

            if unit == 'minutes':
                interval *= 60
            elif unit == 'hours':
                interval *= 3600
            elif unit == 'days':
                interval *= 86400

            base_time = self.last_execution or now
            self.next_execution = base_time + timedelta(seconds=interval)
            return self.next_execution

        if self.schedule_type == 'cron':
            cron_expr = (self.schedule_config or {}).get('cron', '0 0 * * *')
            from croniter import croniter

            base_time = self.last_execution or now
            self.next_execution = croniter(cron_expr, base_time).get_next(datetime)
            return self.next_execution

        if self.schedule_type == 'once':
            execute_at_str = (self.schedule_config or {}).get('execute_at')
            if execute_at_str:
                from django.utils.dateparse import parse_datetime

                self.next_execution = parse_datetime(execute_at_str)
            else:
                self.next_execution = None
            return self.next_execution

        self.next_execution = None
        return None

    def mark_executed(self, success: bool, executed_at=None):
        """Update run statistics after a task is dispatched."""
        executed_at = executed_at or timezone.now()

        self.last_execution = executed_at
        self.total_executions += 1
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1

        self.calculate_next_execution()
        self.save(
            update_fields=[
                'last_execution',
                'next_execution',
                'total_executions',
                'successful_executions',
                'failed_executions',
                'updated_at',
            ]
        )


class ScheduledTaskLog(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]

    scheduled_task = models.ForeignKey(
        ScheduledTask,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name='Scheduled task',
    )
    execution = models.ForeignKey(
        'executions.Execution',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scheduled_logs',
        verbose_name='Execution',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='Status')
    message = models.TextField(blank=True, verbose_name='Message')
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='Started at')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Completed at')
    duration = models.IntegerField(null=True, blank=True, verbose_name='Duration seconds')

    class Meta:
        db_table = 'scheduler_scheduledtasklog'
        verbose_name = 'Scheduled task log'
        verbose_name_plural = 'Scheduled task logs'
        ordering = ['-started_at']

    def __str__(self) -> str:
        return f'{self.scheduled_task.name} - {self.started_at}'
