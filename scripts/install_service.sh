#!/bin/bash

# Auto Fund 开机自启动安装脚本
# 使用方法: sudo ./install_service.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 自动获取路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 获取当前用户（非root）
CURRENT_USER=${SUDO_USER:-$USER}
CURRENT_USER_HOME=$(eval echo ~$CURRENT_USER)

echo "=========================================="
echo "   Auto Fund 开机自启动安装"
echo "=========================================="
echo ""
echo "项目目录: $PROJECT_DIR"
echo "当前用户: $CURRENT_USER"
echo ""

# 检查是否以root运行
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] 请使用 sudo 运行此脚本${NC}"
    echo "示例: sudo ./install_service.sh"
    exit 1
fi

# 检查虚拟环境
PYTHON_PATH="$PROJECT_DIR/venv/bin/python"
if [ ! -f "$PYTHON_PATH" ]; then
    echo -e "${RED}[ERROR] 虚拟环境不存在: $PYTHON_PATH${NC}"
    exit 1
fi

echo -e "${GREEN}[OK] 虚拟环境检查通过${NC}"

# 创建 systemd 服务文件
create_service() {
    local service_name=$1
    local exec_path=$2
    local description=$3
    
    cat > "/etc/systemd/system/$service_name.service" << EOF
[Unit]
Description=$description
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$exec_path
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    echo -e "${GREEN}[OK] 创建服务: $service_name${NC}"
}

# 创建 Web 服务
create_service "auto-fund-web" "$SCRIPT_DIR/start_web.sh" "Auto Fund Web Application"

# 创建 QQ 机器人服务
create_service "auto-fund-qq" "$SCRIPT_DIR/start_qq_bot.sh" "Auto Fund QQ Bot"

# 重新加载 systemd
echo ""
echo "[INFO] 重新加载 systemd..."
systemctl daemon-reload

# 启用服务
echo "[INFO] 启用开机自启..."
systemctl enable auto-fund-web.service
systemctl enable auto-fund-qq.service

# 启动服务
echo ""
echo "[INFO] 启动服务..."
systemctl start auto-fund-web.service
systemctl start auto-fund-qq.service

# 等待服务启动
sleep 2

# 检查状态
echo ""
echo "=========================================="
echo "   服务状态"
echo "=========================================="
echo ""

WEB_STATUS=$(systemctl is-active auto-fund-web.service)
QQ_STATUS=$(systemctl is-active auto-fund-qq.service)

if [ "$WEB_STATUS" = "active" ]; then
    echo -e "Web 应用: ${GREEN}运行中${NC}"
else
    echo -e "Web 应用: ${RED}未运行 ($WEB_STATUS)${NC}"
fi

if [ "$QQ_STATUS" = "active" ]; then
    echo -e "QQ 机器人: ${GREEN}运行中${NC}"
else
    echo -e "QQ 机器人: ${RED}未运行 ($QQ_STATUS)${NC}"
fi

echo ""
echo "=========================================="
echo "   安装完成"
echo "=========================================="
echo ""
echo "常用命令:"
echo "  查看状态: sudo systemctl status auto-fund-web"
echo "           sudo systemctl status auto-fund-qq"
echo "  停止服务: sudo systemctl stop auto-fund-web"
echo "           sudo systemctl stop auto-fund-qq"
echo "  重启服务: sudo systemctl restart auto-fund-web"
echo "           sudo systemctl restart auto-fund-qq"
echo "  查看日志: sudo journalctl -u auto-fund-web -f"
echo "           sudo journalctl -u auto-fund-qq -f"
echo ""
echo -e "${GREEN}开机自启动已配置完成！${NC}"
