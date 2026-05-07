from django.db import models
from django.conf import settings


class AISetting(models.Model):
    """AI 配置键值对"""

    CATEGORY_CHOICES = [
        ('provider', 'Provider 选择'),
        ('openai', 'OpenAI 配置'),
        ('qwen', '通义千问配置'),
        ('general', '通用参数'),
        ('execution', '执行引擎'),
    ]

    key = models.CharField('配置键名', max_length=100, unique=True, db_index=True)
    value = models.TextField('配置值', blank=True, default='')
    category = models.CharField('分类', max_length=20, choices=CATEGORY_CHOICES, default='general')
    description = models.CharField('说明', max_length=200, blank=True, default='')
    is_secret = models.BooleanField('是否敏感', default=False)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='更新者',
    )

    class Meta:
        db_table = 'settings_ai_setting'
        verbose_name = 'AI 配置'
        verbose_name_plural = 'AI 配置'
        ordering = ['category', 'key']

    def __str__(self):
        return self.key


class PromptTemplate(models.Model):
    """提示词模板"""

    SERVICE_CHOICES = [
        ('healing', '智能自愈'),
        ('nl2script', 'NL2Script'),
    ]

    SCENARIO_CHOICES = [
        ('strict', '严格模式'),
        ('relaxed', '宽松模式'),
        ('custom', '自定义'),
    ]

    service = models.CharField('服务类型', max_length=20, choices=SERVICE_CHOICES)
    scenario = models.CharField('场景', max_length=20, choices=SCENARIO_CHOICES)
    name = models.CharField('模板名称', max_length=100)
    system_prompt = models.TextField('系统提示词')
    description = models.TextField('模板描述', blank=True, default='')
    is_active = models.BooleanField('是否激活', default=False)
    temperature = models.FloatField('温度', default=0.3)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='更新者',
    )

    class Meta:
        db_table = 'settings_prompt_template'
        verbose_name = '提示词模板'
        verbose_name_plural = '提示词模板'
        unique_together = [('service', 'scenario')]
        ordering = ['service', 'scenario']

    def __str__(self):
        return f'{self.get_service_display()} - {self.name}'
