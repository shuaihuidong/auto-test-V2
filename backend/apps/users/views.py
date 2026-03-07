from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
import secrets
import socket
import os
import base64
from cryptography.fernet import Fernet
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    LoginSerializer,
    ChangePasswordSerializer
)
from .permissions import IsSuperAdmin, IsAdmin, IsTester, IsGuestOrAbove

User = get_user_model()


# RabbitMQ密码加密/解密函数
def encrypt_rabbitmq_password(password: str) -> str:
    """
    加密RabbitMQ密码

    Args:
        password: 明文密码

    Returns:
        加密后的密码字符串
    """
    try:
        # 直接使用Fernet密钥
        f = Fernet(settings.RABBITMQ_ENCRYPTION_KEY.encode() if isinstance(settings.RABBITMQ_ENCRYPTION_KEY, str) else settings.RABBITMQ_ENCRYPTION_KEY)
        encrypted = f.encrypt(password.encode())
        return encrypted.decode()
    except Exception as e:
        raise ValueError(f"密码加密失败: {str(e)}")


def decrypt_rabbitmq_password(encrypted_password: str) -> str:
    """
    解密RabbitMQ密码（支持向后兼容）

    Args:
        encrypted_password: 加密的密码或明文密码

    Returns:
        明文密码
    """
    if not encrypted_password:
        return encrypted_password

    # 如果密码长度较短（<100），可能是明文或旧格式，直接返回
    # Fernet加密后的密码通常长度>100
    if len(encrypted_password) < 100:
        return encrypted_password

    try:
        # 使用Fernet密钥解密
        f = Fernet(settings.RABBITMQ_ENCRYPTION_KEY.encode() if isinstance(settings.RABBITMQ_ENCRYPTION_KEY, str) else settings.RABBITMQ_ENCRYPTION_KEY)
        decrypted = f.decrypt(encrypted_password.encode())
        return decrypted.decode()
    except Exception as e:
        # 如果解密失败，可能是明文密码，直接返回
        # 这样可以向后兼容旧数据
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"密码解密失败，可能是明文密码: {str(e)}")
        return encrypted_password


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
        # 使用 DRF Token 认证
        from rest_framework.authtoken.models import Token
        token, created = Token.objects.get_or_create(user=user)

        # 将token存储在session中供WebSocket验证使用
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
        """根据不同操作应用不同权限"""
        if self.action in ['create', 'destroy', 'set_role']:
            # 创建/删除用户和修改角色：仅管理员
            return [IsAdmin()]
        elif self.action in ['update', 'partial_update']:
            # 更新用户信息：需要特殊处理（用户可更新自己，管理员可更新所有人）
            return [IsGuestOrAbove()]
        elif self.action == 'list':
            # 列表：测试人员及以上
            return [IsTester()]
        return [IsGuestOrAbove()]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        """创建用户时，如果启用了 RabbitMQ，同步创建 RabbitMQ 用户"""
        user = serializer.save()
        if user.rabbitmq_enabled:
            # 生成随机密码
            rabbitmq_password = secrets.token_urlsafe(16)
            # 加密存储密码
            encrypted_password = encrypt_rabbitmq_password(rabbitmq_password)
            user.rabbitmq_password = encrypted_password
            user.save()
            # 创建RabbitMQ用户时使用明文密码
            self.create_rabbitmq_user_for_platform_user(user.username, rabbitmq_password)

    def update(self, request, *args, **kwargs):
        """更新用户信息 - 用户只能更新自己，管理员可以更新所有人"""
        # 获取要更新的用户对象
        instance = self.get_object()
        is_admin = request.user.role in ['admin', 'super_admin']
        is_self = request.user.id == instance.id

        if not is_admin and not is_self:
            return Response(
                {'error': '无权限修改此用户信息'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 如果是普通用户编辑自己，只允许修改特定字段
        if not is_admin:
            # 只允许修改 email 和 password
            allowed_fields = {'email', 'password'}
            request_data = set(request.data.keys())
            invalid_fields = request_data - allowed_fields
            if invalid_fields:
                return Response(
                    {'error': f'普通用户只能修改邮箱和密码，无权修改: {", ".join(invalid_fields)}'},
                    status=status.HTTP_403_FORBIDDEN
                )

        return super().update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        """删除用户时，同步删除 RabbitMQ 用户"""
        if instance.rabbitmq_enabled:
            self.delete_rabbitmq_user_for_platform_user(instance.username)
        instance.delete()

    @action(detail=False, methods=['post'])
    def logout(self, request):
        logout(request)
        return Response({'message': '登出成功'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """获取当前用户信息"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def permissions(self, request):
        """获取当前用户的权限列表"""
        from .permissions import RolePermission
        role_perms = RolePermission.ROLE_PERMISSIONS.get(request.user.role, [])
        return Response({
            'role': request.user.role,
            'role_display': request.user.get_role_display(),
            'permissions': role_perms
        })

    @action(detail=True, methods=['post'])
    def set_role(self, request, pk=None):
        """设置用户角色 - 仅超级管理员"""
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
        """重置用户密码 - 仅管理员"""
        # 检查权限
        if request.user.role not in ['admin', 'super_admin']:
            return Response(
                {'error': '只有管理员可以重置用户密码'},
                status=status.HTTP_403_FORBIDDEN
            )

        user = self.get_object()

        # 不能重置自己的密码
        if user.id == request.user.id:
            return Response(
                {'error': '不能重置自己的密码，请使用修改密码功能'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 重置为默认密码
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
        """修改密码 - 所有登录用户"""
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

    # ==================== RabbitMQ 用户集成相关 ====================

    def create_rabbitmq_user_for_platform_user(self, username, password):
        """为平台用户创建对应的 RabbitMQ 用户（内部方法）"""
        try:
            import requests
            from django.conf import settings

            rabbitmq_api_url = f"http://{settings.RABBITMQ_HOST}:15672/api/users/{username}"
            auth = (settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)

            response = requests.put(
                rabbitmq_api_url,
                json={"password": password, "tags": "management"},
                auth=auth,
                timeout=5
            )

            if response.status_code in [200, 201, 204]:  # 204: 用户已存在但更新成功
                permissions_url = f"http://{settings.RABBITMQ_HOST}:15672/api/permissions/%2F/{username}"
                perm_response = requests.put(
                    permissions_url,
                    json={"configure": ".*", "write": ".*", "read": ".*"},
                    auth=auth,
                    timeout=5
                )
                # 检查权限设置是否成功
                if perm_response.status_code in [200, 201, 204]:
                    return True
            return False

        except Exception as e:
            import logging
            logging.error(f'创建RabbitMQ用户失败: {username}, 错误: {str(e)}')
            return False

    def delete_rabbitmq_user_for_platform_user(self, username):
        """删除平台用户对应的 RabbitMQ 用户（内部方法）"""
        try:
            import requests
            from django.conf import settings

            user_url = f"http://{settings.RABBITMQ_HOST}:15672/api/users/{username}"
            auth = (settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)

            response = requests.delete(user_url, auth=auth, timeout=5)
            return response.status_code in [200, 204]

        except Exception:
            return False

    @action(detail=True, methods=['get'])
    def get_rabbitmq_config(self, request, pk=None):
        """获取用户的 RabbitMQ 配置信息"""
        user = self.get_object()

        # 权限检查：只能查看自己的配置，管理员及以上可以查看所有人的
        is_self = request.user.id == user.id
        is_admin_or_higher_role = request.user.role in ['admin', 'super_admin', 'tester', 'guest']

        # 项目创建者也可以查看项目的 RabbitMQ 配置
        is_project_creator = request.user.id == user.id

        if not (is_self or is_admin or is_project_creator):
            return Response(
                {'error': '无权限查看此用户的 RabbitMQ 配置'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not user.rabbitmq_enabled:
            return Response(
                {'error': '该用户未启用 RabbitMQ 功能'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.rabbitmq_password:
            return Response(
                {'error': 'RabbitMQ 密码未生成，请联系管理员'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 解密密码以返回给客户端
            decrypted_password = decrypt_rabbitmq_password(user.rabbitmq_password)

            # 获取 RabbitMQ 服务器地址
            # RABBITMQ_HOST 是Docker内部通信地址（如'rabbitmq'服务名）
            # 客户端需要的是外部可访问的地址，优先使用 RABBITMQ_PUBLIC_HOST
            rabbitmq_host = os.getenv('RABBITMQ_PUBLIC_HOST', settings.RABBITMQ_HOST)

            # 如果RABBITMQ_HOST是Docker服务名且没有配置PUBLIC_HOST，尝试获取实际IP
            if rabbitmq_host == settings.RABBITMQ_HOST and settings.RABBITMQ_HOST not in ['127.0.0.1', 'localhost']:
                # Docker服务名情况，尝试获取容器主机IP或使用配置的公网IP
                public_host = os.getenv('RABBITMQ_PUBLIC_HOST')
                if public_host:
                    rabbitmq_host = public_host
                else:
                    # 尝试获取主机IP
                    try:
                        hostname = socket.gethostname()
                        rabbitmq_host = socket.gethostbyname(hostname)
                    except Exception:
                        # 使用默认值，前端需要手动配置
                        rabbitmq_host = settings.RABBITMQ_HOST
            elif rabbitmq_host in ['127.0.0.1', 'localhost']:
                # 本地地址情况，获取本机实际IP
                try:
                    hostname = socket.gethostname()
                    rabbitmq_host = socket.gethostbyname(hostname)
                except Exception:
                    rabbitmq_host = settings.RABBITMQ_HOST

            return Response({
                'username': user.username,
                'password': decrypted_password,  # 返回解密后的密码
                'host': rabbitmq_host,
                'port': settings.RABBITMQ_PORT,
                'vhost': settings.RABBITMQ_VHOST
            })

        except Exception as e:
            import logging
            logging.error(f'获取 RabbitMQ 配置时发生错误: {str(e)}', exc_info=True)
            return Response(
                {'error': f'获取配置信息时发生错误: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def toggle_rabbitmq(self, request, pk=None):
        """开关用户的 RabbitMQ 功能 - 仅超级管理员"""
        if request.user.role != 'super_admin':
            return Response(
                {'error': '只有超级管理员可以修改 RabbitMQ 设置'},
                status=status.HTTP_403_FORBIDDEN
            )

        user = self.get_object()
        enable = request.data.get('enable', False)

        if enable and not user.rabbitmq_enabled:
            # 启用 RabbitMQ：生成随机密码并创建用户
            rabbitmq_password = secrets.token_urlsafe(16)
            # 加密存储密码
            encrypted_password = encrypt_rabbitmq_password(rabbitmq_password)
            user.rabbitmq_password = encrypted_password
            user.rabbitmq_enabled = True

            if self.create_rabbitmq_user_for_platform_user(user.username, rabbitmq_password):
                user.save()
                return Response({
                    'message': f'用户 {user.username} 的 RabbitMQ 功能已启用',
                    'rabbitmq_password': rabbitmq_password  # 返回明文密码供用户配置
                })
            else:
                return Response(
                    {'error': '创建 RabbitMQ 用户失败，请检查 RabbitMQ 服务状态'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

        elif not enable and user.rabbitmq_enabled:
            # 禁用 RabbitMQ：删除 RabbitMQ 用户
            if self.delete_rabbitmq_user_for_platform_user(user.username):
                user.rabbitmq_enabled = False
                user.rabbitmq_password = None
                user.save()
                return Response({
                    'message': f'用户 {user.username} 的 RabbitMQ 功能已禁用'
                })
            else:
                return Response(
                    {'error': '删除 RabbitMQ 用户失败，请检查 RabbitMQ 服务状态'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

        return Response({
            'message': f'用户 {user.username} 的 RabbitMQ 状态未改变'
        })

    @action(detail=False, methods=['post'])
    def create_rabbitmq_user(self, request):
        """创建 RabbitMQ 用户 - 仅超级管理员"""
        # 检查权限：只有超级管理员可以创建 RabbitMQ 用户
        if request.user.role != 'super_admin':
            return Response(
                {'error': '只有超级管理员可以创建 RabbitMQ 用户'},
                status=status.HTTP_403_FORBIDDEN
            )

        username = request.data.get('username')
        password = request.data.get('password')
        tags = request.data.get('tags', 'management')

        if not username or not password:
            return Response(
                {'error': '用户名和密码不能为空'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            import requests
            from django.conf import settings

            # 使用 RabbitMQ HTTP API 创建用户
            rabbitmq_api_url = f"http://{settings.RABBITMQ_HOST}:15672/api/users/{username}"
            auth = (settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)

            # 创建用户
            response = requests.put(
                rabbitmq_api_url,
                json={
                    "password": password,
                    "tags": tags
                },
                auth=auth
            )

            if response.status_code in [200, 201]:
                # 设置用户权限（对虚拟主机 / 的完全权限）
                permissions_url = f"http://{settings.RABBITMQ_HOST}:15672/api/permissions/%2F/{username}"
                permissions_response = requests.put(
                    permissions_url,
                    json={
                        "configure": ".*",
                        "write": ".*",
                        "read": ".*"
                    },
                    auth=auth
                )

                if permissions_response.status_code in [200, 201]:
                    return Response({
                        'message': f'RabbitMQ 用户 {username} 创建成功',
                        'username': username,
                        'password': password,
                        'tags': tags,
                        'note': '请将该信息提供给执行机用户，用于配置执行机客户端'
                    }, status=status.HTTP_201_CREATED)
                else:
                    return Response(
                        {'error': f'用户创建成功但设置权限失败: {permissions_response.text}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                return Response(
                    {'error': f'创建用户失败: {response.text}'},
                    status=response.status_code
                )

        except requests.exceptions.ConnectionError:
            return Response(
                {'error': '无法连接到 RabbitMQ 管理接口，请确认 RabbitMQ 服务已启动'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            return Response(
                {'error': f'创建用户时发生错误: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def list_rabbitmq_users(self, request):
        """列出 RabbitMQ 用户 - 仅超级管理员"""
        if request.user.role != 'super_admin':
            return Response(
                {'error': '只有超级管理员可以查看 RabbitMQ 用户'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            import requests
            from django.conf import settings

            # 获取用户列表
            users_url = f"http://{settings.RABBITMQ_HOST}:15672/api/users/"
            auth = (settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)

            response = requests.get(users_url, auth=auth)

            if response.status_code == 200:
                users_data = response.json()
                # 过滤掉系统内置用户（guest 通常在系统中有特殊用途）
                users_list = []
                for user_info in users_data:
                    # 跳过 guest 用户（系统默认，只允许本地访问）
                    if user_info.get('name') != 'guest':
                        users_list.append({
                            'name': user_info.get('name'),
                            'tags': user_info.get('tags', ''),
                            'hashing_algorithm': user_info.get('hashing_algorithm', ''),
                        })
                return Response({'users': users_list})
            else:
                return Response(
                    {'error': f'获取用户列表失败: {response.text}'},
                    status=response.status_code
                )

        except requests.exceptions.ConnectionError:
            return Response(
                {'error': '无法连接到 RabbitMQ 管理接口'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            return Response(
                {'error': f'获取用户列表时发生错误: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post', 'delete'])
    def delete_rabbitmq_user(self, request):
        """删除 RabbitMQ 用户 - 仅超级管理员"""
        if request.user.role != 'super_admin':
            return Response(
                {'error': '只有超级管理员可以删除 RabbitMQ 用户'},
                status=status.HTTP_403_FORBIDDEN
            )

        username = request.data.get('username') if request.method == 'POST' else request.query_params.get('username')

        if not username:
            return Response(
                {'error': '请提供要删除的用户名'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 不允许删除 guest 用户
        if username == 'guest':
            return Response(
                {'error': '不能删除 guest 系统用户'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            import requests
            from django.conf import settings

            # 删除用户
            user_url = f"http://{settings.RABBITMQ_HOST}:15672/api/users/{username}"
            auth = (settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)

            response = requests.delete(user_url, auth=auth)

            if response.status_code in [200, 204]:
                return Response({'message': f'RabbitMQ 用户 {username} 已删除'})
            else:
                return Response(
                    {'error': f'删除用户失败: {response.text}'},
                    status=response.status_code
                )

        except requests.exceptions.ConnectionError:
            return Response(
                {'error': '无法连接到 RabbitMQ 管理接口'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            return Response(
                {'error': f'删除用户时发生错误: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def update_rabbitmq_user_password(self, request):
        """修改 RabbitMQ 用户密码 - 仅超级管理员"""
        if request.user.role != 'super_admin':
            return Response(
                {'error': '只有超级管理员可以修改 RabbitMQ 用户密码'},
                status=status.HTTP_403_FORBIDDEN
            )

        username = request.data.get('username')
        new_password = request.data.get('password')

        if not username or not new_password:
            return Response(
                {'error': '用户名和新密码不能为空'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            import requests
            from django.conf import settings

            # 修改用户密码
            user_url = f"http://{settings.RABBITMQ_HOST}:15672/api/users/{username}"
            auth = (settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)

            response = requests.put(
                user_url,
                json={"password": new_password},
                auth=auth
            )

            if response.status_code in [200, 201]:
                return Response({
                    'message': f'RabbitMQ 用户 {username} 密码已修改',
                    'username': username,
                    'password': new_password
                })
            else:
                return Response(
                    {'error': f'修改密码失败: {response.text}'},
                    status=response.status_code
                )

        except requests.exceptions.ConnectionError:
            return Response(
                {'error': '无法连接到 RabbitMQ 管理接口'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            return Response(
                {'error': f'修改密码时发生错误: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def role_list(request):
    """获取角色列表 - 测试人员及以上"""
    if request.user.role not in ['tester', 'admin', 'super_admin']:
        return Response(
            {'error': '无权限访问'},
            status=status.HTTP_403_FORBIDDEN
        )

    from .permissions import RolePermission
    from .models import User

    roles = []
    for role_value, role_label in User.ROLE_CHOICES:
        # 统计每个角色的用户数量
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
    """获取或更新角色详情 - 仅超级管理员"""
    from .permissions import RolePermission
    from .models import User

    # 验证角色是否存在
    valid_roles = [r[0] for r in User.ROLE_CHOICES]
    if role not in valid_roles:
        return Response(
            {'error': '角色不存在'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        # 获取角色详情
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

    elif request.method == 'PUT':
        # 更新角色权限（超级管理员功能）
        new_permissions = request.data.get('permissions', [])
        valid_permissions = ['view', 'list', 'create', 'update', 'delete', 'execute', 'manage_users', 'manage_settings']

        # 验证权限
        for perm in new_permissions:
            if perm not in valid_permissions:
                return Response(
                    {'error': f'无效的权限: {perm}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 注意：这里只是示例，实际权限应该存储在数据库中
        # 当前权限是硬编码在 permissions.py 中的
        # 如果要支持动态修改权限，需要创建 Role 模型来存储

        return Response(
            {'error': '当前权限系统为硬编码，不支持动态修改。如需修改，请编辑 permissions.py 文件'},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def role_users(request, role):
    """获取指定角色的用户列表 - 管理员及以上"""
    if request.user.role not in ['admin', 'super_admin']:
        return Response(
            {'error': '无权限访问'},
            status=status.HTTP_403_FORBIDDEN
        )

    from .models import User

    # 验证角色是否存在
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
