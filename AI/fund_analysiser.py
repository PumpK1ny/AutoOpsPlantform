from AI.core import ZhipuChat
from AI.config.fund_analysiser_config.system_config import SYSTEM_PROMPT
import DataCollector.fund_data.get_fund_info as gf

class FundAnalysiser(ZhipuChat):
    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, extend_tools="DataCollector/fund_data/tool_config.json")
        self.register_tool_functions_from_module(gf)
    
    def run(self, message):
        return self.chat(message)