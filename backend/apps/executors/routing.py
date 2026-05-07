from django.urls import re_path
from . import consumers_v2
from apps.executions.consumers import ExecutionConsumer

websocket_urlpatterns = [
    # 用于执行器状态展示
    re_path(r'ws/executor-status/?$', consumers_v2.ExecutorStatusConsumer.as_asgi()),
    # 执行实时状态推送（轻量化执行引擎使用）
    re_path(r'ws/execution/(?P<execution_id>\d+)/?$', ExecutionConsumer.as_asgi()),
]
