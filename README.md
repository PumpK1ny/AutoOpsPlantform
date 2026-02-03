<div align="center">

<img src="pic/logo_b.jpeg" alt="Eros Logo" width="250" />

# 🤖 Eros - 智能基金监控系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-2.0+-000000?style=flat-square&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/AI-GLM-FF6B9D?style=flat-square&logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" />
</p>

<p align="center">
  <b>AI 驱动的智能基金分析与监控系统</b><br/>
  自动化数据收集 · 智能分析 · 实时推送 · Web 可视化
</p>

<p align="center">
  <a href="#快速开始">🚀 快速开始</a> •
  <a href="#功能特性">✨ 功能</a> •
  <a href="#技术栈">🛠️ 技术栈</a> •
  <a href="#部署">📦 部署</a> •
  <a href="#配置">⚙️ 配置</a>
</p>

</div>

---

## ✨ 功能特性

<table>
<tr>
<td width="50%">

### 🤖 AI 智能分析
- 基于智谱 AI GLM 模型
- 基金智能分析与评级
- 新闻自动摘要生成

</td>
<td width="50%">

### 📊 数据收集
- 基金实时数据获取
- 行业资金流向追踪
- 多源新闻资讯聚合

</td>
</tr>
<tr>
<td width="50%">

### ⏰ 定时任务
- Cron 表达式支持
- 间隔/定时执行
- 配置文件热重载

</td>
<td width="50%">

### 🔔 消息推送
- QQ 机器人实时推送
- 自定义推送规则
- 多渠道消息通知

</td>
</tr>
</table>

---

## 🛠️ 技术栈

<div align="center">

| 类别 | 技术 |
|:---:|:---|
| **AI 引擎** | ![Zhipu AI](https://img.shields.io/badge/Zhipu_AI-GLM-FF6B9D?style=flat-square) |
| **Web 框架** | ![Flask](https://img.shields.io/badge/Flask-2.0+-000000?style=flat-square&logo=flask) |
| **数据处理** | ![Pandas](https://img.shields.io/badge/Pandas-1.3+-150458?style=flat-square&logo=pandas) ![NumPy](https://img.shields.io/badge/NumPy-1.21+-013243?style=flat-square&logo=numpy) |
| **任务调度** | ![Schedule](https://img.shields.io/badge/Schedule-1.1+-blue?style=flat-square) |
| **前端** | ![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white) ![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white) ![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black) |

</div>

---

## 🚀 快速开始

### 1️⃣ 克隆项目

```bash
git clone <repository-url>
cd auto_fund
```

### 2️⃣ 创建虚拟环境

```bash
# Windows
python -m venv .venv && .venv\Scripts\activate

# Ubuntu/macOS
python3 -m venv venv && source venv/bin/activate
```

### 3️⃣ 安装依赖

```bash
pip install -r requirements.txt
```

### 4️⃣ 配置环境

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥
```

### 5️⃣ 启动服务

```bash
# 启动 Web 界面
python web/app.py

# 启动 QQ 机器人
python message_push/QQ/run.py

# 启动任务调度器
python scheduler/scheduler.py
```

访问 http://localhost:5000 查看 Web 界面

---

## 📦 部署

<details>
<summary><b>🪟 Windows 部署</b></summary>

#### 方法一：启动文件夹（推荐）
1. `Win + R` → 输入 `shell:startup`
2. 将 `scripts/start_all.bat` 快捷方式复制到启动文件夹
3. 重启测试

#### 方法二：任务计划程序
1. `Win + R` → 输入 `taskschd.msc`
2. 创建任务，触发器选择"用户登录时"
3. 操作指向 `scripts/start_all.bat`

</details>

<details>
<summary><b>🐧 Ubuntu 部署（systemd）</b></summary>

```bash
cd scripts
sudo ./install_service.sh
```

自动创建服务：
- `auto-fund-web.service` - Web 应用
- `auto-fund-qq.service` - QQ 机器人
- `auto-fund-scheduler.service` - 任务调度器

```bash
# 查看状态
sudo systemctl status auto-fund-web

# 查看日志
sudo journalctl -u auto-fund-web -f

# 卸载
sudo ./uninstall_service.sh
```

</details>

---

## ⚙️ 配置

### 环境变量 (.env)

```env
# 必填：智谱 AI API 密钥
ZHIPU_API_KEY=your_api_key

# 可选：QQ 机器人
QQ_BOT_APPID=your_appid
QQ_BOT_SECRET=your_secret

# 可选：Web 重启密码
SERVICE_RESTART_PASSWORD=your_password
```

### 调度器配置 (scheduler/config.json)

```json
{
  "tasks": [{
    "id": "news_summary",
    "name": "每日新闻摘要",
    "command": "python workflow/news_summry/run.py",
    "schedule": { "type": "daily", "time": "00:00" },
    "enabled": true
  }]
}
```

---

## 📸 界面预览

<div align="center">

| 首页 | 分析报告 | 系统状态 |
|:---:|:---:|:---:|
| 📊 数据概览 | 💰 基金分析 | 🖥️ 服务监控 |

</div>

---

## 🗺️ 项目结构

```
auto_fund/
├── AI/                    # AI 核心模块
├── DataCollector/         # 数据收集
├── message_push/QQ/       # QQ 机器人
├── pic/                   # 项目图片资源
├── scheduler/             # 任务调度
├── web/                   # Web 应用
├── workflow/              # 工作流
└── scripts/               # 部署脚本
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

<div align="center">

### 🌟 Star 历史

[![Star History Chart](https://api.star-history.com/svg?repos=yourname/auto_fund&type=Date)](https://star-history.com/#yourname/auto_fund&Date)

---

**Made with ❤️ by Eros Team**

<p align="center">
  <a href="https://github.com/yourname/auto_fund">
    <img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white" />
  </a>
</p>

</div>
