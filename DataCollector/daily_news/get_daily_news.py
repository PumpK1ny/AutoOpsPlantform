import requests
import json
import re
import os
import sys
from datetime import datetime
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from AI.summary_core import summarize_text
def get_daily_news():
    url = 'https://top.news.sina.com.cn/ws/GetTopDataList.php'

    headers = {
        "Referer": "https://news.sina.com.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
        "sec-ch-ua-mobile": "?0"
    }

    date = datetime.now().strftime('%Y%m%d')

    params = {
        "top_type": "day",
        "top_cat": "www_www_all_suda_suda",
        "top_time": date,
        "top_show_num": "100",
        "top_order": "DESC",
        "js_var": "all_1_data01"
    }

    response = requests.get(url, headers=headers, params=params)
    text = response.text

    match = re.search(r'var\s+\w+\s*=\s*(\{.*\});', text, re.DOTALL)
    if match:
        json_str = match.group(1)
        data = json.loads(json_str)
        
        news_list = []
        for item in data.get('data', []):
            news_info = {
                'id': item.get('id'),
                'title': item.get('title'),
                'create_date': item.get('create_date'),
                'url': item.get('url'),
            }
            news_list.append(news_info)
        
        result = {
            'total': len(news_list),
            'news': news_list
        }
        
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'json')
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(output_dir, f'daily_news_{date}.json')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        # 去除url
        for item in news_list:
            item.pop('url', None)
        result['news'] = news_list
        return result, output_file
    else:
        return None, None
def get_detail_content(data_file_path,id):
    with open(data_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        news_list = data.get('news', [])
        for item in news_list:
            if item.get('id') == id:
                url = item.get('url')
    headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "cache-control": "max-age=0",
    "if-none-match": "W/",
    "priority": "u=0, i",
    "referer": "https://news.sina.com.cn/hotnews/",
    "sec-ch-ua-mobile": "?0",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0"
    }

    date = requests.get(url,headers=headers)
    date.encoding = date.apparent_encoding
    s = BeautifulSoup(date.text, 'html.parser')
    content = s.find("div",id="article").text
    print("开始总结")
    content = summarize_text(content)
    return content
if __name__ == '__main__':
    #print(get_daily_news())
    print(get_detail_content('data/json/daily_news_20260128.json','6744594'))