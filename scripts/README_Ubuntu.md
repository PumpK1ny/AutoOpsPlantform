# Ubuntu 开机自启动配置

## 文件说明

- `start_web.sh` - 启动 Web 应用 (web/app.py)
- `start_qq_bot.sh` - 启动 QQ 机器人 (message_push/QQ/run.py)
- `start_scheduler.sh` - 启动调度器 (scheduler/run.py)
- `start_all.sh` - 同时启动所有服务
- `install_service.sh` - 一键安装开机自启动服务
- `uninstall_service.sh` - 一键卸载开机自启动服务

## 一键安装（推荐）

最简单的方式是使用提供的安装脚本：

```bash
# 进入scripts目录
cd /root/auto_fund/scripts

# 运行安装脚本（需要sudo权限）
sudo ./install_service.sh
```

安装脚本会自动：
- 检查虚拟环境是否存在
- 为启动脚本添加执行权限
- 创建3个systemd服务（web、qq、scheduler）
- 启用并启动所有服务

卸载服务：

```bash
sudo ./uninstall_service.sh
```

## 手动配置（高级用户）

如果需要手动配置，可以按照以下步骤操作：

### 1. 添加执行权限

```bash
chmod +x /root/auto_fund/scripts/*.sh
```

### 2. 创建 systemd 服务文件

**Web 应用服务：**

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
User=root
WorkingDirectory=/root/auto_fund
ExecStart=/root/auto_fund/scripts/start_web.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**QQ 机器人服务：**

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
User=root
WorkingDirectory=/root/auto_fund
ExecStart=/root/auto_fund/scripts/start_qq_bot.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**调度器服务：**

```bash
sudo nano /etc/systemd/system/auto-fund-scheduler.service
```

内容：
```ini
[Unit]
Description=Auto Fund Scheduler
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/auto_fund
ExecStart=/root/auto_fund/scripts/start_scheduler.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3. 启用并启动服务

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable auto-fund-web.service
sudo systemctl enable auto-fund-qq.service
sudo systemctl enable auto-fund-scheduler.service

# 启动服务
sudo systemctl start auto-fund-web.service
sudo systemctl start auto-fund-qq.service
sudo systemctl start auto-fund-scheduler.service

# 查看状态
sudo systemctl status auto-fund-web.service
sudo systemctl status auto-fund-qq.service
sudo systemctl status auto-fund-scheduler.service
```

## 常用命令

```bash
# 查看所有服务状态
sudo systemctl status auto-fund-web auto-fund-qq auto-fund-scheduler

# 停止服务
sudo systemctl stop auto-fund-web.service
sudo systemctl stop auto-fund-qq.service
sudo systemctl stop auto-fund-scheduler.service

# 重启服务
sudo systemctl restart auto-fund-web.service
sudo systemctl restart auto-fund-qq.service
sudo systemctl restart auto-fund-scheduler.service

# 查看实时日志
sudo journalctl -u auto-fund-web -f
sudo journalctl -u auto-fund-qq -f
sudo journalctl -u auto-fund-scheduler -f

# 查看最近日志
sudo journalctl -u auto-fund-web -n 100
sudo journalctl -u auto-fund-qq -n 100
sudo journalctl -u auto-fund-scheduler -n 100
```

## 手动启动（不使用systemd）

如果需要临时测试服务，可以直接运行启动脚本：

```bash
# 启动所有服务
cd /root/auto_fund/scripts
./start_all.sh

# 单独启动某个服务
./start_web.sh
./start_qq_bot.sh
./start_scheduler.sh
```

## Web 界面服务重启功能

Web 界面提供了服务重启功能，安装脚本会自动配置所需的 sudo 权限。

### 安全说明

重启功能包含多层安全保护：
1. **白名单限制**：只允许重启 `auto-fund-web`、`auto-fund-qq`、`auto-fund-scheduler` 三个服务
2. **双重确认**：需要用户两次确认，第二次需要输入服务ID
3. **POST 请求**：使用 POST 方法并需要显式确认参数
4. **sudo 限制**：通过 sudoers 配置严格限制可执行的命令

### 撤销重启权限

如需撤销 Web 界面的重启权限：
```bash
sudo rm /etc/sudoers.d/auto-fund-restart
```

## 注意事项

- 确保虚拟环境存在：`/root/auto_fund/venv/bin/python`
- 确保所有启动脚本有执行权限
- 使用一键安装脚本会自动处理权限问题
- 如需修改服务配置，编辑相应的服务文件后运行：`sudo systemctl daemon-reload`
