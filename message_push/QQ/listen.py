import botpy
from botpy import logging
from botpy.message import DirectMessage, C2CMessage, GroupMessage
from botpy.manage import C2CManageEvent
from typing import Dict, Callable, Optional
import asyncio
import os
import sys
import random

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()
# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from message_push.QQ.handlers import load_handlers
from message_push.QQ.ai_chat import chat_with_user, _sessions, queue_user_message, get_pending_messages, clear_pending_messages
from message_push.QQ.api_key_manager import api_key_manager

# 机器人凭证配置
APPID = os.getenv("QQ_BOT_APPID", "")
SECRET = os.getenv("QQ_BOT_SECRET", "")

logger = logging.get_logger()


class MessageListener:
    """
    QQ消息监听器
    支持监听指定关键词并自动回复指定内容
    未触发关键词时调用GLM进行对话
    支持文字对话和图片理解
    支持请求取消和消息合并
    """

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._default_reply: Optional[str] = None
        self._ai_enabled: bool = False
        self._user_requests: Dict[str, asyncio.Task] = {}
        self._user_cancel_events: Dict[str, asyncio.Event] = {}

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

    async def _handle_ai_reply(self, message, api, user_openid: str, content: str,
                               msg_type: str = "unknown"):
        """处理AI回复"""
        try:
            status = api_key_manager.get_status()

            if status["is_full"]:
                await message.reply(content="⏳ 当前使用人数较多，正在等待发送...")
                logger.info(f"⏳ 用户 {user_openid} 需等待API密钥")

            if user_openid in self._user_requests and not self._user_requests[user_openid].done():
                logger.info(f"⚡ 用户 {user_openid} 有正在进行的请求，取消并合并消息")
                if user_openid in self._user_cancel_events:
                    self._user_cancel_events[user_openid].set()
                await queue_user_message(user_openid, content)
                if user_openid in _sessions and _sessions[user_openid]:
                    pending_msg = {"role": "user", "content": content}
                    _sessions[user_openid].dialog_history.append(pending_msg)
                return

            if user_openid not in self._user_cancel_events:
                self._user_cancel_events[user_openid] = asyncio.Event()
            else:
                self._user_cancel_events[user_openid].clear()

            async def compress_callback(notify_msg: str):
                await message.reply(content=notify_msg)

            async def run_chat():
                return await chat_with_user(
                    user_openid,
                    content,
                    compress_callback=lambda msg: asyncio.create_task(compress_callback(msg)),
                    cancel_event=self._user_cancel_events[user_openid],
                    msg_api=api
                )

            chat_task = asyncio.create_task(run_chat())
            self._user_requests[user_openid] = chat_task

            result = await chat_task

            del self._user_requests[user_openid]

            is_cancelled = result.get("cancelled", False)
            text = result.get("text", "") if not is_cancelled else ""

            pending = await get_pending_messages(user_openid)
            if pending or is_cancelled:
                message_parts = [content] if content else []
                for p in pending:
                    if p["message"]:
                        message_parts.append(p["message"])
                combined_message = "\n".join(message_parts)
                await clear_pending_messages(user_openid)

                logger.info(f"🔄 用户 {user_openid} 有待处理消息，合并发送: {combined_message[:50]}...")

                if user_openid not in self._user_cancel_events:
                    self._user_cancel_events[user_openid] = asyncio.Event()
                else:
                    self._user_cancel_events[user_openid].clear()

                async def run_combined_chat():
                    return await chat_with_user(
                        user_openid,
                        combined_message,
                        compress_callback=lambda msg: asyncio.create_task(compress_callback(msg)),
                        cancel_event=self._user_cancel_events[user_openid],
                        msg_api=api
                    )

                combined_task = asyncio.create_task(run_combined_chat())
                self._user_requests[user_openid] = combined_task
                result = await combined_task
                del self._user_requests[user_openid]

                is_cancelled = result.get("cancelled", False)
                text = result.get("text", "") if not is_cancelled else ""

            if is_cancelled:
                return

            messages = [text]

            if r"||" in text:
                temp_messages = []
                for msg in messages:
                    temp_messages.extend(msg.split(r"||"))
                messages = temp_messages

            if "\n\n" in text:
                temp_messages = []
                for msg in messages:
                    temp_messages.extend(msg.split("\n\n"))
                messages = temp_messages

            messages = [msg.strip() for msg in messages if msg.strip()]
            user_openid = getattr(message.author, 'user_openid', getattr(message.author, 'id', 'unknown'))

            for i, msg in enumerate(messages):
                if msg.strip():
                    await api.post_c2c_message(
                        openid=user_openid,
                        msg_type=0,
                        content=msg.strip(),
                        msg_seq=i + 1
                    )
                    if i < len(messages) - 1:
                        await asyncio.sleep(random.uniform(0.5, 1))
            logger.info(f"🤖 AI回复: {text[:50]}...")

        except asyncio.CancelledError:
            logger.info(f"⏹️ 用户 {user_openid} 的请求已取消")
            if user_openid in self._user_requests:
                del self._user_requests[user_openid]
        except Exception as e:
            logger.error(f"❌ AI回复失败: {e}")
            if user_openid in self._user_requests:
                del self._user_requests[user_openid]

    async def handle_message(self, message, api, msg_type: str = "unknown"):
        """处理消息"""
        content = message.content or ""
        user_openid = getattr(message.author, 'user_openid', getattr(message.author, 'id', 'unknown'))

        # 忽略图片附件，只处理文本消息
        logger.info(f"[{msg_type}] 用户 {user_openid}: {content[:50]}...")

        handler = self._find_handler(content)

        if handler:
            try:
                reply_content = handler(message)
                if asyncio.iscoroutine(reply_content):
                    reply_content = await reply_content

                if reply_content is not None:
                    if reply_content:
                        await message.reply(content=reply_content)
                        logger.info(f"✅ 关键词回复: {reply_content[:50]}...")
                    else:
                        logger.info("✅ 处理器已处理消息，无需回复")
                    return
                logger.info("🔄 处理器返回None，转交AI处理")

            except Exception as e:
                logger.error(f"❌ 处理器执行失败: {e}")

        if self._ai_enabled:
            await self._handle_ai_reply(message, api, user_openid, content, msg_type)
            return

        if self._default_reply:
            try:
                await message.reply(content=self._default_reply)
                logger.info("✅ 已发送默认回复")
            except Exception as e:
                logger.error(f"❌ 发送默认回复失败: {e}")


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

    setup_handlers()

    if enable_ai:
        listener.enable_ai()

    listener.set_default_reply("抱歉，我暂时无法处理您的请求，请稍后再试。")

    intents = botpy.Intents.none()
    intents.direct_message = True
    intents.public_messages = True

    client = MyClient(intents=intents)

    logger.info("=" * 50)
    logger.info("✅ 机器人已启动，等待用户消息...")
    logger.info("=" * 50)
    client.run(appid=APPID, secret=SECRET)


if __name__ == "__main__":
    run_listener(enable_ai=True)
