from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from django_filters import CharFilter, BooleanFilter
from .models import Script, DataSource
from .serializers import ScriptSerializer, ScriptDetailSerializer, DataSourceSerializer
from apps.projects.models import ProjectMember, Project
from apps.users.permissions import IsScriptOwnerOrAdmin
import json
import yaml
import asyncio
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
        自然语言转测试脚本 (NL2Script)

        请求体:
            {
                "prompt": "打开百度搜索playwright",   # 必填
                "context": "当前在登录页面",           # 可选，上下文
                "save_to_project": 1,                 # 可选，保存到项目 ID
                "script_name": "百度搜索测试"          # 可选，脚本名称
            }

        响应:
            {
                "steps": [...],          # 平台标准步骤
                "token_usage": {...},    # Token 消耗
                "model": "gpt-4o",
                "provider": "openai",
                "script_id": 123         # 如果 save_to_project 有值
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
            from ai_service import get_llm_gateway
            from ai_service.nl2script import NL2ScriptService

            gateway = get_llm_gateway()
            service = NL2ScriptService(gateway)

            # 异步调用 LLM
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    service.generate(prompt=prompt, context=context)
                )
            finally:
                loop.close()

            # 可选：直接保存为脚本
            script_id = None
            save_to_project = request.data.get('save_to_project')
            if save_to_project:
                script_name = request.data.get('script_name', f'AI生成 - {prompt[:20]}')
                script = Script.objects.create(
                    project_id=save_to_project,
                    name=script_name,
                    description=f'AI 自动生成: {prompt}',
                    type='web',
                    framework='playwright',
                    steps=result['steps'],
                    ai_generated=True,
                    created_by=user,
                )
                script_id = script.id

            return Response({
                'steps': result['steps'],
                'raw_steps': result.get('raw_steps', []),
                'token_usage': result['token_usage'],
                'model': result['model'],
                'provider': result['provider'],
                'script_id': script_id,
            })

        except Exception as e:
            logger.error(f"NL2Script 失败: {e}")
            return Response(
                {'error': f'AI 生成失败: {str(e)}'},
                status=500,
            )

    @action(detail=False, methods=['post'])
    def nl2script_batch(self, request):
        """
        批量自然语言转测试脚本

        请求体:
        {
            "prompts": ["打开百度搜索xx", "登录系统测试", ...],
            "context": "当前在登录页面",
            "save_to_project": 1,
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
        save_to_project = request.data.get('save_to_project')

        try:
            from ai_service import get_llm_gateway
            from ai_service.nl2script import NL2ScriptService

            gateway = get_llm_gateway()
            service = NL2ScriptService(gateway)

            loop = asyncio.new_event_loop()
            try:
                results = loop.run_until_complete(
                    service.batch_generate(
                        prompts=prompts,
                        context=context,
                        max_concurrency=max_concurrency,
                    )
                )
            finally:
                loop.close()

            # 可选：批量保存为脚本
            total_tokens = 0
            saved_ids = []
            if save_to_project:
                for r in results:
                    if r.get('success') and r.get('steps'):
                        script = Script.objects.create(
                            project_id=save_to_project,
                            name=f"AI生成 - {r['prompt'][:20]}",
                            description=f"AI 批量生成: {r['prompt']}",
                            type='web',
                            framework='playwright',
                            steps=r['steps'],
                            ai_generated=True,
                            created_by=user,
                        )
                        saved_ids.append(script.id)
                        r['script_id'] = script.id

            # 汇总 Token
            for r in results:
                total_tokens += r.get('token_usage', {}).get('total_tokens', 0)

            return Response({
                'results': results,
                'total': len(results),
                'success_count': sum(1 for r in results if r.get('success')),
                'failed_count': sum(1 for r in results if not r.get('success')),
                'total_tokens': total_tokens,
                'saved_ids': saved_ids,
            })

        except Exception as e:
            logger.error(f"批量 NL2Script 失败: {e}")
            return Response(
                {'error': f'批量生成失败: {str(e)}'},
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
