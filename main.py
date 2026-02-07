from AI.news_collector import NewsCollector
from AI.sector_fund_flow_analyzer import SectorFundFlowAnalyzer

if __name__ == "__main__":

    ai = SectorFundFlowAnalyzer()
    ai.run("""
    执行板块资金流向分析，获取今日和5日板块资金流向数据并生成分析报告
    """)
