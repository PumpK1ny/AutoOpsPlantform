import akshare as ak
import pandas as pd
import os
def get_fund_daily(fund_code, period="1年"):
    """
    使用akshare获取基金日线数据
    :param fund_code: 基金代码
    :param period: 时间段，可选值："1月", "3月", "6月", "1年", "3年", "5年", "今年来", "成立来"，默认近一年
    :return: 基金日线数据DataFrame
    """
    # 获取原始数据
    data = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势", period=period)
    
    # 转换净值日期为datetime类型
    data['净值日期'] = pd.to_datetime(data['净值日期'])
    
    # 获取当前日期
    today = pd.Timestamp.now()
    
    # 根据period参数过滤数据
    if period == "1月":
        start_date = today - pd.DateOffset(months=1)
    elif period == "3月":
        start_date = today - pd.DateOffset(months=3)
    elif period == "6月":
        start_date = today - pd.DateOffset(months=6)
    elif period == "1年":
        start_date = today - pd.DateOffset(years=1)
    elif period == "3年":
        start_date = today - pd.DateOffset(years=3)
    elif period == "5年":
        start_date = today - pd.DateOffset(years=5)
    elif period == "今年来":
        start_date = pd.Timestamp(year=today.year, month=1, day=1)
    else:  # 成立来
        return data
    
    # 过滤出指定时间段的数据
    data = data[data['净值日期'] >= start_date]
    
    return data
def calculate_factors(fund_code, period="1年"):
    """
    计算基金因子和技术指标
    :param fund_code: 基金代码
    :param period: 时间段，可选值："1月", "3月", "6月", "1年", "3年", "5年", "今年来", "成立来"，默认近一年
    :return: 基金因子DataFrame
    """
    try:
        # 检查文件是否存在，不存在则获取数据
        if not os.path.exists(f"data/{fund_code}_daily.csv"):
            data = get_fund_daily(fund_code, period=period)
        else:
            data = pd.read_csv(f"data/{fund_code}_daily.csv")
        
        # 确保净值日期为datetime类型
        data['净值日期'] = pd.to_datetime(data['净值日期'])
        # 按日期排序
        data = data.sort_values('净值日期')
        
        # 计算日收益率
        daily_returns = data['单位净值'].pct_change().dropna()
        
        # 计算均线指标
        data['MA5'] = data['单位净值'].rolling(window=5).mean()
        data['MA10'] = data['单位净值'].rolling(window=10).mean()
        data['MA20'] = data['单位净值'].rolling(window=20).mean()
        
        # 计算布林带
        data['BB_Middle'] = data['单位净值'].rolling(window=20).mean()
        data['BB_Std'] = data['单位净值'].rolling(window=20).std()
        data['BB_Upper'] = data['BB_Middle'] + 2 * data['BB_Std']
        data['BB_Lower'] = data['BB_Middle'] - 2 * data['BB_Std']
        
        # 计算EMA指标
        data['EMA5'] = data['单位净值'].ewm(span=5, adjust=False).mean()
        data['EMA10'] = data['单位净值'].ewm(span=10, adjust=False).mean()
        data['EMA20'] = data['单位净值'].ewm(span=20, adjust=False).mean()
        data['EMA60'] = data['单位净值'].ewm(span=60, adjust=False).mean()
        
        # 计算MACD指标
        ema_short = data['单位净值'].ewm(span=12, adjust=False).mean()
        ema_long = data['单位净值'].ewm(span=26, adjust=False).mean()
        data['MACD_DIF'] = ema_short - ema_long
        data['MACD_DEA'] = data['MACD_DIF'].ewm(span=9, adjust=False).mean()
        data['MACD_BAR'] = 2 * (data['MACD_DIF'] - data['MACD_DEA'])
        
        # 计算RSI指标
        delta = data['单位净值'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))
        
        # 创建因子DataFrame，只包含一行汇总数据
        factors = pd.DataFrame()
        
        # 计算年化收益率 (使用几何平均)
        total_return = (data['单位净值'].iloc[-1] / data['单位净值'].iloc[0]) - 1
        years = len(data) / 252
        annual_return = (1 + total_return) ** (1 / years) - 1
        
        # 计算最大回撤
        rolling_max = data['单位净值'].rolling(window=len(data), min_periods=1).max()
        drawdown = (data['单位净值'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # 计算年化波动率 (使用日收益率的标准差，乘以 sqrt(252))
        daily_volatility = daily_returns.std()
        annual_volatility = daily_volatility * (252 ** 0.5)
        
        # 计算夏普比率
        risk_free_rate = 0.02
        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility if annual_volatility != 0 else 0
        
        # 将所有因子添加到DataFrame中，只生成一行
        factors = pd.DataFrame({
            '年化收益率': [annual_return],
            '最大回撤': [max_drawdown],
            '年化波动率': [annual_volatility],
            '夏普比率': [sharpe_ratio]
        })
        
        # 保存因子文件
        factors.to_csv(f"data/{fund_code}_factors.csv", index=False)
        
        # 保存包含所有技术指标的日线数据
        data.to_csv(f"data/{fund_code}_daily.csv", index=False)
        
        return factors
    except Exception as e:
        return f"calculate {fund_code} factors failed: {e}"


def calculate_multiple_factors(fund_code_list: list):
    """
    计算多个基金因子
    :param fund_code_list: 基金代码列表
    :return: 基金因子DataFrame
    """
    try:
        for fund_code in fund_code_list:
            calculate_factors(fund_code)
        return "calculate multiple factors success"
    except Exception as e:
        return f"calculate multiple factors failed: {e}"

if __name__ == "__main__":
    ...
    #calculate_daily_data("000001")
    calculate_factors("000001")
