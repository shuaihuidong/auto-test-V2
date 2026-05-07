from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.ScriptViewSet, basename='script')
router.register(r'datasources', views.DataSourceViewSet, basename='datasource')

# BatchTask 使用独立 router 避免被根 ScriptViewSet 的 detail 路由 ^(?P<pk>[^/.]+)/$ 拦截
batch_router = DefaultRouter()
batch_router.register(r'', views.BatchTaskViewSet, basename='batchtask')

urlpatterns = [
    # 自定义 action 路由
    path('modules/', views.ScriptViewSet.as_view({'get': 'modules'}), name='script-modules'),
    # BatchTask 路由放在 router.urls 之前，优先匹配
    path('batch_tasks/', include(batch_router.urls)),
] + router.urls
