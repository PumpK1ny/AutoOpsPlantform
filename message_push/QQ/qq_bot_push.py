import os
import asyncio
import aiohttp
import time

from dotenv import load_dotenv
load_dotenv()

HTTP_API_BASE_URL = os.getenv("QQ_BOT_HTTP_API_URL", "http://localhost:8080")
TARGET_C2C_OPENID = os.getenv("QQ_TARGET_C2C_OPENID", "")
TARGET_GROUP_OPENID = os.getenv("QQ_TARGET_GROUP_OPENID", "")


async def check_service_health(max_retries: int = 3, retry_delay: float = 2.0) -> bool:
    """检查 QQ bot HTTP 服务是否可用"""
    url = f"{HTTP_API_BASE_URL}/health"
    
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        return True
                    print(f"⚠️ 服务健康检查失败: HTTP {response.status}")
        except asyncio.TimeoutError:
            print(f"⚠️ 服务健康检查超时 (尝试 {attempt + 1}/{max_retries})")
        except aiohttp.ClientError as e:
            print(f"⚠️ 服务健康检查失败: {e} (尝试 {attempt + 1}/{max_retries})")
        except Exception as e:
            print(f"⚠️ 服务健康检查异常: {e} (尝试 {attempt + 1}/{max_retries})")
        
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)
    
    return False


async def send_notification(openid: str, content: str, msg_type: str = "c2c", max_retries: int = 3) -> dict:
    """通过 HTTP API 发送通知消息，支持自动重试"""
    url = f"{HTTP_API_BASE_URL}/api/notify"
    payload = {
        "openid": openid,
        "content": content,
        "msg_type": msg_type
    }
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    json=payload, 
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    result = await response.json()
                    if response.status == 200 and result.get("success"):
                        print(f"✅ 通知发送成功 [{msg_type}]: {openid}")
                        return result
                    else:
                        last_error = result.get("error", "未知错误")
                        print(f"⚠️ 发送失败 (尝试 {attempt + 1}/{max_retries}): {last_error}")
        except asyncio.TimeoutError:
            last_error = "请求超时"
            print(f"⚠️ 请求超时 (尝试 {attempt + 1}/{max_retries})")
        except aiohttp.ClientError as e:
            last_error = f"HTTP 请求失败: {e}"
            print(f"⚠️ {last_error} (尝试 {attempt + 1}/{max_retries})")
        except Exception as e:
            last_error = str(e)
            print(f"⚠️ 发送异常: {last_error} (尝试 {attempt + 1}/{max_retries})")
        
        if attempt < max_retries - 1:
            await asyncio.sleep(1)
    
    print(f"❌ 通知发送失败 (重试{max_retries}次后): {last_error}")
    return {"success": False, "error": last_error}


async def send_notification_with_health_check(openid: str, content: str, msg_type: str = "c2c") -> dict:
    """先检查服务健康状态，再发送通知"""
    if not await check_service_health():
        return {"success": False, "error": "QQ bot 服务不可用"}
    
    return await send_notification(openid, content, msg_type)


async def push_c2c_message(openid: str, content: str) -> dict:
    return await send_notification(openid, content, msg_type="c2c")


async def push_group_message(group_openid: str, content: str) -> dict:
    return await send_notification(group_openid, content, msg_type="group")


def send_notification_sync(openid: str, content: str, msg_type: str = "c2c") -> dict:
    return asyncio.run(send_notification_with_health_check(openid, content, msg_type))


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
