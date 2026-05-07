from rest_framework import serializers
from .models import Variable


class VariableSerializer(serializers.ModelSerializer):
    """变量序列化器"""

    scope_display = serializers.CharField(source='get_scope_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    creator_name = serializers.CharField(source='created_by.username', read_only=True)

    # 使用 JSONField 同时支持读写，并通过 to_representation 处理脱敏
    value = serializers.JSONField()

    class Meta:
        model = Variable
        fields = [
            'id', 'name', 'value', 'type', 'type_display', 'scope', 'scope_display',
            'project', 'script', 'description', 'is_sensitive', 'created_by',
            'creator_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def to_representation(self, instance):
        """在序列化时对敏感数据进行脱敏处理"""
        data = super().to_representation(instance)
        if instance.is_sensitive:
            data['value'] = '******'
        return data

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
