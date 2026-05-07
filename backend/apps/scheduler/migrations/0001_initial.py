from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('plans', '0005_plan_execution_mode'),
        ('projects', '0001_initial'),
        ('scripts', '0008_batchtask'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScheduledTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Task name')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('schedule_type', models.CharField(choices=[('interval', 'Interval'), ('cron', 'Cron'), ('once', 'Once')], default='interval', max_length=20, verbose_name='Schedule type')),
                ('schedule_config', models.JSONField(default=dict, verbose_name='Schedule config')),
                ('status', models.CharField(choices=[('enabled', 'Enabled'), ('disabled', 'Disabled'), ('running', 'Running'), ('paused', 'Paused')], default='enabled', max_length=20, verbose_name='Status')),
                ('execute_on_failure', models.BooleanField(default=False, verbose_name='Notify on failure')),
                ('notification_config', models.JSONField(default=dict, verbose_name='Notification config')),
                ('last_execution', models.DateTimeField(blank=True, null=True, verbose_name='Last execution')),
                ('next_execution', models.DateTimeField(blank=True, null=True, verbose_name='Next execution')),
                ('total_executions', models.IntegerField(default=0, verbose_name='Total executions')),
                ('successful_executions', models.IntegerField(default=0, verbose_name='Successful executions')),
                ('failed_executions', models.IntegerField(default=0, verbose_name='Failed executions')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_scheduled_tasks', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('plan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='scheduled_tasks', to='plans.plan', verbose_name='Plan')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scheduled_tasks', to='projects.project', verbose_name='Project')),
                ('script', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='scheduled_tasks', to='scripts.script', verbose_name='Script')),
            ],
            options={
                'verbose_name': 'Scheduled task',
                'verbose_name_plural': 'Scheduled tasks',
                'db_table': 'scheduler_scheduledtask',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ScheduledTaskLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('success', 'Success'), ('failed', 'Failed'), ('skipped', 'Skipped')], max_length=20, verbose_name='Status')),
                ('message', models.TextField(blank=True, verbose_name='Message')),
                ('started_at', models.DateTimeField(auto_now_add=True, verbose_name='Started at')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='Completed at')),
                ('duration', models.IntegerField(blank=True, null=True, verbose_name='Duration seconds')),
                ('execution', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='scheduled_logs', to='executions.execution', verbose_name='Execution')),
                ('scheduled_task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='scheduler.scheduledtask', verbose_name='Scheduled task')),
            ],
            options={
                'verbose_name': 'Scheduled task log',
                'verbose_name_plural': 'Scheduled task logs',
                'db_table': 'scheduler_scheduledtasklog',
                'ordering': ['-started_at'],
            },
        ),
    ]
