"""QQ机器人AI对话模块 - 支持GLM-4.6V多模态、多API密钥管理、工具调用"""

import os
import json
import base64
import re
import asyncio
import time
import inspect
from dotenv import load_dotenv
from zhipuai import ZhipuAI
import aiohttp
import message_push.QQ.bot_tool as bot_tool
# 加载环境变量
load_dotenv()

# 导入API密钥管理器
from message_push.QQ.api_key_manager import (
    api_key_manager, 
    get_wait_time_estimate,
    create_zhipu_client_with_rotation,
    get_api_key_simple
)

def import_global_functions(module):
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        globals()[name] = obj

import_global_functions(bot_tool)
# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_DIR = os.path.join(BASE_DIR, "chat_history")
SYSTEM_PROMPT_FILE = os.path.join(BASE_DIR, "system_prompt.txt")
# 压缩阈值（token数，大约估算）
COMPRESS_THRESHOLD = 10000

# HTTP API 配置
HTTP_API_BASE_URL = os.getenv("QQ_BOT_HTTP_API_URL", "http://localhost:8080")

# 确保历史记录目录存在
os.makedirs(HISTORY_DIR, exist_ok=True)


def load_info(user_openid: str) -> str:
    """从文件加载system prompt"""
    if os.path.exists(SYSTEM_PROMPT_FILE):
        with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()
    else:
        system_prompt = "你是QQ群里的聊天机器人，性格活泼可爱，喜欢用表情包。请用简洁友好的中文回答。"

    if os.path.exists(os.path.join(BASE_DIR, "bio", f"{user_openid}.json")):
        with open(os.path.join(BASE_DIR, "bio", f"{user_openid}.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
            bio_content = data
    else:
        bio_content = {}
    return system_prompt, bio_content


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


async def _call_zhipu_api_with_rotation(model: str, messages: list, api_params: dict = None) -> any:
    """
    调用智谱API，支持密钥轮换
    """
    loop = asyncio.get_event_loop()
    
    if api_params is None:
        api_params = {
            "model": model,
            "messages": messages,
            "max_tokens": int(os.getenv("QQ_BOT_MAX_TOKENS", "1024")),
            "temperature": 0.7,
            "top_p": 0.7,
            "stream": False,
            "thinking": {"type": "disabled"}
        }
    
    # 获取轮换客户端
    rotating_client = create_zhipu_client_with_rotation()
    
    if rotating_client:
        # 使用支持轮换的客户端
        return await loop.run_in_executor(
            None,
            lambda: rotating_client.chat_completions_create(**api_params)
        )
    else:
        # 回退到普通客户端
        api_key = get_api_key_simple()
        client = ZhipuAI(api_key=api_key)
        return await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(**api_params)
        )


class ChatAI:
    """多模态AI对话类 - 支持GLM-4.6V、多API密钥管理、工具调用"""

    def __init__(self, user_openid: str, msg_api=None):
        self.user_openid = user_openid
        self.msg_api = msg_api
        self.text_model = os.getenv("QQCHAT_TEXT_MODEL", "glm-4.7-flash")
        self.base_system_prompt, self.bio = load_info(user_openid)
        self.system_prompt = self.base_system_prompt

        self.dialog_history, self.summary = load_history(user_openid)

        self.is_compressing = False
        self.compress_callback = None

        # 工具调用相关
        self.tools = []
        self._tool_functions = {}
        self.enable_depth_thinking = "disabled" # 禁用深度思考
        self.show_thinking_content = os.getenv("ZHIPU_SHOW_THINKING_CONTENT", "true").lower() == "true"
        self.default_max_tokens = int(os.getenv("QQ_BOT_MAX_TOKENS", "1024"))
        self.default_temperature = float(os.getenv("ZHIPU_DEFAULT_TEMPERATURE", "0.7"))
        self.default_top_p = float(os.getenv("ZHIPU_DEFAULT_TOP_P", "0.7"))
        # 加载工具
        self.load_tools_from_file("message_push/QQ/bot_tool.json")

    async def send_message(self, content: str, msg_type: str = "c2c", max_retries: int = 3) -> dict:
        if self.msg_api:
            try:
                messages = [content]
                if r"||" in content:
                    temp_messages = []
                    for msg in messages:
                        temp_messages.extend(msg.split(r"||"))
                    messages = temp_messages
                if "\n\n" in content:
                    temp_messages = []
                    for msg in messages:
                        temp_messages.extend(msg.split("\n\n"))
                    messages = temp_messages
                messages = [msg.strip() for msg in messages if msg.strip()]

                for i, msg in enumerate(messages):
                    if msg.strip():
                        await self.msg_api.post_c2c_message(
                            openid=self.user_openid,
                            msg_type=0,
                            content=msg.strip(),
                            msg_seq=i + 1
                        )
                        if i < len(messages) - 1:
                            await asyncio.sleep(0.5)
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            from message_push.QQ.qq_bot_push import send_notification_with_health_check
            return await send_notification_with_health_check(self.user_openid, content, msg_type)

    def register_tool_function(self, name, func):
        """注册工具函数"""
        self._tool_functions[name] = func

    def register_tool_functions_from_module(self, module):
        """从模块注册所有函数"""
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            self._tool_functions[name] = obj

    def load_tools_from_file(self, file_path):
        """从JSON文件加载工具配置"""
        if not os.path.exists(file_path):
            return
        with open(file_path, "r", encoding="utf-8") as f:
            new_tools = json.load(f)
            if isinstance(new_tools, list):
                self.tools.extend(new_tools)
            else:
                self.tools.append(new_tools)

    async def _execute_func(self, func, args):
        """执行工具函数"""
        if isinstance(args, str):
            args = json.loads(args)
        def truncate_value(v):
            if isinstance(v, list):
                v_str = str(v)
                return v_str[:15] + '···' if len(v_str) > 15 else v
            elif isinstance(v, str):
                return v[:15] + '···' if len(v) > 15 else v
            else:
                v_str = str(v)
                return v_str[:15] + '···' if len(v_str) > 15 else v
        args_short = {k: truncate_value(v) for k, v in args.items()}
        print(f"\n\n🔧 执行工具函数: {func.__name__} 参数: {args_short}")
        
        # 发送QQ通知
        await self.send_message(f"🔧：{func.__name__}")
        
        return func(**args)

    def _serialize_result(self, result):
        """序列化函数返回结果"""
        if result is None:
            return None
        if hasattr(result, '__class__') and result.__class__.__name__ == 'DataFrame':
            return self._serialize_result(result.to_dict('records'))
        if hasattr(result, '__class__') and result.__class__.__name__ == 'Series':
            return self._serialize_result(result.to_dict())
        if hasattr(result, '__class__') and 'ndarray' in result.__class__.__name__:
            return self._serialize_result(result.tolist())
        if hasattr(result, '__class__') and result.__class__.__name__ == 'Timestamp':
            return str(result)
        if isinstance(result, (str, int, float, bool)):
            return result
        if isinstance(result, list):
            return [self._serialize_result(item) for item in result]
        if isinstance(result, dict):
            return {k: self._serialize_result(v) for k, v in result.items()}
        return str(result)

    def _process_stream_response(self, response):
        """处理流式响应"""
        reasoning_content = ""
        content = ""
        final_tool_calls = {}
        reasoning_started = False
        content_started = False
        tool_call_started = False

        for chunk in response:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                if not reasoning_started and delta.reasoning_content.strip():
                    print("\n🧠 思考过程：")
                    reasoning_started = True
                reasoning_content += delta.reasoning_content
                print(delta.reasoning_content, end="", flush=True)

            if hasattr(delta, 'content') and delta.content:
                if not content_started and delta.content.strip():
                    print("\n\n💬 回答内容：")
                    content_started = True
                content += delta.content
                print(delta.content, end="", flush=True)

            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                if not tool_call_started:
                    tool_call_started = True
                for tool_call in delta.tool_calls:
                    index = tool_call.index
                    if index not in final_tool_calls:
                        final_tool_calls[index] = {
                            'id': tool_call.id,
                            'type': tool_call.type,
                            'function': {
                                'name': tool_call.function.name,
                                'arguments': tool_call.function.arguments
                            }
                        }
                    else:
                        final_tool_calls[index]['function']['arguments'] += tool_call.function.arguments

        return reasoning_content, content, final_tool_calls

    def _build_context(self) -> list:
        """构建完整的上下文（system + 对话）"""
        context = []
        system = f""""
        {self.system_prompt}
        ## 用户信息：
        id:{self.user_openid}
        ### memory:\n{self.bio}
        """
        context.append({"role": "system", "content": system})
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
        支持工具调用（单轮对话，无while循环）
        
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

        current_task = asyncio.current_task()

        try:
            if cancel_event.is_set():
                return {"text": "", "cancelled": True}

            # 构建API参数
            api_params = {
                "model": model,
                "messages": context,
                "max_tokens": self.default_max_tokens,
                "temperature": self.default_temperature,
                "top_p": self.default_top_p,
                "stream": True,
                "thinking": {"type": self.enable_depth_thinking}
            }
            
            if self.tools:
                api_params["tools"] = self.tools
                api_params["tool_choice"] = "auto"

            # 使用支持密钥轮换的API调用
            response = await _call_zhipu_api_with_rotation(model, context, api_params)
            
            reasoning_content, content, final_tool_calls = self._process_stream_response(response)

            if reasoning_content:
                self.dialog_history.append({
                    "role": "assistant",
                    "content": reasoning_content
                })

            # 如果有工具调用，执行工具并继续
            if final_tool_calls:
                for index, tool_call in final_tool_calls.items():
                    function_name = tool_call['function']['name']
                    function_args = tool_call['function']['arguments']

                    func_ref = self._tool_functions.get(function_name)
                    if not func_ref:
                        func_ref = globals().get(function_name)

                    if func_ref:
                        result = await self._execute_func(func_ref, function_args)
                        serialized_result = self._serialize_result(result)
                        self.dialog_history.append({
                            "role": "tool",
                            "content": json.dumps(serialized_result, ensure_ascii=False),
                            "tool_call_id": tool_call['id']
                        })
                    else:
                        self.dialog_history.append({
                            "role": "tool",
                            "content": json.dumps({"error": f"Function {function_name} not found"}, ensure_ascii=False),
                            "tool_call_id": tool_call['id']
                        })
                        print(f"\n\n⚠️函数 {function_name} 未找到")

                # 执行工具后，再次调用API获取最终回复
                context = self._build_context()
                api_params["messages"] = context
                response = await _call_zhipu_api_with_rotation(model, context, api_params)
                reasoning_content, content, final_tool_calls = self._process_stream_response(response)

                if reasoning_content:
                    self.dialog_history.append({
                        "role": "assistant",
                        "content": reasoning_content
                    })

            if content:
                reply = content.strip() if content else ""
                reply = re.sub(r'</?\w+>', '', reply)
                self.dialog_history.append({"role": "assistant", "content": reply})
                save_history(self.user_openid, self.dialog_history)
                return {"text": reply}
            else:
                # 没有回复，再次请求
                context = self._build_context()
                api_params["messages"] = context
                response = await _call_zhipu_api_with_rotation(model, context, api_params)
                reasoning_content, content, final_tool_calls = self._process_stream_response(response)

                if reasoning_content:
                    self.dialog_history.append({
                        "role": "assistant",
                        "content": reasoning_content
                    })

                # 如果有工具调用，执行工具并继续
                if final_tool_calls:
                    for index, tool_call in final_tool_calls.items():
                        function_name = tool_call['function']['name']
                        function_args = tool_call['function']['arguments']

                        func_ref = self._tool_functions.get(function_name)
                        if not func_ref:
                            func_ref = globals().get(function_name)

                        if func_ref:
                            result = await self._execute_func(func_ref, function_args)
                            serialized_result = self._serialize_result(result)
                            self.dialog_history.append({
                                "role": "tool",
                                "content": json.dumps(serialized_result, ensure_ascii=False),
                                "tool_call_id": tool_call['id']
                            })
                        else:
                            self.dialog_history.append({
                                "role": "tool",
                                "content": json.dumps({"error": f"Function {function_name} not found"}, ensure_ascii=False),
                                "tool_call_id": tool_call['id']
                            })
                            print(f"\n\n⚠️函数 {function_name} 未找到")

                    # 执行工具后，再次调用API获取最终回复
                    context = self._build_context()
                    api_params["messages"] = context
                    response = await _call_zhipu_api_with_rotation(model, context, api_params)
                    reasoning_content, content, final_tool_calls = self._process_stream_response(response)

                    if reasoning_content:
                        self.dialog_history.append({
                            "role": "assistant",
                            "content": reasoning_content
                        })

                if content:
                    reply = content.strip() if content else ""
                    reply = re.sub(r'</?\w+>', '', reply)
                    self.dialog_history.append({"role": "assistant", "content": reply})
                    save_history(self.user_openid, self.dialog_history)
                    return {"text": reply}
                else:
                    return {"text": "抱歉，我没有生成有效的回复。"}

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "1302" in error_str or "1305" in error_str or "请求过多" in error_str or "速率限制" in error_str:
                return {"text": "⏳ API请求繁忙，请稍后再试~"}
            raise


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
                         cancel_event: asyncio.Event = None, msg_api=None) -> dict:
    """
    与指定用户对话
    
    如果用户有正在进行的请求，新消息会被加入队列等待处理
    
    Args:
        user_openid: 用户openid
        message: 用户消息
        compress_callback: 压缩回调函数
        cancel_event: 取消事件
        msg_api: 消息API对象
    
    Returns:
        dict: {"text": 回复文本}
    """
    if user_openid not in _sessions:
        _sessions[user_openid] = ChatAI(user_openid, msg_api)

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
