import botpy
from botpy import logging
from botpy.message import DirectMessage, C2CMessage, GroupMessage
from botpy.manage import C2CManageEvent

# 替换成你的机器人凭证
APPID = os.getenv("QQ_BOT_APPID", "")
SECRET = os.getenv("QQ_BOT_SECRET", "")  # 注意：新版SDK使用 secret 而不是 token

logger = logging.get_logger()


class MyClient(botpy.Client):
    """自定义机器人客户端，继承自 botpy.Client"""
    
    async def on_direct_message_create(self, message: DirectMessage):
        """
        监听私信消息事件（新版对应私聊消息）
        当用户给机器人发送私信时触发
        """
        user_openid = message.author.id
        user_nick = message.author.username
        msg_content = message.content
        
        logger.info("===== 捕获用户私聊 =====")
        logger.info(f"用户昵称：{user_nick}")
        logger.info(f"用户openid：{user_openid} 【复制这个作为TARGET_OPENID】")
        logger.info(f"消息内容：{msg_content}")
        logger.info("=======================\n")
        
        # 可选：自动回复用户
        # await message.reply(content="收到你的消息啦！")

    async def on_c2c_message_create(self, message: C2CMessage):
        """
        监听 C2C 单聊消息事件
        当用户给机器人发送单聊消息时触发
        """
        user_openid = message.author.user_openid
        msg_content = message.content
        msg_id = message.id
        
        logger.info("===== 捕获 C2C 单聊消息 =====")
        logger.info(f"用户openid：{user_openid}")
        logger.info(f"消息内容：{msg_content}")
        logger.info(f"消息ID：{msg_id}")
        logger.info("=======================\n")
        
        # 可选：自动回复用户
        # await message.reply(content="收到你的消息啦！")

    async def on_group_at_message_create(self, message: GroupMessage):
        """
        监听群聊 @机器人 消息事件
        当用户在群里 @机器人 时触发
        """
        member_openid = message.author.member_openid
        group_openid = message.group_openid
        msg_content = message.content
        msg_id = message.id
        
        logger.info("===== 捕获群聊@消息 =====")
        logger.info(f"群openid：{group_openid}")
        logger.info(f"成员openid：{member_openid}")
        logger.info(f"消息内容：{msg_content}")
        logger.info(f"消息ID：{msg_id}")
        logger.info("=======================\n")
        
        # 可选：自动回复群消息
        # await message.reply(content="收到群消息啦！")

    async def on_friend_add(self, event: C2CManageEvent):
        """
        监听好友添加事件
        当用户添加机器人为好友时触发
        """
        user_openid = event.openid
        
        logger.info("===== 捕获新好友添加 =====")
        logger.info(f"用户openid：{user_openid} 【复制这个作为TARGET_OPENID】")
        logger.info("=========================\n")


if __name__ == "__main__":
    # 设置需要监听的事件意图
    intents = botpy.Intents.none()
    intents.direct_message = True  # 私信事件
    intents.public_messages = True  # 群/C2C消息事件（包含好友添加）
    
    # 初始化客户端
    client = MyClient(intents=intents)
    
    # 启动机器人
    logger.info("机器人已启动，等待用户加好友/发消息...")
    client.run(appid=APPID, secret=SECRET)