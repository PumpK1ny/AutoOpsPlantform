"""
API密钥管理器 - 兼容层

⚠️ 注意：此文件仅为向后兼容保留，请直接使用项目根目录的 api_key_manager.py

原功能已迁移到项目根目录的 api_key_manager.py
"""

# 从项目级别管理器重新导出所有功能
from api_key_manager import (
    APIKeyInfo,
    UserRequestTracker,
    CrossProcessAPIKeyManager,
    AsyncAPIKeyManager,
    ZhipuAIClient,
    api_key_manager,
    get_zhipu_client,
    release_client,
    get_wait_time_estimate,
    SyncZhipuClient,
    get_sync_client,
    ManagedZhipuClient,
    get_sync_client_managed,
    cross_process_manager,
)

# 为了向后兼容，保留 APIKeyManager 别名
APIKeyManager = AsyncAPIKeyManager

__all__ = [
    "APIKeyInfo",
    "UserRequestTracker",
    "APIKeyManager",  # 向后兼容别名
    "CrossProcessAPIKeyManager",
    "AsyncAPIKeyManager",
    "ZhipuAIClient",
    "api_key_manager",
    "get_zhipu_client",
    "release_client",
    "get_wait_time_estimate",
    "SyncZhipuClient",
    "get_sync_client",
    "ManagedZhipuClient",
    "get_sync_client_managed",
    "cross_process_manager",
]
