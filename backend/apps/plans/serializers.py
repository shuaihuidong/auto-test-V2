from rest_framework import serializers

from .models import Plan


class PlanSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    script_count = serializers.IntegerField(read_only=True)
    scripts_detail = serializers.SerializerMethodField(read_only=True)
    schedule_type_display = serializers.CharField(source='get_schedule_type_display', read_only=True)
    execution_mode_display = serializers.CharField(source='get_execution_mode_display', read_only=True)

    class Meta:
        model = Plan
        fields = [
            'id',
            'project',
            'project_name',
            'name',
            'description',
            'script_ids',
            'script_count',
            'scripts_detail',
            'schedule_type',
            'schedule_type_display',
            'cron_expression',
            'schedule_enabled',
            'execution_mode',
            'execution_mode_display',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def validate(self, attrs):
        project = attrs.get('project')
        name = attrs.get('name')

        if project and name:
            instance = self.instance
            queryset = Plan.objects.filter(project=project, name=name)
            if instance:
                queryset = queryset.exclude(id=instance.id)

            if queryset.exists():
                raise serializers.ValidationError({'name': '同一个项目下已存在同名计划'})

        schedule_type = attrs.get('schedule_type')
        cron_expression = (attrs.get('cron_expression') or '').strip()
        schedule_enabled = attrs.get('schedule_enabled', True)
        if schedule_type == 'cron' and schedule_enabled:
            if not cron_expression:
                raise serializers.ValidationError({'cron_expression': 'Cron 表达式不能为空'})

            from croniter import croniter

            if not croniter.is_valid(cron_expression):
                raise serializers.ValidationError({'cron_expression': 'Cron 表达式不合法'})

        return attrs

    def get_scripts_detail(self, obj):
        from apps.scripts.models import Script

        if not obj.script_ids:
            return []

        scripts = Script.objects.filter(id__in=obj.script_ids)
        return [{'id': s.id, 'name': s.name, 'type': s.type, 'framework': s.framework} for s in scripts]

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
