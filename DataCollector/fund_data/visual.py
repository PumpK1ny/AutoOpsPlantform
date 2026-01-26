import matplotlib.pyplot as plt
import pandas as pd
import sys
import os

# 添加当前目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from get_fund_info import caculate

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

def visualize_fund(fund_code):
    """
    可视化基金数据，包括净值走势、均线和布林带
    :param fund_code: 基金代码
    """
    # 获取计算后的数据
    data = caculate(fund_code)
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 绘制净值走势
    ax.plot(data['净值日期'], data['单位净值'], label='单位净值', color='k', linewidth=1)
    
    # 绘制均线
    ax.plot(data['净值日期'], data['MA5'], label='5日均线', color='b', linewidth=0.8)
    ax.plot(data['净值日期'], data['MA10'], label='10日均线', color='g', linewidth=0.8)
    ax.plot(data['净值日期'], data['MA20'], label='20日均线', color='r', linewidth=0.8)
    
    # 绘制布林带
    ax.plot(data['净值日期'], data['BB_Upper'], label='布林带上轨', color='c', linestyle='--', linewidth=0.8)
    ax.plot(data['净值日期'], data['BB_Middle'], label='布林带中轨', color='m', linestyle='--', linewidth=0.8)
    ax.plot(data['净值日期'], data['BB_Lower'], label='布林带下轨', color='y', linestyle='--', linewidth=0.8)
    
    # 填充布林带区域
    ax.fill_between(data['净值日期'], data['BB_Upper'], data['BB_Lower'], alpha=0.1, color='c')
    
    # 设置标题和标签
    ax.set_title(f'基金 {fund_code} 净值走势及技术指标', fontsize=14)
    ax.set_xlabel('日期', fontsize=12)
    ax.set_ylabel('净值', fontsize=12)
    
    # 添加图例
    ax.legend(loc='best', fontsize=10)
    
    # 设置网格线
    ax.grid(True, alpha=0.3)
    
    # 自动旋转日期标签
    plt.xticks(rotation=45)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图形
    plt.savefig(f'fund_{fund_code}_visual.png', dpi=300, bbox_inches='tight')
    print(f"图形已保存为 fund_{fund_code}_visual.png")
    
    # 尝试显示图形
    try:
        plt.show()
    except Exception as e:
        print(f"无法显示图形（可能是无GUI环境）：{e}")

if __name__ == "__main__":
    # 默认基金代码
    fund_code = sys.argv[1] if len(sys.argv) > 1 else "000001"
    visualize_fund(fund_code)