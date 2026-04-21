# ============================================
# 生产环境 Docker 执行器
# 基于 Playwright 官方镜像，预装 Chromium 依赖
# ============================================

FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir playwright && \
    playwright install chromium && \
    playwright install-deps chromium && \
    # 清理安装缓存
    pip cache purge && \
    rm -rf /tmp/* /var/cache/apt/*

# 创建非 root 用户和必要目录
RUN groupadd -r executor && useradd -r -g executor -d /app executor && \
    mkdir -p /app/traces /app/logs && \
    chown -R executor:executor /app

# 启动脚本：确保卷挂载目录有正确权限后再启动主进程
COPY --chown=executor:executor entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER executor

# 复制源码
COPY --chown=executor:executor . .

# 默认环境变量
ENV BACKEND_URL=http://backend:8000 \
    RABBITMQ_HOST=rabbitmq \
    RABBITMQ_PORT=5672 \
    RABBITMQ_USER=guest \
    RABBITMQ_PASSWORD=guest \
    PLAYWRIGHT_HEADLESS=true \
    TRACE_ENABLED=true \
    MAX_CONCURRENT=2 \
    HEARTBEAT_INTERVAL=30

ENTRYPOINT ["/app/entrypoint.sh"]
