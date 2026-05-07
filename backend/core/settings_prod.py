"""
生产环境配置 - 部署到服务器时使用
"""

import os
from pathlib import Path
from .settings import *

# 生产环境必须关闭 DEBUG
DEBUG = False

# 安全密钥 - 从环境变量读取，部署时必须设置
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("生产环境必须设置 DJANGO_SECRET_KEY 环境变量")

# 允许的主机 - 部署时修改为实际域名
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    ALLOWED_HOSTS = ['your-domain.com']  # 修改为实际域名

# CORS 配置 - 部署时修改为实际前端域名
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')
if not CORS_ALLOWED_ORIGINS or CORS_ALLOWED_ORIGINS == ['']:
    CORS_ALLOWED_ORIGINS = ['https://your-frontend-domain.com']  # 修改为实际域名

CORS_ALLOW_CREDENTIALS = True

# CSRF 配置 - 部署时修改为实际域名
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')
if not CSRF_TRUSTED_ORIGINS or CSRF_TRUSTED_ORIGINS == ['']:
    CSRF_TRUSTED_ORIGINS = ['https://your-domain.com']  # 修改为实际域名

# 数据库配置 - 从主 settings.py 继承 (通过 DB_ENGINE 环境变量控制)
# 如果需要生产环境专用数据库配置，取消下方注释即可覆盖
# DATABASE_ENGINE = os.getenv('DB_ENGINE', 'postgresql')
# if DATABASE_ENGINE == 'postgresql':
#     DATABASES = {
#         'default': {
#             'ENGINE': 'django.db.backends.postgresql',
#             'NAME': os.getenv('DB_NAME', 'auto_test_platform'),
#             'USER': os.getenv('DB_USER', 'postgres'),
#             'PASSWORD': os.getenv('DB_PASSWORD', ''),
#             'HOST': os.getenv('DB_HOST', 'localhost'),
#             'PORT': os.getenv('DB_PORT', '5432'),
#         }
#     }

# 静态文件收集 - 生产环境需要
STATIC_ROOT = BASE_DIR / 'staticfiles'

# 媒体文件存储 - 可配置为云存储
MEDIA_ROOT = BASE_DIR / 'media'

# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# 创建日志目录
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# 安全设置
SECURE_SSL_REDIRECT = True  # 强制 HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Selenium/Playwright 驱动路径（如需要）
SELENIUM_DRIVER_PATH = os.getenv('SELENIUM_DRIVER_PATH', '')
PLAYWRIGHT_DRIVER_PATH = os.getenv('PLAYWRIGHT_DRIVER_PATH', '')
