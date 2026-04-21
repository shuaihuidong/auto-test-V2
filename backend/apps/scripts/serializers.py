from rest_framework import serializers
from .models import Script, DataSource, ApiTestConfig


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = ['id', 'name', 'type', 'data', 'file', 'file_name', 'row_count', 'created_at']
        read_only_fields = ['id', 'created_at', 'row_count']

    def create(self, validated_data):
        file = validated_data.get('file')
        if file:
            validated_data['file_name'] = file.name

        instance = super().create(validated_data)

        # 如果上传了文件，解析文件内容
        if file:
            try:
                instance.parse_file()
            except Exception as e:
                # 如果解析失败，删除实例
                instance.delete()
                raise serializers.ValidationError(f'文件解析失败: {str(e)}')

        return instance


class ScriptSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    step_count = serializers.IntegerField(read_only=True)
    data_source_name = serializers.CharField(source='data_source.name', read_only=True)

    class Meta:
        model = Script
        fields = ['id', 'project', 'project_name', 'name', 'description', 'type',
                  'framework', 'steps', 'variables', 'timeout', 'retry_count', 'tags',
                  'is_module', 'module_name', 'data_source', 'data_source_name',
                  'data_driven', 'ai_generated', 'heal_enabled',
                  'created_by', 'created_by_name', 'step_count',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def validate(self, attrs):
        # 验证脚本名称在同一项目下的唯一性
        project = attrs.get('project')
        name = attrs.get('name')

        if project and name:
            # 检查是否是更新操作
            instance = self.instance
            queryset = Script.objects.filter(project=project, name=name)

            # 如果是更新操作，排除当前实例
            if instance:
                queryset = queryset.exclude(id=instance.id)

            if queryset.exists():
                raise serializers.ValidationError({
                    'name': '同一项目下已存在同名脚本'
                })

        return attrs

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ScriptDetailSerializer(ScriptSerializer):
    data_source_detail = DataSourceSerializer(source='data_source', read_only=True)

    class Meta(ScriptSerializer.Meta):
        fields = ScriptSerializer.Meta.fields + ['data_source_detail']


class ApiTestConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiTestConfig
        fields = ['id', 'script', 'base_url', 'default_headers', 'auth_type', 'auth_config',
                  'sign_enabled', 'sign_algorithm', 'sign_key', 'sign_position', 'sign_field',
                  'mock_enabled', 'mock_response', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
