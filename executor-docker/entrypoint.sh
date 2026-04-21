#!/bin/bash
# 容器启动入口脚本
# 确保卷挂载目录存在且有正确权限

mkdir -p /app/traces /app/logs

exec python /app/main.py
