from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import Plan
from .serializers import PlanSerializer
from apps.users.permissions import IsPlanOwnerOrAdmin


class PlanViewSet(viewsets.ModelViewSet):
    serializer_class = PlanSerializer
    permission_classes = [IsPlanOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        """获取查询集 - 只返回当前用户有权限访问的计划"""
        user = self.request.user

        # 管理员和超级管理员可以看到所有计划
        if user.role in ['admin', 'super_admin']:
            return Plan.objects.select_related('project', 'created_by').all()

        # 其他用户只能看到自己创建的项目的计划 + 自己创建的计划
        from apps.projects.models import ProjectMember
        user_created_projects = user.created_projects.all()
        member_project_ids = ProjectMember.objects.filter(
            user=user
        ).values_list('project_id', flat=True)

        return Plan.objects.select_related('project', 'created_by').filter(
            Q(project__in=user_created_projects) |
            Q(project__in=member_project_ids) |
            Q(created_by=user)
        ).distinct()

    def perform_create(self, serializer):
        """创建计划时自动设置创建者"""
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        """创建计划 - 权限检查"""
        user = request.user

        # guest 不能创建计划
        if user.role == 'guest':
            return Response(
                {'error': '访客无权创建计划，请联系管理员升级权限'},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """更新计划 - 权限检查"""
        plan = self.get_object()
        user = request.user

        # 管理员及以上有完全权限
        if user.role in ['admin', 'super_admin']:
            return super().update(request, *args, **kwargs)

        # tester 只能更新自己创建的计划
        if user.role == 'tester':
            if plan.created_by != user:
                return Response(
                    {'error': '只能编辑自己创建的计划'},
                    status=status.HTTP_403_FORBIDDEN
                )
            return super().update(request, *args, **kwargs)

        # guest 不能更新
        return Response(
            {'error': '访客无权编辑计划'},
            status=status.HTTP_403_FORBIDDEN
        )

    def destroy(self, request, *args, **kwargs):
        """删除计划 - 权限检查"""
        plan = self.get_object()
        user = request.user

        # 管理员及以上有完全权限
        if user.role in ['admin', 'super_admin']:
            plan.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # tester 只能删除自己创建的计划
        if user.role == 'tester':
            if plan.created_by != user:
                return Response(
                    {'error': '只能删除自己创建的计划'},
                    status=status.HTTP_403_FORBIDDEN
                )
            plan.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # guest 不能删除
        return Response(
            {'error': '访客无权删除计划'},
            status=status.HTTP_403_FORBIDDEN
        )

    @action(detail=True, methods=['post'])
    def add_script(self, request, pk=None):
        """向计划添加脚本"""
        plan = self.get_object()
        user = request.user

        # 权限检查
        if user.role not in ['admin', 'super_admin']:
            if plan.created_by != user and user.role != 'tester':
                return Response(
                    {'error': '只有计划创建者或管理员可以修改计划'},
                    status=status.HTTP_403_FORBIDDEN
                )

        script_id = request.data.get('script_id')
        if not script_id:
            return Response({'error': '请提供script_id'}, status=400)

        if plan.script_ids is None:
            plan.script_ids = []
        if script_id not in plan.script_ids:
            plan.script_ids.append(script_id)
            plan.save()
        return Response({'message': '添加成功', 'script_ids': plan.script_ids})

    @action(detail=True, methods=['post'])
    def remove_script(self, request, pk=None):
        """从计划移除脚本"""
        plan = self.get_object()
        user = request.user

        # 权限检查
        if user.role not in ['admin', 'super_admin']:
            if plan.created_by != user and user.role != 'tester':
                return Response(
                    {'error': '只有计划创建者或管理员可以修改计划'},
                    status=status.HTTP_403_FORBIDDEN
                )

        script_id = request.data.get('script_id')
        if not script_id:
            return Response({'error': '请提供script_id'}, status=400)

        if plan.script_ids and script_id in plan.script_ids:
            plan.script_ids.remove(script_id)
            plan.save()
        return Response({'message': '移除成功', 'script_ids': plan.script_ids})
