from django.db import models
from django.conf import settings
from django.db import transaction
from datetime import datetime
import time


class Execution(models.Model):
    """
    执行记录模型

    支持两种类型：
    1. 父执行记录（计划执行）：包含多个子任务，汇总整体执行情况
    2. 子执行记录（脚本执行）：单个脚本的具体执行
    """
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '执行中'),
        ('paused', '已暂停'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('stopped', '已停止'),
    ]

    TYPE_CHOICES = [
        ('plan', '计划执行'),
        ('script', '脚本执行'),
    ]

    EXECUTION_MODE_CHOICES = [
        ('sequential', '顺序执行'),
        ('parallel', '并行执行'),
    ]

    # 执行类型
    execution_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='script',
        verbose_name='执行类型'
    )

    # 执行模式（仅对父执行记录有效）
    execution_mode = models.CharField(
        max_length=20,
        choices=EXECUTION_MODE_CHOICES,
        default='parallel',
        verbose_name='执行模式'
    )

    # 父执行记录（用于子任务指向父任务）
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='父执行记录'
    )

    plan = models.ForeignKey(
        'plans.Plan',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='executions',
        verbose_name='关联计划'
    )
    script = models.ForeignKey(
        'scripts.Script',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='executions',
        verbose_name='关联脚本'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    result = models.JSONField(default=dict, verbose_name='结果数据')
    # result 格式: {"total": 10, "passed": 8, "failed": 2, "steps": [...]}
    debug_mode = models.BooleanField(default=False, verbose_name='调试模式')
    variables_snapshot = models.JSONField(default=dict, verbose_name='变量快照')
    breakpoints = models.JSONField(default=list, verbose_name='断点列表')
    current_step_index = models.IntegerField(default=0, verbose_name='当前步骤索引')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='执行者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    display_id = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name='显示ID')

    class Meta:
        db_table = 'executions_execution'
        verbose_name = '执行记录'
        verbose_name_plural = '执行记录'
        ordering = ['-created_at']

    def __str__(self):
        if self.execution_type == 'plan':
            return f'📋 {self.plan.name} - {self.get_status_display()}'
        elif self.script:
            return f'📄 {self.script.name} - {self.get_status_display()}'
        return f'Execution {self.id} - {self.get_status_display()}'

    @property
    def duration(self):
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return 0

    @property
    def passed_count(self):
        if self.execution_type == 'plan':
            # 计划执行：返回已完成的脚本数量
            return self.children.filter(status='completed').count()
        return self.result.get('passed', 0) if self.result else 0

    @property
    def failed_count(self):
        if self.execution_type == 'plan':
            # 计划执行：返回失败的脚本数量
            return self.children.filter(status='failed').count()
        return self.result.get('failed', 0) if self.result else 0

    @property
    def total_count(self):
        if self.execution_type == 'plan':
            # 计划执行：返回脚本总数
            return self.children.count()
        # 对于脚本执行，返回脚本中定义的总步骤数，而不是实际执行的步骤数
        if self.script and self.script.steps:
            return len(self.script.steps)
        # 否则返回实际执行的步骤数
        return self.result.get('total', 0) if self.result else 0

    def save(self, *args, **kwargs):
        # 生成 display_id（仅在新建时）
        if not self.display_id:
            self.display_id = self._generate_display_id()
        super().save(*args, **kwargs)

    def _generate_display_id(self):
        """
        生成显示ID：日期 + 序号
        格式：YYYYMMDD + 3位序号（纯数字，共11位）
        例如：20260211001
        """
        max_retries = 10
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    # 获取当前日期
                    now = datetime.now()
                    date_prefix = now.strftime('%Y%m%d')  # 8位

                    # 使用 select_for_update 锁定查询，防止并发冲突
                    max_display_id = Execution.objects.filter(
                        display_id__startswith=date_prefix,
                        execution_type=self.execution_type
                    ).select_for_update().order_by('-display_id').values_list('display_id', flat=True).first()

                    if max_display_id:
                        # 提取最后3位序号并递增
                        last_seq = int(max_display_id[-3:])
                        new_seq = last_seq + 1
                    else:
                        new_seq = 1

                    # 拼接：日期前缀(8位) + 3位序号（纯数字，共11位）
                    new_display_id = f"{date_prefix}{new_seq:03d}"

                    # 验证 ID 是否已存在（双重检查）
                    if Execution.objects.filter(display_id=new_display_id).exists():
                        # 如果已存在，继续下一轮重试
                        continue

                    return new_display_id
            except Exception:
                # 如果发生任何错误，重试
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.01)
                continue

        # 如果重试次数用完，使用时间戳确保唯一性
        now = datetime.now()
        return f"{now.strftime('%Y%m%d%H%M%S')}"


class HealLog(models.Model):
    """
    智能自愈日志 - 记录定位器自动修复历史
    当步骤执行因定位器失效而失败时，系统尝试推荐替代定位器并记录全过程。
    """
    HEAL_STATUS_CHOICES = [
        ('success', '修复成功'),
        ('failed', '修复失败'),
        ('pending', '待审核'),
    ]

    HEAL_STRATEGY_CHOICES = [
        ('llm_recommend', 'LLM推荐'),
        ('dom_analysis', 'DOM分析'),
        ('rule_based', '规则匹配'),
    ]

    LOCATOR_TYPE_CHOICES = [
        ('css', 'CSS选择器'),
        ('xpath', 'XPath'),
        ('data-testid', 'data-testid属性'),
        ('id', 'ID属性'),
        ('text', '文本选择器'),
    ]

    # 关联关系
    script = models.ForeignKey(
        'scripts.Script',
        on_delete=models.CASCADE,
        related_name='heal_logs',
        verbose_name='关联脚本'
    )
    execution = models.ForeignKey(
        Execution,
        on_delete=models.CASCADE,
        related_name='heal_logs',
        verbose_name='关联执行记录'
    )

    # 步骤信息
    step_index = models.IntegerField(verbose_name='步骤索引')
    step_name = models.CharField(max_length=200, blank=True, verbose_name='步骤名称')

    # 定位器信息
    original_locator = models.CharField(max_length=500, verbose_name='原始定位器')
    suggested_locator = models.CharField(max_length=500, blank=True, verbose_name='推荐替代定位器')
    locator_type = models.CharField(
        max_length=20,
        choices=LOCATOR_TYPE_CHOICES,
        default='css',
        verbose_name='定位器类型'
    )

    # 修复状态与策略
    heal_status = models.CharField(
        max_length=20,
        choices=HEAL_STATUS_CHOICES,
        default='pending',
        verbose_name='修复状态'
    )
    heal_strategy = models.CharField(
        max_length=20,
        choices=HEAL_STRATEGY_CHOICES,
        default='llm_recommend',
        verbose_name='修复策略'
    )
    confidence = models.FloatField(default=0.0, verbose_name='置信度')

    # 分析详情
    reason = models.TextField(blank=True, verbose_name='修复原因说明')
    dom_snapshot = models.TextField(blank=True, verbose_name='DOM快照')

    # LLM 消耗记录
    llm_provider = models.CharField(max_length=50, blank=True, verbose_name='LLM提供商')
    token_consumed = models.IntegerField(default=0, verbose_name='Token消耗量')

    # 应用状态
    auto_applied = models.BooleanField(default=False, verbose_name='已自动应用')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'executions_heallog'
        verbose_name = '自愈日志'
        verbose_name_plural = '自愈日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['script', 'heal_status'], name='idx_heal_script_status'),
            models.Index(fields=['execution', 'step_index'], name='idx_heal_exec_step'),
        ]

    def __str__(self):
        return f'{self.script.name} 步骤{self.step_index} - {self.get_heal_status_display()}'
