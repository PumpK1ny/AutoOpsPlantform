"""QQ机器人AI对话模块 - 支持GLM-4.6V多模态、多API密钥管理"""

import os
import json
import base64
import re
import asyncio
from dotenv import load_dotenv
from zhipuai import ZhipuAI

# 加载环境变量
load_dotenv()

# 导入API密钥管理器
from message_push.QQ.api_key_manager import (
    api_key_manager, get_wait_time_estimate
)

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_DIR = os.path.join(BASE_DIR, "chat_history")
SYSTEM_PROMPT_FILE = os.path.join(BASE_DIR, "system_prompt.txt")

# 压缩阈值（token数，大约估算）
COMPRESS_THRESHOLD = 10000

# 确保历史记录目录存在
os.makedirs(HISTORY_DIR, exist_ok=True)


def load_system_prompt() -> str:
    """从文件加载system prompt"""
    if os.path.exists(SYSTEM_PROMPT_FILE):
        with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "你是QQ群里的聊天机器人，性格活泼可爱，喜欢用表情包。请用简洁友好的中文回答。"


def load_history(user_openid: str) -> tuple[list, str]:
    """
    加载用户历史对话
    
    Returns:
        (对话记录列表, 压缩摘要)
    """
    history_file = os.path.join(HISTORY_DIR, f"{user_openid}.json")
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data.get("history", []), data.get("summary", "")
            return data, ""
    return [], ""


def save_history(user_openid: str, history: list, summary: str = None):
    """
    保存用户历史对话
    
    Args:
        history: 对话记录列表（不包含system）
        summary: 压缩摘要（可选）
    """
    history_file = os.path.join(HISTORY_DIR, f"{user_openid}.json")
    
    if summary:
        data = {"history": history, "summary": summary}
    else:
        data = history
    
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def estimate_tokens(text: str) -> int:
    """估算token数"""
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    others = len(text) - chinese_chars - sum(len(w) for w in re.findall(r'[a-zA-Z]+', text))
    return int(chinese_chars * 1.5 + english_words * 1.2 + others * 0.5)


def calculate_context_tokens(context: list) -> int:
    """计算上下文的token数"""
    total = 0
    for msg in context:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content)
        elif isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    total += estimate_tokens(item.get("text", ""))
                else:
                    total += 1000
    return total


async def _call_zhipu_api(client: ZhipuAI, model: str, messages: list) -> any:
    """
    调用智谱API（异步包装）
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
            top_p=0.7,
            stream=False,
            thinking={"type": "disabled"}
        )
    )


class ChatAI:
    """多模态AI对话类 - 支持GLM-4.6V、多API密钥管理"""

    def __init__(self, user_openid: str):
        self.user_openid = user_openid
        self.text_model = os.getenv("QQCHAT_TEXT_MODEL", "glm-4.7-flash")
        self.base_system_prompt = load_system_prompt()
        self.system_prompt = self.base_system_prompt

        self.dialog_history, self.summary = load_history(user_openid)

        self.is_compressing = False
        self.compress_callback = None

    def _build_context(self) -> list:
        """构建完整的上下文（system + 对话）"""
        context = []
        
        context.append({"role": "system", "content": self.system_prompt})
        context.extend(self.dialog_history)
        return context

    def set_compress_callback(self, callback):
        """设置压缩完成回调"""
        self.compress_callback = callback

    async def check_and_compress(self) -> bool:
        """检查并执行压缩"""
        context = self._build_context()
        tokens = calculate_context_tokens(context)
        if tokens < COMPRESS_THRESHOLD:
            return False

        self.is_compressing = True
        try:
            from message_push.QQ.ai_chat_compress import compress_context
            summary = compress_context(context)
            self.summary = summary
            
            summary_message = {"role": "assistant", "content": f"【历史对话摘要】\n{summary}"}
            save_history(self.user_openid, [summary_message])
            self.dialog_history = [summary_message]
            
            self.is_compressing = False
            if self.compress_callback:
                await self.compress_callback("✅ 上下文压缩完成！已保留关键信息，可以继续对话了~")
            return True
        except Exception as e:
            self.is_compressing = False
            if self.compress_callback:
                await self.compress_callback(f"⚠️ 上下文压缩失败: {e}")
            return False

    async def chat(self, message: str, cancel_event: asyncio.Event = None) -> dict:
        """
        发送消息并获取回复
        仅使用文本模型 QQCHAT_TEXT_MODEL (glm-4.7-flash)
        忽略所有图片内容
        
        使用API密钥管理器处理并发请求
        
        Args:
            cancel_event: 用于取消请求的事件
        
        Returns:
            dict: {"text": 回复文本}
        """
        if self.is_compressing:
            return {"text": "⏳ 正在压缩历史对话，请稍等..."}

        if cancel_event is None:
            cancel_event = asyncio.Event()

        model = self.text_model

        compress_result = await self.check_and_compress()
        if compress_result:
            return {"text": "🔄 检测到对话历史较长，正在自动压缩上下文..."}

        user_message = {"role": "user", "content": message}

        self.dialog_history.append(user_message)

        context = self._build_context()

        status = api_key_manager.get_status()
        if status["is_full"] and status["queue_size"] == 0:
            pass

        key_info = await api_key_manager.get_api_key()

        max_retries = 3
        retry_delay = 4
        response = None
        last_error = None
        current_task = asyncio.current_task()

        if current_task:
            api_key_manager.register_user_request(self.user_openid, current_task, key_info.name)

        try:
            for attempt in range(max_retries):
                try:
                    if cancel_event.is_set():
                        api_key_manager.unregister_user_request(self.user_openid)
                        return {"text": "", "cancelled": True}

                    client = ZhipuAI(api_key=key_info.key)
                    response = await _call_zhipu_api(client, model, context)
                    api_key_manager.mark_success(key_info)
                    break
                except asyncio.CancelledError:
                    api_key_manager.unregister_user_request(self.user_openid)
                    raise
                except Exception as e:
                    last_error = str(e)
                    api_key_manager.mark_error(key_info, last_error)
                    if "429" in last_error or "1305" in last_error or "请求过多" in last_error:
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay * (attempt + 1))
                            continue
                    raise
        finally:
            api_key_manager.unregister_user_request(self.user_openid)
            await api_key_manager.release_api_key(key_info)
        
        if response is None:
            return {"text": "⏳ API请求繁忙，请稍后再试~"}

        reply = response.choices[0].message.content
        reply = reply.strip() if reply else ""
        
        reply = re.sub(r'</?\w+>', '', reply)

        self.dialog_history.append({"role": "assistant", "content": reply})

        save_history(self.user_openid, self.dialog_history)

        return {"text": reply}


_sessions = {}
_pending_messages = {}
_pending_lock = asyncio.Lock()


async def queue_user_message(user_openid: str, message: str) -> None:
    """将用户消息加入待处理队列"""
    async with _pending_lock:
        if user_openid not in _pending_messages:
            _pending_messages[user_openid] = []
        _pending_messages[user_openid].append({
            "message": message
        })


async def get_pending_messages(user_openid: str) -> list:
    """获取并清空用户待处理消息"""
    async with _pending_lock:
        messages = _pending_messages.get(user_openid, []).copy()
        _pending_messages[user_openid] = []
        return messages


async def clear_pending_messages(user_openid: str) -> None:
    """清空用户待处理消息"""
    async with _pending_lock:
        _pending_messages[user_openid] = []


async def has_pending_messages(user_openid: str) -> bool:
    """检查用户是否有待处理消息"""
    async with _pending_lock:
        return len(_pending_messages.get(user_openid, [])) > 0


async def chat_with_user(user_openid: str, message: str, compress_callback=None,
                         cancel_event: asyncio.Event = None) -> dict:
    """
    与指定用户对话
    
    如果用户有正在进行的请求，新消息会被加入队列等待处理
    
    Returns:
        dict: {"text": 回复文本}
    """
    if user_openid not in _sessions:
        _sessions[user_openid] = ChatAI(user_openid)

    if compress_callback:
        _sessions[user_openid].set_compress_callback(compress_callback)

    if cancel_event is None:
        cancel_event = asyncio.Event()

    pending = await get_pending_messages(user_openid)
    if pending:
        message_parts = [message] if message else []
        for p in pending:
            if p["message"]:
                message_parts.append(p["message"])
        combined_message = "\n".join(message_parts)
        await clear_pending_messages(user_openid)
        return await _sessions[user_openid].chat(combined_message, cancel_event)

    return await _sessions[user_openid].chat(message, cancel_event)


def get_api_status():
    """获取API密钥状态（供调试）"""
    return api_key_manager.get_status()
