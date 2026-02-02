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
    echo "请先创建虚拟环境: python3 -m venv venv"
    exit 1
fi

echo -e "${GREEN}[OK] 虚拟环境检查通过${NC}"

# 检查并设置启动脚本执行权限
echo "[INFO] 检查启动脚本执行权限..."
START_SCRIPTS=(
    "$SCRIPT_DIR/start_web.sh"
    "$SCRIPT_DIR/start_qq_bot.sh"
    "$SCRIPT_DIR/start_scheduler.sh"
)

for script in "${START_SCRIPTS[@]}"; do
    if [ ! -f "$script" ]; then
        echo -e "${RED}[ERROR] 启动脚本不存在: $script${NC}"
        exit 1
    fi
    if [ ! -x "$script" ]; then
        echo "[INFO] 添加执行权限: $script"
        chmod +x "$script"
    fi
done

echo -e "${GREEN}[OK] 启动脚本权限检查通过${NC}"

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

# 创建 Scheduler 服务
create_service "auto-fund-scheduler" "$SCRIPT_DIR/start_scheduler.sh" "Auto Fund Scheduler"

# 重新加载 systemd
echo ""
echo "[INFO] 重新加载 systemd..."
systemctl daemon-reload

# 启用服务
echo "[INFO] 启用开机自启..."
systemctl enable auto-fund-web.service
systemctl enable auto-fund-qq.service
systemctl enable auto-fund-scheduler.service

# 配置 Web 界面重启权限
echo ""
echo "[INFO] 配置 Web 界面服务重启权限..."
SUDOERS_FILE="/etc/sudoers.d/auto-fund-restart"

cat > "$SUDOERS_FILE" << EOF
# Auto Fund 服务重启权限配置
# 允许指定用户无需密码重启 auto-fund 相关服务

# 允许重启服务
$CURRENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart auto-fund-*.service
$CURRENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl status auto-fund-*.service
$CURRENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl is-active auto-fund-*.service

# 也支持 /usr/bin 路径
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart auto-fund-*.service
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl status auto-fund-*.service
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl is-active auto-fund-*.service
EOF

chmod 440 "$SUDOERS_FILE"

# 验证 sudo 配置
if visudo -c -f "$SUDOERS_FILE" >/dev/null 2>&1; then
    echo -e "${GREEN}[OK] Web 重启权限配置完成${NC}"
else
    echo -e "${YELLOW}[WARN] sudoers 配置验证失败，Web 重启功能可能无法使用${NC}"
    rm -f "$SUDOERS_FILE"
fi

# 启动服务
echo ""
echo "[INFO] 启动服务..."
systemctl start auto-fund-web.service
systemctl start auto-fund-qq.service
systemctl start auto-fund-scheduler.service

# 等待服务启动
sleep 3

# 检查状态
echo ""
echo "=========================================="
echo "   服务状态"
echo "=========================================="
echo ""

WEB_STATUS=$(systemctl is-active auto-fund-web.service 2>/dev/null || echo "unknown")
QQ_STATUS=$(systemctl is-active auto-fund-qq.service 2>/dev/null || echo "unknown")
SCHEDULER_STATUS=$(systemctl is-active auto-fund-scheduler.service 2>/dev/null || echo "unknown")

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

if [ "$SCHEDULER_STATUS" = "active" ]; then
    echo -e "调度器: ${GREEN}运行中${NC}"
else
    echo -e "调度器: ${RED}未运行 ($SCHEDULER_STATUS)${NC}"
fi

echo ""
echo "=========================================="
echo "   安装完成"
echo "=========================================="
echo ""
echo "常用命令:"
echo "  查看状态: sudo systemctl status auto-fund-web"
echo "           sudo systemctl status auto-fund-qq"
echo "           sudo systemctl status auto-fund-scheduler"
echo "  停止服务: sudo systemctl stop auto-fund-web"
echo "           sudo systemctl stop auto-fund-qq"
echo "           sudo systemctl stop auto-fund-scheduler"
echo "  重启服务: sudo systemctl restart auto-fund-web"
echo "           sudo systemctl restart auto-fund-qq"
echo "           sudo systemctl restart auto-fund-scheduler"
echo "  查看日志: sudo journalctl -u auto-fund-web -f"
echo "           sudo journalctl -u auto-fund-qq -f"
echo "           sudo journalctl -u auto-fund-scheduler -f"
echo ""
echo "卸载服务:"
echo "  sudo $SCRIPT_DIR/uninstall_service.sh"
echo ""
echo "Web 界面:"
echo "  访问 http://<服务器IP>:5000/system 查看系统状态"
echo "  可在 Web 界面直接重启各服务"
echo ""
echo -e "${GREEN}开机自启动已配置完成！${NC}"
