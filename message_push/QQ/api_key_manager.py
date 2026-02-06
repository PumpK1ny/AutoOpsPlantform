"""
API密钥管理器 - 支持多API密钥管理

功能：
1. 支持配置多个API密钥（不同账号）
2. 确保每个API密钥同一时间只被一个请求使用
3. 自动选择空闲密钥
4. 全部繁忙时无限等待，直到有空闲密钥
"""

import os
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


@dataclass
class APIKeyInfo:
    """API密钥信息"""
    name: str
    key: str
    is_busy: bool = False
    busy_since: Optional[datetime] = None
    request_count: int = 0
    error_count: int = 0
    current_user_openid: Optional[str] = None


class UserRequestTracker:
    """用户请求跟踪器 - 用于跟踪每个用户的正在进行的请求"""

    def __init__(self):
        self._user_requests: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

    def add_request(self, user_openid: str, task: asyncio.Task, api_key_name: str):
        """添加用户请求"""
        if user_openid in self._user_requests:
            old_task = self._user_requests[user_openid].get("task")
            if old_task and not old_task.done():
                old_task.cancel()
        self._user_requests[user_openid] = {
            "task": task,
            "api_key_name": api_key_name,
            "created_at": datetime.now()
        }

    def get_request(self, user_openid: str) -> Optional[dict]:
        """获取用户正在进行的请求"""
        return self._user_requests.get(user_openid)

    def remove_request(self, user_openid: str):
        """移除用户请求记录"""
        if user_openid in self._user_requests:
            del self._user_requests[user_openid]

    def is_processing(self, user_openid: str) -> bool:
        """检查用户是否有正在进行的请求"""
        req = self._user_requests.get(user_openid)
        return req is not None and not req.get("task", asyncio.Future()).done()

    def cancel_request(self, user_openid: str) -> bool:
        """取消用户正在进行的请求"""
        req = self._user_requests.get(user_openid)
        if req and req.get("task"):
            try:
                req["task"].cancel()
                return True
            except Exception:
                pass
        return False


class APIKeyManager:
    """
    API密钥管理器
    
    使用方法：
    1. 在.env中配置多个密钥（ZHIPU_API_KEY_1, ZHIPU_API_KEY_2, ...）
    2. 调用 get_api_key() 获取可用密钥（无限等待）
    3. 使用完成后调用 release_api_key() 释放
    """

    def __init__(self):
        self._keys: Dict[str, APIKeyInfo] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._initialized = False
        self._key_count = 0
        self._user_tracker = UserRequestTracker()

    def _ensure_initialized(self):
        """确保已初始化（同步方法）"""
        if self._initialized:
            return
        
        self._keys.clear()
        
        main_key = os.getenv("ZHIPU_API_KEY")
        if main_key:
            self._keys["ZHIPU_API_KEY"] = APIKeyInfo(name="ZHIPU_API_KEY", key=main_key)
        
        index = 1
        while True:
            key_env = f"ZHIPU_API_KEY_{index}"
            key_value = os.getenv(key_env)
            if key_value:
                self._keys[key_env] = APIKeyInfo(name=key_env, key=key_value)
                index += 1
            else:
                break
        
        self._initialized = True
        self._key_count = len(self._keys)
        print(f"✅ 已加载 {self._key_count} 个API密钥")

    async def get_api_key(self) -> Optional[APIKeyInfo]:
        """
        获取可用的API密钥（无限等待）
        
        如果所有密钥都繁忙，会一直等待直到有空闲密钥
        
        Returns:
            APIKeyInfo: 可用的密钥信息
        """
        self._ensure_initialized()
        
        while True:
            async with self._lock:
                for key_name, key_info in self._keys.items():
                    if not key_info.is_busy:
                        key_info.is_busy = True
                        key_info.busy_since = datetime.now()
                        key_info.request_count += 1
                        return key_info
            
            await self._queue.get()

    async def release_api_key(self, key_info: APIKeyInfo):
        """释放API密钥，并唤醒等待的请求"""
        async with self._lock:
            for name, info in self._keys.items():
                if info.key == key_info.key:
                    info.is_busy = False
                    info.busy_since = None
                    break
        
        if not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass

    def mark_success(self, key_info: APIKeyInfo):
        """标记请求成功"""
        pass

    def mark_error(self, key_info: APIKeyInfo, error: str):
        """标记请求失败"""
        key_info.error_count += 1

    def is_user_processing(self, user_openid: str) -> bool:
        """检查用户是否有正在进行的请求"""
        return self._user_tracker.is_processing(user_openid)

    def cancel_user_request(self, user_openid: str) -> bool:
        """取消用户正在进行的请求"""
        return self._user_tracker.cancel_request(user_openid)

    def register_user_request(self, user_openid: str, task: asyncio.Task, api_key_name: str):
        """注册用户请求（用于跟踪）"""
        self._user_tracker.add_request(user_openid, task, api_key_name)

    def unregister_user_request(self, user_openid: str):
        """注销用户请求"""
        self._user_tracker.remove_request(user_openid)

    def get_status(self) -> Dict[str, Any]:
        """获取管理器状态（同步方法，可从异步上下文中调用）"""
        self._ensure_initialized()
        busy_count = 0
        for key_info in self._keys.values():
            if key_info.is_busy:
                busy_count += 1
        
        total_requests = sum(k.request_count for k in self._keys.values())
        total_errors = sum(k.error_count for k in self._keys.values())
        
        return {
            "total_keys": self._key_count,
            "busy_keys": busy_count,
            "free_keys": self._key_count - busy_count,
            "queue_size": self._queue.qsize(),
            "total_requests": total_requests,
            "total_errors": total_errors,
            "is_full": busy_count >= self._key_count if self._key_count > 0 else False
        }

    def get_all_keys_status(self) -> List[Dict[str, Any]]:
        """获取所有密钥状态（同步方法）"""
        self._ensure_initialized()
        return [
            {
                "name": name,
                "busy": info.is_busy,
                "requests": info.request_count,
                "errors": info.error_count
            }
            for name, info in self._keys.items()
        ]


api_key_manager = APIKeyManager()


def get_wait_time_estimate() -> int:
    """估算当前需要等待的时间（秒）"""
    status = api_key_manager.get_status()
    queue_size = status["queue_size"]
    busy_keys = status["busy_keys"]
    
    if queue_size == 0 and busy_keys == 0:
        return 0
    
    return (queue_size + 1) * 5
