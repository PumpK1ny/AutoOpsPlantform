#!/bin/bash

# Auto Fund 开机自启动卸载脚本
# 使用方法: sudo ./uninstall_service.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "   Auto Fund 开机自启动卸载"
echo "=========================================="
echo ""

# 检查是否以root运行
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] 请使用 sudo 运行此脚本${NC}"
    exit 1
fi

# 停止服务
echo "[INFO] 停止服务..."
systemctl stop auto-fund-web.service 2>/dev/null || true
systemctl stop auto-fund-qq.service 2>/dev/null || true

# 禁用服务
echo "[INFO] 禁用开机自启..."
systemctl disable auto-fund-web.service 2>/dev/null || true
systemctl disable auto-fund-qq.service 2>/dev/null || true

# 删除服务文件
echo "[INFO] 删除服务文件..."
rm -f /etc/systemd/system/auto-fund-web.service
rm -f /etc/systemd/system/auto-fund-qq.service

# 重新加载 systemd
systemctl daemon-reload

echo ""
echo -e "${GREEN}卸载完成！${NC}"
echo "开机自启动已取消"
