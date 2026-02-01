import botpy
from botpy import logging
from botpy.message import DirectMessage, C2CMessage, GroupMessage
from botpy.manage import C2CManageEvent
from typing import Dict, Callable, Optional
import asyncio
import os
import sys
import random
import time

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()
# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from message_push.QQ.handlers import load_handlers
from message_push.QQ.ai_chat import chat_with_user, _sessions
from message_push.QQ.emoji_manager import (
    get_emoji_manager, save_emoji_from_url,
    get_emoji_for_send, get_emoji_by_name_for_send
)

# 机器人凭证配置
APPID = os.getenv("QQ_BOT_APPID", "102834902")
SECRET = os.getenv("QQ_BOT_SECRET", "cSI90skdWQKPVbiqy7HRco0DQet8OfwE")

logger = logging.get_logger()


class MessageListener:
    """
    QQ消息监听器
    支持监听指定关键词并自动回复指定内容
    未触发关键词时调用GLM进行对话
    支持图片消息处理和表情包功能
    """

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._default_reply: Optional[str] = None
        self._ai_enabled: bool = False
        self.emoji_manager = get_emoji_manager()

    def register(self, keyword: str, handler: Callable):
        """注册关键词处理器"""
        self._handlers[keyword] = handler
        logger.info(f"已注册关键词处理器: '{keyword}'")

    def set_default_reply(self, reply: str):
        """设置默认回复内容"""
        self._default_reply = reply
        logger.info(f"已设置默认回复: '{reply[:20]}...'")

    def enable_ai(self):
        """启用AI对话功能"""
        try:
            from message_push.QQ.ai_chat import ChatAI
            test_ai = ChatAI("test")
            self._ai_enabled = True
            logger.info("✅ AI对话功能已启用")
        except Exception as e:
            logger.error(f"❌ AI初始化失败: {e}")
            self._ai_enabled = False

    def _find_handler(self, content: str) -> Optional[Callable]:
        """查找匹配的关键词处理器"""
        for keyword, handler in self._handlers.items():
            if keyword in content:
                return handler
        return None

    async def _send_emoji_reply(self, api, message, text: str, emoji_name: str, msg_type: str):
        """发送带表情包的回复"""
        try:
            # 获取用户openid
            user_openid = getattr(message.author, 'user_openid', getattr(message.author, 'id', 'unknown'))

            # 1. 先发送文本回复
            if msg_type in ["C2C单聊", "私信"]:
                await api.post_c2c_message(
                    openid=user_openid,
                    msg_type=0,
                    content=text,
                    msg_seq=1
                )
            else:
                await message.reply(content=text)
            logger.info(f"🤖 AI文本回复: {text[:50]}...")

            # 2. 查找并发送表情包
            if emoji_name:
                # 先尝试精确匹配
                emoji_path = get_emoji_for_send(emoji_name)
                if not emoji_path:
                    # 尝试按名称查找
                    emoji_path = get_emoji_by_name_for_send(emoji_name)

                if emoji_path and os.path.exists(emoji_path):
                    # 根据消息类型选择发送方式
                    if msg_type == "群聊@":
                        # 群聊使用 file_image 参数
                        await message.reply(content="", file_image=emoji_path)
                        logger.info(f"😄 已发送表情包: {emoji_name}")
                    elif msg_type in ["C2C单聊", "私信"]:
                        # C2C暂不支持发送表情包（需要先上传到URL）
                        logger.info(f"😄 表情包暂不支持C2C发送: {emoji_name}")
                    else:
                        logger.warning(f"⚠️ 未找到表情包: {emoji_name}")
        except Exception as e:
            logger.error(f"❌ 发送表情包失败: {e}")

    async def _handle_ai_reply(self, message, api, user_openid: str, content: str,
                               image_url: str = None, msg_type: str = "unknown"):
        """处理AI回复（支持表情包）"""
        try:
            # 定义压缩完成回调
            async def compress_callback(notify_msg: str):
                await message.reply(content=notify_msg)

            # 调用AI获取回复
            result = chat_with_user(
                user_openid,
                content,
                image_url=image_url,
                compress_callback=lambda msg: asyncio.create_task(compress_callback(msg))
            )

            text = result.get("text", "")

            # 处理多次发送（同时按 || 和 \n\n 分割）
            messages = [text]
            
            # 第一步：按 || 分割
            if r"||" in text:
                temp_messages = []
                for msg in messages:
                    temp_messages.extend(msg.split(r"||"))
                messages = temp_messages
            
            # 第二步：对每个部分按 \n\n 分割
            if "\n\n" in text:
                temp_messages = []
                for msg in messages:
                    temp_messages.extend(msg.split("\n\n"))
                messages = temp_messages
            
            # 过滤空消息
            messages = [msg.strip() for msg in messages if msg.strip()]   
            # 获取用户openid
            user_openid = getattr(message.author, 'user_openid', getattr(message.author, 'id', 'unknown'))

            # 纯文本回复，支持多次发送
            for i, msg in enumerate(messages):
                if msg.strip():
                    # 使用api直接发送，避免reply的去重问题
                    await api.post_c2c_message(
                        openid=user_openid,
                        msg_type=0,
                        content=msg.strip(),
                        msg_seq=i + 1
                    )
                    if i < len(messages) - 1:
                        await asyncio.sleep(random.uniform(0.5, 1))
            logger.info(f"🤖 AI回复: {text[:50]}...")

        except Exception as e:
            logger.error(f"❌ AI回复失败: {e}")

    async def _process_emoji(self, attachment, user_openid: str):
        """处理表情包（保存并命名）"""
        try:
            # 1. 下载保存表情包
            emoji_id = await save_emoji_from_url(attachment.url, attachment.content_type)
            if not emoji_id:
                return None

            # 2. 使用AI分析并命名表情包
            from message_push.QQ.ai_chat import ChatAI

            temp_ai = ChatAI(f"emoji_namer_{emoji_id}")
            prompt = f"""请分析这个表情包的内容，给它起一个有趣的中文名字（2-6个字），并给出3-5个相关标签。

请按以下格式回复：
名称：[表情包名称]
标签：[标签1, 标签2, 标签3]
描述：[简单描述表情包内容]"""

            result = temp_ai.chat(prompt, image_url=attachment.url)
            text = result.get("text", "") if isinstance(result, dict) else result

            # 解析AI回复
            name = None
            tags = []

            for line in text.split('\n'):
                if line.startswith('名称：') or line.startswith('名称:'):
                    name = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                elif line.startswith('标签：') or line.startswith('标签:'):
                    tags_str = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                    tags = [t.strip() for t in tags_str.replace('，', ',').split(',') if t.strip()]

            if name:
                self.emoji_manager.update_emoji_name(emoji_id, name, tags)
                logger.info(f"✅ AI命名表情包: {name} (ID: {emoji_id})")
                return name

            return emoji_id
        except Exception as e:
            logger.error(f"❌ 处理表情包失败: {e}")
            return None

    async def handle_message(self, message, api, msg_type: str = "unknown"):
        """处理消息"""
        content = message.content or ""
        user_openid = getattr(message.author, 'user_openid', getattr(message.author, 'id', 'unknown'))

        # 检查是否有图片附件
        image_url = None
        is_emoji = False
        if hasattr(message, 'attachments') and message.attachments:
            for attachment in message.attachments:
                if attachment.content_type.startswith('image/'):
                    image_url = attachment.url
                    logger.info(f"[{msg_type}] 用户 {user_openid} 发送图片: {image_url}")

                    # 判断是否为表情包（小尺寸图片）
                    if attachment.size and attachment.size < 500 * 1024:  # 小于500KB认为是表情包
                        is_emoji = True
                        # 异步处理表情包（保存并命名）
                        asyncio.create_task(self._process_emoji(attachment, user_openid))
                    break

        logger.info(f"[{msg_type}] 用户 {user_openid}: {content[:50]}...")

        # 1. 查找关键词处理器（优先执行，不走AI）
        handler = self._find_handler(content)

        if handler:
            try:
                reply_content = handler(message)
                # 如果返回的是协程，需要await
                if asyncio.iscoroutine(reply_content):
                    reply_content = await reply_content

                # 使用 is not None 判断，允许返回空字符串表示已处理但不回复
                if reply_content is not None:
                    if reply_content:  # 如果有内容则发送回复
                        await message.reply(content=reply_content)
                        logger.info(f"✅ 关键词回复: {reply_content[:50]}...")
                    else:
                        logger.info("✅ 处理器已处理消息，无需回复")
                    return
                logger.info("🔄 处理器返回None，转交AI处理")

            except Exception as e:
                logger.error(f"❌ 处理器执行失败: {e}")

        # 2. 使用AI回复（支持图片和表情包）
        if self._ai_enabled:
            await self._handle_ai_reply(message, api, user_openid, content, image_url, msg_type)
            return

        # 3. 默认回复
        if self._default_reply:
            try:
                await message.reply(content=self._default_reply)
                logger.info("✅ 已发送默认回复")
            except Exception as e:
                logger.error(f"❌ 发送默认回复失败: {e}")


# 全局监听器实例
listener = MessageListener()


class MyClient(botpy.Client):
    """自定义机器人客户端"""

    async def on_direct_message_create(self, message: DirectMessage):
        """监听私信消息"""
        await listener.handle_message(message, self.api, "私信")

    async def on_c2c_message_create(self, message: C2CMessage):
        """监听 C2C 单聊消息"""
        await listener.handle_message(message, self.api, "C2C单聊")

    async def on_group_at_message_create(self, message: GroupMessage):
        """监听群聊 @机器人 消息"""
        await listener.handle_message(message, self.api, "群聊@")

    async def on_friend_add(self, event: C2CManageEvent):
        """监听好友添加事件"""
        user_openid = event.openid
        logger.info(f"===== 新好友添加 =====")
        logger.info(f"用户openid: {user_openid}")
        logger.info("=====================")


def setup_handlers():
    """加载所有处理器"""
    handlers = load_handlers()
    for keyword, handler in handlers.items():
        listener.register(keyword, handler)
    logger.info(f"✅ 共加载 {len(handlers)} 个关键词处理器")


def run_listener(enable_ai: bool = True):
    """启动消息监听器"""
    logger.info("=" * 50)
    logger.info("🚀 QQ消息监听器启动中...")
    logger.info("=" * 50)

    # 1. 加载处理器
    setup_handlers()

    # 2. 启用AI
    if enable_ai:
        listener.enable_ai()

    # 3. 设置默认回复
    listener.set_default_reply("抱歉，我暂时无法处理您的请求，请稍后再试。")

    # 4. 设置需要监听的事件意图
    intents = botpy.Intents.none()
    intents.direct_message = True
    intents.public_messages = True

    # 5. 初始化客户端
    client = MyClient(intents=intents)

    # 6. 启动机器人
    logger.info("=" * 50)
    logger.info("✅ 机器人已启动，等待用户消息...")
    logger.info("=" * 50)
    client.run(appid=APPID, secret=SECRET)


if __name__ == "__main__":
    run_listener(enable_ai=True)
