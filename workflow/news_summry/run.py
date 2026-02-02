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
    """发送工作流完成通知
    
    Args:
        success: 是否成功
        start_time: 运行开始时间字符串
        duration: 运行时间（秒）
        error_msg: 错误信息
        retry_count: 失败重试次数（成功时显示之前失败次数）
    """
    try:
        from message_push.QQ.qq_bot_push import send_notification_sync
        target_openid = os.getenv("QQ_TARGET_C2C_OPENID")
        if not target_openid:
            print("⚠️ 未配置 QQ_TARGET_C2C_OPENID，无法发送通知")
            return

        if success:
            retry_info = f"\n失败重试次数：{retry_count}" if retry_count > 0 else ""
            content = f"✅ 新闻采集工作流运行完成\n\n工作流运行开始时间：{start_time}\n工作流运行时间：{duration:.2f}秒{retry_info}\n查看：http://47.108.159.171:5000/"
        else:
            content = f"❌ 新闻采集工作流运行失败\n\n工作流运行开始时间：{start_time}\n工作流运行时间：{duration:.2f}秒\n错误信息：{error_msg}"

        result = send_notification_sync(target_openid, content, msg_type="c2c")
        if result.get("success"):
            print("📱 通知发送成功")
        else:
            print(f"⚠️ 通知发送失败: {result.get('error')}")
    except Exception as e:
        print(f"⚠️ 发送通知异常: {e}")

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
    print(f"\n运行时间：{duration:.2f}秒")
    send_workflow_notification(success, start_time_str, duration, error_msg, retry_count - 1 if success else 0)
