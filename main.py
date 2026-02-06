from AI.news_collector import NewsCollector
from AI.fund_analysiser import FundAnalysiser

if __name__ == "__main__":

    ai = FundAnalysiser()
    ai.run("""
    # 基金分析智能体工作流程

    1. 使用 `get_sector_fund_flow` 获取今日资金流向数据，以及 5 日资金流向数据。

    2. 根据资金流向数据，分析基金的动态和趋势。

    3. 最后只回答下面的内容，不得进行总结和输出其他内容：
    - 分析报告已保存为 `data/result/fund_analysis/yyyy-mm-dd.md`。

    ## 要求

    - 不要深度思考每个板块的资金流向数据，只需要根据资金流向数据，分析基金的动态和趋势。
    - 禁止过度思考。
    """)
