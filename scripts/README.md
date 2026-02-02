# Windows 开机自启动配置

## 文件说明

- `start_web.bat` - 启动 Web 应用 (web/app.py)
- `start_qq_bot.bat` - 启动 QQ 机器人 (message_push/QQ/run.py)
- `start_all.bat` - 同时启动所有服务

## 配置开机自启动

### 方法一：添加到启动文件夹（推荐）

1. 按 `Win + R` 打开运行窗口
2. 输入 `shell:startup` 并回车
3. 将 `start_all.bat` 的快捷方式复制到打开的文件夹中
4. 重启电脑测试

### 方法二：使用任务计划程序

1. 按 `Win + R` 打开运行窗口
2. 输入 `taskschd.msc` 并回车
3. 点击右侧"创建基本任务"
4. 配置：
   - 名称：Auto Fund 启动
   - 触发器：当用户登录时
   - 操作：启动程序
   - 程序：`d:\PythonProject\auto_fund\startup_scripts\start_all.bat`

### 方法三：使用注册表

1. 按 `Win + R` 打开运行窗口
2. 输入 `regedit` 并回车
3. 导航到：`HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`
4. 右键 → 新建 → 字符串值
5. 名称：`AutoFundStartup`
6. 值：`d:\PythonProject\auto_fund\startup_scripts\start_all.bat`

## 注意事项

- 确保 `.venv\Scripts\python.exe` 存在
- 如需隐藏命令行窗口，可将 `.bat` 改为 `.vbs` 脚本
- 建议先手动运行测试脚本是否正常工作
