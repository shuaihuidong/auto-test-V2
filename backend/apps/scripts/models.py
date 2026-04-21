from django.db import models
from django.conf import settings


class DataSource(models.Model):
    """
    数据源模型 - 用于参数化测试
    """
    TYPE_CHOICES = [
        ('json', 'JSON数据'),
        ('csv', 'CSV文件'),
        ('excel', 'Excel文件'),
        ('manual', '手动录入'),
    ]

    name = models.CharField(max_length=200, verbose_name='数据源名称')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='manual', verbose_name='数据类型')
    data = models.JSONField(default=dict, verbose_name='数据内容')
    file = models.FileField(upload_to='data_sources/%Y/%m/', blank=True, null=True, verbose_name='数据文件')
    file_name = models.CharField(max_length=255, blank=True, verbose_name='文件名')
    row_count = models.IntegerField(default=0, verbose_name='数据行数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'scripts_datasource'
        verbose_name = '数据源'
        verbose_name_plural = '数据源'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def parse_file(self):
        """解析上传的文件"""
        if not self.file:
            return

        try:
            import pandas as pd

            file_path = self.file.path

            if self.type == 'csv':
                df = pd.read_csv(file_path)
            elif self.type == 'excel':
                df = pd.read_excel(file_path)
            else:
                return

            # 转换为数据格式
            data = {
                'columns': df.columns.tolist(),
                'rows': df.to_dict('records')
            }

            self.data = data
            self.row_count = len(df)
            self.save()

        except Exception as e:
            raise ValueError(f'文件解析失败: {str(e)}')


class Script(models.Model):
    """
    脚本模型
    """
    TYPE_CHOICES = [
        ('web', 'Web自动化'),
        ('mobile', '移动端自动化'),
        ('api', 'API接口测试'),
    ]

    FRAMEWORK_CHOICES = [
        ('playwright', 'Playwright'),
        ('appium', 'Appium'),
        ('httprunner', 'HttpRunner'),
    ]

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='scripts',
        verbose_name='所属项目'
    )
    name = models.CharField(max_length=200, verbose_name='脚本名称')
    description = models.TextField(blank=True, verbose_name='描述')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='脚本类型')
    framework = models.CharField(max_length=20, choices=FRAMEWORK_CHOICES, default='playwright', verbose_name='测试框架')
    steps = models.JSONField(default=list, verbose_name='测试步骤')
    variables = models.JSONField(default=dict, verbose_name='全局变量')
    timeout = models.IntegerField(default=30000, verbose_name='超时时间(ms)')
    retry_count = models.IntegerField(default=0, verbose_name='重试次数')
    tags = models.JSONField(default=list, verbose_name='标签')
    is_module = models.BooleanField(default=False, verbose_name='是否为模块')
    module_name = models.CharField(max_length=200, blank=True, verbose_name='模块名称')
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scripts',
        verbose_name='数据源'
    )
    data_driven = models.BooleanField(default=False, verbose_name='是否参数化')
    # V2.0 新增：AI 生成标记
    ai_generated = models.BooleanField(default=False, verbose_name='AI生成')
    # V2.0 新增：智能自愈开关
    heal_enabled = models.BooleanField(default=False, verbose_name='启用自愈')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_scripts',
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'scripts_script'
        verbose_name = '脚本'
        verbose_name_plural = '脚本'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'name'],
                name='unique_script_name_per_project',
                violation_error_message='同一项目下不能存在同名脚本'
            )
        ]

    def __str__(self):
        return self.name

    @property
    def step_count(self):
        return len(self.steps) if isinstance(self.steps, list) else 0


class ApiTestConfig(models.Model):
    """
    API测试配置模型
    存储API测试的高级配置
    """
    SIGN_ALGORITHM_CHOICES = [
        ('md5', 'MD5'),
        ('sha256', 'SHA256'),
        ('hmac-sha256', 'HMAC-SHA256'),
        ('aes', 'AES'),
        ('rsa', 'RSA'),
    ]

    script = models.OneToOneField(
        Script,
        on_delete=models.CASCADE,
        related_name='api_config',
        verbose_name='关联脚本'
    )
    base_url = models.URLField(blank=True, verbose_name='基础URL')
    default_headers = models.JSONField(default=dict, verbose_name='默认请求头')
    auth_type = models.CharField(
        max_length=20,
        blank=True,
        choices=[('basic', 'Basic Auth'), ('bearer', 'Bearer Token'), ('api_key', 'API Key')],
        verbose_name='认证类型'
    )
    auth_config = models.JSONField(default=dict, verbose_name='认证配置')

    # 签名配置
    sign_enabled = models.BooleanField(default=False, verbose_name='启用签名')
    sign_algorithm = models.CharField(
        max_length=20,
        blank=True,
        choices=SIGN_ALGORITHM_CHOICES,
        verbose_name='签名算法'
    )
    sign_key = models.CharField(max_length=500, blank=True, verbose_name='签名密钥')
    sign_position = models.CharField(
        max_length=20,
        blank=True,
        choices=[('header', '请求头'), ('query', '查询参数'), ('body', '请求体')],
        verbose_name='签名位置'
    )
    sign_field = models.CharField(max_length=100, blank=True, default='sign', verbose_name='签名字段名')

    # Mock配置
    mock_enabled = models.BooleanField(default=False, verbose_name='启用Mock')
    mock_response = models.JSONField(default=dict, verbose_name='Mock响应')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'scripts_apitestconfig'
        verbose_name = 'API测试配置'
        verbose_name_plural = 'API测试配置'

    def __str__(self):
        return f'{self.script.name} - API配置'
