# Ubuntu 开机自启动配置

## 文件说明

- `start_web.sh` - 启动 Web 应用 (web/app.py)
- `start_qq_bot.sh` - 启动 QQ 机器人 (message_push/QQ/run.py)
- `start_all.sh` - 同时启动所有服务

## 使用前配置

**修改脚本中的项目路径：**

编辑所有 `.sh` 文件，将第一行的 `PROJECT_DIR` 改为你的实际路径：

```bash
PROJECT_DIR="/home/username/auto_fund"  # 修改为你的实际路径
```

## 添加执行权限

```bash
chmod +x /path/to/auto_fund/startup_scripts/*.sh
```

## 配置开机自启动

### 方法一：使用 systemd 服务（推荐）

1. **创建 Web 应用服务文件：**

```bash
sudo nano /etc/systemd/system/auto-fund-web.service
```

内容：
```ini
[Unit]
Description=Auto Fund Web Application
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/auto_fund
ExecStart=/path/to/auto_fund/.venv/bin/python /path/to/auto_fund/web/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

2. **创建 QQ 机器人服务文件：**

```bash
sudo nano /etc/systemd/system/auto-fund-qq.service
```

内容：
```ini
[Unit]
Description=Auto Fund QQ Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/auto_fund
ExecStart=/path/to/auto_fund/.venv/bin/python /path/to/auto_fund/message_push/QQ/run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

3. **启用并启动服务：**

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable auto-fund-web.service
sudo systemctl enable auto-fund-qq.service

# 启动服务
sudo systemctl start auto-fund-web.service
sudo systemctl start auto-fund-qq.service

# 查看状态
sudo systemctl status auto-fund-web.service
sudo systemctl status auto-fund-qq.service
```

### 方法二：使用 crontab

```bash
# 编辑当前用户的 crontab
crontab -e

# 添加以下行（开机时执行）
@reboot /path/to/auto_fund/startup_scripts/start_all.sh
```

### 方法三：使用 rc.local

```bash
# 编辑 rc.local
sudo nano /etc/rc.local

# 在 exit 0 之前添加：
/path/to/auto_fund/startup_scripts/start_all.sh &

# 确保 rc.local 有执行权限
sudo chmod +x /etc/rc.local
```

## 常用命令

```bash
# 手动启动
./start_all.sh

# 查看日志
tail -f /tmp/web_app.log
tail -f /tmp/qq_bot.log

# 停止服务（使用 systemd）
sudo systemctl stop auto-fund-web.service
sudo systemctl stop auto-fund-qq.service

# 重启服务
sudo systemctl restart auto-fund-web.service
```

## 注意事项

- 确保 `.venv/bin/python` 存在且可执行
- 确保项目路径正确
- 使用 systemd 方法时，建议先手动测试脚本是否正常工作
