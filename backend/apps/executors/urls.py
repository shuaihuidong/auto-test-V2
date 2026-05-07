from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VariableViewSet

variable_router = DefaultRouter()
variable_router.register(r'', VariableViewSet, basename='variable')

urlpatterns = [
    path('variables/', include(variable_router.urls)),
]
