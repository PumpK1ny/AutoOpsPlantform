"""
API密钥管理器 - 支持多API密钥管理（项目级别，跨进程）

功能：
1. 支持配置多个API密钥（不同账号）
2. 确保每个API密钥同一时间只被一个请求使用（跨进程）
3. 使用文件锁实现进程间同步
4. 自动选择空闲密钥
5. 全部繁忙时无限等待，直到有空闲密钥
6. 提供统一的 ZhipuAI 客户端获取接口

使用方法：
1. 在.env中配置多个密钥（ZHIPU_API_KEY_1, ZHIPU_API_KEY_2, ...）
2. 使用 get_sync_client_managed() 获取带管理的客户端（同步版本）
3. 使用完成后客户端会自动释放密钥
"""

import os
import asyncio
import time
import threading
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv
from zhipuai import ZhipuAI
from filelock import FileLock, Timeout

load_dotenv()

# 锁文件目录
LOCK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".api_key_locks")
os.makedirs(LOCK_DIR, exist_ok=True)


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


class CrossProcessAPIKeyManager:
    """
    跨进程API密钥管理器

    使用文件锁实现进程间同步，确保同一时间只有一个进程使用某个API密钥
    """

    def __init__(self):
        self._keys: Dict[str, APIKeyInfo] = {}
        self._initialized = False
        self._key_count = 0
        self._local_lock = threading.Lock()

    def _ensure_initialized(self):
        """确保已初始化"""
        if self._initialized:
            return

        with self._local_lock:
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
            if self._key_count > 0:
                print(f"✅ 已加载 {self._key_count} 个API密钥")

    def _get_lock_file(self, key_name: str) -> str:
        """获取锁文件路径"""
        return os.path.join(LOCK_DIR, f"{key_name}.lock")

    def get_available_key(self, timeout: Optional[float] = None) -> Optional[APIKeyInfo]:
        """
        获取可用的API密钥（跨进程安全）

        Args:
            timeout: 超时时间（秒），None表示无限等待

        Returns:
            APIKeyInfo: 可用的密钥信息，获取锁失败返回None
        """
        self._ensure_initialized()

        start_time = time.time()

        while True:
            # 尝试所有密钥
            for key_name, key_info in self._keys.items():
                lock_file = self._get_lock_file(key_name)
                lock = FileLock(lock_file)

                try:
                    # 尝试非阻塞获取锁
                    lock.acquire(timeout=0.1)
                    # 获取锁成功，返回这个密钥
                    key_info.is_busy = True
                    key_info.busy_since = datetime.now()
                    key_info.request_count += 1
                    # 将锁对象附加到key_info上，方便后续释放
                    key_info._lock = lock
                    return key_info
                except Timeout:
                    # 锁被占用，尝试下一个
                    continue

            # 所有密钥都被占用，检查超时
            if timeout and (time.time() - start_time) >= timeout:
                return None

            # 等待后重试
            time.sleep(0.2)

    def release_key(self, key_info: APIKeyInfo):
        """
        释放API密钥

        Args:
            key_info: 要释放的密钥信息
        """
        if hasattr(key_info, '_lock') and key_info._lock:
            try:
                key_info._lock.release()
            except:
                pass
            key_info._lock = None
        key_info.is_busy = False
        key_info.busy_since = None

    def get_status(self) -> Dict[str, Any]:
        """获取管理器状态"""
        self._ensure_initialized()

        # 检查每个密钥的锁状态
        busy_count = 0
        for key_name in self._keys.keys():
            lock_file = self._get_lock_file(key_name)
            lock = FileLock(lock_file)
            try:
                lock.acquire(timeout=0)
                # 锁空闲，立即释放
                lock.release()
            except Timeout:
                # 锁被占用
                busy_count += 1

        total_requests = sum(k.request_count for k in self._keys.values())
        total_errors = sum(k.error_count for k in self._keys.values())

        return {
            "total_keys": self._key_count,
            "busy_keys": busy_count,
            "free_keys": self._key_count - busy_count,
            "total_requests": total_requests,
            "total_errors": total_errors,
            "is_full": busy_count >= self._key_count if self._key_count > 0 else False
        }

    def get_all_keys_status(self) -> List[Dict[str, Any]]:
        """获取所有密钥状态"""
        self._ensure_initialized()

        result = []
        for name, info in self._keys.items():
            lock_file = self._get_lock_file(name)
            lock = FileLock(lock_file)
            try:
                lock.acquire(timeout=0)
                is_busy = False
                lock.release()
            except Timeout:
                is_busy = True

            result.append({
                "name": name,
                "busy": is_busy,
                "requests": info.request_count,
                "errors": info.error_count
            })
        return result


# 全局管理器实例（跨进程）
cross_process_manager = CrossProcessAPIKeyManager()


class ManagedZhipuClient:
    """
    托管的ZhipuAI客户端（同步版本，跨进程安全）

    使用示例：
        with ManagedZhipuClient() as client:
            response = client.chat.completions.create(...)
    """

    def __init__(self, timeout: Optional[float] = None):
        self.timeout = timeout
        self._key_info: Optional[APIKeyInfo] = None
        self._client: Optional[ZhipuAI] = None

    def __enter__(self) -> ZhipuAI:
        """获取客户端（上下文管理器入口）"""
        self._key_info = cross_process_manager.get_available_key(self.timeout)
        if not self._key_info:
            raise RuntimeError("无法获取可用的API密钥")

        self._client = ZhipuAI(api_key=self._key_info.key)
        return self._client

    def __exit__(self, exc_type, exc_val, exc_tb):
        """释放客户端（上下文管理器出口）"""
        if self._key_info:
            cross_process_manager.release_key(self._key_info)
            self._key_info = None
        self._client = None


def get_sync_client_managed(timeout: Optional[float] = None) -> ManagedZhipuClient:
    """
    获取托管的同步ZhipuAI客户端（跨进程安全）

    Args:
        timeout: 获取密钥的超时时间（秒），None表示无限等待

    Returns:
        ManagedZhipuClient: 托管客户端，需要使用with语句

    使用示例：
        with get_sync_client_managed() as client:
            response = client.chat.completions.create(...)
    """
    return ManagedZhipuClient(timeout)


# ==================== 异步版本（保留用于异步场景） ====================

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


class AsyncAPIKeyManager:
    """异步API密钥管理器（单进程内使用）"""

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

    async def get_api_key(self) -> Optional[APIKeyInfo]:
        """获取可用的API密钥（无限等待）"""
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

    def get_status(self) -> Dict[str, Any]:
        """获取管理器状态"""
        self._ensure_initialized()
        busy_count = sum(1 for k in self._keys.values() if k.is_busy)
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


# 异步管理器实例（单进程内使用）
api_key_manager = AsyncAPIKeyManager()


class ZhipuAIClient:
    """包装 ZhipuAI 客户端，自动管理 API 密钥生命周期（异步）"""

    def __init__(self, api_key_info: APIKeyInfo):
        self._key_info = api_key_info
        self._client = ZhipuAI(api_key=api_key_info.key)

    @property
    def key_info(self) -> APIKeyInfo:
        return self._key_info

    def chat_completions_create(self, **kwargs):
        return self._client.chat.completions.create(**kwargs)

    def __getattr__(self, name):
        return getattr(self._client, name)


async def get_zhipu_client() -> ZhipuAIClient:
    """获取带管理的 ZhipuAI 客户端（异步）"""
    key_info = await api_key_manager.get_api_key()
    return ZhipuAIClient(key_info)


async def release_client(client: ZhipuAIClient):
    """释放客户端占用的 API 密钥"""
    await api_key_manager.release_api_key(client.key_info)


def get_wait_time_estimate() -> int:
    """估算当前需要等待的时间（秒）"""
    status = cross_process_manager.get_status()
    queue_size = status.get("queue_size", 0)
    busy_keys = status["busy_keys"]

    if queue_size == 0 and busy_keys == 0:
        return 0

    return (queue_size + 1) * 5


# 简单的同步客户端（不管理并发，用于简单场景）
class SyncZhipuClient:
    """同步版本的 ZhipuAI 客户端（不管理并发）"""

    def __init__(self):
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            raise ValueError("API密钥未提供，请设置环境变量ZHIPU_API_KEY")
        self._client = ZhipuAI(api_key=api_key)

    def chat_completions_create(self, **kwargs):
        return self._client.chat.completions.create(**kwargs)

    def __getattr__(self, name):
        return getattr(self._client, name)


def get_sync_client() -> SyncZhipuClient:
    """获取同步版本的 ZhipuAI 客户端（不管理并发）"""
    return SyncZhipuClient()
