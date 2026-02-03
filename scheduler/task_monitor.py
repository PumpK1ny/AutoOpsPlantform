"""
任务监控模块 - 用于追踪和管理所有正在运行的任务
支持历史记录持久化到文件
"""
import json
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class TaskExecution:
    """任务执行记录"""
    task_id: str
    task_name: str
    task_type: str  # 'scheduled' - 定时任务, 'manual' - 手动运行
    start_time: datetime
    pid: Optional[int] = None
    status: str = "running"  # running, completed, failed, timeout
    output: str = ""
    error: str = ""
    end_time: Optional[datetime] = None


class TaskMonitor:
    """
    任务监控器 - 单例模式
    用于追踪所有正在运行和最近完成的任务
    支持历史记录持久化
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
    
    def __init__(self, history_file: str = "scheduler/task_history.json"):
        if self._initialized:
            return
        
        self._initialized = True
        self._running_tasks: Dict[str, TaskExecution] = {}
        self._task_history: List[TaskExecution] = []
        self._max_history = 100  # 最多保留100条历史记录
        self._lock = threading.Lock()
        self._history_lock = threading.Lock()
        
        # 历史记录文件路径
        self._history_file = Path(history_file)
        self._ensure_history_dir()
        
        # 加载历史记录
        self._load_history()
    
    def _ensure_history_dir(self):
        """确保历史记录目录存在"""
        try:
            self._history_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"创建历史记录目录失败: {e}")
    
    def _load_history(self):
        """从文件加载历史记录"""
        try:
            if self._history_file.exists():
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for item in data.get('history', []):
                    execution = TaskExecution(
                        task_id=item.get('task_id', ''),
                        task_name=item.get('task_name', ''),
                        task_type=item.get('task_type', 'scheduled'),
                        start_time=datetime.fromisoformat(item['start_time']) if item.get('start_time') else datetime.now(),
                        pid=item.get('pid'),
                        status=item.get('status', 'completed'),
                        output=item.get('output', ''),
                        error=item.get('error', ''),
                        end_time=datetime.fromisoformat(item['end_time']) if item.get('end_time') else None
                    )
                    self._task_history.append(execution)
                
                # 限制历史记录数量
                if len(self._task_history) > self._max_history:
                    self._task_history = self._task_history[:self._max_history]
                
                print(f"已加载 {len(self._task_history)} 条任务历史记录")
        except Exception as e:
            print(f"加载任务历史记录失败: {e}")
    
    def _save_history(self):
        """保存历史记录到文件"""
        try:
            with self._history_lock:
                data = {
                    'last_updated': datetime.now().isoformat(),
                    'history': []
                }
                
                for task in self._task_history:
                    data['history'].append({
                        'task_id': task.task_id,
                        'task_name': task.task_name,
                        'task_type': task.task_type,
                        'status': task.status,
                        'pid': task.pid,
                        'start_time': task.start_time.isoformat() if task.start_time else None,
                        'end_time': task.end_time.isoformat() if task.end_time else None,
                        'output': task.output[:1000] if task.output else '',  # 限制保存长度
                        'error': task.error[:1000] if task.error else ''
                    })
                
                with open(self._history_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存任务历史记录失败: {e}")
    
    def start_task(self, task_id: str, task_name: str, task_type: str = "scheduled", pid: Optional[int] = None) -> TaskExecution:
        """
        记录任务开始执行
        
        Args:
            task_id: 任务ID
            task_name: 任务名称
            task_type: 任务类型 ('scheduled' 或 'manual')
            pid: 进程ID
        
        Returns:
            TaskExecution: 任务执行记录
        """
        execution = TaskExecution(
            task_id=task_id,
            task_name=task_name,
            task_type=task_type,
            start_time=datetime.now(),
            pid=pid,
            status="running"
        )
        
        with self._lock:
            self._running_tasks[task_id] = execution
        
        return execution
    
    def end_task(self, task_id: str, status: str = "completed", output: str = "", error: str = ""):
        """
        记录任务结束
        
        Args:
            task_id: 任务ID
            status: 结束状态 (completed, failed, timeout)
            output: 任务输出
            error: 错误信息
        """
        with self._lock:
            if task_id in self._running_tasks:
                execution = self._running_tasks.pop(task_id)
                execution.status = status
                execution.output = output
                execution.error = error
                execution.end_time = datetime.now()
                
                # 添加到历史记录
                with self._history_lock:
                    self._task_history.insert(0, execution)
                    # 限制历史记录数量
                    if len(self._task_history) > self._max_history:
                        self._task_history = self._task_history[:self._max_history]
                
                # 保存到文件
                self._save_history()
    
    def update_task_output(self, task_id: str, output: str):
        """更新任务输出"""
        with self._lock:
            if task_id in self._running_tasks:
                self._running_tasks[task_id].output = output
    
    def update_task_pid(self, task_id: str, pid: int):
        """更新任务进程ID"""
        with self._lock:
            if task_id in self._running_tasks:
                self._running_tasks[task_id].pid = pid
    
    def get_running_tasks(self) -> List[Dict]:
        """获取所有正在运行的任务"""
        with self._lock:
            return [self._task_to_dict(task) for task in self._running_tasks.values()]
    
    def get_task_history(self, limit: int = 20) -> List[Dict]:
        """获取任务历史记录"""
        with self._history_lock:
            return [self._task_to_dict(task) for task in self._task_history[:limit]]
    
    def is_task_running(self, task_id: str) -> bool:
        """检查任务是否正在运行"""
        with self._lock:
            return task_id in self._running_tasks
    
    def get_running_count(self) -> int:
        """获取正在运行的任务数量"""
        with self._lock:
            return len(self._running_tasks)
    
    def _task_to_dict(self, task: TaskExecution) -> Dict:
        """将任务执行记录转换为字典"""
        data = {
            "task_id": task.task_id,
            "task_name": task.task_name,
            "task_type": task.task_type,
            "status": task.status,
            "pid": task.pid,
            "start_time": task.start_time.strftime("%Y-%m-%d %H:%M:%S") if task.start_time else None,
            "end_time": task.end_time.strftime("%Y-%m-%d %H:%M:%S") if task.end_time else None,
            "duration": self._calculate_duration(task),
            "output": task.output[:500] if task.output else "",  # 限制输出长度
            "error": task.error[:500] if task.error else ""
        }
        return data
    
    def _calculate_duration(self, task: TaskExecution) -> Optional[str]:
        """计算任务执行时长"""
        if not task.start_time:
            return None
        
        end = task.end_time or datetime.now()
        duration = end - task.start_time
        
        total_seconds = int(duration.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}秒"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}分{seconds}秒"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}小时{minutes}分"
    
    def clear_history(self):
        """清空历史记录"""
        with self._history_lock:
            self._task_history.clear()
        self._save_history()
    
    def get_summary(self) -> Dict:
        """获取任务监控摘要"""
        with self._lock:
            running_count = len(self._running_tasks)
        
        with self._history_lock:
            history_count = len(self._task_history)
            # 统计最近完成的任务状态
            recent_completed = [t for t in self._task_history if t.status == "completed"][:10]
            recent_failed = [t for t in self._task_history if t.status in ["failed", "timeout"]][:10]
        
        return {
            "running_count": running_count,
            "history_count": history_count,
            "recent_completed": len(recent_completed),
            "recent_failed": len(recent_failed),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


# 全局任务监控器实例
task_monitor = TaskMonitor()


if __name__ == "__main__":
    # 测试代码
    monitor = TaskMonitor()
    
    # 模拟任务开始
    monitor.start_task("task1", "测试任务1", "manual", 12345)
    time.sleep(1)
    
    print("正在运行的任务:", monitor.get_running_tasks())
    print("任务摘要:", monitor.get_summary())
    
    # 模拟任务结束
    monitor.end_task("task1", "completed", "任务执行成功")
    
    print("\n任务历史:", monitor.get_task_history())
    print("\n最终摘要:", monitor.get_summary())
    
    # 验证持久化
    print("\n验证持久化...")
    monitor2 = TaskMonitor()
    print("新实例历史记录数:", len(monitor2.get_task_history()))
