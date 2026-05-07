from django.urls import path
from . import views

urlpatterns = [
    # AI 配置
    path('ai/', views.ai_settings_view, name='ai-settings'),
    path('ai/check/', views.ai_config_check_view, name='ai-config-check'),

    # 执行引擎状态
    path('execution/status/', views.execution_engine_status_view, name='execution-engine-status'),

    # Prompt 模板
    path('prompts/', views.prompt_template_list_view, name='prompt-template-list'),
    path('prompts/<int:pk>/', views.prompt_template_detail_view, name='prompt-template-detail'),
    path('prompts/<int:pk>/activate/', views.prompt_template_activate_view, name='prompt-template-activate'),
]
