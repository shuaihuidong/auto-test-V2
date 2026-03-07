from rest_framework import permissions


class RolePermission(permissions.BasePermission):
    """
    基于角色的权限控制
    """

    # 角色等级映射 (数值越大权限越高)
    ROLE_LEVELS = {
        'guest': 1,
        'tester': 2,
        'admin': 3,
        'super_admin': 4,
    }

    # 各角色对应的权限
    ROLE_PERMISSIONS = {
        'guest': ['view', 'list'],
        'tester': ['view', 'list', 'create', 'update', 'delete', 'execute'],
        'admin': ['view', 'list', 'create', 'update', 'delete', 'execute', 'manage_users'],
        'super_admin': ['view', 'list', 'create', 'update', 'delete', 'execute', 'manage_users', 'manage_settings'],
    }

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        role = user.role
        if role not in self.ROLE_PERMISSIONS:
            return False

        # 获取请求方法对应的权限类型
        method_permissions = {
            'GET': 'view',
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete',
        }

        # 列表视图使用 list 权限
        if hasattr(view, 'action') and view.action == 'list':
            required_perm = 'list'
        elif hasattr(view, 'action') and view.action == 'retrieve':
            required_perm = 'view'
        else:
            required_perm = method_permissions.get(request.method, 'view')

        return required_perm in self.ROLE_PERMISSIONS[role]

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsSuperAdmin(permissions.BasePermission):
    """仅超级管理员可访问"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'super_admin'


class IsAdmin(permissions.BasePermission):
    """管理员及以上可访问"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['admin', 'super_admin']


class IsTester(permissions.BasePermission):
    """测试人员及以上可访问"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['tester', 'admin', 'super_admin']


class IsGuestOrAbove(permissions.BasePermission):
    """访客及以上（所有登录用户）可访问"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsProjectOwnerOrAdmin(permissions.BasePermission):
    """
    项目权限：管理员有最高权限，项目创建者只能编辑/删除自己的项目
    - admin/super_admin: 完全权限
    - 项目创建者: 可以编辑/删除自己的项目
    - tester/guest: 只能查看
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user

        # 管理员及以上有完全权限
        if user.role in ['admin', 'super_admin']:
            return True

        # 安全操作（GET, HEAD, OPTIONS）允许所有有权限的用户
        if request.method in permissions.SAFE_METHODS:
            return True

        # 写操作：只有项目创建者可以操作
        if hasattr(obj, 'creator'):
            return obj.creator == user

        return False


class IsScriptOwnerOrAdmin(permissions.BasePermission):
    """
    脚本权限：
    - admin/super_admin: 完全权限
    - tester: 只能修改/删除自己创建的脚本，可以创建新脚本
    - guest: 只能查看
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # guest 只能查看
        if user.role == 'guest':
            return request.method in permissions.SAFE_METHODS

        # tester 及以上可以创建
        if request.method == 'POST':
            return user.role in ['tester', 'admin', 'super_admin']

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user

        # 管理员及以上有完全权限
        if user.role in ['admin', 'super_admin']:
            return True

        # 安全操作允许所有有权限的用户
        if request.method in permissions.SAFE_METHODS:
            return True

        # tester 只能操作自己创建的脚本
        if user.role == 'tester':
            if hasattr(obj, 'created_by'):
                return obj.created_by == user

        return False


class IsPlanOwnerOrAdmin(permissions.BasePermission):
    """
    计划权限：
    - admin/super_admin: 完全权限
    - tester: 只能修改/删除自己创建的计划，可以创建新计划
    - guest: 只能查看
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # guest 只能查看
        if user.role == 'guest':
            return request.method in permissions.SAFE_METHODS

        # tester 及以上可以创建
        if request.method == 'POST':
            return user.role in ['tester', 'admin', 'super_admin']

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user

        # 管理员及以上有完全权限
        if user.role in ['admin', 'super_admin']:
            return True

        # 安全操作允许所有有权限的用户
        if request.method in permissions.SAFE_METHODS:
            return True

        # tester 只能操作自己创建的计划
        if user.role == 'tester':
            if hasattr(obj, 'created_by'):
                return obj.created_by == user

        return False


class IsExecutionOwnerOrAdmin(permissions.BasePermission):
    """
    执行记录权限：
    - admin/super_admin: 完全权限
    - tester: 只能查看/操作自己的执行记录，可以创建新执行
    - guest: 只能查看自己的执行记录
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # guest 只能查看
        if user.role == 'guest':
            return request.method in permissions.SAFE_METHODS

        # tester 及以上可以创建执行
        if request.method == 'POST':
            return user.role in ['tester', 'admin', 'super_admin']

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user

        # 管理员及以上有完全权限
        if user.role in ['admin', 'super_admin']:
            return True

        # 安全操作允许查看自己的记录
        if request.method in permissions.SAFE_METHODS:
            if hasattr(obj, 'created_by'):
                return obj.created_by == user

        # 只能操作自己的执行记录
        if hasattr(obj, 'created_by'):
            return obj.created_by == user

        return False
