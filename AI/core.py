import json
import os
import inspect
import threading
import time
from dotenv import load_dotenv
from zhipuai import ZhipuAI
import AI.default_tool
from AI.default_tool import Todo



def import_global_functions(module):
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        globals()[name] = obj

import_global_functions(AI.default_tool)

load_dotenv()

def get_env_float(key, default):
    value = os.getenv(key, default)
    if isinstance(value, str):
        value = value.split('#')[0].strip()
    return float(value)

def get_env_int(key, default):
    value = os.getenv(key, default)
    if isinstance(value, str):
        value = value.split('#')[0].strip()
    return int(value)

class ZhipuChat:
    def __init__(self, api_key=None, model=None, system_prompt=None, extend_tools=None):
        api_base_url = os.getenv("ZHIPU_API_URL", "https://open.bigmodel.cn/api/paas/v4")
        
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY")
        self.model = model or os.getenv("ZHIPU_DEFAULT_MODEL", "glm-4.7-flash")
        self.api_url = f"{api_base_url}/chat/completions"
        self.system_prompt = system_prompt or ""
        self.default_tool_config_path = os.getenv("ZHIPU_DEFAULT_TOOL_CONFIG_PATH")
        self.enable_depth_thinking = os.getenv("ZHIPU_ENABLE_DEPTH_THINKING", "disable").lower()
        self.show_thinking_content = os.getenv("ZHIPU_SHOW_THINKING_CONTENT", "true").lower() == "true"
        
        self.default_max_tokens = get_env_int("ZHIPU_DEFAULT_MAX_TOKENS", "16384")
        self.default_temperature = get_env_float("ZHIPU_DEFAULT_TEMPERATURE", "0.2")
        self.default_top_p = get_env_float("ZHIPU_DEFAULT_TOP_P", "0.2")
        self.stream_timeout = get_env_int("ZHIPU_STREAM_TIMEOUT", "60")
        
        if not self.api_key:
            raise ValueError("API密钥未提供，请设置环境变量ZHIPU_API_KEY或传入api_key参数")

        self.client = ZhipuAI(api_key=self.api_key)
        
        self.context = []
        self.tools = []
        self.context.append({"role": "system", "content": self.system_prompt})
        
        self._tool_functions = {}
        self.todo = Todo()
        
        self._register_todo_methods()
        
        self._load_tools()
        if extend_tools:
            self._load_tools(extend_tools)

    def _register_todo_methods(self):
        self._tool_functions["self.todo.create"] = self.todo.create
        self._tool_functions["self.todo.doing"] = self.todo.doing
        self._tool_functions["self.todo.update"] = self.todo.update
        self._tool_functions["self.todo.finish"] = self.todo.finish

    def _load_tools(self, file_path=None):
        if not file_path:
            self.tools = json.load(open(self.default_tool_config_path, "r", encoding="utf-8"))
        else:
            if type(file_path) == list:
                for file_path in file_path:
                    new_tools = json.load(open(file_path, "r", encoding="utf-8"))
                    if isinstance(new_tools, list):
                        self.tools.extend(new_tools)
                    else:
                        self.tools.append(new_tools)
            else:
                new_tools = json.load(open(file_path, "r", encoding="utf-8"))
                if isinstance(new_tools, list):
                    self.tools.extend(new_tools)
                else:
                    self.tools.append(new_tools)

    def register_tool_function(self, name, func):
        self._tool_functions[name] = func

    def register_tool_functions_from_module(self, module):
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            self._tool_functions[name] = obj

    def _execute_func(self, func, args):
        if isinstance(args, str):
            args = json.loads(args)
        #简化显示的args，限制每个参数的长度为15个字符，超过15个字符的参数用...表示
        args_short = {k: v[:15]+'···' if len(v) > 15 else v for k, v in args.items()}
        self._log(f"\n\n🔧 执行工具函数: {func.__name__} 参数: {args_short}", level="info")
        return func(**args)

    def _serialize_result(self, result):
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

    def _log(self, message, level="info"):
        if level == "info":
            print(f"\033[37m{message}\033[0m")
        if level == "error":
            print(f"\033[31m{message}\033[0m")
        if level == "thinking":
            print(f"\033[33m{message}\033[0m")

    def _process_stream_response(self, response):
        reasoning_content = ""
        content = ""
        final_tool_calls = {}
        reasoning_started = False
        content_started = False
        tool_call_started = False
        
        timeout_event = threading.Event()
        timeout_occurred = False
        
        def timeout_monitor():
            timeout_event.wait(self.stream_timeout)
            if not timeout_event.is_set():
                nonlocal timeout_occurred
                timeout_occurred = True
        
        timeout_thread = threading.Thread(target=timeout_monitor, daemon=True)
        timeout_thread.start()
        
        try:
            for chunk in response:
                if timeout_occurred:
                    raise TimeoutError(f"流式响应超时，超过 {self.stream_timeout} 秒没有收到数据")
                
                timeout_event.set()
                
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
                        # print("\n\n🔧 工具调用：")
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
            
            if timeout_occurred:
                raise TimeoutError(f"流式响应超时，超过 {self.stream_timeout} 秒没有收到数据")
            
            # if final_tool_calls:
            #     print("\n📋 命中 Function Calls :")
            #     for index, tool_call in final_tool_calls.items():
            #         print(f"  {index}: 函数名: {tool_call['function']['name']}, 参数: {tool_call['function']['arguments']}")
            
            # print()
            return reasoning_content, content, final_tool_calls
        
        finally:
            timeout_event.set()

    def chat(self, message):
        self.context.append({"role": "user", "content": message})
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                while True:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=self.context,
                        max_tokens=self.default_max_tokens,
                        temperature=self.default_temperature,
                        top_p=self.default_top_p,
                        thinking={"type": self.enable_depth_thinking},
                        tools=self.tools if self.tools else None,
                        tool_choice="auto" if self.tools else None,
                        stream=True
                    )
                    reasoning_content, content, final_tool_calls = self._process_stream_response(response)
                    
                    if reasoning_content:
                        self.context.append({
                            "role": "assistant",
                            "content": reasoning_content
                        })
                    
                    if content:
                        self.context.append({
                            "role": "assistant",
                            "content": content
                        })
                    
                    if not final_tool_calls:
                        break
                    
                    for index, tool_call in final_tool_calls.items():
                        function_name = tool_call['function']['name']
                        function_args = tool_call['function']['arguments']
                        
                        func_ref = self._tool_functions.get(function_name)
                        if not func_ref:
                            func_ref = globals().get(function_name)
                        
                        if func_ref:
                            result = self._execute_func(func_ref, function_args)
                            serialized_result = self._serialize_result(result)
                            self.context.append({
                                "role": "tool",
                                "content": json.dumps(serialized_result, ensure_ascii=False),
                                "tool_call_id": tool_call['id']
                            })
                        else:
                            self.context.append({
                                "role": "tool",
                                "content": json.dumps({"error": f"Function {function_name} not found"}, ensure_ascii=False),
                                "tool_call_id": tool_call['id']
                            })
                            self._log(f"\n\n⚠️函数 {function_name} 未找到", level="error")
                return
            
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "1302" in error_str or "并发数过高" in error_str:
                    retry_count += 1
                    if retry_count < max_retries:
                        self._log(f"速率限制，等待5秒后重试 (第{retry_count}/{max_retries}次)", level="info")
                        time.sleep(5)
                        continue
                    else:
                        self._log(f"已达到最大重试次数 {max_retries}，放弃重试", level="error")
                        raise Exception(f"API请求失败: {str(e)}")
                else:
                    raise Exception(f"API请求失败: {str(e)}")

    def clear_context(self):
        self.context = []
    
    def get_context(self):
        return self.context
    
    def set_context(self, context):
        self.context = context

if __name__ == "__main__":
    import os
    api_key = os.getenv("ZHIPU_API_KEY")
    if not api_key:
        api_key = input("请输入智普API密钥: ")
    
    chat = ZhipuChat(api_key)
    print("开始对话，输入'退出'结束")
    
    while True:
        user_input = input("用户: ")
        if user_input == "退出":
            break
        
        try:
            chat.chat(user_input)
        except Exception as e:
            print(f"错误: {e}")
            break
