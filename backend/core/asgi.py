"""
ASGI config for auto test platform project.
"""

import os
import asyncio
import sys


def _ensure_windows_proactor_event_loop_policy() -> None:
    if sys.platform != 'win32':
        return

    policy = asyncio.get_event_loop_policy()
    if not isinstance(policy, asyncio.WindowsProactorEventLoopPolicy):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
_ensure_windows_proactor_event_loop_policy()

from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

django_asgi_app = get_asgi_application()

# WebSocket 路由必须在 Django 应用初始化之后再导入
from apps.executors.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
