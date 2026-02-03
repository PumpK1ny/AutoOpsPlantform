"""
基础指令处理器
"""

import os
import sys
import asyncio
import time

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def handle_market(message):
    """处理市场走向查询"""
    return "📈 市场走向分析网站\n\nhttp://47.108.159.171:5000/"


async def handle_compress_async(message):
    """手动触发上下文压缩（异步版本）"""
    user_openid = getattr(message.author, 'user_openid', getattr(message.author, 'id', 'unknown'))

    try:
        from message_push.QQ.ai_chat import _sessions, load_history, load_system_prompt
        from message_push.QQ.ai_chat_compress import compress_context

        # 先从内存获取session，如果没有则从文件加载
        if user_openid in _sessions:
            session = _sessions[user_openid]
            dialog_history = session.dialog_history
            summary = session.summary
        else:
            # 从文件加载历史（返回元组）
            dialog_history, summary = load_history(user_openid)

        if not dialog_history and not summary:
            return "❌ 还没有对话历史，无需压缩~"

        # 检查是否有足够的历史
        if len(dialog_history) < 2:  # 至少需要2轮对话（4条消息）
            return "❌ 对话历史太少，无需压缩~提示：需要至少2轮对话（4条消息）才能压缩。"

        # 构建完整上下文用于压缩
        system_prompt = load_system_prompt()
        context = [{"role": "system", "content": system_prompt}]
        if summary:
            context[0]["content"] += f"\n\n【历史对话摘要】\n{summary}"
        context.extend(dialog_history)

        # 先发送开始压缩提示（使用post_c2c_message）
        await message._api.post_c2c_message(
            openid=user_openid,
            msg_type=0,
            content="🔄 正在压缩上下文，请稍等...",
            msg_seq=1
        )

        # 执行压缩
        new_summary = compress_context(context)

        # 将摘要作为assistant消息保存
        summary_message = {"role": "assistant", "content": f"【历史对话摘要】\n{new_summary}"}

        # 保存到文件（覆盖原来的对话记录）
        from message_push.QQ.ai_chat import save_history
        save_history(user_openid, [summary_message])

        # 如果session在内存中，更新对话历史为摘要
        if user_openid in _sessions:
            _sessions[user_openid].dialog_history = [summary_message]
            _sessions[user_openid].summary = new_summary

        # 添加延迟避免去重
        await asyncio.sleep(1)

        # 发送完成提示（使用post_c2c_message）
        await message._api.post_c2c_message(
            openid=user_openid,
            msg_type=0,
            content=f"""✅ 上下文压缩完成！

【压缩摘要】
{new_summary}

已保留关键信息，可以继续对话了~""",
            msg_seq=2
        )

        # 返回空字符串表示消息已处理，不再转交AI
        return ""

    except Exception as e:
        return f"❌ 压缩失败: {e}"


def handle_compress(message):
    """手动触发上下文压缩 - 返回协程让调用方执行"""
    # 直接返回协程，让 listen.py 的 async/await 机制处理
    return handle_compress_async(message)


def register_handlers():
    """注册处理器"""
    return {
        "市场走向": handle_market,
        "上下文压缩": handle_compress,
    }
