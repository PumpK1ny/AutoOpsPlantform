import os
import sys
import time
# 获取当前文件所在目录下的 workflow.md 内容
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKFLOW_PATH = os.path.join(CURRENT_DIR, "workflow.md")
with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
    WORKFLOW = f.read()
print("#"*50)
print("#"," "*15,"新闻采集工作流"," "*15,"#")
print("#"*50)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from agent.fund_news_analysiser.A import Agent

def send_workflow_notification(success: bool, start_time: str, duration: float, error_msg: str = None, retry_count: int = 0):
    try:
        from message_push.QQ.qq_bot_push import send_notification_sync, check_service_health
        target_openid = os.getenv("QQ_TARGET_C2C_OPENID")
        if not target_openid:
            print("⚠️ 未配置 QQ_TARGET_C2C_OPENID，无法发送通知")
            return False

        if success:
            retry_info = f"\n失败重试次数：{retry_count}" if retry_count > 0 else ""
            content = f"✅ 新闻采集工作流运行完成\n\n工作流运行开始时间：{start_time}\n工作流运行时间：{duration:.2f}秒{retry_info}\n查看：http://47.108.159.171:5000/"
        else:
            content = f"❌ 新闻采集工作流运行失败\n\n工作流运行开始时间：{start_time}\n工作流运行时间：{duration:.2f}秒\n错误信息：{error_msg}"

        import asyncio
        if not asyncio.run(check_service_health(max_retries=3, retry_delay=3.0)):
            print("⚠️ QQ bot 服务不可用，等待后重试...")
            time.sleep(10)
            if not asyncio.run(check_service_health(max_retries=2, retry_delay=5.0)):
                print("❌ QQ bot 服务仍然不可用，跳过通知发送")
                return False

        result = send_notification_sync(target_openid, content, msg_type="c2c")
        if result.get("success"):
            print("📱 通知发送成功")
            return True
        else:
            print(f"⚠️ 通知发送失败: {result.get('error')}")
            return False
    except Exception as e:
        print(f"⚠️ 发送通知异常: {e}")
        return False

if __name__ == "__main__":
    start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    
    start_time = time.time()
    max_retries = 3
    retry_count = 0
    success = False
    error_msg = None
    
    for attempt in range(max_retries):
        try:
            print(f"\n{'='*50}")
            print(f"第 {attempt + 1} 次尝试运行工作流...")
            print('='*50)
            ai = Agent()
            ai.run(WORKFLOW)
            success = True
            error_msg = None
            break
        except Exception as e:
            retry_count += 1
            error_msg = str(e)
            print(f"⚠️ 第 {attempt + 1} 次运行失败: {error_msg}")
            if attempt < max_retries - 1:
                print(f"等待 2 秒后重试...")
                time.sleep(2)
    

    end_time = time.time()
    duration = end_time - start_time

    notification_sent = False
    for notify_attempt in range(3):
        if send_workflow_notification(success, start_time_str, duration, error_msg, retry_count):
            notification_sent = True
            break
        else:
            remaining = 2 - notify_attempt
            if remaining > 0:
                print(f"等待 5 秒后重试发送通知... (剩余 {remaining} 次)")
                time.sleep(5)

    if not notification_sent:
        print("❌ 通知发送失败，请检查 QQ bot 服务状态")

    print(f"\n运行时间：{duration:.2f}秒")
    print("工作流运行完成")
    print("="*50)
