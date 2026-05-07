"""Seed execution engine settings"""

from django.db import migrations


def seed_execution_settings(apps, schema_editor):
    AISetting = apps.get_model('settings', 'AISetting')

    defaults = [
        {
            'key': 'MAX_CONCURRENT_EXECUTIONS',
            'value': '3',
            'category': 'execution',
            'description': '最大并发执行数（同时启动的浏览器实例数）',
            'is_secret': False,
        },
    ]

    for item in defaults:
        AISetting.objects.get_or_create(
            key=item['key'],
            defaults={
                'value': item['value'],
                'category': item['category'],
                'description': item['description'],
                'is_secret': item['is_secret'],
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('settings', '0002_seed_defaults'),
    ]

    operations = [
        migrations.RunPython(seed_execution_settings, migrations.RunPython.noop),
    ]
