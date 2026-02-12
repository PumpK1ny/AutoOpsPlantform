"""
QQ机器人启动脚本（带HTTP API）

功能：
1. 加载自定义消息处理器（handlers目录）
2. 启动QQ消息监听（WebSocket）
3. 启动HTTP API服务，接收通知推送请求
4. 未触发关键词时调用GLM-4.7-flash进行AI对话

使用方法：
    python run.py

HTTP API 接口：
    POST http://localhost:8080/api/notify
    {
        "openid": "用户openid",
        "content": "通知内容",
        "msg_type": "c2c"  // 可选，默认c2c，可选值：c2c, group
    }

扩展自定义回复：
    在 handlers/ 目录下新建 .py 文件，实现 register_handlers() 函数返回关键词-处理器字典
"""

import os
import sys
import asyncio
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from datetime import datetime, timedelta

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from message_push.QQ.listen import run_listener, APPID, SECRET, logger
from botpy.http import BotHttp
from botpy.robot import Token

HTTP_HOST = os.getenv("QQ_BOT_HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("QQ_BOT_HTTP_PORT", "8080"))
TOKEN_REFRESH_INTERVAL = int(os.getenv("QQ_BOT_TOKEN_REFRESH_INTERVAL", "300"))

_http_client = None
_http_client_lock = asyncio.Lock()
_last_login_time = None
_login_count = 0


async def get_http_client(force_refresh: bool = False):
    """获取或创建 HTTP 客户端，支持自动刷新token"""
    global _http_client, _last_login_time, _login_count
    
    async with _http_client_lock:
        now = datetime.now()
        
        need_refresh = (
            force_refresh or 
            _http_client is None or 
            _last_login_time is None or
            (now - _last_login_time).total_seconds() > TOKEN_REFRESH_INTERVAL
        )
        
        if need_refresh:
            try:
                if _http_client is not None:
                    try:
                        _http_client.close()
                    except:
                        pass
                
                token = Token(APPID, SECRET)
                _http_client = BotHttp(timeout=10)
                await _http_client.login(token)
                _last_login_time = now
                _login_count += 1
                logger.info(f"✅ HTTP 客户端已初始化/刷新 (第{_login_count}次)")
            except Exception as e:
                logger.error(f"❌ HTTP 客户端初始化失败: {e}")
                _http_client = None
                raise
        
        return _http_client


async def send_notification_with_retry(openid: str, content: str, msg_type: str = "c2c", max_retries: int = 3):
    """发送通知消息，支持自动重试和token刷新"""
    last_error = None
    
    for attempt in range(max_retries):
        try:
            force_refresh = attempt > 0
            http = await get_http_client(force_refresh=force_refresh)
            
            if msg_type == "c2c":
                from botpy.http import Route
                route = Route("POST", f"/v2/users/{openid}/messages")
                result = await http.request(route, json={"content": content})
            elif msg_type == "group":
                from botpy.http import Route
                route = Route("POST", f"/v2/groups/{openid}/messages")
                result = await http.request(route, json={"content": content})
            else:
                return {"success": False, "error": f"不支持的消息类型: {msg_type}"}
            
            logger.info(f"✅ 通知发送成功 [{msg_type}]: {openid}")
            return {"success": True, "result": result}
            
        except Exception as e:
            last_error = str(e)
            logger.warning(f"⚠️ 第 {attempt + 1} 次发送失败: {last_error}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
    
    logger.error(f"❌ 通知发送失败 (重试{max_retries}次后): {last_error}")
    return {"success": False, "error": last_error}


class NotifyHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""
    
    def log_message(self, format, *args):
        """自定义日志"""
        logger.info(f"[HTTP] {format % args}")
    
    def _send_json(self, status_code: int, data: dict):
        """发送 JSON 响应"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    
    def do_OPTIONS(self):
        """处理 CORS 预检请求"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_GET(self):
        """处理 GET 请求"""
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "qq-bot"})
        else:
            self._send_json(404, {"error": "Not Found"})
    
    def do_POST(self):
        if self.path == "/api/notify":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(post_data)
                
                openid = data.get("openid")
                content = data.get("content")
                msg_type = data.get("msg_type", "c2c")
                
                if not openid:
                    self._send_json(400, {"success": False, "error": "缺少参数: openid"})
                    return
                
                if not content:
                    self._send_json(400, {"success": False, "error": "缺少参数: content"})
                    return
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    send_notification_with_retry(openid, content, msg_type, max_retries=3)
                )
                loop.close()
                
                if result["success"]:
                    self._send_json(200, result)
                else:
                    self._send_json(500, result)
                    
            except json.JSONDecodeError:
                self._send_json(400, {"success": False, "error": "JSON 解析失败"})
            except Exception as e:
                logger.error(f"❌ HTTP API 错误: {e}")
                self._send_json(500, {"success": False, "error": str(e)})
        else:
            self._send_json(404, {"error": "Not Found"})


def run_http_server():
    """在单独线程中运行 HTTP 服务器"""
    server = HTTPServer((HTTP_HOST, HTTP_PORT), NotifyHandler)
    logger.info(f"🌐 HTTP API 服务已启动: http://{HTTP_HOST}:{HTTP_PORT}")
    logger.info(f"   健康检查: http://{HTTP_HOST}:{HTTP_PORT}/health")
    logger.info(f"   通知接口: POST http://{HTTP_HOST}:{HTTP_PORT}/api/notify")
    server.serve_forever()


def main():
    """主函数：同时启动 QQ 机器人和 HTTP API"""
    print("""
    ╔══════════════════════════════════════════════════╗
    ║                                                  ║
    ║       🤖 QQ基金分析机器人启动器                     ║
    ║          （带 HTTP API 通知服务）                  ║
    ║                                                  ║
    ╚══════════════════════════════════════════════════╝
    """)
    
    # 检查环境变量
    from message_push.QQ.api_key_manager import get_api_key_simple
    api_key = get_api_key_simple()
    if not api_key:
        print("⚠️ 警告: 未设置 ZHIPU_API_KEY 环境变量")
        print("   AI对话功能可能无法正常工作")
        print("   请在 .env 文件中设置 ZHIPU_API_KEY=your_api_key")
        print("   支持多密钥配置，使用逗号分隔: ZHIPU_API_KEY=key1,key2,key3\n")
    
    # 启动 HTTP 服务器（在后台线程）
    http_thread = Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # 启动 QQ 消息监听（主线程，阻塞）
    try:
        run_listener(enable_ai=True)
    except KeyboardInterrupt:
        print("\n\n👋 机器人已停止")
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
