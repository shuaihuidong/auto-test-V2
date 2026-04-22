from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    """自定义用户管理器 - create_superuser 自动设置 role"""

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        if not extra_fields.get('role'):
            extra_fields.setdefault('role', 'guest')
        return super().create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'super_admin')
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """
    自定义用户模型 - 权限分级
    """
    ROLE_CHOICES = [
        ('super_admin', '超级管理员'),
        ('admin', '管理员'),
        ('tester', '测试人员'),
        ('guest', '访客'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='guest', verbose_name='角色')
    email = models.EmailField(unique=True, verbose_name='邮箱')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    rabbitmq_password = models.CharField(max_length=500, null=True, blank=True,
                                        verbose_name='RabbitMQ密码（加密）')
    rabbitmq_enabled = models.BooleanField(default=False, verbose_name='启用RabbitMQ')

    objects = CustomUserManager()

    class Meta:
        db_table = 'users_user'
        verbose_name = '用户'
        verbose_name_plural = '用户'
        ordering = ['-created_at']

    def __str__(self):
        return self.username
