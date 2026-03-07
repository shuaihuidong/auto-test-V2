from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Report
from .serializers import ReportSerializer, ChartDataSerializer
from .generators import ReportGenerator
import os


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['execution']
    search_fields = ['execution__plan__name', 'execution__script__name']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """获取查询集 - 根据用户权限返回报告"""
        queryset = Report.objects.select_related('execution').all()
        user = self.request.user

        # 管理员和超级管理员可以看到所有报告
        if user.role not in ['admin', 'super_admin']:
            queryset = queryset.filter(execution__created_by=user)

        return queryset
        user = self.request.user
        if user.role not in ['admin', 'super_admin']:
            queryset = queryset.filter(execution__created_by=user)

        return queryset

    @action(detail=True, methods=['get'])
    def html(self, request, pk=None):
        """下载HTML报告"""
        report = self.get_object()
        if not report.html_report or not os.path.exists(report.html_report):
            return Response({'error': 'HTML报告不存在'}, status=404)

        from django.http import FileResponse
        return FileResponse(
            open(report.html_report, 'rb'),
            content_type='text/html',
            filename=f'report_{report.execution_id}.html'
        )

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """下载PDF报告"""
        report = self.get_object()

        # 如果PDF不存在，尝试生成
        pdf_path = getattr(report, 'pdf_report', None)
        if not pdf_path or not os.path.exists(pdf_path):
            try:
                from .generators import ReportGenerator
                generator = ReportGenerator(report.execution)
                pdf_path = generator.generate_pdf()
                # 保存PDF路径到报告
                report.pdf_report = pdf_path
                report.save()
            except Exception as e:
                return Response({'error': f'PDF生成失败: {str(e)}'}, status=500)

        from django.http import FileResponse
        return FileResponse(
            open(pdf_path, 'rb'),
            content_type='application/pdf',
            filename=f'report_{report.execution_id}.pdf'
        )

    @action(detail=False, methods=['get'])
    def charts(self, request):
        """获取图表统计数据"""
        # 获取最近30天的执行数据
        from django.db.models import Count
        from apps.executions.models import Execution
        from django.utils import timezone
        from datetime import timedelta

        thirty_days_ago = timezone.now() - timedelta(days=30)
        executions = Execution.objects.filter(
            created_at__gte=thirty_days_ago,
            status__in=['completed', 'failed']
        )

        # 通过率趋势
        trend_data = []
        for i in range(30):
            date = thirty_days_ago + timedelta(days=i)
            day_executions = executions.filter(
                created_at__date=date.date()
            )
            total = day_executions.count()
            passed = day_executions.filter(status='completed').count()
            trend_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'total': total,
                'passed': passed,
                'pass_rate': round(passed / total * 100, 2) if total > 0 else 0
            })

        # 耗时分布
        duration_data = [
            {'range': '0-30s', 'count': 0},
            {'range': '30-60s', 'count': 0},
            {'range': '60-120s', 'count': 0},
            {'range': '120s+', 'count': 0}
        ]
        for exec in executions:
            duration = exec.duration
            if duration <= 30:
                duration_data[0]['count'] += 1
            elif duration <= 60:
                duration_data[1]['count'] += 1
            elif duration <= 120:
                duration_data[2]['count'] += 1
            else:
                duration_data[3]['count'] += 1

        # 失败原因分析
        failed_executions = executions.filter(status='failed')
        failure_reasons = {}
        for exec in failed_executions:
            result = exec.result or {}
            error = result.get('error', '未知错误')
            failure_reasons[error] = failure_reasons.get(error, 0) + 1

        failure_analysis = [
            {'reason': k, 'count': v}
            for k, v in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)
        ]

        return Response({
            'trend': trend_data,
            'distribution': duration_data,
            'failure_analysis': failure_analysis
        })

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """手动生成报告"""
        execution_id = request.data.get('execution_id')
        if not execution_id:
            return Response({'error': '请提供execution_id'}, status=400)

        from apps.executions.models import Execution
        try:
            execution = Execution.objects.get(id=execution_id)
        except Execution.DoesNotExist:
            return Response({'error': '执行记录不存在'}, status=404)

        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"开始生成报告 - execution_id={execution_id}, execution_type={execution.execution_type}")

        # 如果报告已存在，先删除旧的报告
        from .models import Report
        existing_reports = Report.objects.filter(execution=execution)
        if existing_reports.exists():
            logger.info(f"删除旧的报告: {existing_reports.count()} 条")
            existing_reports.delete()

        generator = ReportGenerator(execution)
        report = generator.generate()

        logger.info(f"报告生成完成 - report_id={report.id}, summary_keys={list(report.summary.keys()) if report.summary else []}, charts_keys={list(report.charts_data.keys()) if report.charts_data else []}")

        return Response(ReportSerializer(report).data)

    @action(detail=False, methods=['get'])
    def trend_analysis(self, request):
        """获取历史趋势数据"""
        from apps.executions.models import Execution
        from datetime import timedelta

        script_id = request.query_params.get('script_id')
        project_id = request.query_params.get('project_id')
        days = int(request.query_params.get('days', 30))

        # 构建查询
        queryset = Execution.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=days),
            status__in=['completed', 'failed']
        )

        if script_id:
            queryset = queryset.filter(script_id=script_id)
        elif project_id:
            queryset = queryset.filter(script__project_id=project_id)
        else:
            return Response({'error': '请提供 script_id 或 project_id'}, status=400)

        queryset = queryset.order_by('created_at')

        # 生成趋势数据
        trend_data = []
        for execution in queryset:
            result = execution.result or {}
            trend_data.append({
                'execution_id': execution.id,
                'date': execution.created_at.date().isoformat(),
                'time': execution.created_at.strftime('%H:%M:%S'),
                'status': execution.status,
                'pass_rate': execution.calculate_pass_rate() if hasattr(execution, 'calculate_pass_rate') else 0,
                'total': result.get('total', 0),
                'passed': result.get('passed', 0),
                'failed': result.get('failed', 0),
                'duration': execution.duration
            })

        # 计算汇总统计
        if trend_data:
            avg_pass_rate = sum(d['pass_rate'] for d in trend_data) / len(trend_data)
            avg_duration = sum(d['duration'] for d in trend_data) / len(trend_data)
            total_executions = len(trend_data)
            successful_executions = sum(1 for d in trend_data if d['status'] == 'completed')
        else:
            avg_pass_rate = 0
            avg_duration = 0
            total_executions = 0
            successful_executions = 0

        return Response({
            'trend': trend_data,
            'summary': {
                'total_executions': total_executions,
                'successful_executions': successful_executions,
                'avg_pass_rate': round(avg_pass_rate, 2),
                'avg_duration': round(avg_duration, 2)
            }
        })
