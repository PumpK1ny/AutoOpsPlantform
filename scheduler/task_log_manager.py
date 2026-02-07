"""
任务日志管理模块
管理每个任务的独立日志文件，支持实时写入和读取
"""
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
import json


class TaskLogManager:
    """
    任务日志管理器 - 单例模式
    管理每个任务的日志文件，支持实时写入
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, logs_dir: str = "logs/tasks"):
        if self._initialized:
            return
        
        self._initialized = True
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # 当前正在写入的日志文件句柄 {task_id: file_handle}
        self._active_logs: Dict[str, tuple] = {}  # (file_path, file_handle, start_time)
        self._active_logs_lock = threading.Lock()
        
        # 保留日志文件数量
        self._max_logs_per_task = 10
        
        # 启动清理线程
        self._cleanup_thread = threading.Thread(target=self._cleanup_old_logs_loop, daemon=True)
        self._cleanup_thread.start()
    
    def _get_task_log_dir(self, task_id: str) -> Path:
        """获取任务的日志目录"""
        task_dir = self.logs_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir
    
    def start_task_log(self, task_id: str, task_name: str) -> str:
        """
        开始记录任务日志
        
        Args:
            task_id: 任务ID
            task_name: 任务名称
            
        Returns:
            str: 日志文件路径
        """
        task_dir = self._get_task_log_dir(task_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = task_dir / f"{timestamp}.log"
        
        # 创建日志文件并写入头部信息
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"{'='*60}\n")
            f.write(f"任务: {task_name}\n")
            f.write(f"任务ID: {task_id}\n")
            f.write(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*60}\n\n")
            f.flush()
        
        # 记录到活跃日志
        with self._active_logs_lock:
            # 如果该任务已有活跃日志，先关闭
            if task_id in self._active_logs:
                old_path, old_handle, _ = self._active_logs[task_id]
                try:
                    old_handle.close()
                except:
                    pass
            
            # 以追加模式打开新日志文件
            file_handle = open(log_file, 'a', encoding='utf-8')
            self._active_logs[task_id] = (str(log_file), file_handle, datetime.now())
        
        # 更新 latest.log 软链接/快捷方式
        self._update_latest_link(task_id, log_file)
        
        return str(log_file)
    
    def _update_latest_link(self, task_id: str, log_file: Path):
        """更新 latest.log 链接指向最新的日志文件"""
        task_dir = self._get_task_log_dir(task_id)
        latest_link = task_dir / "latest.log"
        
        try:
            # 写入一个指向最新日志的元数据文件
            meta_file = task_dir / "latest.json"
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'latest_log': str(log_file.name),
                    'updated_at': datetime.now().isoformat()
                }, f)
        except Exception as e:
            print(f"更新 latest 链接失败: {e}")
    
    def write_log(self, task_id: str, content: str, is_error: bool = False):
        """
        写入日志内容
        
        Args:
            task_id: 任务ID
            content: 日志内容
            is_error: 是否是错误输出
        """
        with self._active_logs_lock:
            if task_id not in self._active_logs:
                return
            
            _, file_handle, _ = self._active_logs[task_id]
            
            try:
                timestamp = datetime.now().strftime("%H:%M:%S")
                prefix = "[ERR]" if is_error else "[OUT]"
                file_handle.write(f"{timestamp} {prefix} {content}")
                if not content.endswith('\n'):
                    file_handle.write('\n')
                file_handle.flush()
            except Exception as e:
                print(f"写入日志失败: {e}")
    
    def end_task_log(self, task_id: str, status: str = "completed"):
        """
        结束任务日志记录
        
        Args:
            task_id: 任务ID
            status: 任务结束状态
        """
        with self._active_logs_lock:
            if task_id not in self._active_logs:
                return
            
            log_path, file_handle, start_time = self._active_logs[task_id]
            
            try:
                # 写入结束标记
                duration = datetime.now() - start_time
                file_handle.write(f"\n{'='*60}\n")
                file_handle.write(f"任务结束状态: {status}\n")
                file_handle.write(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                file_handle.write(f"执行时长: {duration}\n")
                file_handle.write(f"{'='*60}\n")
                file_handle.flush()
                file_handle.close()
            except Exception as e:
                print(f"结束日志失败: {e}")
            finally:
                del self._active_logs[task_id]
    
    def get_task_logs(self, task_id: str) -> List[Dict]:
        """
        获取任务的所有日志文件列表
        
        Args:
            task_id: 任务ID
            
        Returns:
            List[Dict]: 日志文件列表
        """
        task_dir = self._get_task_log_dir(task_id)
        logs = []
        
        try:
            for log_file in sorted(task_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True):
                stat = log_file.stat()
                logs.append({
                    'filename': log_file.name,
                    'path': str(log_file),
                    'size': self._format_size(stat.st_size),
                    'created': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'is_latest': self._is_latest_log(task_id, log_file.name)
                })
        except Exception as e:
            print(f"获取任务日志列表失败: {e}")
        
        return logs
    
    def _is_latest_log(self, task_id: str, filename: str) -> bool:
        """检查是否是最近的日志文件"""
        task_dir = self._get_task_log_dir(task_id)
        meta_file = task_dir / "latest.json"
        
        try:
            if meta_file.exists():
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    return meta.get('latest_log') == filename
        except:
            pass
        
        return False
    
    def get_log_content(self, task_id: str, log_filename: str, lines: int = 100) -> str:
        """
        获取日志文件内容
        
        Args:
            task_id: 任务ID
            log_filename: 日志文件名
            lines: 返回最后多少行
            
        Returns:
            str: 日志内容
        """
        task_dir = self._get_task_log_dir(task_id)
        log_file = task_dir / log_filename
        
        if not log_file.exists():
            return "日志文件不存在"
        
        try:
            # 检查是否是当前活跃日志
            with self._active_logs_lock:
                if task_id in self._active_logs:
                    active_path, active_handle, _ = self._active_logs[task_id]
                    if active_path == str(log_file):
                        # 是当前活跃日志，需要先刷新缓冲区
                        active_handle.flush()
            
            # 读取文件内容
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        except Exception as e:
            return f"读取日志失败: {e}"
    
    def get_latest_log_content(self, task_id: str, lines: int = 100) -> str:
        """获取最新日志内容"""
        task_dir = self._get_task_log_dir(task_id)
        meta_file = task_dir / "latest.json"
        
        try:
            if meta_file.exists():
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    latest_log = meta.get('latest_log')
                    if latest_log:
                        return self.get_log_content(task_id, latest_log, lines)
        except:
            pass
        
        # 如果没有元数据文件，找最新的日志文件
        logs = self.get_task_logs(task_id)
        if logs:
            return self.get_log_content(task_id, logs[0]['filename'], lines)
        
        return "暂无日志"
    
    def is_task_running(self, task_id: str) -> bool:
        """检查任务是否正在运行（有活跃日志）"""
        with self._active_logs_lock:
            return task_id in self._active_logs
    
    def _cleanup_old_logs_loop(self):
        """定期清理旧日志的循环"""
        while True:
            time.sleep(3600)  # 每小时检查一次
            self._cleanup_old_logs()
    
    def _cleanup_old_logs(self):
        """清理每个任务的旧日志文件，只保留最近的N个"""
        try:
            for task_dir in self.logs_dir.iterdir():
                if not task_dir.is_dir():
                    continue
                
                # 获取所有日志文件（按修改时间排序）
                log_files = sorted(
                    task_dir.glob("*.log"),
                    key=lambda x: x.stat().st_mtime,
                    reverse=True
                )
                
                # 删除旧的日志文件
                for old_file in log_files[self._max_logs_per_task:]:
                    try:
                        old_file.unlink()
                        print(f"清理旧日志: {old_file}")
                    except Exception as e:
                        print(f"删除旧日志失败: {old_file}, {e}")
        except Exception as e:
            print(f"清理旧日志失败: {e}")
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# 全局任务日志管理器实例
task_log_manager = TaskLogManager()


if __name__ == "__main__":
    # 测试代码
    manager = TaskLogManager()
    
    # 模拟任务日志
    task_id = "test_task"
    task_name = "测试任务"
    
    log_file = manager.start_task_log(task_id, task_name)
    print(f"日志文件: {log_file}")
    
    # 模拟写入日志
    for i in range(5):
        manager.write_log(task_id, f"这是第 {i+1} 行输出")
        time.sleep(0.5)
    
    manager.write_log(task_id, "这是一个错误", is_error=True)
    
    # 结束日志
    manager.end_task_log(task_id, "completed")
    
    # 读取日志
    print("\n日志内容:")
    print(manager.get_latest_log_content(task_id))
    
    # 获取日志列表
    print("\n日志列表:")
    for log in manager.get_task_logs(task_id):
        print(f"  {log}")
