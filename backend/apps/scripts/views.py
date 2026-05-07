from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from django_filters import CharFilter, BooleanFilter
from .models import Script, DataSource, BatchTask
from .serializers import ScriptSerializer, ScriptDetailSerializer, DataSourceSerializer, BatchTaskSerializer
from apps.projects.models import ProjectMember, Project
from apps.users.permissions import IsScriptOwnerOrAdmin
import json
import yaml
import asyncio
import threading
from loguru import logger


class ScriptFilterSet(FilterSet):
    """自定义脚本过滤器，处理 project=0 的情况"""
    # 使用 CharFilter 接收字符串，避免外键验证
    project = CharFilter(method='filter_project')
    type = CharFilter(field_name='type')
    framework = CharFilter(field_name='framework')
    is_module = BooleanFilter(field_name='is_module')

    class Meta:
        model = Script
        fields = []

    def filter_project(self, queryset, name, value):
        """处理project过滤，当value=0时不过滤"""
        if value == '0' or value == 0 or value == '':
            return queryset  # 不按项目过滤
        try:
            project_id = int(value)
            return queryset.filter(project_id=project_id)
        except (ValueError, TypeError):
            return queryset


class DataSourceViewSet(viewsets.ModelViewSet):
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class ScriptViewSet(viewsets.ModelViewSet):
    serializer_class = ScriptSerializer
    permission_classes = [IsScriptOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ScriptFilterSet
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        """获取查询集 - 根据用户权限返回脚本，处理project=0的情况"""
        queryset = Script.objects.select_related('project', 'created_by', 'data_source').all()
        user = self.request.user

        # 管理员和超级管理员可以看到所有脚本
        if user.role in ['admin', 'super_admin']:
            # 处理project参数，只过滤指定project=0时不过滤
            project_param = self.request.query_params.get('project')
            if project_param is not None and str(project_param) != '0':
                queryset = queryset.filter(project=project_param)
            return queryset

        # 获取用户有权限访问的项目：自己创建的 + 作为成员加入的
        user_created_projects = user.created_projects.all()
        member_project_ids = ProjectMember.objects.filter(
            user=user
        ).values_list('project_id', flat=True)

        # 合并有权限的项目
        accessible_projects = user_created_projects | Project.objects.filter(
            id__in=member_project_ids
        )

        # 处理project参数
        project_param = self.request.query_params.get('project')
        if project_param is not None and str(project_param) != '0':
            # 检查用户是否有权限访问该项目
            if not accessible_projects.filter(id=project_param).exists():
                # 用户没有权限访问该项目，返回空查询集
                return Script.objects.none()
            queryset = queryset.filter(project=project_param)
        else:
            # 没有指定项目，返回用户有权限访问的所有项目的脚本
            queryset = queryset.filter(project__in=accessible_projects)

        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ScriptDetailSerializer
        return ScriptSerializer

    def perform_create(self, serializer):
        """创建脚本时自动设置创建者"""
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        """创建脚本 - 权限检查"""
        user = request.user

        # guest 不能创建脚本
        if user.role == 'guest':
            return Response(
                {'error': '访客无权创建脚本，请联系管理员升级权限'},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """更新脚本 - 权限检查"""
        script = self.get_object()
        user = request.user

        # 管理员及以上有完全权限
        if user.role in ['admin', 'super_admin']:
            return super().update(request, *args, **kwargs)

        # tester 只能更新自己创建的脚本
        if user.role == 'tester':
            if script.created_by != user:
                return Response(
                    {'error': '只能编辑自己创建的脚本'},
                    status=status.HTTP_403_FORBIDDEN
                )
            return super().update(request, *args, **kwargs)

        # guest 不能更新
        return Response(
            {'error': '访客无权编辑脚本'},
            status=status.HTTP_403_FORBIDDEN
        )

    def destroy(self, request, *args, **kwargs):
        """删除脚本 - 权限检查"""
        script = self.get_object()
        user = request.user

        # 管理员及以上有完全权限
        if user.role in ['admin', 'super_admin']:
            script.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # tester 只能删除自己创建的脚本
        if user.role == 'tester':
            if script.created_by != user:
                return Response(
                    {'error': '只能删除自己创建的脚本'},
                    status=status.HTTP_403_FORBIDDEN
                )
            script.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # guest 不能删除
        return Response(
            {'error': '访客无权删除脚本'},
            status=status.HTTP_403_FORBIDDEN
        )

    @action(detail=False, methods=['get'])
    def modules(self, request):
        """获取可复用的模块列表"""
        modules = self.get_queryset().filter(is_module=True)
        serializer = self.get_serializer(modules, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """复制脚本"""
        script = self.get_object()
        user = request.user

        # guest 不能复制脚本
        if user.role == 'guest':
            return Response(
                {'error': '访客无权复制脚本'},
                status=status.HTTP_403_FORBIDDEN
            )

        new_script = Script.objects.create(
            project=script.project,
            name=f'{script.name} (副本)',
            description=script.description,
            type=script.type,
            framework=script.framework,
            steps=script.steps,
            variables=script.variables,
            is_module=False,
            created_by=request.user
        )
        serializer = self.get_serializer(new_script)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """导出脚本"""
        script = self.get_object()
        format_type = request.query_params.get('format', 'json')

        data = {
            'name': script.name,
            'description': script.description,
            'type': script.type,
            'framework': script.framework,
            'steps': script.steps,
            'variables': script.variables,
            'data_driven': script.data_driven,
        }

        if format_type == 'yaml':
            content = yaml.dump(data, allow_unicode=True)
            content_type = 'application/x-yaml'
            file_name = f'{script.name}.yaml'
        else:
            content = json.dumps(data, indent=2, ensure_ascii=False)
            content_type = 'application/json'
            file_name = f'{script.name}.json'

        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response

    @action(detail=True, methods=['get'])
    def export_code(self, request, pk=None):
        """导出代码"""
        script = self.get_object()
        language = request.query_params.get('language', 'python')

        if language == 'python':
            code = self._generate_python_code(script)
            content_type = 'text/x-python'
            file_name = f'{script.name}.py'
        elif language == 'java':
            code = self._generate_java_code(script)
            content_type = 'text/x-java'
            file_name = f'{script.name}.java'
        elif language == 'javascript':
            code = self._generate_javascript_code(script)
            content_type = 'text/javascript'
            file_name = f'{script.name}.js'
        else:
            return Response({'error': '不支持的语言'}, status=400)

        response = HttpResponse(code, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response

    def _generate_python_code(self, script):
        """生成 Python Playwright 代码"""
        lines = [
            '"""',
            f'Auto-generated test script: {script.name}',
            f'{script.description}',
            '"""',
            '',
            'import asyncio',
            'from playwright.async_api import async_playwright',
            '',
            f'# 初始化变量',
            f'variables = {json.dumps(script.variables, indent=4)}',
            '',
            'async def main():',
            '    async with async_playwright() as p:',
            '        browser = await p.chromium.launch(headless=False)',
            '        page = await browser.new_page()',
            '',
        ]

        for i, step in enumerate(script.steps):
            step_type = step.get('type')
            params = step.get('params', {})
            name = step.get('name', f'Step {i + 1}')

            lines.append(f'        # {name}')

            if step_type == 'goto':
                url = params.get('url', '')
                lines.append(f'        await page.goto("{url}")')

            elif step_type == 'click':
                locator = params.get('locator', {})
                locator_str = self._locator_to_playwright(locator)
                lines.append(f'        await page.locator("{locator_str}").click()')

            elif step_type == 'input':
                locator = params.get('locator', {})
                locator_str = self._locator_to_playwright(locator)
                value = params.get('value', '')
                lines.append(f'        await page.locator("{locator_str}").fill("{value}")')

            elif step_type == 'assert_text':
                text = params.get('text', '')
                lines.append(f'        # Assert text contains: {text}')

            elif step_type == 'wait':
                duration = params.get('duration', 1)
                lines.append(f'        await asyncio.sleep({duration})')

            elif step_type == 'wait_element':
                locator = params.get('locator', {})
                locator_str = self._locator_to_playwright(locator)
                timeout = params.get('timeout', 10) * 1000
                lines.append(f'        await page.locator("{locator_str}").wait_for(timeout={timeout})')

            elif step_type == 'screenshot':
                lines.append(f'        await page.screenshot(path="screenshot_{i}.png")')

            lines.append('')

        lines.extend([
            '        await browser.close()',
            '',
            'if __name__ == "__main__":',
            '    asyncio.run(main())',
        ])

        return '\n'.join(lines)

    @staticmethod
    def _locator_to_playwright(locator: dict) -> str:
        """将平台定位器格式转为 Playwright 定位器字符串"""
        if not locator:
            return ''
        loc_type = locator.get('type', 'css')
        loc_value = locator.get('value', '')
        if loc_type == 'xpath':
            return f'xpath={loc_value}'
        elif loc_type == 'id':
            return f'#{loc_value}'
        elif loc_type == 'text':
            return f'text={loc_value}'
        else:
            return loc_value

    def _generate_java_code(self, script):
        """生成Java代码"""
        code = f'''/**
 * Auto-generated test script: {script.name}
 * {script.description}
 */

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

public class {script.name.replace(" ", "")}Test {{
    public static void main(String[] args) {{
        // Initialize variables
        Map<String, Object> variables = new HashMap<>();
'''

        for key, value in script.variables.items():
            code += f'        variables.put("{key}", {json.dumps(value)});\n'

        code += '''
        // Initialize driver
        WebDriver driver = new ChromeDriver();
        driver.manage().timeouts().implicitlyWait(Duration.ofSeconds(10));

        try {
'''

        for i, step in enumerate(script.steps):
            step_type = step.get('type')
            params = step.get('params', {})
            name = step.get('name', f'Step {i+1}')

            code += f'            // {name}\n'

            if step_type == 'goto':
                url = params.get('url', '')
                code += f'            driver.get("{url}");\n'

            elif step_type == 'click':
                locator = params.get('locator', {})
                locator_type = locator.get('type', 'xpath')
                locator_value = locator.get('value', '')
                code += f'            driver.findElement(By.{locator_type.toUpperCase()}("{locator_value}")).click();\n'

            elif step_type == 'input':
                locator = params.get('locator', {})
                locator_type = locator.get('type', 'xpath')
                locator_value = locator.get('value', '')
                value = params.get('value', '')
                code += f'            WebElement element = driver.findElement(By.{locator_type.toUpperCase()}("{locator_value}"));\n'
                code += f'            element.clear();\n'
                code += f'            element.sendKeys("{value}");\n'

            elif step_type == 'wait':
                duration = params.get('duration', 1)
                code += f'            Thread.sleep({duration * 1000});\n'

            code += '\n'

        code += '''        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            driver.quit();
        }
    }
}
'''
        return code

    def _generate_javascript_code(self, script):
        """生成JavaScript代码"""
        # 使用字符串格式化避免 f-string 转义问题
        header_template = '''/**
 * Auto-generated test script: {name}
 * {description}
 */

const {{ Builder, By, until }} = require('selenium-webdriver');

// Initialize variables
const variables = {variables};

(async function test() {{
    let driver = await new Builder().forBrowser('chrome').build();

    try {{
'''

        footer = '''    }} finally {{
        await driver.quit();
    }}
}})();
'''

        code = header_template.format(
            name=script.name,
            description=script.description,
            variables=json.dumps(script.variables)
        )

        for i, step in enumerate(script.steps):
            step_type = step.get('type')
            params = step.get('params', {})
            name = step.get('name', f'Step {i+1}')

            code += f'        // {name}\n'

            if step_type == 'goto':
                url = params.get('url', '')
                code += f'        await driver.get("{url}");\n'

            elif step_type == 'click':
                locator = params.get('locator', {})
                locator_type = locator.get('type', 'xpath')
                locator_value = locator.get('value', '')
                code += f'        await driver.findElement(By.{locator_type}("{locator_value}")).click();\n'

            elif step_type == 'input':
                locator = params.get('locator', {})
                locator_type = locator.get('type', 'xpath')
                locator_value = locator.get('value', '')
                value = params.get('value', '')
                code += f'        let element = await driver.findElement(By.{locator_type}("{locator_value}"));\n'
                code += f'        await element.clear();\n'
                code += f'        await element.sendKeys("{value}");\n'

            elif step_type == 'wait':
                duration = params.get('duration', 1)
                code += f'        await driver.sleep({duration * 1000});\n'

            code += '\n'

        code += footer
        return code

    @action(detail=False, methods=['post'])
    def import_script(self, request):
        """导入脚本"""
        user = request.user

        # guest 不能导入脚本
        if user.role == 'guest':
            return Response(
                {'error': '访客无权导入脚本'},
                status=status.HTTP_403_FORBIDDEN
            )

        file = request.FILES.get('file')
        if not file:
            return Response({'error': '请上传文件'}, status=400)

        try:
            content = file.read().decode('utf-8')

            if file.name.endswith('.yaml') or file.name.endswith('.yml'):
                data = yaml.safe_load(content)
            else:
                data = json.loads(content)

            # 创建脚本
            script = Script.objects.create(
                project_id=request.data.get('project'),
                name=data.get('name', file.name),
                description=data.get('description', ''),
                type=data.get('type', 'web'),
                framework=data.get('framework', 'playwright'),
                steps=data.get('steps', []),
                variables=data.get('variables', {}),
                data_driven=data.get('data_driven', False),
                created_by=request.user
            )

            serializer = self.get_serializer(script)
            return Response(serializer.data)

        except Exception as e:
            return Response({'error': f'导入失败: {str(e)}'}, status=400)

    @action(detail=False, methods=['post'])
    def nl2script(self, request):
        """
        自然语言转测试脚本 (NL2Script) — 仅生成，不自动保存

        请求体:
            {
                "prompt": "打开百度搜索playwright",   # 必填
                "context": "当前在登录页面"            # 可选，上下文
            }

        响应:
            {
                "steps": [...],          # 平台标准步骤
                "token_usage": {...},    # Token 消耗
                "model": "gpt-4o",
                "provider": "openai"
            }
        """
        user = request.user
        if user.role == 'guest':
            return Response(
                {'error': '访客无权使用 AI 生成脚本'},
                status=status.HTTP_403_FORBIDDEN,
            )

        prompt = request.data.get('prompt', '').strip()
        if not prompt:
            return Response({'error': '请输入操作描述'}, status=400)

        context = request.data.get('context', '')

        try:
            from ai_service import get_llm_gateway, is_ai_configured
            from ai_service.nl2script import NL2ScriptService

            if not is_ai_configured():
                return Response(
                    {'error': 'AI 服务未配置，请在管理后台设置 LLM API Key'},
                    status=503,
                )

            gateway = get_llm_gateway()
            service = NL2ScriptService(gateway)

            # 从 DB 获取 prompt 和 temperature
            try:
                from apps.settings.resolver import get_active_prompt
                system_prompt, temperature = get_active_prompt('nl2script')
            except Exception:
                from ai_service.nl2script import NL2SCRIPT_SYSTEM_PROMPT
                system_prompt = NL2SCRIPT_SYSTEM_PROMPT
                temperature = 0.3

            # 异步调用 LLM
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    service.generate(prompt=prompt, context=context, system_prompt=system_prompt, temperature=temperature)
                )
            finally:
                loop.close()

            return Response({
                'steps': result['steps'],
                'raw_steps': result.get('raw_steps', []),
                'token_usage': result['token_usage'],
                'model': result['model'],
                'provider': result['provider'],
            })

        except Exception as e:
            logger.error(f"NL2Script 失败: {e}")
            error_msg = str(e)
            # 提供更友好的错误提示
            if 'Provider' in error_msg or 'provider' in error_msg.lower():
                from ai_service import get_llm_gateway
                try:
                    gw = get_llm_gateway()
                    provider_name = gw.primary.provider_name if gw.primary else 'unknown'
                    error_msg = (
                        f'AI 调用失败 (当前使用: {provider_name})。'
                        f'请检查 AI 设置中该 Provider 的 API Key 是否正确。'
                        f'原始错误: {error_msg}'
                    )
                except Exception:
                    pass
            return Response(
                {'error': f'AI 生成失败: {error_msg}'},
                status=500,
            )

    @action(detail=False, methods=['post'])
    def nl2script_batch_parse_file(self, request):
        """
        解析上传的 Excel/CSV 文件，返回列名和行数据供前端列映射

        请求: multipart/form-data, 字段名 file
        响应:
        {
            "columns": ["用例编号", "用例名称", ...],
            "rows": [{"用例编号": 1, ...}, ...],
            "total_rows": 25,
            "file_name": "test_cases.xlsx"
        }
        """
        user = request.user
        if user.role == 'guest':
            return Response(
                {'error': '访客无权使用此功能'},
                status=status.HTTP_403_FORBIDDEN,
            )

        file = request.FILES.get('file')
        if not file:
            return Response({'error': '请上传文件'}, status=400)

        # 文件类型检查
        file_ext = file.name.rsplit('.', 1)[-1].lower() if '.' in file.name else ''
        if file_ext not in ('xlsx', 'xls', 'csv'):
            return Response({'error': '仅支持 .xlsx / .xls / .csv 文件'}, status=400)

        # 文件大小检查 10MB
        if file.size > 10 * 1024 * 1024:
            return Response({'error': '文件大小不能超过 10MB'}, status=400)

        try:
            import pandas as pd
            import numpy as np
            import io

            if file_ext == 'csv':
                df = pd.read_csv(io.BytesIO(file.read()))
            else:
                df = pd.read_excel(io.BytesIO(file.read()))

            total_rows = len(df)

            if total_rows == 0:
                return Response({'error': '文件内容为空'}, status=400)

            # 超过 50 行截断
            truncated = total_rows > 50
            if truncated:
                df = df.head(50)

            # NaN 转空字符串，确保 JSON 可序列化
            df = df.fillna('')
            # 处理 numpy 类型
            rows = []
            for _, row in df.iterrows():
                clean_row = {}
                for col in df.columns:
                    val = row[col]
                    if isinstance(val, (np.integer,)):
                        val = int(val)
                    elif isinstance(val, (np.floating,)):
                        val = float(val)
                    elif isinstance(val, np.bool_):
                        val = bool(val)
                    clean_row[str(col)] = val
                rows.append(clean_row)

            return Response({
                'columns': [str(c) for c in df.columns],
                'rows': rows,
                'total_rows': total_rows,
                'file_name': file.name,
            })

        except Exception as e:
            logger.error(f"文件解析失败: {e}")
            return Response(
                {'error': f'文件解析失败: {str(e)}'},
                status=400,
            )

    @action(detail=False, methods=['post'])
    def nl2script_batch(self, request):
        """
        批量自然语言转测试脚本（仅生成，不自动保存）

        请求体:
        {
            "prompts": ["打开百度搜索xx", "登录系统测试", ...],
            "context": "当前在登录页面",
            "max_concurrency": 3
        }
        """
        user = request.user
        if user.role == 'guest':
            return Response(
                {'error': '访客无权使用 AI 生成脚本'},
                status=status.HTTP_403_FORBIDDEN,
            )

        prompts = request.data.get('prompts', [])
        if not prompts or not isinstance(prompts, list):
            return Response({'error': '请提供 prompts 列表'}, status=400)

        if len(prompts) > 50:
            return Response({'error': '单次批量最多 50 条'}, status=400)

        context = request.data.get('context', '')
        max_concurrency = min(request.data.get('max_concurrency', 3), 5)

        try:
            from ai_service import get_llm_gateway, is_ai_configured
            from ai_service.nl2script import NL2ScriptService

            if not is_ai_configured():
                return Response(
                    {'error': 'AI 服务未配置，请在管理后台设置 LLM API Key'},
                    status=503,
                )

            gateway = get_llm_gateway()
            service = NL2ScriptService(gateway)

            # 从 DB 获取 prompt 和 temperature
            try:
                from apps.settings.resolver import get_active_prompt
                system_prompt, temperature = get_active_prompt('nl2script')
            except Exception:
                from ai_service.nl2script import NL2SCRIPT_SYSTEM_PROMPT
                system_prompt = NL2SCRIPT_SYSTEM_PROMPT
                temperature = 0.3

            loop = asyncio.new_event_loop()
            try:
                results = loop.run_until_complete(
                    service.batch_generate(
                        prompts=prompts,
                        context=context,
                        max_concurrency=max_concurrency,
                        system_prompt=system_prompt,
                        temperature=temperature,
                    )
                )
            finally:
                loop.close()

            # 汇总 Token
            total_tokens = 0
            for r in results:
                total_tokens += r.get('token_usage', {}).get('total_tokens', 0)

            return Response({
                'results': results,
                'total': len(results),
                'success_count': sum(1 for r in results if r.get('success')),
                'failed_count': sum(1 for r in results if not r.get('success')),
                'total_tokens': total_tokens,
            })

        except Exception as e:
            logger.error(f"批量 NL2Script 失败: {e}")
            return Response(
                {'error': f'批量生成失败: {str(e)}'},
                status=500,
            )

    @action(detail=False, methods=['post'])
    def nl2script_save(self, request):
        """
        保存 AI 生成的脚本（用户确认后调用）

        请求体:
        {
            "steps": [...],
            "project_id": 1,
            "script_name": "百度搜索测试",
            "prompt": "打开百度搜索..."
        }
        """
        user = request.user
        if user.role == 'guest':
            return Response(
                {'error': '访客无权保存脚本'},
                status=status.HTTP_403_FORBIDDEN,
            )

        steps = request.data.get('steps', [])
        project_id = request.data.get('project_id')
        script_name = request.data.get('script_name', '').strip()
        prompt_text = request.data.get('prompt', '')

        if not steps:
            return Response({'error': '步骤不能为空'}, status=400)
        if not project_id:
            return Response({'error': '请选择项目'}, status=400)

        if not script_name:
            script_name = f'AI生成 - {prompt_text[:20]}' if prompt_text else 'AI生成脚本'

        try:
            script = Script.objects.create(
                project_id=project_id,
                name=script_name,
                description=f'AI 自动生成: {prompt_text}' if prompt_text else 'AI 自动生成',
                type='web',
                framework='playwright',
                steps=steps,
                ai_generated=True,
                created_by=user,
            )
            return Response({'script_id': script.id})
        except Exception as e:
            logger.error(f"保存 AI 脚本失败: {e}")
            return Response({'error': f'保存失败: {str(e)}'}, status=500)

    @action(detail=False, methods=['post'])
    def nl2script_batch_save(self, request):
        """
        批量保存用户确认的脚本

        请求体:
        {
            "project_id": 1,
            "scripts": [
                { "prompt": "...", "steps": [...], "script_name": "..." },
                ...
            ]
        }
        """
        user = request.user
        if user.role == 'guest':
            return Response(
                {'error': '访客无权保存脚本'},
                status=status.HTTP_403_FORBIDDEN,
            )

        project_id = request.data.get('project_id')
        scripts = request.data.get('scripts', [])

        if not project_id:
            return Response({'error': '请选择项目'}, status=400)
        if not scripts or not isinstance(scripts, list):
            return Response({'error': '请提供要保存的脚本列表'}, status=400)

        saved_ids = []
        try:
            for s in scripts:
                steps = s.get('steps', [])
                prompt_text = s.get('prompt', '')
                script_name = s.get('script_name', '').strip()
                if not script_name:
                    script_name = f'AI生成 - {prompt_text[:20]}' if prompt_text else 'AI生成脚本'

                # 支持前端传入 description 和 tags（向后兼容）
                description = s.get('description', '')
                if not description:
                    description = f'AI 批量生成: {prompt_text}' if prompt_text else 'AI 批量生成'
                tags = s.get('tags', [])

                script = Script.objects.create(
                    project_id=project_id,
                    name=script_name,
                    description=description,
                    tags=tags if isinstance(tags, list) else [],
                    type='web',
                    framework='playwright',
                    steps=steps,
                    ai_generated=True,
                    created_by=user,
                )
                saved_ids.append(script.id)

            return Response({'saved_ids': saved_ids})
        except Exception as e:
            logger.error(f"批量保存 AI 脚本失败: {e}")
            return Response({'error': f'批量保存失败: {str(e)}'}, status=500)

    @action(detail=False, methods=['post'])
    def nl2script_review(self, request):
        """
        AI 审查生成的脚本质量

        请求体:
        {
            "items": [
                { "prompt": "打开百度搜索...", "steps": [...] },
                ...
            ]
        }

        响应:
        {
            "reviews": [
                {
                    "quality_score": 85,
                    "intent_match": 90,
                    "suggestions": ["..."],
                    "passed": true
                },
                ...
            ]
        }
        """
        user = request.user
        if user.role == 'guest':
            return Response(
                {'error': '访客无权使用 AI 审查'},
                status=status.HTTP_403_FORBIDDEN,
            )

        items = request.data.get('items', [])
        if not items or not isinstance(items, list):
            return Response({'error': '请提供审查项列表'}, status=400)

        try:
            from ai_service import get_llm_gateway, is_ai_configured
            from ai_service.nl2script import NL2ScriptService

            if not is_ai_configured():
                return Response(
                    {'error': 'AI 服务未配置，请在管理后台设置 LLM API Key'},
                    status=503,
                )

            gateway = get_llm_gateway()
            service = NL2ScriptService(gateway)

            loop = asyncio.new_event_loop()
            try:
                reviews = []
                for item in items:
                    review = loop.run_until_complete(
                        service.review_steps(
                            prompt=item.get('prompt', ''),
                            steps=item.get('steps', []),
                        )
                    )
                    reviews.append(review)
            finally:
                loop.close()

            return Response({'reviews': reviews})

        except Exception as e:
            logger.error(f"AI 审查失败: {e}")
            return Response(
                {'error': f'AI 审查失败: {str(e)}'},
                status=500,
            )

    @action(detail=False, methods=['post'])
    def sandbox_validate(self, request):
        """
        沙盒验证 - 对已有步骤做静态校验（不实际启动浏览器）

        校验内容：步骤类型合法、定位器格式正确、必填参数存在、步骤顺序逻辑合理。
        快速返回，不消耗 LLM Token。

        请求体:
        {
            "steps": [...],
            "url": "https://example.com"  // 可选，用于校验 goto 步骤
        }

        响应:
        {
            "valid": true/false,
            "errors": [{"step_index": 0, "field": "...", "message": "..."}],
            "warnings": [{"step_index": 2, "message": "..."}]
        }
        """
        steps = request.data.get('steps', [])
        if not steps:
            return Response({'error': '请提供 steps'}, status=400)

        valid_step_types = {
            'goto', 'click', 'input', 'clear', 'select', 'checkbox',
            'double_click', 'right_click', 'hover', 'assert_text',
            'assert_title', 'assert_url', 'assert_element', 'assert_visible',
            'wait', 'wait_element', 'screenshot', 'scroll', 'upload',
            'download', 'refresh', 'back', 'forward',
        }
        requires_locator = {
            'click', 'input', 'clear', 'select', 'checkbox', 'double_click',
            'right_click', 'hover', 'assert_element', 'assert_visible',
            'wait_element', 'scroll', 'upload',
        }
        requires_value = {'input', 'select', 'goto', 'assert_text', 'assert_title', 'assert_url'}

        errors = []
        warnings = []

        for i, step in enumerate(steps):
            step_type = step.get('type', '')
            params = step.get('params', {})
            name = step.get('name', f'步骤{i + 1}')

            # 检查步骤类型
            if not step_type:
                errors.append({'step_index': i, 'field': 'type', 'message': f'"{name}" 缺少步骤类型'})
            elif step_type not in valid_step_types:
                errors.append({'step_index': i, 'field': 'type', 'message': f'未知步骤类型: {step_type}'})

            # 检查需要定位器的步骤
            if step_type in requires_locator:
                locator = params.get('locator')
                if not locator or not isinstance(locator, dict) or not locator.get('value'):
                    errors.append({
                        'step_index': i, 'field': 'locator',
                        'message': f'"{name}" 需要有效的定位器',
                    })

            # 检查需要值的步骤
            if step_type in requires_value:
                value = params.get('value') or params.get('url') or params.get('text') or params.get('expected')
                if not value:
                    errors.append({
                        'step_index': i, 'field': 'value',
                        'message': f'"{name}" 需要提供值',
                    })

            # 建议性警告
            if step_type == 'goto' and i > 0:
                prev_type = steps[i - 1].get('type', '')
                if prev_type not in ('goto', 'click', 'wait', 'wait_element'):
                    warnings.append({
                        'step_index': i,
                        'message': f'建议在 goto 步骤前确保前序操作已完成',
                    })

            if step_type in ('click', 'input') and i > 0:
                prev_type = steps[i - 1].get('type', '')
                if prev_type == 'goto':
                    warnings.append({
                        'step_index': i,
                        'message': f'goto 后建议加 wait_element 等待页面加载',
                    })

        return Response({
            'valid': len(errors) == 0,
            'error_count': len(errors),
            'warning_count': len(warnings),
            'errors': errors,
            'warnings': warnings,
        })

    @action(detail=False, methods=['post'])
    def sandbox_execute(self, request):
        """
        沙盒执行 - 在服务端直接使用 Playwright 运行脚本步骤

        请求体:
        {
            "steps": [...],
            "browser": "chromium",  // 可选，默认 chromium
            "headless": true        // 可选，默认 true
        }

        响应:
        {
            "success": true/false,
            "results": { total, passed, failed, steps, logs },
            "error": "..." // 如果整体失败
        }
        """
        steps = request.data.get('steps', [])
        if not steps:
            return Response({'error': '请提供 steps'}, status=400)

        from engine.playwright_engine import PlaywrightEngine

        browser_type = request.data.get('browser', 'chromium')
        headless = request.data.get('headless', True)

        engine = PlaywrightEngine({
            'browser': browser_type,
            'headless': headless,
            'timeout': 30000,
            'continue_on_failure': True,
            'screenshot_on_failure': True,
        })

        try:
            # 初始化浏览器
            if not engine.setup():
                return Response({
                    'success': False,
                    'error': '浏览器启动失败，请确认已安装 Playwright 浏览器 (playwright install)',
                }, status=500)

            # 执行步骤
            results = engine.execute_steps(steps)

            return Response({
                'success': results.get('failed', 0) == 0,
                'results': results,
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': f'沙盒执行异常: {str(e)}',
            }, status=500)

        finally:
            engine.teardown()


# ==================== 批量任务后台执行 ====================

def _run_batch_task(task_id, prompts, context, user_id):
    """
    在后台线程中执行批量生成任务。

    流程：串行生成 → 自动 AI 评审 → 更新状态
    """
    import django
    try:
        django.setup()
    except Exception:
        pass

    try:
        task = BatchTask.objects.get(id=task_id)
        task.status = 'running'
        task.total_count = len(prompts)
        task.save(update_fields=['status', 'total_count', 'updated_at'])
    except BatchTask.DoesNotExist:
        logger.error(f"BatchTask {task_id} 不存在")
        return

    try:
        from ai_service import get_llm_gateway, is_ai_configured
        from ai_service.nl2script import NL2ScriptService

        if not is_ai_configured():
            task.status = 'failed'
            task.error_message = 'AI 服务未配置，请在管理后台设置 LLM API Key'
            task.save(update_fields=['status', 'error_message', 'updated_at'])
            return

        gateway = get_llm_gateway()
        service = NL2ScriptService(gateway)

        # 从 DB 获取 prompt 和 temperature
        try:
            from apps.settings.resolver import get_active_prompt
            system_prompt, temperature = get_active_prompt('nl2script')
        except Exception:
            from ai_service.nl2script import NL2SCRIPT_SYSTEM_PROMPT
            system_prompt = NL2SCRIPT_SYSTEM_PROMPT
            temperature = 0.3

        # 逐条生成，每条完成后立即更新 DB 进度
        results = []
        for i, prompt_text in enumerate(prompts):
            if i > 0:
                asyncio.run(asyncio.sleep(3))

            try:
                result = asyncio.run(
                    service.generate(
                        prompt=prompt_text,
                        context=context,
                        system_prompt=system_prompt,
                        temperature=temperature,
                    )
                )
                result["index"] = i
                result["prompt"] = prompt_text
                result["success"] = True
                results.append(result)

                # 更新进度到 DB
                task.refresh_from_db()
                task.completed_count += 1
                task.save(update_fields=['completed_count', 'updated_at'])
            except Exception as e:
                logger.error(f"批量生成第 {i} 条失败: {e}")
                results.append({
                    "index": i,
                    "prompt": prompt_text,
                    "success": False,
                    "error": str(e),
                    "steps": [],
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                })
                task.refresh_from_db()
                task.failed_count += 1
                task.save(update_fields=['failed_count', 'updated_at'])
        # 按原始顺序排列
        results.sort(key=lambda x: x["index"])

        # 进入评审阶段
        task.status = 'reviewing'
        task.save(update_fields=['status', 'completed_count', 'failed_count', 'updated_at'])

        # 对成功的脚本进行 AI 评审
        success_items = []
        result_map = {}  # index -> result
        for r in results:
            result_map[r['index']] = r
            if r.get('success') and r.get('steps'):
                success_items.append({
                    'index': r['index'],
                    'prompt': r.get('prompt', ''),
                    'steps': r['steps'],
                })

        reviews_map = {}
        if success_items:
            try:
                review_loop = asyncio.new_event_loop()
                try:
                    for item in success_items:
                        review = review_loop.run_until_complete(
                            service.review_steps(
                                prompt=item['prompt'],
                                steps=item['steps'],
                            )
                        )
                        reviews_map[item['index']] = review
                finally:
                    review_loop.close()
            except Exception as e:
                logger.warning(f"AI 评审失败（不影响生成结果）: {e}")

        # 组装最终 results
        final_results = []
        for r in results:
            entry = {
                'index': r.get('index', 0),
                'prompt': r.get('prompt', ''),
                'success': r.get('success', False),
                'steps': r.get('steps', []),
                'error': r.get('error', ''),
                'token_usage': r.get('token_usage', {}),
            }
            if r.get('index') in reviews_map:
                review = reviews_map[r['index']]
                entry['review'] = {
                    'quality_score': review.get('quality_score', 0),
                    'intent_match': review.get('intent_match', 0),
                    'suggestions': review.get('suggestions', []),
                    'passed': review.get('passed', False),
                }
            final_results.append(entry)

        task.results = final_results
        task.status = 'completed'
        task.save(update_fields=['status', 'results', 'updated_at'])

        completed = sum(1 for r in results if r.get('success'))
        failed = sum(1 for r in results if not r.get('success'))
        logger.info(f"BatchTask {task_id} 完成: {completed} 成功, {failed} 失败")

    except Exception as e:
        logger.error(f"BatchTask {task_id} 执行失败: {e}")
        try:
            task = BatchTask.objects.get(id=task_id)
            task.status = 'failed'
            task.error_message = str(e)[:2000]
            task.save(update_fields=['status', 'error_message', 'updated_at'])
        except Exception:
            pass


def _regenerate_batch_results(task_id, items_to_regenerate, user_id):
    """
    在后台线程中重新生成指定索引的批量任务结果。

    items_to_regenerate: [{'index': 0, 'prompt': '...'}, ...]
    """
    import django
    try:
        django.setup()
    except Exception:
        pass

    try:
        task = BatchTask.objects.get(id=task_id)
    except BatchTask.DoesNotExist:
        logger.error(f"BatchTask {task_id} 不存在")
        return

    try:
        from ai_service import get_llm_gateway, is_ai_configured
        from ai_service.nl2script import NL2ScriptService

        if not is_ai_configured():
            task.status = 'failed'
            task.error_message = 'AI 服务未配置'
            task.save(update_fields=['status', 'error_message', 'updated_at'])
            return

        gateway = get_llm_gateway()
        service = NL2ScriptService(gateway)

        try:
            from apps.settings.resolver import get_active_prompt
            system_prompt, temperature = get_active_prompt('nl2script')
        except Exception:
            from ai_service.nl2script import NL2SCRIPT_SYSTEM_PROMPT
            system_prompt = NL2SCRIPT_SYSTEM_PROMPT
            temperature = 0.3

        # 逐条重新生成
        for item in items_to_regenerate:
            idx = item['index']
            prompt_text = item['prompt']

            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    service.generate(
                        prompt=prompt_text,
                        context='',
                        system_prompt=system_prompt,
                        temperature=temperature,
                    )
                )

                # AI 评审
                review_data = None
                try:
                    review = loop.run_until_complete(
                        service.review_steps(prompt=prompt_text, steps=result.get('steps', []))
                    )
                    review_data = {
                        'quality_score': review.get('quality_score', 0),
                        'intent_match': review.get('intent_match', 0),
                        'suggestions': review.get('suggestions', []),
                        'passed': review.get('passed', False),
                    }
                except Exception as e:
                    logger.warning(f"重新生成评审失败 (index={idx}): {e}")

                new_entry = {
                    'index': idx,
                    'prompt': prompt_text,
                    'success': True,
                    'regenerating': False,
                    'steps': result.get('steps', []),
                    'error': '',
                    'token_usage': result.get('token_usage', {}),
                }
                if review_data:
                    new_entry['review'] = review_data

                # 替换 results 中对应条目
                task.refresh_from_db()
                results = task.results or []
                replaced = False
                for i, r in enumerate(results):
                    if r.get('index') == idx:
                        results[i] = new_entry
                        replaced = True
                        break
                if not replaced:
                    results.append(new_entry)

                task.results = results
                task.save(update_fields=['results', 'updated_at'])

            except Exception as e:
                logger.error(f"重新生成第 {idx} 条失败: {e}")
                error_entry = {
                    'index': idx,
                    'prompt': prompt_text,
                    'success': False,
                    'regenerating': False,
                    'error': str(e),
                    'steps': [],
                    'token_usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                }
                task.refresh_from_db()
                results = task.results or []
                for i, r in enumerate(results):
                    if r.get('index') == idx:
                        results[i] = error_entry
                        break
                task.results = results
                task.save(update_fields=['results', 'updated_at'])
            finally:
                loop.close()

            # 间隔 3 秒
            if len(items_to_regenerate) > 1:
                await_sync = asyncio.new_event_loop()
                try:
                    await_sync.run_until_complete(asyncio.sleep(3))
                finally:
                    await_sync.close()

        # 重新计算计数（不改变 status，保持 completed）
        task.refresh_from_db()
        results = task.results or []
        task.total_count = len(results)
        task.completed_count = sum(1 for r in results if r.get('success'))
        task.failed_count = sum(1 for r in results if not r.get('success'))
        task.save(update_fields=['total_count', 'completed_count', 'failed_count', 'updated_at'])

        logger.info(f"BatchTask {task_id} 重新生成完成")

    except Exception as e:
        logger.error(f"BatchTask {task_id} 重新生成失败: {e}")
        # 重新生成失败不影响整体任务状态，只标记对应条目为失败
        try:
            task = BatchTask.objects.get(id=task_id)
            results = task.results or []
            regen_indexes = [item['index'] for item in items_to_regenerate]
            for i, r in enumerate(results):
                if r.get('index') in regen_indexes and r.get('regenerating'):
                    results[i] = {
                        'index': r.get('index'),
                        'prompt': r.get('prompt', ''),
                        'success': False,
                        'error': f'重新生成失败: {str(e)[:200]}',
                        'steps': [],
                        'token_usage': {},
                    }
            task.results = results
            task.total_count = len(results)
            task.completed_count = sum(1 for r in results if r.get('success'))
            task.failed_count = sum(1 for r in results if not r.get('success'))
            task.save(update_fields=['results', 'total_count', 'completed_count', 'failed_count', 'updated_at'])
        except Exception:
            pass


# ==================== 批量任务 ViewSet ====================

class BatchTaskViewSet(viewsets.ModelViewSet):
    """批量生成任务 API"""
    serializer_class = BatchTaskSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']  # 只读 + 创建 + 删除

    def get_queryset(self):
        return BatchTask.objects.filter(created_by=self.request.user).order_by('-created_at')

    def create(self, request):
        """
        创建批量生成任务

        请求体:
        {
            "name": "任务名称",
            "prompts": ["描述1", "描述2", ...],
            "context": "可选上下文"
        }
        """
        user = request.user
        if user.role == 'guest':
            return Response(
                {'error': '访客无权使用此功能'},
                status=status.HTTP_403_FORBIDDEN,
            )

        name = request.data.get('name', '').strip()
        prompts = request.data.get('prompts', [])
        context = request.data.get('context', '')

        if not prompts or not isinstance(prompts, list):
            return Response({'error': '请提供 prompts 列表'}, status=400)

        if len(prompts) > 50:
            return Response({'error': '单次批量最多 50 条'}, status=400)

        if not name:
            name = f'批量生成 - {len(prompts)} 条'

        # 创建任务记录
        task = BatchTask.objects.create(
            name=name,
            status='pending',
            total_count=len(prompts),
            created_by=user,
        )

        # 启动后台线程
        thread = threading.Thread(
            target=_run_batch_task,
            args=(task.id, prompts, context, user.id),
            daemon=True,
        )
        thread.start()

        serializer = BatchTaskSerializer(task)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def save_scripts(self, request, pk=None):
        """
        将选中结果保存为脚本

        请求体:
        {
            "project_id": 1,
            "items": [
                { "index": 0, "script_name": "测试1", "steps": [...] },
                ...
            ]
        }
        """
        user = request.user
        if user.role == 'guest':
            return Response(
                {'error': '访客无权保存脚本'},
                status=status.HTTP_403_FORBIDDEN,
            )

        task = self.get_object()
        project_id = request.data.get('project_id')
        items = request.data.get('items', [])

        if not project_id:
            return Response({'error': '请选择项目'}, status=400)
        if not items:
            return Response({'error': '请选择要保存的脚本'}, status=400)

        saved_ids = []
        try:
            for item in items:
                steps = item.get('steps', [])
                index = item.get('index')
                script_name = item.get('script_name', '').strip()

                if not script_name:
                    # 从任务结果中找对应的 prompt
                    prompt = ''
                    for r in (task.results or []):
                        if r.get('index') == index:
                            prompt = r.get('prompt', '')
                            break
                    script_name = f'AI生成 - {prompt[:20]}' if prompt else f'AI生成 - 步骤{index}'

                # 查找对应的 prompt 和 review 信息
                prompt = ''
                review_data = None
                for r in (task.results or []):
                    if r.get('index') == index:
                        prompt = r.get('prompt', '')
                        review_data = r.get('review')
                        break

                description = f'AI 批量生成: {prompt}'
                if review_data:
                    description += f' | 质量分: {review_data.get("quality_score", 0)}'

                # 重名自动加后缀
                base_name = script_name
                suffix = 1
                while Script.objects.filter(project_id=project_id, name=script_name).exists():
                    script_name = f'{base_name} ({suffix})'
                    suffix += 1

                script = Script.objects.create(
                    project_id=project_id,
                    name=script_name,
                    description=description,
                    type='web',
                    framework='playwright',
                    steps=steps,
                    ai_generated=True,
                    created_by=user,
                )
                saved_ids.append(script.id)

            return Response({'saved_ids': saved_ids})
        except Exception as e:
            logger.error(f"批量保存脚本失败: {e}")
            return Response({'error': f'保存失败: {str(e)}'}, status=500)

    @action(detail=True, methods=['post'])
    def delete_results(self, request, pk=None):
        """
        删除选中的结果条目

        请求体: { "indexes": [0, 2, 5] }
        """
        task = self.get_object()
        indexes = request.data.get('indexes', [])
        if not indexes or not isinstance(indexes, list):
            return Response({'error': '请提供要删除的索引列表'}, status=400)

        original_results = task.results or []
        index_set = set(indexes)
        new_results = [r for r in original_results if r.get('index') not in index_set]

        # 重新计算计数
        task.results = new_results
        task.total_count = len(new_results)
        task.completed_count = sum(1 for r in new_results if r.get('success'))
        task.failed_count = sum(1 for r in new_results if not r.get('success'))
        task.save()

        serializer = BatchTaskSerializer(task)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def regenerate_results(self, request, pk=None):
        """
        重新生成选中的结果条目

        请求体: { "indexes": [0, 2, 5] }
        """
        task = self.get_object()
        indexes = request.data.get('indexes', [])
        if not indexes or not isinstance(indexes, list):
            return Response({'error': '请提供要重新生成的索引列表'}, status=400)

        # 找到对应的 prompts
        original_results = task.results or []
        prompts_to_regenerate = []
        for idx in indexes:
            for r in original_results:
                if r.get('index') == idx:
                    prompts_to_regenerate.append({'index': idx, 'prompt': r.get('prompt', '')})
                    break

        if not prompts_to_regenerate:
            return Response({'error': '未找到对应的条目'}, status=400)

        # 将对应条目标记为 regenerating，保持任务 completed 状态不变
        regen_set = set(indexes)
        for i, r in enumerate(original_results):
            if r.get('index') in regen_set:
                original_results[i] = {
                    'index': r.get('index'),
                    'prompt': r.get('prompt', ''),
                    'success': False,
                    'regenerating': True,
                    'error': '正在重新生成...',
                    'steps': [],
                    'token_usage': {},
                }
        task.results = original_results
        task.save(update_fields=['results', 'updated_at'])

        # 启动后台线程重新生成
        thread = threading.Thread(
            target=_regenerate_batch_results,
            args=(task.id, prompts_to_regenerate, request.user.id),
            daemon=True,
        )
        thread.start()

        return Response({'message': '已开始重新生成'})
