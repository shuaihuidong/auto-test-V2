from rest_framework import serializers
from .models import Execution, HealLog


class ExecutionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    script_name = serializers.CharField(source='script.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    duration = serializers.IntegerField(read_only=True)
    passed_count = serializers.IntegerField(read_only=True)
    failed_count = serializers.IntegerField(read_only=True)
    total_count = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    execution_type_display = serializers.CharField(source='get_execution_type_display', read_only=True)
    execution_mode_display = serializers.CharField(source='get_execution_mode_display', read_only=True)
    children_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Execution
        fields = ['id', 'display_id', 'execution_type', 'execution_type_display', 'execution_mode', 'execution_mode_display',
                  'parent', 'plan', 'plan_name', 'script', 'script_name', 'status', 'status_display',
                  'result', 'duration', 'passed_count', 'failed_count', 'total_count',
                  'children_count', 'started_at', 'completed_at', 'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['id', 'display_id', 'started_at', 'completed_at', 'created_at']

    def get_children_count(self, obj):
        return obj.children.count() if obj.execution_type == 'plan' else 0

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ExecutionCreateSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField(required=False)
    script_id = serializers.IntegerField(required=False)
    executor_id = serializers.IntegerField(required=False, allow_null=True)
    execution_mode = serializers.ChoiceField(
        choices=['sequential', 'parallel'],
        default='parallel',
        required=False
    )

    def validate(self, attrs):
        if not attrs.get('plan_id') and not attrs.get('script_id'):
            raise serializers.ValidationError("必须提供plan_id或script_id")

        # 如果是计划执行，从计划中获取执行模式（如果未指定）
        plan_id = attrs.get('plan_id')
        if plan_id and not attrs.get('execution_mode'):
            from apps.plans.models import Plan
            try:
                plan = Plan.objects.get(id=plan_id)
                attrs['execution_mode'] = plan.execution_mode
            except Plan.DoesNotExist:
                attrs['execution_mode'] = 'parallel'

        return attrs


class HealLogSerializer(serializers.ModelSerializer):
    """智能自愈日志序列化器"""
    script_name = serializers.CharField(source='script.name', read_only=True)
    execution_display_id = serializers.CharField(source='execution.display_id', read_only=True)
    heal_status_display = serializers.CharField(source='get_heal_status_display', read_only=True)
    heal_strategy_display = serializers.CharField(source='get_heal_strategy_display', read_only=True)
    locator_type_display = serializers.CharField(source='get_locator_type_display', read_only=True)

    class Meta:
        model = HealLog
        fields = [
            'id', 'script', 'script_name', 'execution', 'execution_display_id',
            'step_index', 'step_name',
            'original_locator', 'suggested_locator', 'locator_type', 'locator_type_display',
            'heal_status', 'heal_status_display',
            'heal_strategy', 'heal_strategy_display',
            'confidence', 'reason', 'dom_snapshot',
            'llm_provider', 'token_consumed', 'auto_applied',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class HealLogCreateSerializer(serializers.Serializer):
    """创建自愈日志的请求结构"""
    script_id = serializers.IntegerField()
    execution_id = serializers.IntegerField()
    step_index = serializers.IntegerField()
    step_name = serializers.CharField(required=False, allow_blank=True)
    original_locator = serializers.CharField()
    suggested_locator = serializers.CharField()
    locator_type = serializers.ChoiceField(
        choices=['css', 'xpath', 'data-testid', 'id', 'text'],
        default='css'
    )
    heal_strategy = serializers.ChoiceField(
        choices=['llm_recommend', 'dom_analysis', 'rule_based'],
        default='llm_recommend'
    )
    confidence = serializers.FloatField(min_value=0.0, max_value=1.0, default=0.0)
    reason = serializers.CharField(required=False, allow_blank=True)
    dom_snapshot = serializers.CharField(required=False, allow_blank=True)
    llm_provider = serializers.CharField(required=False, allow_blank=True)
    token_consumed = serializers.IntegerField(default=0)

    def validate(self, attrs):
        from apps.scripts.models import Script
        # 校验关联对象存在
        if not Script.objects.filter(id=attrs['script_id']).exists():
            raise serializers.ValidationError({'script_id': '脚本不存在'})
        if not Execution.objects.filter(id=attrs['execution_id']).exists():
            raise serializers.ValidationError({'execution_id': '执行记录不存在'})
        return attrs
