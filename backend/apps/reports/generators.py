"""
报告生成器
"""
import os
import json
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from jinja2 import Template
from .models import Report


class ReportGenerator:
    """测试报告生成器
    生成HTML格式测试报告
    """

    # 常见错误类型对应的修复建议
    ERROR_SUGGESTIONS = {
        # 元素相关错误
        '元素未找到': '请检查：1) 元素定位器是否正确；2) 页面是否完全加载；3) 元素是否在iframe中；4) 是否需要等待元素出现',
        '元素不存在': '请检查：1) 元素定位器是否正确；2) 页面是否完全加载；3) 元素是否在iframe中；4) 是否需要等待元素出现',
        '未找到元素': '请检查：1) 元素定位器是否正确；2) 页面是否完全加载；3) 元素是否在iframe中；4) 是否需要等待元素出现',
        '找不到元素': '请检查：1) 元素定位器是否正确；2) 页面是否完全加载；3) 元素是否在iframe中；4) 是否需要等待元素出现',
        '无法定位元素': '请检查：1) 元素定位器是否正确；2) 页面是否完全加载；3) 元素是否在iframe中；4) 是否需要等待元素出现',
        'element not found': '请检查：1) 元素定位器是否正确；2) 页面是否完全加载；3) 元素是否在iframe中；4) 是否需要等待元素出现',
        'not found': '请检查：1) 元素定位器是否正确；2) 页面是否完全加载；3) 元素是否在iframe中；4) 是否需要等待元素出现',

        # 超时相关错误
        '超时': '请检查：1) 网络连接是否正常；2) 服务器响应是否过慢；3) 是否需要增加等待时间',
        'timeout': '请检查：1) 网络连接是否正常；2) 服务器响应是否过慢；3) 是否需要增加等待时间',
        '等待超时': '请检查：1) 网络连接是否正常；2) 服务器响应是否过慢；3) 是否需要增加等待时间',
        '页面加载超时': '请检查：1) 网络连接是否正常；2) 页面是否存在；3) 是否需要增加页面加载超时时间',
        '等待元素超时': '请检查：1) 元素定位器是否正确；2) 页面是否完全加载；3) 是否需要增加超时时间',

        # 选择器相关错误
        '无效的选择器': '请检查：1) CSS选择器语法是否正确；2) XPath表达式是否正确；3) 尝试使用其他定位方式',
        'invalid selector': '请检查：1) CSS选择器语法是否正确；2) XPath表达式是否正确；3) 尝试使用其他定位方式',
        '选择器错误': '请检查：1) CSS选择器语法是否正确；2) XPath表达式是否正确；3) 尝试使用其他定位方式',

        # 连接相关错误
        '连接失败': '请检查：1) 网络连接是否正常；2) URL是否正确；3) 防火墙是否阻止连接；4) 服务是否正常运行',
        'connection': '请检查：1) 网络连接是否正常；2) URL是否正确；3) 防火墙是否阻止连接；4) 服务是否正常运行',
        '无法连接': '请检查：1) 网络连接是否正常；2) URL是否正确；3) 防火墙是否阻止连接；4) 服务是否正常运行',

        # 浏览器相关错误
        '浏览器未启动': '请检查：1) 浏览器驱动是否正确安装；2) 浏览器版本是否与驱动兼容；3) 重新启动执行机',
        'browser': '请检查：1) 浏览器驱动是否正确安装；2) 浏览器版本是否与驱动兼容；3) 重新启动执行机',

        # JavaScript相关错误
        'javascript': '请检查：1) JavaScript代码是否有语法错误；2) 变量是否已定义；3) 异常是否被正确处理',
        '脚本错误': '请检查：1) JavaScript代码是否有语法错误；2) 变量是否已定义；3) 异常是否被正确处理',

        # 断言相关错误
        '断言失败': '请检查：1) 期望值是否正确；2) 实际值是否符合预期；3) 断言条件是否正确',
        'assert': '请检查：1) 期望值是否正确；2) 实际值是否符合预期；3) 断言条件是否正确',
        '不符合预期': '请检查：1) 期望值是否正确；2) 实际值是否符合预期；3) 业务逻辑是否正确',
        '验证失败': '请检查：1) 期望值是否正确；2) 实际值是否符合预期；3) 页面状态是否正确',

        # 输入相关错误
        '输入失败': '请检查：1) 元素是否存在且可编辑；2) 输入值格式是否正确；3) 元素是否被遮挡或禁用',

        # 文件操作相关错误
        '上传失败': '请检查：1) 文件路径是否正确；2) 文件是否存在；3) 元素类型是否为文件输入',
        '下载失败': '请检查：1) 网络连接是否正常；2) URL是否正确；3) 下载目录是否有写入权限',
        '未找到文件输入元素': '请检查：1) 文件上传元素定位器是否正确；2) 元素是否在iframe中；3) 元素是否可见',

        # 参数相关错误
        '缺少参数': '请检查：1) 步骤配置是否完整；2) 必填参数是否都已设置；3) 参数名称是否正确',
        '缺少locator': '请检查：1) 步骤中是否配置了元素定位器；2) locator参数是否正确',

        # 未知错误
        '未知步骤类型': '请检查：1) 步骤类型是否正确；2) 参考支持的步骤类型列表；3) 更新执行机版本',
        '未知': '请查看详细的错误日志以获取更多信息',
    }

    def __init__(self, execution):
        """
        测试报告生成器
        生成HTML格式测试报告
        """
        self.execution = execution
        self.report_dir = settings.REPORTS_ROOT
        self.screenshot_dir = settings.SCREENSHOTS_ROOT

    def _get_suggestion_for_error(self, error_message: str) -> str:
        """
        根据错误消息获取修复建议

        Args:
            error_message: 错误消息

        Returns:
            修复建议
        """
        if not error_message:
            return "请查看详细的错误日志以获取更多信息"

        error_lower = error_message.lower()

        # 检查是否匹配已知的错误类型
        for key, suggestion in self.ERROR_SUGGESTIONS.items():
            if key.lower() in error_lower:
                return suggestion

        # 默认建议
        return "请检查：1) 测试步骤配置是否正确；2) 测试环境是否正常；3) 查看详细日志获取更多信息"

    def generate(self) -> Report:
        """生成测试报告"""
        # 检查是否已存在报告
        try:
            report = Report.objects.get(execution=self.execution)
        except Report.DoesNotExist:
            report = Report(execution=self.execution)

        # 生成汇总数据
        summary = self._generate_summary()
        report.summary = summary

        # 生成图表数据
        charts_data = self._generate_charts_data()
        report.charts_data = charts_data

        # 生成HTML报告
        html_path = self._generate_html_report()
        report.html_report = html_path

        report.save()
        return report

    def _generate_summary(self) -> dict:
        """生成汇总数据"""
        # 如果是计划执行记录，聚合所有子脚本的数据
        if self.execution.execution_type == 'plan':
            return self._generate_plan_summary()
        else:
            return self._generate_script_summary()

    def _generate_script_summary(self) -> dict:
        """生成单个脚本的汇总数据"""
        result = self.execution.result or {}
        steps = result.get('steps', [])

        # 计算通过率
        total = result.get('total', len(steps))
        passed = result.get('passed', 0)
        failed = result.get('failed', 0)
        pass_rate = round((passed / total * 100) if total > 0 else 0, 2)

        # 计算总耗时
        total_duration = sum(step.get('duration', 0) for step in steps)

        # 统计各类型步骤
        step_types = {}
        for step in steps:
            step_type = step.get('type', 'unknown')
            if step_type not in step_types:
                step_types[step_type] = {'total': 0, 'passed': 0, 'failed': 0}
            step_types[step_type]['total'] += 1
            if step.get('success'):
                step_types[step_type]['passed'] += 1
            else:
                step_types[step_type]['failed'] += 1

        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': pass_rate,
            'total_duration': round(total_duration / 1000, 2),  # 转换为秒
            'step_types': step_types,
            'execution_id': self.execution.id,
            'script_name': self.execution.script.name if self.execution.script else 'N/A',
            'plan_name': self.execution.plan.name if self.execution.plan else 'N/A',
            'started_at': self.execution.started_at.isoformat() if self.execution.started_at else None,
            'completed_at': self.execution.completed_at.isoformat() if self.execution.completed_at else None,
            'execution_type': 'script'
        }

    def _generate_plan_summary(self) -> dict:
        """生成计划执行的汇总数据"""
        # 获取所有子脚本执行记录
        children = self.execution.children.all()

        # 统计脚本完成情况
        total_scripts = children.count()
        completed_scripts = children.filter(status='completed').count()
        failed_scripts = children.filter(status='failed').count()
        running_scripts = children.filter(status='running').count()
        pending_scripts = children.filter(status='pending').count()

        # 统计各状态脚本数
        script_status = {
            'completed': completed_scripts,
            'failed': failed_scripts,
            'running': running_scripts,
            'pending': pending_scripts
        }

        # 计算脚本通过率（基于脚本数）
        finished_scripts = completed_scripts + failed_scripts
        pass_rate = round((completed_scripts / finished_scripts * 100) if finished_scripts > 0 else 0, 2)

        # 计算总耗时（所有子脚本的总和）
        total_duration = sum(child.duration or 0 for child in children)

        # 统计步骤总数（用于显示总步骤数）
        total_steps = sum(child.total_count or 0 for child in children)
        passed_steps = sum(child.passed_count or 0 for child in children)
        failed_steps = sum(child.failed_count or 0 for child in children)

        return {
            'total_scripts': total_scripts,
            'passed': completed_scripts,  # 完成的脚本数
            'failed': failed_scripts,     # 失败的脚本数
            'pass_rate': pass_rate,       # 基于脚本数的通过率
            'total_duration': round(total_duration, 2),
            'script_status': script_status,
            'total_steps': total_steps,   # 总步骤数
            'passed_steps': passed_steps, # 通过的步骤数
            'failed_steps': failed_steps, # 失败的步骤数
            'execution_id': self.execution.id,
            'script_name': 'N/A',
            'plan_name': self.execution.plan.name if self.execution.plan else 'N/A',
            'started_at': self.execution.started_at.isoformat() if self.execution.started_at else None,
            'completed_at': self.execution.completed_at.isoformat() if self.execution.completed_at else None,
            'execution_type': 'plan'
        }

    def _generate_charts_data(self) -> dict:
        """生成图表数据"""
        # 如果是计划执行记录，生成脚本级别的图表
        if self.execution.execution_type == 'plan':
            return self._generate_plan_charts_data()
        else:
            return self._generate_script_charts_data()

    def _generate_script_charts_data(self) -> dict:
        """生成单个脚本的图表数据"""
        result = self.execution.result or {}
        executed_steps = result.get('steps', [])

        # 获取原始脚本步骤信息（包含 type 等信息）
        script = self.execution.script
        original_steps = script.steps if script else []

        # 趋势图数据（按步骤顺序，合并执行结果和原始步骤信息）
        trend_data = []
        for i, step_result in enumerate(executed_steps):
            # 获取对应的原始步骤信息
            original_step = original_steps[i] if i < len(original_steps) else {}

            trend_data.append({
                'index': i + 1,
                'name': step_result.get('name', original_step.get('name', f'Step {i + 1}')),
                'type': step_result.get('type', original_step.get('type', 'unknown')),
                'duration': step_result.get('duration', 0),
                'success': step_result.get('success', False),
                'message': step_result.get('message', ''),
                'error': '' if step_result.get('success') else (step_result.get('error') or step_result.get('message', '执行失败')),
                'screenshot': step_result.get('screenshot', ''),
                'healed': step_result.get('healed', False),
                'original_locator': step_result.get('original_locator'),
                'suggested_locator': step_result.get('suggested_locator'),
                'confidence': step_result.get('confidence', 0),
            })

        # 耗时分布
        duration_ranges = {
            '0-100ms': 0,
            '100-500ms': 0,
            '500-1000ms': 0,
            '1000-3000ms': 0,
            '3000ms+': 0
        }
        for step in executed_steps:
            duration = step.get('duration', 0)
            if duration < 100:
                duration_ranges['0-100ms'] += 1
            elif duration < 500:
                duration_ranges['100-500ms'] += 1
            elif duration < 1000:
                duration_ranges['500-1000ms'] += 1
            elif duration < 3000:
                duration_ranges['1000-3000ms'] += 1
            else:
                duration_ranges['3000ms+'] += 1

        # 失败原因分析
        failure_reasons = {}
        for step in executed_steps:
            if not step.get('success'):
                # 使用 message 字段获取错误信息
                error = step.get('message', 'Unknown error')
                failure_reasons[error] = failure_reasons.get(error, 0) + 1

        failure_analysis = [
            {
                'reason': k,
                'count': v,
                'suggestion': self._get_suggestion_for_error(k)
            }
            for k, v in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)
        ]

        return {
            'trend': trend_data,
            'distribution': [
                {'range': k, 'count': v} for k, v in duration_ranges.items()
            ],
            'failure_analysis': failure_analysis
        }

    def _generate_plan_charts_data(self) -> dict:
        """生成计划执行的图表数据"""
        children = self.execution.children.all()

        # 脚本执行趋势数据
        script_data = []
        for child in children:
            result = child.result or {}
            steps = result.get('steps', [])

            # 获取错误原因
            error_reason = ''
            if child.status == 'failed':
                # 找到第一个失败的步骤
                for step in steps:
                    if not step.get('success'):
                        error_reason = f"步骤 {step.get('step_index', 0) + 1} [{step.get('name', '未知步骤')}]: {step.get('message', '未知错误')}"
                        break
                if not error_reason:
                    error_reason = result.get('message', '') or result.get('error', '执行失败')

            script_data.append({
                'id': child.id,
                'execution_id': child.id,
                'name': child.script.name if child.script else f'Script {child.id}',
                'status': child.status,
                'duration': child.duration or 0,
                'success': child.status == 'completed',
                'error_reason': error_reason,
                'total_count': child.total_count or len(steps),
                'passed_count': child.passed_count or sum(1 for s in steps if s.get('success')),
                'failed_count': child.failed_count or sum(1 for s in steps if not s.get('success'))
            })

        # 状态分布
        status_distribution = {
            'completed': children.filter(status='completed').count(),
            'failed': children.filter(status='failed').count(),
            'running': children.filter(status='running').count(),
            'pending': children.filter(status='pending').count()
        }

        # 失败脚本分析
        failed_scripts = []
        for child in children.filter(status='failed'):
            result = child.result or {}
            steps = result.get('steps', [])

            # 找到第一个失败的步骤
            failed_step = None
            for step in steps:
                if not step.get('success'):
                    failed_step = step
                    break

            # 构建详细失败原因
            if failed_step:
                error_msg = failed_step.get('message', '未知错误')
                reason = f"步骤 {failed_step.get('step_index', 0) + 1} [{failed_step.get('name', '未知步骤')}] 失败: {error_msg}"
                suggestion = self._get_suggestion_for_error(error_msg)
            else:
                error_msg = result.get('message', '') or result.get('error', '执行失败')
                reason = error_msg
                suggestion = self._get_suggestion_for_error(error_msg)

            failed_scripts.append({
                'name': child.script.name if child.script else f'Script {child.id}',
                'execution_id': child.id,
                'reason': reason,
                'suggestion': suggestion,
                'failed_step_name': failed_step.get('name') if failed_step else None,
                'failed_step_type': failed_step.get('type') if failed_step else None
            })

        return {
            'scripts': script_data,
            'status_distribution': [
                {'status': k, 'count': v} for k, v in status_distribution.items()
            ],
            'failed_scripts': failed_scripts
        }

    def _generate_html_report(self) -> str:
        """生成HTML报告"""
        os.makedirs(self.report_dir, exist_ok=True)

        filename = f'report_{self.execution.id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
        filepath = os.path.join(self.report_dir, filename)

        # 如果是计划执行记录，生成计划报告
        if self.execution.execution_type == 'plan':
            html_content = self._render_plan_template()
        else:
            # 准备模板数据
            template_data = {
                'execution': self.execution,
                'summary': self._generate_summary(),
                'steps': (self.execution.result or {}).get('steps', []),
                'logs': (self.execution.result or {}).get('logs', []),
                'screenshots': (self.execution.result or {}).get('screenshots', []),
                'charts_data': self._generate_charts_data(),
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            html_content = self._render_template(template_data)

        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return filepath

    def generate_pdf(self) -> str:
        """生成PDF报告"""
        try:
            from weasyprint import HTML, CSS

            # 生成HTML内容
            template_data = {
                'execution': self.execution,
                'summary': self._generate_summary(),
                'steps': (self.execution.result or {}).get('steps', []),
                'logs': (self.execution.result or {}).get('logs', []),
                'screenshots': (self.execution.result or {}).get('screenshots', []),
                'charts_data': self._generate_charts_data(),
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            html_content = self._render_template(template_data)

            # 生成PDF文件路径
            os.makedirs(self.report_dir, exist_ok=True)
            filename = f'report_{self.execution.id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            pdf_path = os.path.join(self.report_dir, filename)

            # 使用 weasyprint 生成 PDF
            HTML(string=html_content).write_pdf(pdf_path)

            return pdf_path

        except ImportError:
            raise Exception("PDF生成需要安装 weasyprint 库。请运行: pip install weasyprint")
        except Exception as e:
            raise Exception(f"PDF生成失败: {str(e)}")

    def _render_template(self, data: dict) -> str:
        """渲染HTML模板"""
        template_html = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告 - {{ summary.script_name }}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px 8px 0 0;
        }
        .header h1 { margin-bottom: 10px; }
        .meta { opacity: 0.9; }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
        }
        .card {
            background: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .card .label { color: #666; margin-bottom: 8px; }
        .card .value { font-size: 32px; font-weight: bold; }
        .card.passed .value { color: #52c41a; }
        .card.failed .value { color: #f5222d; }
        .card.rate .value { color: #1890ff; }
        .section {
            padding: 30px;
            border-top: 1px solid #eee;
        }
        .section h2 {
            margin-bottom: 20px;
            color: #333;
        }
        .chart-container {
            height: 400px;
            margin: 20px 0;
        }
        .steps-table {
            width: 100%;
            border-collapse: collapse;
        }
        .steps-table th, .steps-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        .steps-table th {
            background: #fafafa;
            font-weight: 600;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }
        .status-badge.success { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
        .status-badge.failed { background: #fff2f0; color: #f5222d; border: 1px solid #ffccc7; }
        .error-msg { color: #f5222d; font-size: 12px; margin-top: 4px; }
        .screenshot {
            max-width: 300px;
            border-radius: 4px;
            cursor: pointer;
        }
        .log-entry {
            padding: 8px;
            border-left: 3px solid #ddd;
            margin-bottom: 8px;
            font-family: monospace;
            font-size: 12px;
        }
        .log-entry.info { border-left-color: #1890ff; }
        .log-entry.error { border-left-color: #f5222d; }
        .footer {
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>测试报告 - {{ summary.script_name }}</h1>
            <div class="meta">
                执行ID: #{{ execution.id }} |
                开始时间: {{ summary.started_at }} |
                完成时间: {{ summary.completed_at }}
            </div>
        </div>

        <div class="summary">
            <div class="card">
                <div class="label">总用例数</div>
                <div class="value">{{ summary.total }}</div>
            </div>
            <div class="card passed">
                <div class="label">通过数</div>
                <div class="value">{{ summary.passed }}</div>
            </div>
            <div class="card failed">
                <div class="label">失败数</div>
                <div class="value">{{ summary.failed }}</div>
            </div>
            <div class="card rate">
                <div class="label">通过率</div>
                <div class="value">{{ summary.pass_rate }}%</div>
            </div>
            <div class="card">
                <div class="label">总耗时</div>
                <div class="value">{{ summary.total_duration }}s</div>
            </div>
        </div>

        <div class="section">
            <h2>测试趋势</h2>
            <div id="trendChart" class="chart-container"></div>
        </div>

        <div class="section">
            <h2>耗时分布</h2>
            <div id="durationChart" class="chart-container"></div>
        </div>

        {% if charts_data.failure_analysis %}
        <div class="section">
            <h2>失败原因分析</h2>
            <div id="failureChart" class="chart-container"></div>
            <div style="margin-top: 20px;">
                <h3 style="margin-bottom: 15px;">修复建议</h3>
                {% for item in charts_data.failure_analysis %}
                <div style="background: #fff7e6; padding: 12px; margin-bottom: 10px; border-left: 4px solid #fa8c16; border-radius: 4px;">
                    <div style="font-weight: 600; color: #d46b08; margin-bottom: 6px;">
                        {{ item.reason }} (出现 {{ item.count }} 次)
                    </div>
                    <div style="color: #8c8c8c; font-size: 14px; line-height: 1.6;">
                        💡 建议: {{ item.suggestion }}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <div class="section">
            <h2>步骤详情</h2>
            <table class="steps-table">
                <thead>
                    <tr>
                        <th width="60">序号</th>
                        <th width="150">步骤名称</th>
                        <th width="100">类型</th>
                        <th width="80">状态</th>
                        <th width="100">耗时</th>
                        <th>详情/错误</th>
                    </tr>
                </thead>
                <tbody>
                    {% for step in steps %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td>{{ step.name }}</td>
                        <td>{{ step.type }}</td>
                        <td>
                            {% if step.success %}
                            <span class="status-badge success">通过</span>
                            {% else %}
                            <span class="status-badge failed">失败</span>
                            {% endif %}
                        </td>
                        <td>{{ step.duration }}ms</td>
                        <td>
                            {{ step.message }}
                            {% if step.error %}
                            <div class="error-msg">{{ step.error }}</div>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        {% if logs %}
        <div class="section">
            <h2>执行日志</h2>
            {% for log in logs %}
            <div class="log-entry {{ log.level }}">{{ log.timestamp }} [{{ log.level.upper() }}] Step {{ log.step }}: {{ log.message }}</div>
            {% endfor %}
        </div>
        {% endif %}

        <div class="footer">
            报告生成时间: {{ generated_at }} | 自动化测试平台
        </div>
    </div>

    <script>
        // 趋势图
        const trendChart = echarts.init(document.getElementById('trendChart'));
        trendChart.setOption({
            title: { text: '步骤执行趋势' },
            tooltip: { trigger: 'axis' },
            xAxis: {
                type: 'category',
                data: {{ charts_data.trend | map(attribute='name') | list | tojson }},
                axisLabel: { rotate: 45 }
            },
            yAxis: { type: 'value', name: '耗时 (ms)' },
            series: [{
                name: '耗时',
                type: 'line',
                data: {{ charts_data.trend | map(attribute='duration') | list | tojson }},
                itemStyle: {
                    color: function(params) {
                        return {{ charts_data.trend | map(attribute='success') | list | tojson }}[params.dataIndex] ? '#52c41a' : '#f5222d';
                    }
                }
            }]
        });

        // 耗时分布图
        const durationChart = echarts.init(document.getElementById('durationChart'));
        durationChart.setOption({
            title: { text: '耗时分布' },
            tooltip: { trigger: 'item' },
            xAxis: { type: 'category', data: {{ charts_data.distribution | map(attribute='range') | list | tojson }} },
            yAxis: { type: 'value', name: '步骤数' },
            series: [{
                type: 'bar',
                data: {{ charts_data.distribution | map(attribute='count') | list | tojson }},
                itemStyle: { color: '#1890ff' }
            }]
        });

        {% if charts_data.failure_analysis %}
        // 失败原因图
        const failureChart = echarts.init(document.getElementById('failureChart'));
        failureChart.setOption({
            title: { text: '失败原因分析' },
            tooltip: { trigger: 'item' },
            series: [{
                type: 'pie',
                radius: '60%',
                data: {{ charts_data.failure_analysis | tojson }},
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowOffsetX: 0,
                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }]
        });
        {% endif %}
    </script>
</body>
</html>
        '''

        # 使用Jinja2渲染
        template = Template(template_html)
        return template.render(**data)

    def _render_plan_template(self) -> str:
        """渲染计划执行的HTML模板"""
        summary = self._generate_summary()
        charts_data = self._generate_charts_data()
        children = self.execution.children.all()

        template_html = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告 - {{ summary.plan_name }}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px 8px 0 0;
        }
        .header h1 { margin-bottom: 10px; }
        .meta { opacity: 0.9; }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
        }
        .card {
            background: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .card .label { color: #666; margin-bottom: 8px; }
        .card .value { font-size: 32px; font-weight: bold; }
        .card.passed .value { color: #52c41a; }
        .card.failed .value { color: #f5222d; }
        .card.rate .value { color: #1890ff; }
        .section {
            padding: 30px;
            border-top: 1px solid #eee;
        }
        .section h2 {
            margin-bottom: 20px;
            color: #333;
        }
        .chart-container {
            height: 400px;
            margin: 20px 0;
        }
        .scripts-table {
            width: 100%;
            border-collapse: collapse;
        }
        .scripts-table th, .scripts-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        .scripts-table th {
            background: #fafafa;
            font-weight: 600;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }
        .status-badge.completed { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
        .status-badge.failed { background: #fff2f0; color: #f5222d; border: 1px solid #ffccc7; }
        .status-badge.running { background: #e6f7ff; color: #1890ff; border: 1px solid #91d5ff; }
        .status-badge.pending { background: #fafafa; color: #8c8c8c; border: 1px solid #d9d9d9; }
        .error-text { color: #f5222d; font-size: 12px; }
        .error-detail { color: #f5222d; font-size: 12px; max-width: 300px; word-break: break-word; }
        .footer {
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>测试计划报告 - {{ summary.plan_name }}</h1>
            <div class="meta">
                执行ID: #{{ execution.id }} |
                开始时间: {{ summary.started_at }} |
                完成时间: {{ summary.completed_at }}
            </div>
        </div>

        <div class="summary">
            <div class="card">
                <div class="label">脚本总数</div>
                <div class="value">{{ summary.total_scripts }}</div>
            </div>
            <div class="card">
                <div class="label">总用例数</div>
                <div class="value">{{ summary.total_cases }}</div>
            </div>
            <div class="card passed">
                <div class="label">通过数</div>
                <div class="value">{{ summary.passed }}</div>
            </div>
            <div class="card failed">
                <div class="label">失败数</div>
                <div class="value">{{ summary.failed }}</div>
            </div>
            <div class="card rate">
                <div class="label">通过率</div>
                <div class="value">{{ summary.pass_rate }}%</div>
            </div>
            <div class="card">
                <div class="label">总耗时</div>
                <div class="value">{{ summary.total_duration }}s</div>
            </div>
        </div>

        <div class="section">
            <h2>脚本状态分布</h2>
            <div id="statusChart" class="chart-container"></div>
        </div>

        <div class="section">
            <h2>脚本执行详情</h2>
            <table class="scripts-table">
                <thead>
                    <tr>
                        <th width="60">ID</th>
                        <th width="200">脚本名称</th>
                        <th width="100">状态</th>
                        <th width="100">用例总数</th>
                        <th width="100">通过数</th>
                        <th width="100">失败数</th>
                        <th width="100">耗时(秒)</th>
                        <th width="300">失败原因</th>
                    </tr>
                </thead>
                <tbody>
                    {% for script in charts_data.scripts %}
                    <tr>
                        <td>{{ script.id }}</td>
                        <td>{{ script.name }}</td>
                        <td>
                            <span class="status-badge {{ script.status }}">{{ script.status|upper }}</span>
                        </td>
                        <td>{{ script.total_count }}</td>
                        <td style="color: #52c41a;">{{ script.passed_count }}</td>
                        <td style="color: #f5222d;">{{ script.failed_count }}</td>
                        <td>{{ script.duration }}</td>
                        <td style="color: #f5222d; font-size: 12px;">{{ script.error_reason if script.error_reason else '-' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        {% if charts_data.failed_scripts %}
        <div class="section">
            <h2>失败脚本详情</h2>
            <table class="scripts-table">
                <thead>
                    <tr>
                        <th width="200">脚本名称</th>
                        <th width="400">失败原因</th>
                        <th width="600">修复建议</th>
                    </tr>
                </thead>
                <tbody>
                    {% for script in charts_data.failed_scripts %}
                    <tr>
                        <td>{{ script.name }}</td>
                        <td style="color: #f5222d;">{{ script.reason }}</td>
                        <td style="color: #8c8c8c; font-size: 13px;">💡 {{ script.suggestion }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        <div class="footer">
            报告生成时间: {{ generated_at }} | 自动化测试平台
        </div>
    </div>

    <script>
        // 状态分布图
        const statusChart = echarts.init(document.getElementById('statusChart'));
        statusChart.setOption({
            title: { text: '脚本状态分布' },
            tooltip: { trigger: 'item' },
            series: [{
                type: 'pie',
                radius: '60%',
                data: {{ charts_data.status_distribution | tojson }},
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowOffsetX: 0,
                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }]
        });
    </script>
</body>
</html>
        '''

        # 使用Jinja2渲染
        template = Template(template_html)
        return template.render(
            execution=self.execution,
            summary=summary,
            charts_data=charts_data,
            generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
