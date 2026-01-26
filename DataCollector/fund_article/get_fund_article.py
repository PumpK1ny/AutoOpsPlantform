import requests
from bs4 import BeautifulSoup
import json

def get_hot_article_ranking():
    """
    获取东方财富基金吧48小时热门文章排行和一周热门文章排行
    :return: 包含两个排行榜的JSON数据
    """
    try:
        # 请求头设置
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Referer": "https://guba.eastmoney.com/jj_2.html",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
            "sec-ch-ua-mobile": "?0"
        }
        
        # 获取基金吧首页内容
        url = "https://guba.eastmoney.com/jj_1.html"
        response = requests.get(url, headers=headers)
        html_content = response.text
        
        # 解析HTML内容
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 初始化结果列表
        hot_48h = []
        hot_week = []
        
        # 查找所有热门文章排行区域
        hot_sections = soup.find_all('div', class_=['gbbox2', 'gbhbl', 'titCont'])
        
        for section in hot_sections:
            # 获取标题，判断是48小时还是一周
            h5 = section.find('h5')
            if not h5:
                continue
            
            title_text = h5.get_text(strip=True)
            
            # 查找文章列表
            ul = section.find('ul', class_='hotop')
            if not ul:
                continue
            
            articles = []
            
            # 遍历每个文章项，添加索引
            idx = 1
            for li in ul.find_all('li'):
                # 查找标题元素
                tit_span = li.find('span', class_='tit')
                if not tit_span:
                    continue
                
                # 获取标题内容和链接
                a_tags = tit_span.find_all('a')
                if len(a_tags) < 2:
                    continue
                
                articles.append({
                    'idx': idx,
                    'title': tit_span.get_text(strip=True),
                    'href': a_tags[1].get('href', '')
                })
                idx += 1
            
            # 根据标题类型添加到对应列表
            if '48小时' in title_text:
                hot_48h = articles
            elif '一周' in title_text:
                hot_week = articles
        
        # 构建最终结果
        result = {
            '48小时热门文章': hot_48h,
            '一周热门文章': hot_week
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return {"error": str(e)}

if __name__ == '__main__':
    print(get_hot_article_ranking())