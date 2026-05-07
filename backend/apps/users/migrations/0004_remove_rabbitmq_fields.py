"""Remove RabbitMQ fields from User model"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_user_rabbitmq_enabled_user_rabbitmq_password'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='rabbitmq_password',
        ),
        migrations.RemoveField(
            model_name='user',
            name='rabbitmq_enabled',
        ),
    ]
