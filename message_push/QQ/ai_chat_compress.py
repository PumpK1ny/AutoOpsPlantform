"""对话压缩模块 - 用于压缩过长的对话历史"""

import os
import asyncio
from api_key_manager import get_sync_client


class ChatCompressor:
    """对话历史压缩器"""

    def __init__(self):
        self.client = get_sync_client()
        self.model = os.getenv("ZHIPU_DEFAULT_MODEL", "glm-4.7-flash")

    def compress(self, context: list) -> str:
        """
        压缩对话历史

        Args:
            context: 完整对话历史

        Returns:
            压缩后的摘要
        """
        # 构建压缩提示词（使用固定的压缩提示）
        compress_prompt = f"""你是一个专业的对话历史压缩助手。请对以下对话历史进行智能压缩总结。

【压缩目标】
1. 保留所有重要的用户偏好、需求和关键信息
2. 保留对话中的关键决策和结论
3. 保留用户的个人习惯和特殊要求
4. 去除重复的问候和闲聊内容
5. 用简洁的语言概括对话脉络

【对话历史】
"""

        # 将对话历史转换为文本
        for msg in context[1:]:  # 跳过system消息
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg.get("content", "")
            if isinstance(content, str):
                compress_prompt += f"\n{role}: {content}\n"
            elif isinstance(content, list):
                # 多模态消息（图片等）
                has_image = any(item.get("type") == "image_url" for item in content)
                text_parts = [item.get("text", "") for item in content if item.get("type") == "text"]
                text = " ".join(text_parts)
                compress_prompt += f"\n{role}: {text}{'[图片]' if has_image else ''}\n"

        compress_prompt += """

【输出格式】
请严格按照以下JSON格式输出，不要添加任何其他内容：

{
  "key_info": ["关键信息1", "关键信息2"],
  "dialogue_summary": "对话脉络的简要概括",
  "user_traits": ["用户特征1", "用户特征2"]
}"""

        # 调用API进行压缩
        max_tokens = int(os.getenv("ZHIPU_DEFAULT_MAX_TOKENS", "5000"))
        response = self.client.chat_completions_create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个专业的对话历史压缩助手，擅长提取和保留关键信息。请严格按照JSON格式输出。压缩后的长度要合适，不能过长或者过短。"},
                {"role": "user", "content": compress_prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.3,
            top_p=0.8,
            stream=False,
            response_format={"type": "json_object"}
        )

        summary_text = response.choices[0].message.content

        # 解析JSON响应
        try:
            import json
            result = json.loads(summary_text)
            key_info = result.get("key_info", [])
            dialogue_summary = result.get("dialogue_summary", "")
            user_traits = result.get("user_traits", [])

            # 构建摘要
            summary_parts = []
            if key_info:
                summary_parts.append("【关键信息】\n" + "\n".join(f"- {info}" for info in key_info))
            if dialogue_summary:
                summary_parts.append(f"\n【对话脉络】\n{dialogue_summary}")
            if user_traits:
                summary_parts.append(f"\n【用户特征】\n" + ", ".join(user_traits))

            summary = "\n".join(summary_parts) if summary_parts else "暂无关键信息"

        except json.JSONDecodeError:
            # 如果JSON解析失败，使用原始文本
            summary = summary_text[:500]

        return summary


# 全局压缩器实例
_compressor = None


def get_compressor() -> ChatCompressor:
    """获取压缩器实例"""
    global _compressor
    if _compressor is None:
        _compressor = ChatCompressor()
    return _compressor


def compress_context(context: list) -> str:
    """
    压缩对话历史的便捷函数

    Args:
        context: 完整对话历史

    Returns:
        压缩摘要
    """
    compressor = get_compressor()
    return compressor.compress(context)
