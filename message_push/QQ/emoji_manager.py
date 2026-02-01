"""
表情包管理模块
自动保存、命名和管理用户发送的表情包
支持图片、GIF等格式
"""

import os
import json
import hashlib
import aiohttp
import aiofiles
from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 表情包存储目录
EMOJI_DIR = r"d:\PythonProject\auto_fund\message_push\QQ\emojis"
# 表情包索引文件
EMOJI_INDEX_FILE = os.path.join(EMOJI_DIR, "emoji_index.json")


class EmojiManager:
    """表情包管理器"""
    
    def __init__(self):
        self.emoji_dir = EMOJI_DIR
        self.index_file = EMOJI_INDEX_FILE
        self.emojis: Dict[str, dict] = {}  # 表情包索引
        self._ensure_dirs()
        self._load_index()
    
    def _ensure_dirs(self):
        """确保目录存在"""
        os.makedirs(self.emoji_dir, exist_ok=True)
    
    def _load_index(self):
        """加载表情包索引"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    self.emojis = json.load(f)
                logger.info(f"✅ 已加载 {len(self.emojis)} 个表情包")
            except Exception as e:
                logger.error(f"❌ 加载表情包索引失败: {e}")
                self.emojis = {}
        else:
            self.emojis = {}
    
    def _save_index(self):
        """保存表情包索引"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.emojis, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ 保存表情包索引失败: {e}")
    
    def _get_file_extension(self, content_type: str) -> str:
        """根据content_type获取文件扩展名"""
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/bmp': '.bmp',
        }
        return mime_to_ext.get(content_type.lower(), '.png')
    
    def _generate_emoji_id(self, url: str) -> str:
        """生成表情包唯一ID"""
        return hashlib.md5(url.encode()).hexdigest()[:12]
    
    async def download_emoji(self, url: str, content_type: str) -> Optional[str]:
        """
        下载表情包
        
        Args:
            url: 表情包URL
            content_type: 媒体类型
            
        Returns:
            本地文件路径或None
        """
        try:
            emoji_id = self._generate_emoji_id(url)
            ext = self._get_file_extension(content_type)
            filename = f"{emoji_id}{ext}"
            filepath = os.path.join(self.emoji_dir, filename)
            
            # 检查是否已存在
            if emoji_id in self.emojis:
                logger.info(f"📝 表情包已存在: {emoji_id}")
                return filepath
            
            # 下载表情包
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        async with aiofiles.open(filepath, 'wb') as f:
                            await f.write(content)
                        
                        # 添加到索引
                        self.emojis[emoji_id] = {
                            "id": emoji_id,
                            "filename": filename,
                            "filepath": filepath,
                            "url": url,
                            "content_type": content_type,
                            "created_at": datetime.now().isoformat(),
                            "name": None,  # 等待AI命名
                            "tags": [],
                            "usage_count": 0
                        }
                        self._save_index()
                        
                        logger.info(f"✅ 下载表情包成功: {emoji_id}")
                        return filepath
                    else:
                        logger.error(f"❌ 下载表情包失败: HTTP {response.status}")
                        return None
        except Exception as e:
            logger.error(f"❌ 下载表情包失败: {e}")
            return None
    
    def get_emoji(self, emoji_id: str) -> Optional[dict]:
        """获取表情包信息"""
        return self.emojis.get(emoji_id)
    
    def get_emoji_by_name(self, name: str) -> Optional[dict]:
        """根据名称查找表情包"""
        for emoji in self.emojis.values():
            if emoji.get("name") == name:
                return emoji
        return None
    
    def search_emojis(self, keyword: str) -> List[dict]:
        """搜索表情包"""
        results = []
        keyword = keyword.lower()
        for emoji in self.emojis.values():
            name = emoji.get("name", "")
            tags = emoji.get("tags", [])
            if keyword in name.lower() or any(keyword in tag.lower() for tag in tags):
                results.append(emoji)
        return results
    
    def update_emoji_name(self, emoji_id: str, name: str, tags: List[str] = None):
        """
        更新表情包名称和标签
        
        Args:
            emoji_id: 表情包ID
            name: 名称
            tags: 标签列表
        """
        if emoji_id in self.emojis:
            self.emojis[emoji_id]["name"] = name
            if tags:
                self.emojis[emoji_id]["tags"] = tags
            self._save_index()
            logger.info(f"✅ 更新表情包名称: {emoji_id} -> {name}")
    
    def increment_usage(self, emoji_id: str):
        """增加使用次数"""
        if emoji_id in self.emojis:
            self.emojis[emoji_id]["usage_count"] = self.emojis[emoji_id].get("usage_count", 0) + 1
            self._save_index()
    
    def get_random_emoji(self) -> Optional[dict]:
        """随机获取一个表情包"""
        import random
        if self.emojis:
            return random.choice(list(self.emojis.values()))
        return None
    
    def get_all_emojis(self) -> List[dict]:
        """获取所有表情包"""
        return list(self.emojis.values())
    
    def get_unnamed_emojis(self) -> List[dict]:
        """获取未命名的表情包"""
        return [e for e in self.emojis.values() if not e.get("name")]


# 全局表情包管理器实例
_emoji_manager: Optional[EmojiManager] = None


def get_emoji_manager() -> EmojiManager:
    """获取表情包管理器实例"""
    global _emoji_manager
    if _emoji_manager is None:
        _emoji_manager = EmojiManager()
    return _emoji_manager


async def save_emoji_from_url(url: str, content_type: str) -> Optional[str]:
    """
    从URL保存表情包
    
    Args:
        url: 表情包URL
        content_type: 媒体类型
        
    Returns:
        表情包ID或None
    """
    manager = get_emoji_manager()
    filepath = await manager.download_emoji(url, content_type)
    if filepath:
        return manager._generate_emoji_id(url)
    return None


def get_emoji_for_send(emoji_id: str) -> Optional[str]:
    """
    获取用于发送的表情包路径
    
    Args:
        emoji_id: 表情包ID
        
    Returns:
        本地文件路径或None
    """
    manager = get_emoji_manager()
    emoji = manager.get_emoji(emoji_id)
    if emoji:
        manager.increment_usage(emoji_id)
        return emoji.get("filepath")
    return None


def get_emoji_by_name_for_send(name: str) -> Optional[str]:
    """
    根据名称获取表情包路径
    
    Args:
        name: 表情包名称
        
    Returns:
        本地文件路径或None
    """
    manager = get_emoji_manager()
    emoji = manager.get_emoji_by_name(name)
    if emoji:
        manager.increment_usage(emoji["id"])
        return emoji.get("filepath")
    return None
