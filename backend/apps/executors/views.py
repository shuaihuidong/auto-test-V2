from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q
import logging

from .models import Variable
from apps.scripts.models import Script
from .serializers import VariableSerializer

logger = logging.getLogger(__name__)


class VariableViewSet(viewsets.ModelViewSet):
    """变量管理视图集"""
    serializer_class = VariableSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['scope', 'type', 'is_sensitive']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['scope', 'project', 'script', 'name']

    def get_queryset(self):
        """获取查询集"""
        queryset = Variable.objects.all()
        user = self.request.user

        # 管理员和超级管理员可以看到所有变量
        if user.role in ['admin', 'super_admin']:
            return queryset

        # 其他用户只能看到自己创建的项目的变量
        user_created_projects = user.created_projects.all()
        queryset = queryset.filter(
            Q(project__in=user_created_projects) | Q(script__project__in=user_created_projects)
        )

        return queryset.distinct()

    @action(detail=False, methods=['get'])
    def by_project(self, request):
        """获取项目变量"""
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response({'error': '缺少project_id参数'}, status=status.HTTP_400_BAD_REQUEST)

        variables = self.get_queryset().filter(scope='project', project_id=project_id)
        serializer = self.get_serializer(variables, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_script(self, request):
        """获取脚本变量（包含项目变量）"""
        script_id = request.query_params.get('script_id')
        if not script_id:
            return Response({'error': '缺少script_id参数'}, status=status.HTTP_400_BAD_REQUEST)

        # 获取脚本所属项目
        script = get_object_or_404(Script, id=script_id)

        # 获取项目变量
        project_variables = self.get_queryset().filter(scope='project', project_id=script.project.id)

        # 获取脚本级变量
        script_variables = self.get_queryset().filter(scope='script', script_id=script_id)

        # 合并变量（脚本级优先）
        all_variables = list(project_variables) + list(script_variables)
        serializer = self.get_serializer(all_variables, many=True)
        return Response(serializer.data)
