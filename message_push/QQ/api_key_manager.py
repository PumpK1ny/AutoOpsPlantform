"""
API密钥管理器 - 支持多API密钥管理和自动轮换

功能：
1. 支持配置多个API密钥（通过逗号分隔的环境变量）
2. 当检测到429速率限制错误时，自动切换至下一个API密钥
3. 确保每个API密钥同一时间只被一个请求使用
4. 自动选择空闲密钥，全部繁忙时等待
"""

import os
import asyncio
import time
import threading
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from dotenv import load_dotenv
from zhipuai import ZhipuAI

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
    rate_limited_until: Optional[float] = None
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


class RotatingZhipuClient:
    """
    支持密钥轮换的智谱AI客户端
    
    当检测到429错误时，自动切换到下一个可用密钥
    """
    
    def __init__(self, api_keys: List[APIKeyInfo]):
        self._api_keys = api_keys
        self._current_index = 0
        self._lock = threading.Lock()
        
    def _get_current_key(self) -> APIKeyInfo:
        """获取当前密钥"""
        with self._lock:
            return self._api_keys[self._current_index]
    
    def _rotate_to_next_key(self) -> APIKeyInfo:
        """切换到下一个可用密钥"""
        with self._lock:
            original_index = self._current_index
            for i in range(1, len(self._api_keys) + 1):
                next_index = (self._current_index + i) % len(self._api_keys)
                key_info = self._api_keys[next_index]
                # 检查密钥是否被速率限制
                if key_info.rate_limited_until and time.time() < key_info.rate_limited_until:
                    continue
                self._current_index = next_index
                return self._api_keys[self._current_index]
            # 所有密钥都被限制，返回原始密钥
            return self._api_keys[original_index]
    
    def _mark_rate_limited(self, key_info: APIKeyInfo, cooldown_seconds: int = 60):
        """标记密钥被速率限制"""
        key_info.rate_limited_until = time.time() + cooldown_seconds
        key_info.error_count += 1
    
    def _is_rate_limit_error(self, error_str: str) -> bool:
        """检查是否为速率限制错误"""
        rate_limit_indicators = ["429", "1302", "1305", "并发数过高", "请求过多", "rate limit"]
        return any(indicator in error_str.lower() for indicator in rate_limit_indicators)
    
    def _create_zhipu_client(self, key_info: APIKeyInfo) -> ZhipuAI:
        """创建ZhipuAI客户端"""
        return ZhipuAI(api_key=key_info.key)
    
    def chat_completions_create(self, **kwargs):
        """
        调用chat.completions.create，支持自动密钥轮换
        
        当遇到429错误时，会自动切换到下一个密钥重试
        """
        max_retries = len(self._api_keys) * 2  # 最多尝试所有密钥的两倍次数
        last_error = None
        
        for attempt in range(max_retries):
            key_info = self._get_current_key()
            
            try:
                client = self._create_zhipu_client(key_info)
                key_info.request_count += 1
                response = client.chat.completions.create(**kwargs)
                return response
                
            except Exception as e:
                error_str = str(e)
                last_error = e
                
                if self._is_rate_limit_error(error_str):
                    # 标记当前密钥被限制并轮换
                    self._mark_rate_limited(key_info)
                    key_info = self._rotate_to_next_key()
                    
                    # 如果还有可用密钥，继续重试
                    if key_info.rate_limited_until is None or time.time() >= key_info.rate_limited_until:
                        time.sleep(0.5)  # 短暂延迟后重试
                        continue
                
                # 非速率限制错误，直接抛出
                raise
        
        # 所有密钥都尝试过，抛出最后一个错误
        if last_error:
            raise last_error
        raise Exception("所有API密钥均不可用")


class APIKeyManager:
    """
    API密钥管理器
    
    使用方法：
    1. 在.env中配置多个密钥（ZHIPU_API_KEY=key1,key2,key3）
    2. 调用 get_api_key() 获取可用密钥（无限等待）
    3. 使用完成后调用 release_api_key() 释放
    4. 使用 create_rotating_client() 创建支持自动轮换的客户端
    """

    def __init__(self):
        self._keys: Dict[str, APIKeyInfo] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._initialized = False
        self._key_count = 0
        self._user_tracker = UserRequestTracker()
        self._rotating_client: Optional[RotatingZhipuClient] = None

    def _ensure_initialized(self):
        """确保已初始化（同步方法）"""
        if self._initialized:
            return
        
        self._keys.clear()
        
        # 从环境变量读取密钥，支持逗号分隔的多个密钥
        main_key_env = os.getenv("ZHIPU_API_KEY", "")
        if main_key_env:
            # 分割多个密钥
            keys = [k.strip() for k in main_key_env.split(",") if k.strip()]
            for i, key in enumerate(keys):
                key_name = f"ZHIPU_API_KEY_{i}" if i > 0 else "ZHIPU_API_KEY"
                self._keys[key_name] = APIKeyInfo(name=key_name, key=key)
        
        # 向后兼容：检查旧的ZHIPU_API_KEY_N格式
        index = 1
        while True:
            key_env = f"ZHIPU_API_KEY_{index}"
            key_value = os.getenv(key_env)
            if key_value and key_env not in self._keys:
                self._keys[key_env] = APIKeyInfo(name=key_env, key=key_value)
                index += 1
            else:
                break
        
        self._initialized = True
        self._key_count = len(self._keys)
        
        # 创建轮换客户端
        if self._keys:
            self._rotating_client = RotatingZhipuClient(list(self._keys.values()))
        
        print(f"✅ 已加载 {self._key_count} 个API密钥")

    def create_rotating_client(self) -> Optional[RotatingZhipuClient]:
        """
        创建支持密钥轮换的客户端
        
        Returns:
            RotatingZhipuClient: 支持自动密钥轮换的客户端
        """
        self._ensure_initialized()
        return self._rotating_client
    
    def get_single_key(self) -> Optional[str]:
        """
        获取单个API密钥（用于简单场景）
        
        Returns:
            str: 第一个可用的API密钥
        """
        self._ensure_initialized()
        if self._keys:
            return list(self._keys.values())[0].key
        return None

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


# 全局API密钥管理器实例
api_key_manager = APIKeyManager()


def get_wait_time_estimate() -> int:
    """估算当前需要等待的时间（秒）"""
    status = api_key_manager.get_status()
    queue_size = status["queue_size"]
    busy_keys = status["busy_keys"]
    
    if queue_size == 0 and busy_keys == 0:
        return 0
    
    return (queue_size + 1) * 5


def create_zhipu_client_with_rotation() -> Optional[RotatingZhipuClient]:
    """
    创建支持密钥轮换的智谱AI客户端
    
    Returns:
        RotatingZhipuClient: 支持自动密钥轮换的客户端，如果未配置密钥则返回None
    """
    return api_key_manager.create_rotating_client()


def get_api_key_simple() -> Optional[str]:
    """
    简单获取API密钥（用于非异步场景）
    
    Returns:
        str: 第一个可用的API密钥，如果未配置则返回None
    """
    return api_key_manager.get_single_key()
