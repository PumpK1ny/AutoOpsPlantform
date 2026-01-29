import os
from dotenv import load_dotenv
from zhipuai import ZhipuAI

load_dotenv()

def summarize_text(text, api_key=None, model=None):
    api_key = api_key or os.getenv("ZHIPU_API_KEY")
    model = model or os.getenv("ZHIPU_DEFAULT_MODEL", "glm-4.7-flash")
    if not api_key:
        raise ValueError("API密钥未提供")
    client = ZhipuAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是一个专业的文本总结助手，擅长将长文本、复杂文档或多篇内容进行精炼总结,但注意要保留可能影响基金市场相关的信息，确保总结的准确和完整。总结字数控制在100字内"},
            {"role": "user", "content": text}
        ],
        max_tokens=16384,
        temperature=0.2,
        top_p=0.2
    )
    return response.choices[0].message.content
