import akshare as ak
import pandas as pd
import os
import requests
import json

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
        fund_dir = f"data/funds/{fund_code}"
        daily_file = f"{fund_dir}/daily.csv"
        
        if not os.path.exists(daily_file):
            data = get_fund_daily(fund_code, period=period)
        else:
            data = pd.read_csv(daily_file)
        
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
        
        # 创建基金目录（如果不存在）
        os.makedirs(fund_dir, exist_ok=True)
        
        # 保存因子文件
        factors.to_csv(f"{fund_dir}/factors.csv", index=False)
        
        # 保存包含所有技术指标的日线数据
        data.to_csv(daily_file, index=False)
        
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


def get_sector_fund_flow(fid="今日"):
    """
    获取东方财富网板块资金流向数据
    :param fid: 时间维度，可选值："今日", "5日", "10日"，默认5日
    :return: 板块资金流向DataFrame
    """
    # 定义不同时间维度的配置
    time_config = {
        "今日": {
            "fid": "f62",
            "fields": "f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13",
            "amount_fields": ['f62', 'f66', 'f72', 'f78', 'f84'],
            "percentage_fields": ['f3', 'f184', 'f69', 'f75', 'f81', 'f87'],
            "column_mapping": {
                'f14': '板块名称',
                'f3': '涨跌幅(%)',
                'f62': '主力净流入(亿元)',
                'f184': '主力净占比(%)',
                'f66': '超大单净流入(亿元)',
                'f69': '超大单净占比(%)',
                'f72': '大单净流入(亿元)',
                'f75': '大单净占比(%)',
                'f78': '中单净流入(亿元)',
                'f81': '中单净占比(%)',
                'f84': '小单净流入(亿元)',
                'f87': '小单净占比(%)',
                'f204': '领涨股票',
                'f205': '领涨股票代码'
            }
        },
        "5日": {
            "fid": "f164",
            "fields": "f12,f14,f2,f109,f164,f165,f166,f167,f168,f169,f170,f171,f172,f173,f257,f258,f124,f1,f13",
            "amount_fields": ['f164', 'f166', 'f168', 'f170', 'f172'],
            "percentage_fields": ['f109', 'f165', 'f167', 'f169', 'f171', 'f173'],
            "column_mapping": {
                'f14': '板块名称',
                'f109': '涨跌幅(%)',
                'f164': '主力净流入(亿元)',
                'f165': '主力净占比(%)',
                'f166': '超大单净流入(亿元)',
                'f167': '超大单净占比(%)',
                'f168': '大单净流入(亿元)',
                'f169': '大单净占比(%)',
                'f170': '中单净流入(亿元)',
                'f171': '中单净占比(%)',
                'f172': '小单净流入(亿元)',
                'f173': '小单净占比(%)',
                'f257': '领涨股票',
                'f258': '领涨股票代码'
            }
        },
        "10日": {
            "fid": "f174",
            "fields": "f12,f14,f2,f160,f174,f175,f176,f177,f178,f179,f180,f181,f182,f183,f260,f261,f124,f1,f13",
            "amount_fields": ['f174', 'f176', 'f178', 'f180', 'f182'],
            "percentage_fields": ['f160', 'f175', 'f177', 'f179', 'f181', 'f183'],
            "column_mapping": {
                'f14': '板块名称',
                'f160': '涨跌幅(%)',
                'f174': '主力净流入(亿元)',
                'f175': '主力净占比(%)',
                'f176': '超大单净流入(亿元)',
                'f177': '超大单净占比(%)',
                'f178': '大单净流入(亿元)',
                'f179': '大单净占比(%)',
                'f180': '中单净流入(亿元)',
                'f181': '中单净占比(%)',
                'f182': '小单净流入(亿元)',
                'f183': '小单净占比(%)',
                'f260': '领涨股票',
                'f261': '领涨股票代码'
            }
        }
    }
    
    # 验证fid参数
    if fid not in time_config:
        return "fid must be 今日, 5日, 10日"
    
    # 获取当前时间维度的配置
    config = time_config[fid]

    try:
        url = 'https://push2.eastmoney.com/api/qt/clist/get'

        headers = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Connection": "keep-alive",
        "Referer": "https://data.eastmoney.com/bkzj/hy.html",
        "Sec-Fetch-Dest": "script",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
        "sec-ch-ua-mobile": "?0"
        }

        params = {
            "cb": "jQuery1123019197073107348805_1769439769705",  # 回调函数名，用于 JSONP 跨域
            "fid": config["fid"],
            "po": "1",                                          # 排序方式：1 为降序
            "pz": "100",                                         # 每页返回条数：100 条
            "pn": "1",                                          # 页码：第 1 页
            "np": "1",                                          # 未知用途，固定传 1
            "fltt": "2",                                        # 未知用途，固定传 2
            "invt": "2",                                        # 未知用途，固定传 2
            "ut": "8dec03ba335b81bf4ebdf7b29ec27d15",           # 用户令牌，固定值
            "fs": "m:90 t:2",                                   # 筛选条件：m:90 为行业板块，t:2 为全部
            "fields": config["fields"]                         # 使用当前时间维度的fields参数
        }
        response = requests.get(url, headers=headers, params=params)
        
        # 解析JSONP响应
        callback_name = response.text.split('(')[0]
        data = json.loads(response.text.split(f"{callback_name}(")[1].split(");")[0])
        
        # 解析数据并转换为DataFrame
        sector_data = data['data']['diff']
        data_frame = pd.DataFrame(sector_data)

        # 1. 将金额字段转换为亿元
        for field in config["amount_fields"]:
            if field in data_frame.columns:
                data_frame[field] = (data_frame[field] / 10**8).round(2)
        
        # 2. 格式化百分比字段
        for field in config["percentage_fields"]:
            if field in data_frame.columns:
                data_frame[field] = data_frame[field].round(2)
        
        # 3. 选择需要的列并重命名
        selected_columns = list(config["column_mapping"].keys())
        data_frame = data_frame[selected_columns]
        data_frame.columns = list(config["column_mapping"].values())
        os.makedirs('data/sector_fund_flow', exist_ok=True)
        # 保存数据，文件名包含时间维度信息
        time_str = pd.Timestamp.now().strftime("%Y%m%d")
        file_path = f'data/sector_fund_flow/{time_str}_{fid}.csv'
        data_frame.to_csv(file_path, index=False)
        
        return f"get sector fund flow success,path: {file_path}"
    except Exception as e:
        return f"get sector fund flow failed: {e}"







if __name__ == "__main__":
    ...
    #calculate_daily_data("000001")
    result = get_fund_daily("000001")
    print(result)
