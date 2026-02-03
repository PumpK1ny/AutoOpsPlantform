import os
from dotenv import load_dotenv
from api_key_manager import get_sync_client

load_dotenv()

def summarize_text(text, api_key=None, model=None):
    """
    使用智谱AI总结文本

    Args:
        text: 需要总结的文本
        api_key: 可选，自定义API密钥
        model: 可选，自定义模型

    Returns:
        str: 总结后的文本
    """
    model = model or os.getenv("ZHIPU_DEFAULT_MODEL", "glm-4.7-flash")

    if api_key:
        # 如果提供了自定义API密钥，使用原始方式
        from zhipuai import ZhipuAI
        client = ZhipuAI(api_key=api_key)
    else:
        # 使用项目级别的API密钥管理器
        client = get_sync_client()

    response = client.chat_completions_create(
        model=model,
        messages=[
            {"role": "system", "content": "你是一个专业的文本总结助手，擅长将长文本、复杂文档或多篇内容进行精炼总结,但注意要保留可能影响基金市场相关的信息，确保总结的准确和完整。总结字数控制在500字内"},
            {"role": "user", "content": text}
        ],
        max_tokens=16384,
        temperature=0.2,
        top_p=0.2
    )
    return response.choices[0].message.content
