import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
if not User.objects.filter(username='admin').exists():
    user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    user.role = 'super_admin'
    user.save(update_fields=['role'])
    print('Admin user created: admin / admin123')
else:
    print('Admin user already exists')
