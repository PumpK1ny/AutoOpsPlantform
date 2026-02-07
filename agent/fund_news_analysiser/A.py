from AI.news_collector import NewsCollector
from AI.sector_fund_flow_analyzer import SectorFundFlowAnalyzer
from AI.core import ZhipuChat
from agent.fund_news_analysiser.system_config import SYSTEM_PROMPT


class Agent(ZhipuChat):
    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, extend_tools="agent/fund_news_analysiser/sub_agent.json")
        # 实例化子Agent并注册其run方法为工具函数
        self.news_collector = NewsCollector()
        self.sector_fund_flow_analyzer = SectorFundFlowAnalyzer()
        self.register_tool_function("NewsCollector.run", self.news_collector.run)
        self.register_tool_function("SectorFundFlowAnalyzer.run", self.sector_fund_flow_analyzer.run)

    def run(self, message):
        return self.chat(message)
