from django.db import models
from django.conf import settings


class Variable(models.Model):
    """
    变量管理模型
    支持项目级和脚本级变量
    """
    SCOPE_CHOICES = [
        ('project', '项目级'),
        ('script', '脚本级'),
    ]

    TYPE_CHOICES = [
        ('string', '字符串'),
        ('number', '数字'),
        ('boolean', '布尔值'),
        ('json', 'JSON对象'),
    ]

    name = models.CharField(max_length=200, verbose_name='变量名')
    value = models.JSONField(verbose_name='变量值')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='string', verbose_name='变量类型')
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, verbose_name='作用域')

    # 关联对象（根据scope不同，关联不同的对象）
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='variables',
        verbose_name='所属项目'
    )
    script = models.ForeignKey(
        'scripts.Script',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='managed_variables',
        verbose_name='所属脚本'
    )

    # 描述
    description = models.TextField(blank=True, verbose_name='描述')

    # 是否敏感数据（如密码、token等，敏感数据在API中需要脱敏）
    is_sensitive = models.BooleanField(default=False, verbose_name='是否敏感')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_variables',
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'executors_variable'
        verbose_name = '变量'
        verbose_name_plural = '变量'
        ordering = ['scope', 'project', 'script', 'name']
        unique_together = [['scope', 'project', 'script', 'name']]

    def __str__(self):
        return f'{self.name} = {self.value}'
