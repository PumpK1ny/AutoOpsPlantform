from AI.core import ZhipuChat
from AI.config.news_collector_config.system_config import SYSTEM_PROMPT
import DataCollector.fund_news.get_news as gn
import DataCollector.fund_article.get_fund_article as fa
class NewsCollector(ZhipuChat):
    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, extend_tools=["DataCollector/fund_news/tool_config.json", "DataCollector/fund_article/tool_config.json"])
        self.register_tool_functions_from_module(gn)
        self.register_tool_functions_from_module(fa)
    
    def run(self, message):
        return self.chat(message)