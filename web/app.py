"""
数据分析结果展示 Web 应用
展示 data/result 下的 markdown 文件
"""

import os
import json
import subprocess
import platform
import sys
from datetime import datetime
from flask import Flask, render_template, jsonify, send_from_directory, request

# 添加项目根目录到 Python 路径
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

# 导入任务监控器
try:
    from scheduler.task_monitor import task_monitor
    TASK_MONITOR_AVAILABLE = True
except ImportError:
    TASK_MONITOR_AVAILABLE = False
    task_monitor = None

app = Flask(__name__)

# 加载重启密码
ENV_FILE = os.path.join(PROJECT_DIR, ".env")
RESTART_PASSWORD = None

if os.path.exists(ENV_FILE):
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("SERVICE_RESTART_PASSWORD="):
                RESTART_PASSWORD = line.split("=", 1)[1].strip()
                break

if not RESTART_PASSWORD:
    RESTART_PASSWORD = "Eros@@@"  # 默认密码

RESULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "result")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def get_folders():
    """获取结果文件夹列表"""
    if not os.path.exists(RESULT_DIR):
        return []
    folders = []
    for item in os.listdir(RESULT_DIR):
        item_path = os.path.join(RESULT_DIR, item)
        if os.path.isdir(item_path):
            folders.append({
                "name": item,
                "display_name": get_folder_display_name(item)
            })
    return folders


def get_folder_display_name(folder_name):
    """获取文件夹显示名称"""
    names = {
        "final": "📊 最终结果",
        "fund_analysis": "💰 基金分析",
        "news": "📰 新闻资讯"
    }
    return names.get(folder_name, folder_name)


def get_files_by_folder(folder_name):
    """获取指定文件夹下的所有 md 文件"""
    folder_path = os.path.join(RESULT_DIR, folder_name)
    if not os.path.exists(folder_path):
        return []
    
    files = []
    for item in os.listdir(folder_path):
        if item.endswith(".md"):
            file_path = os.path.join(folder_path, item)
            stat = os.stat(file_path)
            date_str = item.replace(".md", "")
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                formatted_date = date.strftime("%Y年%m月%d日")
            except:
                formatted_date = date_str
            
            files.append({
                "name": item,
                "date": date_str,
                "display_date": formatted_date,
                "size": format_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
    
    files.sort(key=lambda x: x["date"], reverse=True)
    return files


def format_size(size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def read_markdown_content(folder_name, file_name):
    """读取 markdown 文件内容"""
    file_path = os.path.join(RESULT_DIR, folder_name, file_name)
    if not os.path.exists(file_path):
        return None
    
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


@app.route("/")
def index():
    """首页"""
    from datetime import datetime
    folders = get_folders()
    return render_template("index.html", folders=folders, result_dir=RESULT_DIR, now=datetime.now())


@app.route("/api/folders")
def api_folders():
    """获取文件夹列表 API"""
    return jsonify(get_folders())


@app.route("/api/files/<path:folder_name>")
def api_files(folder_name):
    """获取指定文件夹下的文件列表"""
    return jsonify(get_files_by_folder(folder_name))


@app.route("/api/content/<path:folder_name>/<file_name>")
def api_content(folder_name, file_name):
    """获取文件内容"""
    content = read_markdown_content(folder_name, file_name)
    if content is None:
        return jsonify({"error": "文件不存在"})
    return jsonify({
        "content": content,
        "folder": folder_name,
        "file": file_name
    })


@app.route("/static/<path:path>")
def serve_static(path):
    """静态文件服务"""
    return send_from_directory(STATIC_DIR, path)


@app.route("/themes")
def themes_preview():
    """配色方案预览页面"""
    return render_template("themes.html")


def get_service_status(service_name):
    """获取 systemd 服务状态"""
    try:
        # 检查服务是否正在运行
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        is_active = result.returncode == 0 and result.stdout.strip() == "active"

        # 检查服务是否已启用（开机自启）
        result = subprocess.run(
            ["systemctl", "is-enabled", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        is_enabled = result.returncode == 0 and result.stdout.strip() == "enabled"

        return {
            "running": is_active,
            "enabled": is_enabled
        }
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        # 如果 systemctl 不可用（非 Linux 系统）
        return {
            "running": False,
            "enabled": False
        }


@app.route("/api/system/status")
def api_system_status():
    """获取系统服务状态 API"""
    services = {
        "auto-fund-web": {
            "name": "Web 应用",
            "description": "数据分析结果展示 Web 服务"
        },
        "auto-fund-qq": {
            "name": "QQ 机器人",
            "description": "QQ 消息推送机器人服务"
        },
        "auto-fund-scheduler": {
            "name": "任务调度器",
            "description": "定时任务调度服务"
        }
    }

    result = []
    for service_id, info in services.items():
        status = get_service_status(f"{service_id}.service")
        result.append({
            "id": service_id,
            "name": info["name"],
            "description": info["description"],
            "running": status["running"],
            "enabled": status["enabled"]
        })

    return jsonify({
        "services": result,
        "platform": platform.system(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@app.route("/system")
def system_status():
    """系统状态页面"""
    return render_template("system.html", now=datetime.now())


def get_service_logs(service_id, lines=100):
    """获取服务日志"""
    log_files = {
        "auto-fund-web": None,  # Web 应用使用 journalctl
        "auto-fund-qq": "botpy.log",
        "auto-fund-scheduler": "scheduler/scheduler.log"
    }

    log_file = log_files.get(service_id)

    try:
        if log_file:
            # 从文件读取日志
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), log_file)
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    all_lines = f.readlines()
                    return "".join(all_lines[-lines:])
            else:
                return f"日志文件不存在: {log_file}"
        else:
            # 使用 journalctl 读取 systemd 服务日志
            result = subprocess.run(
                ["journalctl", "-u", f"{service_id}.service", "-n", str(lines), "--no-pager"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout
            else:
                return f"无法读取日志: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "读取日志超时"
    except FileNotFoundError:
        return "journalctl 命令不可用，请检查系统环境"
    except Exception as e:
        return f"读取日志出错: {str(e)}"


@app.route("/api/system/logs/<service_id>")
def api_service_logs(service_id):
    """获取指定服务的日志"""
    lines = request.args.get("lines", 100, type=int)
    logs = get_service_logs(service_id, lines)
    return jsonify({
        "service": service_id,
        "logs": logs,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


# 允许重启的服务白名单
ALLOWED_SERVICES = {
    "auto-fund-web",
    "auto-fund-qq",
    "auto-fund-scheduler"
}


def restart_systemd_service(service_id):
    """
    重启 systemd 服务
    返回 (success: bool, message: str)
    """
    if service_id not in ALLOWED_SERVICES:
        return False, "不允许重启此服务"

    service_name = f"{service_id}.service"

    try:
        # 首先检查服务是否存在
        result = subprocess.run(
            ["systemctl", "status", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )

        # 服务不存在
        if result.returncode != 0 and "could not be found" in result.stderr.lower():
            return False, f"服务 {service_name} 不存在"

        # 执行重启命令
        restart_result = subprocess.run(
            ["sudo", "systemctl", "restart", service_name],
            capture_output=True,
            text=True,
            timeout=30
        )

        if restart_result.returncode == 0:
            # 等待一下，然后检查服务状态
            import time
            time.sleep(1)

            status_result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=5
            )

            if status_result.returncode == 0 and status_result.stdout.strip() == "active":
                return True, "服务重启成功"
            else:
                return False, "服务已重启但未能正常启动，请查看日志"
        else:
            error_msg = restart_result.stderr.strip() if restart_result.stderr else "未知错误"
            return False, f"重启失败: {error_msg}"

    except subprocess.TimeoutExpired:
        return False, "重启操作超时"
    except FileNotFoundError as e:
        return False, f"命令不存在: {str(e)}"
    except Exception as e:
        return False, f"重启出错: {str(e)}"


@app.route("/api/system/restart/<service_id>", methods=["POST"])
def api_restart_service(service_id):
    """
    重启指定服务
    需要 POST 请求，并包含密码验证
    """
    data = request.get_json(silent=True) or {}

    provided_password = data.get("password", "")
    if provided_password != RESTART_PASSWORD:
        return jsonify({
            "success": False,
            "message": "密码错误"
        }), 403

    success, message = restart_systemd_service(service_id)

    return jsonify({
        "success": success,
        "message": message,
        "service": service_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


SCHEDULER_CONFIG_PATH = os.path.join(PROJECT_DIR, "scheduler", "config.json")
SCHEDULER_LOG_PATH = os.path.join(PROJECT_DIR, "scheduler", "scheduler.log")


def load_scheduler_config():
    """加载调度器配置"""
    if not os.path.exists(SCHEDULER_CONFIG_PATH):
        return None
    try:
        with open(SCHEDULER_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"加载调度器配置失败: {e}")
        return None


def save_scheduler_config(config):
    """保存调度器配置"""
    try:
        with open(SCHEDULER_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存调度器配置失败: {e}")
        return False


def get_task_status_from_log(task_id):
    """从日志文件获取任务状态"""
    if not os.path.exists(SCHEDULER_LOG_PATH):
        return None
    
    try:
        with open(SCHEDULER_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        
        last_run = None
        last_status = None
        task_pattern = f"任务: {task_id}"
        
        for line in reversed(lines):
            if task_pattern in line or f"'{task_id}'" in line:
                if "最后运行" in line:
                    import re
                    match = re.search(r"最后运行: ([\d\- :]+)", line)
                    if match:
                        last_run = match.group(1)
                if "状态:" in line:
                    import re
                    match = re.search(r"状态: (\w+)", line)
                    if match:
                        last_status = match.group(1)
                if last_run or last_status:
                    break
        
        return {
            "last_run": last_run,
            "last_status": last_status
        }
    except Exception as e:
        return None


@app.route("/api/scheduler/tasks")
def api_scheduler_tasks():
    """获取所有调度任务"""
    config = load_scheduler_config()
    if not config:
        return jsonify({"error": "无法加载调度器配置"}), 500
    
    tasks = []
    for task_dict in config.get("tasks", []):
        task_status = get_task_status_from_log(task_dict.get("id", ""))
        tasks.append({
            "id": task_dict.get("id"),
            "name": task_dict.get("name", ""),
            "description": task_dict.get("description", ""),
            "command": task_dict.get("command", ""),
            "schedule": task_dict.get("schedule", {}),
            "enabled": task_dict.get("enabled", True),
            "timeout": task_dict.get("timeout", 300),
            "working_directory": task_dict.get("working_directory", "."),
            "last_run": task_status.get("last_run") if task_status else None,
            "last_status": task_status.get("last_status") if task_status else None
        })
    
    return jsonify({
        "tasks": tasks,
        "settings": config.get("settings", {}),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@app.route("/api/scheduler/run/<task_id>", methods=["POST"])
def api_scheduler_run(task_id):
    """手动运行指定任务"""
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")
    
    if password != RESTART_PASSWORD:
        return jsonify({
            "success": False,
            "message": "密码错误"
        }), 403
    
    config = load_scheduler_config()
    if not config:
        return jsonify({"success": False, "message": "无法加载调度器配置"}), 500
    
    task = None
    for task_dict in config.get("tasks", []):
        if task_dict.get("id") == task_id:
            task = task_dict
            break
    
    if not task:
        return jsonify({"success": False, "message": f"任务 {task_id} 不存在"}), 404
    
    if not task.get("enabled", True):
        return jsonify({"success": False, "message": "任务已禁用，无法运行"}), 400
    
    try:
        import subprocess
        import threading
        work_dir = task.get("working_directory", PROJECT_DIR)
        timeout = task.get("timeout", 300)
        
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['LANG'] = 'en_US.UTF-8'
        
        # 记录任务到监控器（手动运行）
        if TASK_MONITOR_AVAILABLE:
            task_monitor.start_task(
                task_id=task_id,
                task_name=task.get('name', ''),
                task_type="manual"
            )
        
        # 使用 Popen 启动进程以便获取 PID
        process = subprocess.Popen(
            task.get("command"),
            shell=True,
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # 更新 PID 到监控器
        if TASK_MONITOR_AVAILABLE:
            task_monitor.update_task_pid(task_id, process.pid)
        
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            
            if process.returncode == 0:
                # 记录任务完成
                if TASK_MONITOR_AVAILABLE:
                    task_monitor.end_task(
                        task_id=task_id,
                        status="completed",
                        output=stdout,
                        error=""
                    )
                return jsonify({
                    "success": True,
                    "message": f"任务 '{task.get('name')}' 执行成功",
                    "output": stdout[:500] if stdout else "",
                    "pid": process.pid
                })
            else:
                # 记录任务失败
                if TASK_MONITOR_AVAILABLE:
                    task_monitor.end_task(
                        task_id=task_id,
                        status="failed",
                        output=stdout,
                        error=stderr
                    )
                return jsonify({
                    "success": False,
                    "message": f"任务执行失败",
                    "error": stderr[:500] if stderr else "",
                    "pid": process.pid
                })
        
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            
            # 记录任务超时
            if TASK_MONITOR_AVAILABLE:
                task_monitor.end_task(
                    task_id=task_id,
                    status="timeout",
                    output="",
                    error=f"任务执行超时（{timeout}秒）"
                )
            return jsonify({
                "success": False,
                "message": f"任务执行超时（{timeout}秒）",
                "pid": process.pid
            })
    
    except Exception as e:
        # 记录任务异常
        if TASK_MONITOR_AVAILABLE:
            task_monitor.end_task(
                task_id=task_id,
                status="error",
                output="",
                error=str(e)
            )
        return jsonify({
            "success": False,
            "message": f"执行出错: {str(e)}"
        })


@app.route("/api/scheduler/toggle/<task_id>", methods=["POST"])
def api_scheduler_toggle(task_id):
    """启用/禁用任务"""
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")
    
    if password != RESTART_PASSWORD:
        return jsonify({
            "success": False,
            "message": "密码错误"
        }), 403
    
    config = load_scheduler_config()
    if not config:
        return jsonify({"success": False, "message": "无法加载调度器配置"}), 500
    
    task_found = False
    new_state = False
    for task_dict in config.get("tasks", []):
        if task_dict.get("id") == task_id:
            task_found = True
            current_state = task_dict.get("enabled", True)
            task_dict["enabled"] = not current_state
            new_state = not current_state
            break
    
    if not task_found:
        return jsonify({"success": False, "message": f"任务 {task_id} 不存在"}), 404
    
    if save_scheduler_config(config):
        return jsonify({
            "success": True,
            "message": f"任务已{'启用' if new_state else '禁用'}",
            "enabled": new_state
        })
    else:
        return jsonify({"success": False, "message": "保存配置失败"}), 500


@app.route("/api/scheduler/update", methods=["POST"])
def api_scheduler_update():
    """更新任务配置"""
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")
    task_id = data.get("task_id")
    task_config = data.get("config", {})
    
    if password != RESTART_PASSWORD:
        return jsonify({
            "success": False,
            "message": "密码错误"
        }), 403
    
    if not task_id:
        return jsonify({"success": False, "message": "缺少任务ID"}), 400
    
    config = load_scheduler_config()
    if not config:
        return jsonify({"success": False, "message": "无法加载调度器配置"}), 500
    
    task_found = False
    for task_dict in config.get("tasks", []):
        if task_dict.get("id") == task_id:
            task_found = True
            for key, value in task_config.items():
                if key not in ["id"]:
                    task_dict[key] = value
            break
    
    if not task_found:
        return jsonify({"success": False, "message": f"任务 {task_id} 不存在"}), 404
    
    if save_scheduler_config(config):
        return jsonify({
            "success": True,
            "message": "任务配置已更新"
        })
    else:
        return jsonify({"success": False, "message": "保存配置失败"}), 500


@app.route("/api/scheduler/logs")
def api_scheduler_logs():
    """获取调度器日志"""
    lines = request.args.get("lines", 100, type=int)
    
    if not os.path.exists(SCHEDULER_LOG_PATH):
        return jsonify({
            "logs": "",
            "message": "日志文件不存在"
        })
    
    try:
        with open(SCHEDULER_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
            log_content = "".join(all_lines[-lines:])
        
        return jsonify({
            "logs": log_content,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return jsonify({
            "logs": "",
            "message": f"读取日志失败: {str(e)}"
        })


# ==================== 任务监控 API ====================

@app.route("/api/task-monitor/running")
def api_task_monitor_running():
    """获取所有正在运行的任务"""
    if not TASK_MONITOR_AVAILABLE:
        return jsonify({
            "error": "任务监控模块不可用",
            "tasks": []
        }), 503
    
    try:
        running_tasks = task_monitor.get_running_tasks()
        return jsonify({
            "tasks": running_tasks,
            "count": len(running_tasks),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return jsonify({
            "error": f"获取运行中任务失败: {str(e)}",
            "tasks": []
        }), 500


@app.route("/api/task-monitor/history")
def api_task_monitor_history():
    """获取任务执行历史"""
    if not TASK_MONITOR_AVAILABLE:
        return jsonify({
            "error": "任务监控模块不可用",
            "history": []
        }), 503
    
    try:
        limit = request.args.get("limit", 20, type=int)
        history = task_monitor.get_task_history(limit=limit)
        return jsonify({
            "history": history,
            "count": len(history),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return jsonify({
            "error": f"获取任务历史失败: {str(e)}",
            "history": []
        }), 500


@app.route("/api/task-monitor/summary")
def api_task_monitor_summary():
    """获取任务监控摘要"""
    if not TASK_MONITOR_AVAILABLE:
        return jsonify({
            "error": "任务监控模块不可用",
            "running_count": 0,
            "history_count": 0
        }), 503
    
    try:
        summary = task_monitor.get_summary()
        return jsonify(summary)
    except Exception as e:
        return jsonify({
            "error": f"获取任务摘要失败: {str(e)}",
            "running_count": 0,
            "history_count": 0
        }), 500


@app.route("/api/task-monitor/status/<task_id>")
def api_task_monitor_status(task_id):
    """获取指定任务的运行状态"""
    if not TASK_MONITOR_AVAILABLE:
        return jsonify({
            "error": "任务监控模块不可用",
            "task_id": task_id,
            "is_running": False
        }), 503
    
    try:
        is_running = task_monitor.is_task_running(task_id)
        return jsonify({
            "task_id": task_id,
            "is_running": is_running,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return jsonify({
            "error": f"获取任务状态失败: {str(e)}",
            "task_id": task_id,
            "is_running": False
        }), 500


if __name__ == "__main__":
    print("=" * 50)
    print("  📊 数据分析结果展示系统")
    print("=" * 50)
    print(f"  结果目录: {RESULT_DIR}")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
