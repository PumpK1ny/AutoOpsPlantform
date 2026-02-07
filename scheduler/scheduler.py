import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from threading import Thread, Lock
from typing import Dict, List, Optional
import schedule
import pytz

try:
    from .task_monitor import task_monitor
    from .task_log_manager import task_log_manager
    TASK_MONITOR_AVAILABLE = True
    TASK_LOG_AVAILABLE = True
except ImportError:
    try:
        from task_monitor import task_monitor
        from task_log_manager import task_log_manager
        TASK_MONITOR_AVAILABLE = True
        TASK_LOG_AVAILABLE = True
    except ImportError:
        task_monitor = None
        task_log_manager = None
        TASK_MONITOR_AVAILABLE = False
        TASK_LOG_AVAILABLE = False


class ConfigWatcher(Thread):
    def __init__(self, scheduler: 'TaskScheduler', check_interval: int = 5):
        super().__init__(daemon=True)
        self.scheduler = scheduler
        self.check_interval = check_interval
        self.last_mtime: Optional[float] = None
        self.running = False
        self.logger = logging.getLogger("ConfigWatcher")
        
    def start_watching(self):
        self.running = True
        self.last_mtime = self._get_mtime()
        self.start()
        self.logger.info(f"配置文件监控已启动，检查间隔: {self.check_interval}秒")
        
    def stop_watching(self):
        self.running = False
        self.logger.info("配置文件监控已停止")
        
    def _get_mtime(self) -> Optional[float]:
        try:
            return self.scheduler.config_path.stat().st_mtime
        except FileNotFoundError:
            return None
            
    def run(self):
        while self.running:
            time.sleep(self.check_interval)
            current_mtime = self._get_mtime()
            
            if current_mtime is not None and self.last_mtime is not None:
                if current_mtime != self.last_mtime:
                    self.logger.info("检测到配置文件变化，正在重新加载...")
                    try:
                        self.scheduler.reload_config()
                        self.last_mtime = current_mtime
                        self.logger.info("配置文件重载成功")
                    except Exception as e:
                        self.logger.error(f"配置文件重载失败: {e}")
            
            self.last_mtime = current_mtime


class TaskConfig:
    def __init__(self, config_dict: dict):
        self.id = config_dict.get('id')
        self.name = config_dict.get('name', '')
        self.description = config_dict.get('description', '')
        self.command = config_dict.get('command')
        self.schedule = config_dict.get('schedule', {})
        self.enabled = config_dict.get('enabled', True)
        self.working_directory = config_dict.get('working_directory', '.')
        self.timeout = config_dict.get('timeout', 300)


class SchedulerSettings:
    def __init__(self, settings_dict: dict):
        self.timezone = settings_dict.get('timezone', 'Asia/Shanghai')
        self.log_level = settings_dict.get('log_level', 'INFO')
        self.max_concurrent_tasks = settings_dict.get('max_concurrent_tasks', 3)
        self.retry_count = settings_dict.get('retry_count', 3)
        self.retry_delay = settings_dict.get('retry_delay', 60)


class TaskRunner:
    def __init__(self, task: TaskConfig, settings: SchedulerSettings):
        self.task = task
        self.settings = settings
        self.logger = logging.getLogger(f"Task-{task.id}")
        self.running = False
        self.last_run: Optional[datetime] = None
        self.last_status: Optional[str] = None
        self.last_output: Optional[str] = None

    def run(self):
        if not self.task.enabled:
            self.logger.info(f"任务 {self.task.name} 已禁用，跳过执行")
            return

        self.running = True
        self.logger.info(f"开始执行任务: {self.task.name}")
        self.logger.info(f"执行命令: {self.task.command}")
        self.logger.info(f"工作目录: {self.task.working_directory}")

        # 记录任务开始到监控器
        if TASK_MONITOR_AVAILABLE and task_monitor:
            execution = task_monitor.start_task(
                task_id=self.task.id,
                task_name=self.task.name,
                task_type="scheduled"
            )

        # 开始记录任务日志
        log_file = None
        if TASK_LOG_AVAILABLE and task_log_manager:
            log_file = task_log_manager.start_task_log(self.task.id, self.task.name)
            self.logger.info(f"任务日志文件: {log_file}")

        final_status = "failed"
        final_output = ""
        final_error = ""

        for attempt in range(self.settings.retry_count):
            try:
                self.logger.info(f"第 {attempt + 1} 次尝试执行...")
                result = self._execute_command_with_logging()
                self.last_run = datetime.now(pytz.timezone(self.settings.timezone))

                self.logger.info(f"子进程返回码: {result['returncode']}")

                if result['returncode'] == 0:
                    self.last_status = "success"
                    self.last_output = result['stdout']
                    final_status = "completed"
                    final_output = result['stdout']
                    self.logger.info(f"任务 {self.task.name} 执行成功")
                    break
                else:
                    self.last_status = "failed"
                    self.last_output = result['stderr']
                    final_status = "failed"
                    final_error = result['stderr']
                    self.logger.error(f"任务 {self.task.name} 执行失败")

                    if attempt < self.settings.retry_count - 1:
                        self.logger.info(f"{self.settings.retry_delay}秒后重试...")
                        time.sleep(self.settings.retry_delay)

            except subprocess.TimeoutExpired as e:
                self.last_status = "timeout"
                self.last_output = f"任务执行超时 ({self.task.timeout}秒)"
                final_status = "timeout"
                final_error = f"任务执行超时 ({self.task.timeout}秒)"
                self.logger.error(f"任务 {self.task.name} 执行超时 ({self.task.timeout}秒)")

                if attempt < self.settings.retry_count - 1:
                    time.sleep(self.settings.retry_delay)

            except Exception as e:
                self.last_status = "error"
                self.last_output = str(e)
                final_status = "error"
                final_error = str(e)
                self.logger.error(f"任务 {self.task.name} 执行异常: {e}")

                if attempt < self.settings.retry_count - 1:
                    time.sleep(self.settings.retry_delay)

        # 结束任务日志记录
        if TASK_LOG_AVAILABLE and task_log_manager:
            task_log_manager.end_task_log(self.task.id, final_status)

        # 记录任务结束到监控器
        if TASK_MONITOR_AVAILABLE and task_monitor:
            task_monitor.end_task(
                task_id=self.task.id,
                status=final_status,
                output=final_output,
                error=final_error
            )

        self.logger.info(f"任务 {self.task.name} 执行结束，最终状态: {self.last_status}")
        self.running = False

    def _execute_command_with_logging(self) -> dict:
        """
        执行命令并实时捕获输出到日志文件
        
        Returns:
            dict: 包含 returncode, stdout, stderr
        """
        work_dir = Path(self.task.working_directory).expanduser().resolve()
        
        # 设置环境变量，确保子进程使用 UTF-8 编码
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['LANG'] = 'en_US.UTF-8'
        
        self.logger.info(f"启动子进程: {self.task.command}")
        
        # 使用 Popen 启动子进程，捕获输出
        process = subprocess.Popen(
            self.task.command,
            shell=True,
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        stdout_lines = []
        stderr_lines = []
        
        # 创建线程实时读取输出
        def read_stdout():
            try:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        line_str = line.rstrip('\n\r')
                        stdout_lines.append(line_str)
                        if TASK_LOG_AVAILABLE and task_log_manager:
                            task_log_manager.write_log(self.task.id, line_str, is_error=False)
            except Exception as e:
                self.logger.error(f"读取stdout失败: {e}")
        
        def read_stderr():
            try:
                for line in iter(process.stderr.readline, ''):
                    if line:
                        line_str = line.rstrip('\n\r')
                        stderr_lines.append(line_str)
                        if TASK_LOG_AVAILABLE and task_log_manager:
                            task_log_manager.write_log(self.task.id, line_str, is_error=True)
            except Exception as e:
                self.logger.error(f"读取stderr失败: {e}")
        
        # 启动读取线程
        stdout_thread = Thread(target=read_stdout, daemon=True)
        stderr_thread = Thread(target=read_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()
        
        # 等待进程完成或超时
        try:
            returncode = process.wait(timeout=self.task.timeout)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            returncode = -1  # 超时标记
        
        # 等待读取线程完成
        stdout_thread.join(timeout=2)
        stderr_thread.join(timeout=2)
        
        # 关闭管道
        try:
            process.stdout.close()
            process.stderr.close()
        except:
            pass
        
        return {
            'returncode': returncode,
            'stdout': '\n'.join(stdout_lines),
            'stderr': '\n'.join(stderr_lines)
        }


class TaskScheduler:
    def __init__(self, config_path: str = "scheduler/config.json"):
        self.config_path = Path(config_path)
        self.tasks: Dict[str, TaskRunner] = {}
        self.settings: Optional[SchedulerSettings] = None
        self.running = False
        self.lock = Lock()
        self.scheduler_thread: Optional[Thread] = None
        self.config_watcher: Optional[ConfigWatcher] = None
        self.logger = logging.getLogger("TaskScheduler")
        
        self._setup_logging()
        self._load_config()

    def _setup_logging(self):
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('scheduler/scheduler.log', encoding='utf-8')
            ]
        )

    def _load_config(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
            
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        self.settings = SchedulerSettings(config.get('settings', {}))
        
        for task_dict in config.get('tasks', []):
            task = TaskConfig(task_dict)
            self.tasks[task.id] = TaskRunner(task, self.settings)
            
        self.logger.info(f"已加载 {len(self.tasks)} 个任务")

    def reload_config(self):
        self.logger.info("重新加载配置...")
        with self.lock:
            self.tasks.clear()
            self._load_config()
            if self.running:
                schedule.clear()
                self._schedule_tasks()

    def _schedule_tasks(self):
        for task_id, runner in self.tasks.items():
            task = runner.task
            if not task.enabled:
                continue
                
            schedule_type = task.schedule.get('type')
            
            if schedule_type == 'cron':
                self._schedule_cron(task, runner)
            elif schedule_type == 'interval':
                self._schedule_interval(task, runner)
            elif schedule_type == 'daily':
                self._schedule_daily(task, runner)
            else:
                self.logger.warning(f"未知的调度类型: {schedule_type}")

    def _schedule_cron(self, task: TaskConfig, runner: TaskRunner):
        expression = task.schedule.get('expression', '')
        parts = expression.split()
        
        if len(parts) == 5:
            minute, hour, day, month, day_of_week = parts
            
            job = schedule.every()
            
            if day_of_week != '*':
                job = job.day_of_week
            elif day != '*':
                job = job.day
                
            job.at(f"{hour}:{minute}").do(self._run_task, runner)
            self.logger.info(f"已设置 cron 任务: {task.name} ({expression})")
        else:
            self.logger.error(f"无效的 cron 表达式: {expression}")

    def _schedule_interval(self, task: TaskConfig, runner: TaskRunner):
        minutes = task.schedule.get('minutes', 60)
        schedule.every(minutes).minutes.do(self._run_task, runner)
        self.logger.info(f"已设置间隔任务: {task.name} (每 {minutes} 分钟)")

    def _schedule_daily(self, task: TaskConfig, runner: TaskRunner):
        time_str = task.schedule.get('time', '00:00')
        schedule.every().day.at(time_str).do(self._run_task, runner)
        self.logger.info(f"已设置每日任务: {task.name} (每天 {time_str})")

    def _run_task(self, runner: TaskRunner):
        if runner.running:
            self.logger.warning(f"任务 {runner.task.name} 正在运行中，跳过本次执行")
            return
            
        thread = Thread(target=runner.run, daemon=True)
        thread.start()

    def start(self, watch_config: bool = True):
        if self.running:
            self.logger.warning("调度器已在运行")
            return
            
        self.running = True
        self._schedule_tasks()
        
        self.scheduler_thread = Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        # 启动配置文件监控
        if watch_config:
            self.config_watcher = ConfigWatcher(self, check_interval=5)
            self.config_watcher.start_watching()
        
        self.logger.info("调度器已启动")

    def _run_scheduler(self):
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"调度器异常: {e}")
                time.sleep(5)

    def stop(self):
        self.running = False
        if self.config_watcher:
            self.config_watcher.stop_watching()
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        schedule.clear()
        self.logger.info("调度器已停止")

    def get_task_status(self) -> List[dict]:
        status_list = []
        for task_id, runner in self.tasks.items():
            status_list.append({
                'id': task_id,
                'name': runner.task.name,
                'enabled': runner.task.enabled,
                'running': runner.running,
                'last_run': runner.last_run.isoformat() if runner.last_run else None,
                'last_status': runner.last_status,
                'last_output': runner.last_output[:500] if runner.last_output else None
            })
        return status_list

    def run_task_now(self, task_id: str):
        if task_id not in self.tasks:
            raise ValueError(f"任务不存在: {task_id}")
            
        runner = self.tasks[task_id]
        thread = Thread(target=runner.run, daemon=True)
        thread.start()
        return True


if __name__ == "__main__":
    scheduler = TaskScheduler()
    
    try:
        scheduler.start()
        
        while True:
            time.sleep(10)
            status = scheduler.get_task_status()
            for s in status:
                print(f"任务: {s['name']}, 状态: {s['last_status']}, 最后运行: {s['last_run']}")
                
    except KeyboardInterrupt:
        print("\n正在停止调度器...")
        scheduler.stop()
