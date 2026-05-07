from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    LoginSerializer,
    ChangePasswordSerializer
)
from .permissions import IsSuperAdmin, IsAdmin, IsTester, IsGuestOrAbove

User = get_user_model()


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """登录视图 - 豁免 CSRF"""
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    username = serializer.validated_data['username']
    password = serializer.validated_data['password']

    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        from rest_framework.authtoken.models import Token
        token, created = Token.objects.get_or_create(user=user)

        request.session['executor_token'] = token.key
        request.session['executor_user_id'] = user.id
        request.session.save()

        return Response({
            'message': '登录成功',
            'token': token.key,
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'error': '用户名或密码错误'
        }, status=status.HTTP_401_UNAUTHORIZED)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsGuestOrAbove]

    def get_permissions(self):
        if self.action in ['create', 'destroy', 'set_role']:
            return [IsAdmin()]
        elif self.action in ['update', 'partial_update']:
            return [IsGuestOrAbove()]
        elif self.action == 'list':
            return [IsTester()]
        return [IsGuestOrAbove()]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        serializer.save()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        is_admin = request.user.role in ['admin', 'super_admin']
        is_self = request.user.id == instance.id

        if not is_admin and not is_self:
            return Response(
                {'error': '无权限修改此用户信息'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not is_admin:
            allowed_fields = {'email', 'password'}
            request_data = set(request.data.keys())
            invalid_fields = request_data - allowed_fields
            if invalid_fields:
                return Response(
                    {'error': f'普通用户只能修改邮箱和密码，无权修改: {", ".join(invalid_fields)}'},
                    status=status.HTTP_403_FORBIDDEN
                )

        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        logout(request)
        return Response({'message': '登出成功'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def permissions(self, request):
        from .permissions import RolePermission
        role_perms = RolePermission.ROLE_PERMISSIONS.get(request.user.role, [])
        return Response({
            'role': request.user.role,
            'role_display': request.user.get_role_display(),
            'permissions': role_perms
        })

    @action(detail=True, methods=['post'])
    def set_role(self, request, pk=None):
        if request.user.role != 'super_admin':
            return Response(
                {'error': '只有超级管理员可以修改用户角色'},
                status=status.HTTP_403_FORBIDDEN
            )
        user = self.get_object()
        new_role = request.data.get('role')
        valid_roles = ['super_admin', 'admin', 'tester', 'guest']
        if new_role not in valid_roles:
            return Response(
                {'error': '无效的角色'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.role = new_role
        user.save()
        return Response({
            'message': f'用户角色已更新为 {user.get_role_display()}',
            'user': UserSerializer(user).data
        })

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        if request.user.role not in ['admin', 'super_admin']:
            return Response(
                {'error': '只有管理员可以重置用户密码'},
                status=status.HTTP_403_FORBIDDEN
            )

        user = self.get_object()

        if user.id == request.user.id:
            return Response(
                {'error': '不能重置自己的密码，请使用修改密码功能'},
                status=status.HTTP_400_BAD_REQUEST
            )

        default_password = '123456'
        user.set_password(default_password)
        user.save()

        return Response({
            'message': f'用户 {user.username} 的密码已重置为默认密码',
            'default_password': default_password,
            'user': UserSerializer(user).data
        })

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        if not user.check_password(old_password):
            return Response(
                {'error': '原密码错误'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()
        return Response({'message': '密码修改成功'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def role_list(request):
    if request.user.role not in ['tester', 'admin', 'super_admin']:
        return Response(
            {'error': '无权限访问'},
            status=status.HTTP_403_FORBIDDEN
        )

    from .permissions import RolePermission
    from .models import User

    roles = []
    for role_value, role_label in User.ROLE_CHOICES:
        count = User.objects.filter(role=role_value).count()
        roles.append({
            'value': role_value,
            'label': role_label,
            'level': RolePermission.ROLE_LEVELS.get(role_value, 0),
            'permissions': RolePermission.ROLE_PERMISSIONS.get(role_value, []),
            'user_count': count
        })

    return Response({'results': roles})


@api_view(['GET', 'PUT'])
@permission_classes([IsSuperAdmin])
def role_detail(request, role):
    from .permissions import RolePermission
    from .models import User

    valid_roles = [r[0] for r in User.ROLE_CHOICES]
    if role not in valid_roles:
        return Response(
            {'error': '角色不存在'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        role_label = dict(User.ROLE_CHOICES).get(role, role)
        users = User.objects.filter(role=role)
        user_data = UserSerializer(users, many=True).data

        return Response({
            'value': role,
            'label': role_label,
            'level': RolePermission.ROLE_LEVELS.get(role, 0),
            'permissions': RolePermission.ROLE_PERMISSIONS.get(role, []),
            'users': user_data,
            'user_count': users.count()
        })

    return Response(
        {'error': '当前权限系统为硬编码，不支持动态修改'},
        status=status.HTTP_501_NOT_IMPLEMENTED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def role_users(request, role):
    if request.user.role not in ['admin', 'super_admin']:
        return Response(
            {'error': '无权限访问'},
            status=status.HTTP_403_FORBIDDEN
        )

    from .models import User

    valid_roles = [r[0] for r in User.ROLE_CHOICES]
    if role not in valid_roles:
        return Response(
            {'error': '角色不存在'},
            status=status.HTTP_404_NOT_FOUND
        )

    users = User.objects.filter(role=role)
    serializer = UserSerializer(users, many=True)

    return Response({
        'role': role,
        'role_label': dict(User.ROLE_CHOICES).get(role, role),
        'users': serializer.data,
        'count': users.count()
    })
