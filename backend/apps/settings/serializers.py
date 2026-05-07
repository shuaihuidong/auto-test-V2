from rest_framework import serializers
from .models import AISetting, PromptTemplate


class AISettingSerializer(serializers.ModelSerializer):
    """AI 配置序列化器 - GET 时自动脱敏"""

    class Meta:
        model = AISetting
        fields = ['id', 'key', 'value', 'category', 'description', 'is_secret', 'updated_at']
        read_only_fields = ['id', 'updated_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # 脱敏: is_secret=True 时返回 sk-abc****xyz 格式
        if instance.is_secret and instance.value:
            val = instance.value
            if len(val) > 8:
                ret['value'] = val[:3] + '****' + val[-3:]
            else:
                ret['value'] = '****'
        return ret


class AISettingUpdateSerializer(serializers.Serializer):
    """批量更新 AI 配置"""

    settings = serializers.ListField(
        child=serializers.DictField(), allow_empty=False
    )

    def validate_settings(self, value):
        for item in value:
            if 'key' not in item:
                raise serializers.ValidationError('每项必须包含 key 字段')
        return value


class PromptTemplateSerializer(serializers.ModelSerializer):
    """提示词模板序列化器"""

    class Meta:
        model = PromptTemplate
        fields = [
            'id', 'service', 'scenario', 'name', 'system_prompt',
            'description', 'is_active', 'temperature', 'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']


class PromptTemplateCreateSerializer(serializers.ModelSerializer):
    """创建提示词模板"""

    class Meta:
        model = PromptTemplate
        fields = [
            'service', 'scenario', 'name', 'system_prompt',
            'description', 'is_active', 'temperature',
        ]
