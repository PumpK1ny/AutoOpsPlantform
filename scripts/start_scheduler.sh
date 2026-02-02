#!/bin/bash

# 调度器启动脚本

# 自动获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="$PROJECT_DIR/venv/bin/python"
APP="$PROJECT_DIR/scheduler/run.py"

echo "[INFO] 脚本目录: $SCRIPT_DIR"
echo "[INFO] 项目目录: $PROJECT_DIR"
echo "[INFO] 正在启动调度器..."
echo "[INFO] 使用 Python: $PYTHON"
echo "[INFO] 应用路径: $APP"

cd "$PROJECT_DIR" || exit 1

# 检查虚拟环境是否存在
if [ ! -f "$PYTHON" ]; then
    echo "[ERROR] 虚拟环境不存在: $PYTHON"
    exit 1
fi

# 启动应用
exec "$PYTHON" "$APP"
