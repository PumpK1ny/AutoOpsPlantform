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

if __name__ == "__main__":
    start_time = time.time()
    ai = Agent()
    ai.run(WORKFLOW)
    end_time = time.time()
    print(f"\n运行时间：{end_time - start_time}秒")
