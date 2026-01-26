from nt import write
import requests
import json
import os
import time
from dotenv import load_dotenv
import importlib
import os
import inspect
import AI.default_tool
# 动态导入 default_tool 模块中的所有函数
def import_global_functions(module):
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        globals()[name] = obj

import_global_functions(AI.default_tool)

# 加载环境变量
load_dotenv()
        
# 辅助函数：处理环境变量值
def get_env_float(key, default):
    value = os.getenv(key, default)
    # 处理可能包含注释的情况，只取数值部分
    if isinstance(value, str):
        value = value.split('#')[0].strip()
    return float(value)
def get_env_int(key, default):
    value = os.getenv(key, default)
    # 处理可能包含注释的情况，只取数值部分
    if isinstance(value, str):
        value = value.split('#')[0].strip()
    return int(value)
class ZhipuChat:
    """
    智普API对话类，支持连续对话和上下文管理
    """
    def __init__(self, api_key=None, model=None, system_prompt=None, extend_tools=None,):   
        """
        初始化
        :param api_key: 智普API密钥，默认从环境变量加载
        :param model: 模型名称，默认从环境变量加载
        """
        # 从环境变量加载配置
        api_base_url = os.getenv("ZHIPU_API_URL", "https://open.bigmodel.cn/api/paas/v4")
        
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY")
        self.model = model or os.getenv("ZHIPU_DEFAULT_MODEL", "glm-4.7-flash")
        self.api_url = f"{api_base_url}/chat/completions"
        self.system_prompt = system_prompt or ""
        # 从环境变量加载深度思考参数
        self.default_tool_config_path = os.getenv("ZHIPU_DEFAULT_TOOL_CONFIG_PATH")
        self.enable_depth_thinking = os.getenv("ZHIPU_ENABLE_DEPTH_THINKING", "disable").lower()
        self.show_thinking_content = os.getenv("ZHIPU_SHOW_THINKING_CONTENT", "true").lower() == "true"
        
        # 从环境变量加载默认参数
        self.default_max_tokens = get_env_int("ZHIPU_DEFAULT_MAX_TOKENS", "16384")
        self.default_temperature = get_env_float("ZHIPU_DEFAULT_TEMPERATURE", "0.2")
        self.default_top_p = get_env_float("ZHIPU_DEFAULT_TOP_P", "0.2")
        
        # 创建请求头
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 验证API密钥是否存在
        if not self.api_key:
            raise ValueError("API密钥未提供，请设置环境变量ZHIPU_API_KEY或传入api_key参数")

        self.context = []
        self.tools = []
        self.context.append({"role": "system", "content": self.system_prompt})
        
        # 工具函数注册表
        self._tool_functions = {}
        
        self._load_tools() # 加载默认工具函数
        if extend_tools: # 如果有额外工具配置文件
            self._load_tools(extend_tools)
    def _load_tools(self,file_path=None):
        if not file_path: # 如果没有指定文件路径，默认加载默认配置文件
            self.tools = json.load(open(self.default_tool_config_path,"r",encoding="utf-8"))

        else: # 需要动态加载新的工具函数文件
            if type(file_path) == list: # 如果是列表，遍历每个文件路径
                for file_path in file_path:
                    new_tools = json.load(open(file_path,"r",encoding="utf-8"))
                    if isinstance(new_tools, list):
                        self.tools.extend(new_tools)
                    else:
                        self.tools.append(new_tools)
            else: # 只有一个文件路径，直接加载
                new_tools = json.load(open(file_path,"r",encoding="utf-8"))
                if isinstance(new_tools, list):
                    self.tools.extend(new_tools)
                else:
                    self.tools.append(new_tools)
    
    def register_tool_function(self, name, func):
        """
        注册工具函数
        :param name: 函数名称
        :param func: 函数对象
        """
        self._tool_functions[name] = func
    
    def register_tool_functions_from_module(self, module):
        """
        从模块中注册所有函数
        :param module: 模块对象
        """
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            self._tool_functions[name] = obj
    def _send_request(self, messages):
        """
        发送请求到智普API
        :param messages: 消息列表
        :return: 响应内容
        """
        # 构建payload
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.default_max_tokens,
            "temperature": self.default_temperature,
            "top_p": self.default_top_p,
            "thinking":{
                "type":self.enable_depth_thinking
            }
        }
        
        if self.tools:
            payload["tools"] = self.tools
            payload["tool_choice"] = "auto"
    
        response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=600)
        response.raise_for_status()
        
        result = response.json()
        return result
    def _exclute_func(self,func,args):
        """
        执行工具函数
        :param func: 工具函数对象
        :param args: 工具函数参数
        :return: 工具函数执行结果
        """
        if isinstance(args, str):
            args = json.loads(args)
        self._log(f"执行工具函数: {func.__name__} 参数: {args}",level="info")
        return func(**args)
    
    def _serialize_result(self, result):
        """
        序列化工具函数执行结果，支持多种数据类型
        :param result: 工具函数执行结果
        :return: 可序列化的结果
        """
        if result is None:
            return None
        
        # 如果是 pandas DataFrame，转换为字典
        if hasattr(result, '__class__') and result.__class__.__name__ == 'DataFrame':
            return result.to_dict('records')
        
        # 如果是 pandas Series，转换为字典
        if hasattr(result, '__class__') and result.__class__.__name__ == 'Series':
            return result.to_dict()
        
        # 如果是 numpy 数组，转换为列表
        if hasattr(result, '__class__') and 'ndarray' in result.__class__.__name__:
            return result.tolist()
        
        # 如果是基本类型，直接返回
        if isinstance(result, (str, int, float, bool, list, dict)):
            return result
        
        # 其他类型尝试转换为字符串
        return str(result)
    def _log(self, message,level="info"):
        """
        记录日志
        :param message: 日志消息
        """
        if level == "info":# 白色转义
            print(f"\033[37m{message}\033[0m")
        if level == "error":# 红色转义
            print(f"\033[31m{message}\033[0m")
        if level == "thinking":# 黄色转义
            print(f"\033[33m{message}\033[0m")
        
    def chat(self, message):
        """
        对话方法
        :param message: 用户输入消息
        :return: 模型回复
        """
        # 添加用户消息到上下文
        self.context.append({"role": "user", "content": message})
        
        try:
            result = self._send_request(self.context)
            
            # 获取模型消息
            model_message = result.get("choices", [{}])[0].get("message", {})
            
            # 检查是否有思考内容
            if self.show_thinking_content:
                thinking_content = model_message.get("reasoning_content")
                if thinking_content:
                    self.context.append({
                        "role": "assistant",
                        "content": thinking_content
                    })
                    self._log(f"💡 AI思考: {thinking_content}",level="thinking")
            
            self._log(f"AI: {model_message.get('content', '')}",level="info")
            
            # 将模型消息添加到上下文
            self.context.append(model_message)
            
            # 检查是否有工具调用
            while "tool_calls" in model_message and model_message["tool_calls"]:
                tool_call = model_message["tool_calls"][0]
                function_name = tool_call["function"]["name"]
                function_args = tool_call["function"]["arguments"]
                

                # 优先从实例的工具函数注册表中获取函数
                func_ref = self._tool_functions.get(function_name)
                
                # 如果实例注册表中没有，再从全局命名空间获取
                if not func_ref:
                    func_ref = globals().get(function_name)
                
                if func_ref:
                    result = self._exclute_func(func_ref, function_args)
                    
                    # 序列化结果，支持 DataFrame 等类型
                    serialized_result = self._serialize_result(result)
                
                    # 将函数结果返回给模型
                    self.context.append({
                        "role": "tool",
                        "content": json.dumps(serialized_result, ensure_ascii=False),
                        "tool_call_id": tool_call["id"]
                    })
                else:
                    # 如果找不到函数引用，返回错误信息
                    self.context.append({
                        "role": "tool",
                        "content": json.dumps({"error": f"Function {function_name} not found"}, ensure_ascii=False),
                        "tool_call_id": tool_call["id"]
                    })
                    self._log(f"函数 {function_name} 未找到",level="error")
                # 调用后再次发送请求
                result = self._send_request(self.context)
                thinking_content = result.get("choices", [{}])[0].get("message", {}).get("reasoning_content")
                if thinking_content:
                    self.context.append({
                        "role": "assistant",
                        "content": thinking_content
                    })
                    self._log(f"💡 AI思考: {thinking_content}",level="thinking")
                    
                model_message = result.get("choices", [{}])[0].get("message", {})
                self.context.append(model_message)
                self._log(f"AI: {model_message.get('content', '')}",level="info")



        except Exception as e:
            raise Exception(f"API请求失败: {str(e)}")
    
    def clear_context(self):
        """
        清空上下文
        """
        self.context = []
    
    def get_context(self):
        """
        获取当前上下文
        :return: 上下文列表
        """
        return self.context
    
    def set_context(self, context):
        """
        设置上下文
        :param context: 上下文列表
        """
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
            reply = chat.chat(user_input)
            print(f"AI: {reply}")
        except Exception as e:
            print(f"错误: {e}")
            break