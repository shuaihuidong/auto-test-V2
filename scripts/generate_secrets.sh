#!/usr/bin/env bash
# ============================================
# generate_secrets.sh - 自动生成安全密钥
# ============================================
# 用法:
#   ./scripts/generate_secrets.sh           # 生成缺失的密钥
#   ./scripts/generate_secrets.sh --force   # 强制重新生成所有密钥
#
# 输出: .env 文件 (在项目根目录)
# ============================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# 解析参数
FORCE=false
for arg in "$@"; do
    case $arg in
        --force|-f) FORCE=true ;;
        --help|-h)
            echo "用法: $0 [--force]"
            echo ""
            echo "选项:"
            echo "  --force, -f    强制重新生成所有密钥 (覆盖已有值)"
            echo "  --help,  -h    显示帮助信息"
            exit 0
            ;;
        *) error "未知参数: $arg" ;;
    esac
done

# ---- 工具函数 ----

# 生成 Django Secret Key
generate_django_secret() {
    python3 -c "
import secrets, string
chars = string.ascii_letters + string.digits + string.punctuation
print(''.join(secrets.choice(chars) for _ in range(50)))
" 2>/dev/null || python -c "
import secrets, string
chars = string.ascii_letters + string.digits + string.punctuation
print(''.join(secrets.choice(chars) for _ in range(50)))
" 2>/dev/null || openssl rand -base64 48 | tr -d '\n'
}

# 生成 Fernet 加密密钥
generate_fernet_key() {
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || \
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || \
    openssl rand -base64 32 | tr -d '\n'
}

# 生成随机密码
generate_password() {
    python3 -c "
import secrets, string
chars = string.ascii_letters + string.digits
print(''.join(secrets.choice(chars) for _ in range(24)))
" 2>/dev/null || python -c "
import secrets, string
chars = string.ascii_letters + string.digits
print(''.join(secrets.choice(chars) for _ in range(24)))
" 2>/dev/null || openssl rand -base64 24 | tr -d '=/+' | tr -d '\n'
}

# 从 .env 文件读取值
get_env_value() {
    local key="$1"
    if [ -f "$ENV_FILE" ]; then
        grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d'=' -f2-
    fi
}

# 设置 .env 文件中的值
set_env_value() {
    local key="$1"
    local value="$2"

    if [ ! -f "$ENV_FILE" ]; then
        echo "$key=$value" > "$ENV_FILE"
        return
    fi

    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        # 替换已有值
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
        else
            sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
        fi
    else
        # 追加新值
        echo "$key=$value" >> "$ENV_FILE"
    fi
}

# ---- 主流程 ----

info "Auto Test Platform - 密钥生成工具"
info "项目目录: $PROJECT_DIR"
info "配置文件: $ENV_FILE"
echo ""

# 创建 .env 文件 (如果不存在)
if [ ! -f "$ENV_FILE" ]; then
    touch "$ENV_FILE"
    info "创建 .env 文件"
fi

# ---- 生成 DJANGO_SECRET_KEY ----
current=$(get_env_value "DJANGO_SECRET_KEY")
if [ "$FORCE" = true ] || [ -z "$current" ] || [ "$current" = "your-secret-key-here-change-in-production" ]; then
    new_key=$(generate_django_secret)
    set_env_value "DJANGO_SECRET_KEY" "$new_key"
    info "DJANGO_SECRET_KEY: 已生成 (50 字符随机密钥)"
else
    info "DJANGO_SECRET_KEY: 已存在, 跳过 (使用 --force 重新生成)"
fi

# ---- 生成 RABBITMQ_ENCRYPTION_KEY ----
current=$(get_env_value "RABBITMQ_ENCRYPTION_KEY")
if [ "$FORCE" = true ] || [ -z "$current" ]; then
    new_key=$(generate_fernet_key)
    set_env_value "RABBITMQ_ENCRYPTION_KEY" "$new_key"
    info "RABBITMQ_ENCRYPTION_KEY: 已生成 (Fernet 密钥)"
else
    info "RABBITMQ_ENCRYPTION_KEY: 已存在, 跳过 (使用 --force 重新生成)"
fi

# ---- 生成 POSTGRES_PASSWORD ----
current=$(get_env_value "DB_PASSWORD")
if [ "$FORCE" = true ] || [ -z "$current" ] || [ "$current" = "your-password" ] || [ "$current" = "your-secure-password" ]; then
    new_pass=$(generate_password)
    set_env_value "DB_PASSWORD" "$new_pass"
    info "DB_PASSWORD: 已生成 (24 字符随机密码)"
else
    info "DB_PASSWORD: 已存在, 跳过 (使用 --force 重新生成)"
fi

# ---- 生成 RABBITMQ_PASSWORD ----
current=$(get_env_value "RABBITMQ_PASSWORD")
if [ "$FORCE" = true ] || [ -z "$current" ] || [ "$current" = "guest" ]; then
    new_pass=$(generate_password)
    set_env_value "RABBITMQ_PASSWORD" "$new_pass"
    set_env_value "RABBITMQ_USER" "autotest"
    info "RABBITMQ_PASSWORD: 已生成 (24 字符随机密码)"
    info "RABBITMQ_USER: 已设置为 'autotest'"
else
    info "RABBITMQ_PASSWORD: 已存在, 跳过 (使用 --force 重新生成)"
fi

# ---- 设置默认值 (如果缺失) ----

defaults=(
    "DB_ENGINE:sqlite3"
    "DB_NAME:auto_test_platform"
    "DB_USER:postgres"
    "DB_HOST:localhost"
    "DB_PORT:5432"
    "DEBUG:False"
    "STORAGE_TYPE:local"
)

for item in "${defaults[@]}"; do
    key="${item%%:*}"
    default_val="${item#*:}"
    current=$(get_env_value "$key")
    if [ -z "$current" ]; then
        set_env_value "$key" "$default_val"
        info "$key: 设置默认值 '$default_val'"
    fi
done

echo ""
info "密钥生成完成!"
info "配置文件: $ENV_FILE"
warn "请确保 .env 文件不被提交到版本控制 (已添加到 .gitignore)"
echo ""
echo "使用方式:"
echo "  Docker Compose (默认 SQLite):     docker compose up -d"
echo "  Docker Compose (PostgreSQL):       docker compose --profile postgres up -d"
echo "  Docker Compose (MinIO 存储):       docker compose --profile minio up -d"
echo "  Docker Compose (全部服务):         docker compose --profile postgres --profile minio up -d"
