from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.users.permissions import IsSuperAdmin
from .models import AISetting, PromptTemplate
from .serializers import (
    AISettingSerializer,
    AISettingUpdateSerializer,
    PromptTemplateSerializer,
    PromptTemplateCreateSerializer,
)

import re


# ==================== AI 配置 API ====================

_MASK_PATTERN = re.compile(r'^.+\*\*\*\*.+$')


@api_view(['GET', 'PUT'])
@permission_classes([IsSuperAdmin])
def ai_settings_view(request):
    """
    GET: 获取所有 AI 配置 (secret 值脱敏)
    PUT: 批量更新配置
    """
    if request.method == 'GET':
        settings = AISetting.objects.all()
        serializer = AISettingSerializer(settings, many=True)
        return Response(serializer.data)

    # PUT - 批量更新
    serializer = AISettingUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    items = serializer.validated_data['settings']
    updated = []

    for item in items:
        key = item.get('key')
        value = item.get('value', '')

        try:
            setting = AISetting.objects.get(key=key)

            # 如果值是脱敏格式 (含 ****)，跳过更新
            if setting.is_secret and _MASK_PATTERN.match(value):
                continue

            setting.value = value
            setting.updated_by = request.user
            setting.save(update_fields=['value', 'updated_at'])
            updated.append(key)
        except AISetting.DoesNotExist:
            pass

    # 返回更新后的列表
    settings = AISetting.objects.all()
    out_serializer = AISettingSerializer(settings, many=True)
    return Response(out_serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ai_config_check_view(request):
    """检查 AI 是否已配置"""
    from .resolver import get_ai_config

    config = get_ai_config()
    primary = config.get('PRIMARY_PROVIDER', 'openai')
    key_mapping = {
        'openai': 'OPENAI_API_KEY',
        'qwen': 'QWEN_API_KEY',
    }
    key_name = key_mapping.get(primary, 'OPENAI_API_KEY')
    api_key = config.get(key_name, '')

    return Response({
        'configured': bool(api_key and api_key.strip()),
        'primary_provider': primary,
        'fallback_provider': config.get('FALLBACK_PROVIDER', ''),
    })


# ==================== 执行引擎 API ====================

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def execution_engine_status_view(request):
    """获取执行引擎线程池状态"""
    from services.execution_runner import get_pool, _get_max_workers

    pool = get_pool()
    db_max = _get_max_workers()
    current_max = pool.max_workers

    return Response({
        'max_workers': current_max,
        'active': pool.active_count(),
        'queued': pool.queued_count(),
        'db_config_value': db_max,
        'needs_restart': db_max != current_max,
    })


# ==================== Prompt 模板 API ====================

@api_view(['GET', 'POST'])
@permission_classes([IsSuperAdmin])
def prompt_template_list_view(request):
    """列出 / 新建提示词模板"""
    if request.method == 'GET':
        service = request.query_params.get('service')
        qs = PromptTemplate.objects.all()
        if service:
            qs = qs.filter(service=service)
        serializer = PromptTemplateSerializer(qs, many=True)
        return Response(serializer.data)

    # POST - 新建
    serializer = PromptTemplateCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # 如果设置为激活，先取消同 service 的其他激活模板
    if serializer.validated_data.get('is_active'):
        PromptTemplate.objects.filter(
            service=serializer.validated_data['service'],
            is_active=True,
        ).update(is_active=False)

    template = serializer.save(updated_by=request.user)
    return Response(
        PromptTemplateSerializer(template).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsSuperAdmin])
def prompt_template_detail_view(request, pk):
    """获取 / 更新 / 删除提示词模板"""
    try:
        template = PromptTemplate.objects.get(pk=pk)
    except PromptTemplate.DoesNotExist:
        return Response({'error': '模板不存在'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = PromptTemplateSerializer(template)
        return Response(serializer.data)

    if request.method == 'PUT':
        serializer = PromptTemplateCreateSerializer(
            template, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        # 如果设置为激活，先取消同 service 的其他激活模板
        if serializer.validated_data.get('is_active'):
            PromptTemplate.objects.filter(
                service=template.service,
                is_active=True,
            ).exclude(pk=template.pk).update(is_active=False)

        serializer.save(updated_by=request.user)
        return Response(PromptTemplateSerializer(template).data)

    # DELETE
    template.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PUT'])
@permission_classes([IsSuperAdmin])
def prompt_template_activate_view(request, pk):
    """激活模板"""
    try:
        template = PromptTemplate.objects.get(pk=pk)
    except PromptTemplate.DoesNotExist:
        return Response({'error': '模板不存在'}, status=status.HTTP_404_NOT_FOUND)

    # 取消同 service 其他激活模板
    PromptTemplate.objects.filter(
        service=template.service,
        is_active=True,
    ).update(is_active=False)

    template.is_active = True
    template.updated_by = request.user
    template.save(update_fields=['is_active', 'updated_at'])

    return Response(PromptTemplateSerializer(template).data)
