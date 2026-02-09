#!/bin/bash

# 启动所有服务

# 自动获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="$PROJECT_DIR/.venv/bin/python"

echo "=========================================="
echo "   Auto Fund - 启动所有服务"
echo "=========================================="
echo "[INFO] 项目目录: $PROJECT_DIR"
echo ""

# 检查虚拟环境
if [ ! -f "$PYTHON" ]; then
    echo "[ERROR] 虚拟环境不存在: $PYTHON"
    exit 1
fi

cd "$PROJECT_DIR" || exit 1

# 启动 Web 应用
echo "[1/2] 正在启动 Web 应用..."
nohup "$PYTHON" "$PROJECT_DIR/web/app.py" > /tmp/web_app.log 2>&1 &
WEB_PID=$!
echo "[OK] Web 应用已启动 (PID: $WEB_PID)"
echo ""

# 等待一下
sleep 2

# 启动 QQ 机器人
echo "[2/2] 正在启动 QQ 机器人..."
nohup "$PYTHON" "$PROJECT_DIR/message_push/QQ/run.py" > /tmp/qq_bot.log 2>&1 &
QQ_PID=$!
echo "[OK] QQ 机器人已启动 (PID: $QQ_PID)"
echo ""

echo "=========================================="
echo "   所有服务已启动完成"
echo "=========================================="
echo ""
echo "查看日志:"
echo "  Web 应用: tail -f /tmp/web_app.log"
echo "  QQ 机器人: tail -f /tmp/qq_bot.log"
echo ""
echo "停止服务:"
echo "  kill $WEB_PID"
echo "  kill $QQ_PID"
