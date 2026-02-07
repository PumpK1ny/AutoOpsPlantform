from AI.core import ZhipuChat
from AI.config.fund_analysiser_config.system_config import SYSTEM_PROMPT
import DataCollector.fund_data.get_fund_info as gf

class SectorFundFlowAnalyzer(ZhipuChat):
    """
    板块资金流向分析器
    
    专注于分析板块资金流向数据，提供市场洞察。
    只能获取板块资金流向数据，无法获取个股、新闻、政策等其他信息。
    """
    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, extend_tools="DataCollector/fund_data/tool_config.json")
        self.register_tool_functions_from_module(gf)

    def run(self, message):
        """
        执行板块资金流向分析

        Args:
            message: 用户输入的消息

        Returns:
            分析结果
        """
        return self.chat(message)
