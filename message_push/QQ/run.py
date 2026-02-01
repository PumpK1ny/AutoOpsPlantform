"""
QQ机器人启动脚本

功能：
1. 加载自定义消息处理器（handlers目录）
2. 启动QQ消息监听
3. 未触发关键词时调用GLM-4.7-flash进行AI对话

使用方法：
    python run.py

扩展自定义回复：
    在 handlers/ 目录下新建 .py 文件，实现 register_handlers() 函数返回关键词-处理器字典
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from message_push.QQ.listen import run_listener


def main():
    """主函数：启动QQ消息监听"""
    print("""
    ╔══════════════════════════════════════════════════╗
    ║                                                  ║
    ║       🤖 QQ基金分析机器人启动器                     ║
    ║                                                  ║
    ╚══════════════════════════════════════════════════╝
    """)

    # 检查环境变量
    api_key = os.getenv("ZHIPU_API_KEY")
    if not api_key:
        print("⚠️ 警告: 未设置 ZHIPU_API_KEY 环境变量")
        print("   AI对话功能可能无法正常工作")
        print("   请在 .env 文件中设置 ZHIPU_API_KEY=your_api_key\n")

    # 启动监听
    try:
        run_listener(enable_ai=True)
    except KeyboardInterrupt:
        print("\n\n👋 机器人已停止")
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
