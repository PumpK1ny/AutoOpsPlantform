"""QQ机器人AI对话模块 - 支持GLM-4.6V多模态、表情包toolcall"""

import os
import json
import base64
import re
from dotenv import load_dotenv
from zhipuai import ZhipuAI

# 加载环境变量
load_dotenv()

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
        # 保存为字典格式（包含摘要）
        data = {"history": history, "summary": summary}
    else:
        # 保存为列表格式（兼容旧版本）
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


class ChatAI:
    """多模态AI对话类 - 支持GLM-4.6V、图片理解、表情包toolcall"""



    def __init__(self, user_openid: str):
        self.user_openid = user_openid
        self.client = ZhipuAI(api_key=os.getenv("ZHIPU_API_KEY"))
        self.model = os.getenv("QQCHAT_DEFAULT_MODEL", "glm-4.6v-flash")
        self.base_system_prompt = load_system_prompt()
        self.system_prompt = self.base_system_prompt

        # 加载对话记录和压缩摘要（只加载user/assistant消息，不包含system）
        self.dialog_history, self.summary = load_history(user_openid)

        self.is_compressing = False
        self.compress_callback = None

    def _build_context(self) -> list:
        """构建完整的上下文（system + 对话）"""
        context = []
        
        # 1. system prompt
        context.append({"role": "system", "content": self.system_prompt})
        
        # 2. 对话历史（user/assistant消息）
        context.extend(self.dialog_history)
        return context

    def set_compress_callback(self, callback):
        """设置压缩完成回调"""
        self.compress_callback = callback

    def check_and_compress(self) -> bool:
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
            
            # 保存为assistant消息
            summary_message = {"role": "assistant", "content": f"【历史对话摘要】\n{summary}"}
            save_history(self.user_openid, [summary_message])
            self.dialog_history = [summary_message]
            
            self.is_compressing = False
            if self.compress_callback:
                self.compress_callback("✅ 上下文压缩完成！已保留关键信息，可以继续对话了~")
            return True
        except Exception as e:
            self.is_compressing = False
            if self.compress_callback:
                self.compress_callback(f"⚠️ 上下文压缩失败: {e}")
            return False

    def chat(self, message: str, image_url: str = None, image_base64: str = None) -> dict:
        """
        发送消息并获取回复
        
        Returns:
            dict: {"text": 回复文本}
        """
        if self.is_compressing:
            return {"text": "⏳ 正在压缩历史对话，请稍等..."}

        if not image_url and not image_base64:
            if self.check_and_compress():
                return {"text": "🔄 检测到对话历史较长，正在自动压缩上下文..."}

        # 构建消息
        if image_url or image_base64:
            content = []
            if image_url:
                content.append({"type": "image_url", "image_url": {"url": image_url}})
            elif image_base64:
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}})
            if message:
                content.append({"type": "text", "text": message})
            user_message = {"role": "user", "content": content}
        else:
            user_message = {"role": "user", "content": message}

        self.dialog_history.append(user_message)

        # 构建完整上下文
        context = self._build_context()

        # 调用API，带重试机制
        max_retries = 3
        retry_delay = 4  # 秒
        response = None
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=context,
                    max_tokens=2048,
                    temperature=0.7,
                    top_p=0.7,
                    stream=False,
                    thinking={"type": "disabled"}
                )
                break  # 成功则跳出重试循环
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "1305" in error_msg or "请求过多" in error_msg:
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(retry_delay * (attempt + 1))  # 递增延迟
                        continue
                raise  # 非429错误或重试次数用尽，抛出异常
        
        if response is None:
            return {"text": "⏳ API请求繁忙，请稍后再试~"}

        reply = response.choices[0].message.content
        reply = reply.strip() if reply else ""
        
        # 去除XML标签（如</arg_value>等）
        import re
        reply = re.sub(r'</?\w+>', '', reply)

        # 添加助手回复到对话历史
        self.dialog_history.append({"role": "assistant", "content": reply})

        save_history(self.user_openid, self.dialog_history)

        return {"text": reply}


# 内存中的会话缓存
_sessions = {}


def chat_with_user(user_openid: str, message: str, image_url: str = None,
                   image_base64: str = None, compress_callback=None) -> dict:
    """
    与指定用户对话
    
    Returns:
        dict: {"text": 回复文本}
    """
    if user_openid not in _sessions:
        _sessions[user_openid] = ChatAI(user_openid)

    if compress_callback:
        _sessions[user_openid].set_compress_callback(compress_callback)

    return _sessions[user_openid].chat(message, image_url, image_base64)
