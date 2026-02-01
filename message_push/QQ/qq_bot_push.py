import botpy
from botpy import logging
from botpy.http import BotHttp, Route
from botpy.robot import Token
import asyncio

# 1. 配置机器人凭证
APPID = os.getenv("QQ_BOT_APPID", "102834902")
SECRET = os.getenv("QQ_BOT_SECRET", "cSI90skdWQKPVbiqy7HRco0DQet8OfwE")  # 注意：新版SDK使用 secret 而不是 token

# 目标用户/群组openid（用户添加机器人后，可通过事件监听获取）
TARGET_C2C_OPENID = "CC5640C5E4C8F9C1BE264E44DDE53C99"  # C2C单聊用户openid
TARGET_GROUP_OPENID = ""  # 群聊openid（可选）

logger = logging.get_logger()


async def push_c2c_message(http: BotHttp, openid: str, content: str, msg_id: str = None):
    """
    主动推送 C2C 单聊消息

    参数:
        http: BotHttp 实例
        openid: 目标用户openid
        content: 消息内容
        msg_id: 可选，回复的消息ID
    """
    try:
        # 构造请求体
        json_data = {
            "content": content,
        }
        if msg_id:
            json_data["msg_id"] = msg_id

        # 创建路由
        route = Route("POST", f"/v2/users/{openid}/messages")

        # 发送请求
        result = await http.request(route, json=json_data)
        logger.info(f"C2C推送成功，返回结果：{result}")
        return result
    except Exception as e:
        logger.error(f"C2C推送失败：{str(e)}")
        return None


async def push_group_message(http: BotHttp, group_openid: str, content: str, msg_id: str = None):
    """
    主动推送群聊消息

    参数:
        http: BotHttp 实例
        group_openid: 目标群openid
        content: 消息内容
        msg_id: 可选，回复的消息ID
    """
    try:
        # 构造请求体
        json_data = {
            "content": content,
        }
        if msg_id:
            json_data["msg_id"] = msg_id

        # 创建路由
        route = Route("POST", f"/v2/groups/{group_openid}/messages")

        # 发送请求
        result = await http.request(route, json=json_data)
        logger.info(f"群消息推送成功，返回结果：{result}")
        return result
    except Exception as e:
        logger.error(f"群消息推送失败：{str(e)}")
        return None


async def main():
    """主函数：演示如何使用 botpy 进行主动消息推送"""

    # 2. 创建 Token 实例
    token = Token(APPID, SECRET)

    # 3. 创建 HTTP 客户端
    http = BotHttp(timeout=5)

    try:
        # 4. 登录获取 access_token
        logger.info("正在登录机器人账号...")
        user = await http.login(token)
        logger.info(f"登录成功，机器人名称：{user.get('username', 'Unknown')}")

        # 5. 构造推送消息
        push_content = "这是来自QQ机器人的主动推送消息！"

        # 6. 执行 C2C 单聊推送（用户需先添加机器人为好友）
        if TARGET_C2C_OPENID:
            logger.info(f"正在向用户 {TARGET_C2C_OPENID} 推送消息...")
            await push_c2c_message(http, TARGET_C2C_OPENID, push_content)

        # 7. 执行群聊推送（机器人需要在群里）
        if TARGET_GROUP_OPENID:
            logger.info(f"正在向群 {TARGET_GROUP_OPENID} 推送消息...")
            await push_group_message(http, TARGET_GROUP_OPENID, push_content)

        logger.info("推送任务完成")

    except Exception as e:
        logger.error(f"程序运行出错：{str(e)}")
    finally:
        # 8. 关闭 HTTP 连接
        await http.close()


# 9. 运行推送任务
if __name__ == "__main__":
    # 使用 asyncio 运行异步主函数
    asyncio.run(main())
