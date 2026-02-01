from AI.news_collector import NewsCollector
from AI.fund_analysiser import FundAnalysiser
from AI.core import ZhipuChat
from agent.fund_news_analysiser.system_config import SYSTEM_PROMPT


class Agent(ZhipuChat):
    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, extend_tools="agent/fund_news_analysiser/sub_agent.json")
        # 实例化子Agent并注册其run方法为工具函数
        self.news_collector = NewsCollector()
        self.fund_analysiser = FundAnalysiser()
        self.register_tool_function("NewsCollector.run", self.news_collector.run)
        self.register_tool_function("FundAnalysiser.run", self.fund_analysiser.run)

    def run(self, message):
        return self.chat(message)