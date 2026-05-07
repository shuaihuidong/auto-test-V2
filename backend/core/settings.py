"""
Django settings for auto test platform project.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load local environment variables when present.
# Existing process environment values still win.
load_dotenv(BASE_DIR.parent / '.env')
load_dotenv(BASE_DIR / '.env')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY') or os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# Production secret key checks.
if not DEBUG:
    if not os.getenv('DJANGO_SECRET_KEY') and not os.getenv('SECRET_KEY'):
        raise ValueError(
            "Production requires DJANGO_SECRET_KEY or SECRET_KEY to be set."
        )
    if SECRET_KEY.startswith('django-insecure-'):
        raise ValueError(
            "Production cannot use the default insecure secret key. Set a secure SECRET_KEY."
        )
    if len(SECRET_KEY) < 32:
        raise ValueError(
            "SECRET_KEY must be at least 32 characters long."
        )

# Allowed hosts can be overridden with a comma-separated environment variable.
ALLOWED_HOSTS_ENV = os.getenv('DJANGO_ALLOWED_HOSTS', '*')
if ALLOWED_HOSTS_ENV == '*':
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS_ENV.split(',')]

SETTINGS_MODULE = os.getenv('DJANGO_SETTINGS_MODULE', '')
if not DEBUG and ALLOWED_HOSTS == ['*'] and not SETTINGS_MODULE.endswith('settings_prod'):
    raise ValueError(
        "Production requires DJANGO_ALLOWED_HOSTS to be set and cannot use '*' as a wildcard."
    )

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
    'apps.scheduler',
    'apps.executors',  # Kept for WebSocket routing only
    'apps.reports',
    'apps.drivers',
    'apps.settings',
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

# Database - 鏀寔 DB_ENGINE 鐜鍙橀噺鍔ㄦ€佸垏鎹?
DB_ENGINE = os.getenv('DB_ENGINE', 'sqlite3').lower()

if DB_ENGINE == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'auto_test_platform'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }
elif DB_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('DB_NAME', 'auto_test_platform'),
            'USER': os.getenv('DB_USER', 'root'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '3306'),
        }
    }
else:
    # SQLite (榛樿)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': Path(os.getenv('DB_PATH', '/app/db/db.sqlite3')),  # 鏈湴娴嬭瘯: DB_PATH=db/db.sqlite3
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

# CORS settings - 鏀寔浠庣幆澧冨彉閲忚鍙?
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

# Channel layer config.
# Local mode can switch to in-memory transport to avoid requiring Redis.
CHANNEL_LAYER_BACKEND = os.getenv('CHANNEL_LAYER_BACKEND', 'redis').lower()
if CHANNEL_LAYER_BACKEND == 'inmemory':
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [(os.getenv('REDIS_HOST', '127.0.0.1'), int(os.getenv('REDIS_PORT', 6379)))],
            },
        },
    }

# Session settings - use file storage to avoid losing sessions on restart
SESSION_ENGINE = 'django.contrib.sessions.backends.file'
SESSION_FILE_PATH = BASE_DIR / 'sessions'
os.makedirs(SESSION_FILE_PATH, exist_ok=True)
SESSION_COOKIE_AGE = 86400  # 24灏忔椂
SESSION_SAVE_EVERY_REQUEST = True  # 姣忔璇锋眰閮戒繚瀛榮ession
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True

# ============================================
# AI Service 閰嶇疆 (V2.0 LLM Gateway)
# ============================================
AI_SERVICE = {
    # Provider 閫夋嫨
    'PRIMARY_PROVIDER': os.getenv('AI_PRIMARY_PROVIDER', 'openai'),
    'FALLBACK_PROVIDER': os.getenv('AI_FALLBACK_PROVIDER', 'qwen'),

    # OpenAI 鍏煎閰嶇疆锛堜篃閫傜敤浜?DeepSeek 绛夊吋瀹规帴鍙ｏ級
    'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', ''),
    'OPENAI_API_BASE': os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1'),
    'OPENAI_MODEL': os.getenv('OPENAI_MODEL', 'gpt-4o'),

    # 閫氫箟鍗冮棶閰嶇疆
    'QWEN_API_KEY': os.getenv('QWEN_API_KEY', ''),
    'QWEN_MODEL': os.getenv('QWEN_MODEL', 'qwen-max'),

    # 閫氱敤鍙傛暟
    'MAX_RETRIES': int(os.getenv('AI_MAX_RETRIES', '3')),
    'RETRY_BASE_DELAY': float(os.getenv('AI_RETRY_BASE_DELAY', '1.0')),
    'TIMEOUT': int(os.getenv('AI_TIMEOUT', '60')),
    'DEFAULT_MAX_TOKENS': int(os.getenv('AI_DEFAULT_MAX_TOKENS', '4096')),
}

# ============================================
# 鎵ц寮曟搸閰嶇疆 (杞婚噺鍖栨墽琛屽紩鎿?
# ============================================
EXECUTION_RUNNER = {
    # 鏈€澶у悓鏃舵墽琛岀殑鑴氭湰鏁帮紙鍗冲悓鏃跺惎鍔ㄧ殑 Playwright 娴忚鍣ㄥ疄渚嬫暟锛?
    # 寤鸿鍊硷細鏈嶅姟鍣?4GB 鍐呭瓨 鈫?3锛?GB 鈫?5锛?6GB 鈫?8
    # 鐜鍙橀噺 MAX_CONCURRENT_EXECUTIONS 鍙鐩栨鍊?
    'max_workers': int(os.getenv('MAX_CONCURRENT_EXECUTIONS', '3')),
}

# ============================================
# 瀛樺偍閰嶇疆 (V2.0 Trace 鎸佷箙鍖?
# ============================================
STORAGE_BACKEND = {
    'TYPE': os.getenv('STORAGE_TYPE', 'local'),  # local | minio
    'MINIO_ENDPOINT': os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
    'MINIO_ACCESS_KEY': os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
    'MINIO_SECRET_KEY': os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
    'MINIO_BUCKET': os.getenv('MINIO_BUCKET', 'auto-test-traces'),
    'MINIO_SECURE': os.getenv('MINIO_SECURE', 'false').lower() == 'true',
}
