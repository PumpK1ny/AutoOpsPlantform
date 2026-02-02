import os
import asyncio
import aiohttp

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# HTTP API 配置
HTTP_API_BASE_URL = os.getenv("QQ_BOT_HTTP_API_URL", "http://localhost:8080")

# 目标用户/群组openid（用户添加机器人后，可通过事件监听获取）
TARGET_C2C_OPENID = os.getenv("QQ_TARGET_C2C_OPENID", "")  # C2C单聊用户openid
TARGET_GROUP_OPENID = os.getenv("QQ_TARGET_GROUP_OPENID", "")  # 群聊openid（可选）


async def push_c2c_message(openid: str, content: str) -> dict:
    """
    通过 HTTP API 发送 C2C 单聊消息

    参数:
        openid: 目标用户openid
        content: 消息内容

    Returns:
        dict: 发送结果
    """
    return await send_notification(openid, content, msg_type="c2c")


async def push_group_message(group_openid: str, content: str) -> dict:
    """
    通过 HTTP API 发送群聊消息

    参数:
        group_openid: 目标群openid
        content: 消息内容

    Returns:
        dict: 发送结果
    """
    return await send_notification(group_openid, content, msg_type="group")


async def send_notification(openid: str, content: str, msg_type: str = "c2c") -> dict:
    """
    通过 HTTP API 发送通知消息

    参数:
        openid: 用户或群组的 openid
        content: 消息内容
        msg_type: 消息类型，c2c 或 group

    Returns:
        dict: 发送结果
    """
    url = f"{HTTP_API_BASE_URL}/api/notify"
    payload = {
        "openid": openid,
        "content": content,
        "msg_type": msg_type
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                if response.status == 200 and result.get("success"):
                    print(f"✅ 通知发送成功 [{msg_type}]: {openid}")
                    return result
                else:
                    error = result.get("error", "未知错误")
                    print(f"❌ 通知发送失败: {error}")
                    return result
    except aiohttp.ClientError as e:
        error_msg = f"HTTP 请求失败: {e}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = str(e)
        print(f"❌ 通知发送失败: {error_msg}")
        return {"success": False, "error": error_msg}


def send_notification_sync(openid: str, content: str, msg_type: str = "c2c") -> dict:
    """
    同步方式发送通知（供非异步代码调用）

    参数:
        openid: 用户或群组的 openid
        content: 消息内容
        msg_type: 消息类型，c2c 或 group

    Returns:
        dict: 发送结果
    """
    return asyncio.run(send_notification(openid, content, msg_type))


async def main():
    """主函数：演示如何使用 HTTP API 发送消息"""

    print("🚀 QQ 消息推送演示")
    print(f"HTTP API 地址: {HTTP_API_BASE_URL}")
    print("-" * 50)

    # 构造推送消息
    push_content = "这是来自QQ机器人的主动推送消息！"

    # 1. 执行 C2C 单聊推送（用户需先添加机器人为好友）
    if TARGET_C2C_OPENID:
        print(f"\n📱 正在向用户 {TARGET_C2C_OPENID} 推送消息...")
        result = await push_c2c_message(TARGET_C2C_OPENID, push_content)
        print(f"结果: {result}")
    else:
        print("\n⚠️ 未设置 TARGET_C2C_OPENID，跳过 C2C 推送")

    # 2. 执行群聊推送（机器人需要在群里）
    if TARGET_GROUP_OPENID:
        print(f"\n👥 正在向群 {TARGET_GROUP_OPENID} 推送消息...")
        result = await push_group_message(TARGET_GROUP_OPENID, push_content)
        print(f"结果: {result}")
    else:
        print("\n⚠️ 未设置 TARGET_GROUP_OPENID，跳过群聊推送")

    print("\n✅ 推送任务完成")


if __name__ == "__main__":
    # 使用 asyncio 运行异步主函数
    asyncio.run(main())
