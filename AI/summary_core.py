import os
import sys
import time
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from message_push.QQ.api_key_manager import (
    create_zhipu_client_with_rotation,
    get_api_key_simple
)

load_dotenv()


def summarize_text(text, api_key=None, model=None):
    """
    使用智谱AI对文本进行总结
    
    Args:
        text: 需要总结的文本
        api_key: 可选，指定API密钥
        model: 可选，指定模型
    
    Returns:
        str: 总结后的文本
    """
    # 获取API密钥
    api_key = api_key or get_api_key_simple()
    model = model or os.getenv("ZHIPU_DEFAULT_MODEL", "glm-4.7-flash")
    
    if not api_key:
        raise ValueError("API密钥未提供")
    
    # 创建支持密钥轮换的客户端
    rotating_client = create_zhipu_client_with_rotation()
    
    # 构建请求参数
    request_params = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个专业的文本总结助手，擅长将长文本、复杂文档或多篇内容进行精炼总结,但注意要保留可能影响基金市场相关的信息，确保总结的准确和完整。总结字数控制在500字内"},
            {"role": "user", "content": text}
        ],
        "max_tokens": 16384,
        "temperature": 0.2,
        "top_p": 0.2,
        "stream": False
    }
    
    # 尝试调用API，支持密钥轮换
    max_retries = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            if rotating_client:
                response = rotating_client.chat_completions_create(**request_params)
            else:
                # 回退到普通客户端
                from zhipuai import ZhipuAI
                client = ZhipuAI(api_key=api_key)
                response = client.chat.completions.create(**request_params)
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_str = str(e)
            last_error = e
            
            # 检查是否为速率限制错误
            if "429" in error_str or "1302" in error_str or "1305" in error_str or "并发数过高" in error_str or "请求过多" in error_str:
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))  # 递增延迟
                    continue
            
            # 非速率限制错误或已达到最大重试次数
            raise Exception(f"API请求失败: {error_str}")
    
    # 所有重试都失败
    if last_error:
        raise last_error
    raise Exception("API请求失败，已达到最大重试次数")
