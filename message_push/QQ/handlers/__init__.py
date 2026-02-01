"""
QQ消息处理器模块

每个处理器文件可以定义一个或多个关键词处理器
处理器函数签名: handler(message) -> str
"""

import os
import importlib
from typing import Dict, Callable


def load_handlers() -> Dict[str, Callable]:
    """
    自动加载所有处理器

    Returns:
        关键词到处理函数的映射字典
    """
    handlers = {}

    # 获取当前目录下所有.py文件
    current_dir = os.path.dirname(os.path.abspath(__file__))

    for filename in os.listdir(current_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]
            try:
                # 动态导入模块
                module = importlib.import_module(f'message_push.QQ.handlers.{module_name}')

                # 检查模块是否有 register_handlers 函数
                if hasattr(module, 'register_handlers'):
                    module_handlers = module.register_handlers()
                    if isinstance(module_handlers, dict):
                        handlers.update(module_handlers)
                        print(f"✅ 已加载处理器: {module_name}")

            except Exception as e:
                print(f"❌ 加载处理器 {module_name} 失败: {e}")

    return handlers
