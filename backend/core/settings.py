"""
Django settings for auto test platform project.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY') or os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# 生产环境密钥安全检查
if not DEBUG:
    if not os.getenv('DJANGO_SECRET_KEY') and not os.getenv('SECRET_KEY'):
        raise ValueError(
            "生产环境必须设置 DJANGO_SECRET_KEY 或 SECRET_KEY 环境变量！"
        )
    if SECRET_KEY.startswith('django-insecure-'):
        raise ValueError(
            "生产环境不能使用默认的insecure密钥！请设置安全的SECRET_KEY。"
        )
    if len(SECRET_KEY) < 32:
        raise ValueError(
            "SECRET_KEY 长度必须至少32个字符！"
        )

# Allowed hosts - 支持从环境变量读取，用逗号分隔
ALLOWED_HOSTS_ENV = os.getenv('DJANGO_ALLOWED_HOSTS', '*')
if ALLOWED_HOSTS_ENV == '*':
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS_ENV.split(',')]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'channels',
    'apps.users',
    'apps.projects',
    'apps.plans',
    'apps.scripts',
    'apps.executions',
    'apps.executors',
    'apps.reports',
    'apps.drivers',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'core.middleware.DisableCSRFMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': Path('/app/db/db.sqlite3'),  # 使用持久化卷目录
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# CORS settings - 支持从环境变量读取
CORS_ALLOWED_ORIGINS_ENV = os.getenv('CORS_ALLOWED_ORIGINS', '')
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://localhost:3000',
    'http://127.0.0.1:5173',
    'http://127.0.0.1:3000',
]
if CORS_ALLOWED_ORIGINS_ENV:
    CORS_ALLOWED_ORIGINS.extend([o.strip() for o in CORS_ALLOWED_ORIGINS_ENV.split(',')])
CORS_ALLOW_CREDENTIALS = True

# CSRF settings
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False

# Custom user model
AUTH_USER_MODEL = 'users.User'

# Report settings
REPORTS_ROOT = BASE_DIR / 'reports'
SCREENSHOTS_ROOT = MEDIA_ROOT / 'screenshots'

# Create directories if they don't exist
os.makedirs(REPORTS_ROOT, exist_ok=True)
os.makedirs(SCREENSHOTS_ROOT, exist_ok=True)

# Channels settings
ASGI_APPLICATION = 'core.asgi.application'

# Channel层配置 - 使用Redis支持多进程部署
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(os.getenv('REDIS_HOST', '127.0.0.1'), int(os.getenv('REDIS_PORT', 6379)))],
        },
    },
}

# RabbitMQ settings
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', '127.0.0.1')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'guest')
RABBITMQ_VHOST = os.getenv('RABBITMQ_VHOST', '/')

# RabbitMQ密码加密密钥（生产环境必须设置）
RABBITMQ_ENCRYPTION_KEY = os.getenv('RABBITMQ_ENCRYPTION_KEY')
if not RABBITMQ_ENCRYPTION_KEY:
    # 开发环境使用默认密钥（生产环境必须设置）
    if DEBUG:
        # 生成一个新的Fernet密钥作为开发环境默认值
        RABBITMQ_ENCRYPTION_KEY = 'KI0HBM0qO18jJvi06PWPxS7rqYCbu17BOisPeKWPEOo='
    else:
        raise ValueError(
            "生产环境必须设置 RABBITMQ_ENCRYPTION_KEY 环境变量！\n"
            "生成密钥命令: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

# Session settings - 使用文件存储以避免容器重启导致session丢失
SESSION_ENGINE = 'django.contrib.sessions.backends.file'
SESSION_FILE_PATH = BASE_DIR / 'sessions'
os.makedirs(SESSION_FILE_PATH, exist_ok=True)
SESSION_COOKIE_AGE = 86400  # 24小时
SESSION_SAVE_EVERY_REQUEST = True  # 每次请求都保存session
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True
