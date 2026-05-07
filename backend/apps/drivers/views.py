from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Driver
from .serializers import DriverSerializer
import subprocess
import sys


class DriverViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['framework', 'browser', 'is_recommended']
    search_fields = ['description']

    @action(detail=False, methods=['get'])
    def recommended(self, request):
        """获取推荐的驱动"""
        drivers = self.queryset.filter(is_recommended=True)
        serializer = self.get_serializer(drivers, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def check_environment(self, request):
        """检查环境配置"""
        framework = request.data.get('framework')
        if not framework:
            return Response({'error': '请指定framework'}, status=400)

        result = {
            'framework': framework,
            'installed': False,
            'version': None,
            'message': ''
        }

        try:
            if framework == 'selenium':
                import selenium
                result['installed'] = True
                result['version'] = selenium.__version__
                result['message'] = 'Selenium已安装'

                # 检查ChromeDriver
                try:
                    from selenium import webdriver
                    from selenium.webdriver.chrome.service import Service
                    from webdriver_manager.chrome import ChromeDriverManager
                    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
                    driver.quit()
                    result['chrome_driver'] = True
                except Exception as e:
                    result['chrome_driver'] = False
                    result['message'] += f'\nChromeDriver检查失败: {str(e)}'

            elif framework == 'playwright':
                import playwright
                result['installed'] = True
                result['version'] = playwright.__version__
                result['message'] = 'Playwright已安装'

            elif framework == 'appium':
                import Appium
                result['installed'] = True
                result['version'] = getattr(Appium, '__version__', 'unknown')
                result['message'] = 'Appium已安装'

            elif framework == 'httprunner':
                import httprunner
                result['installed'] = True
                result['version'] = getattr(httprunner, '__version__', 'unknown')
                result['message'] = 'HttpRunner已安装'

        except ImportError:
            result['message'] = f'{framework}未安装'

        return Response(result)
