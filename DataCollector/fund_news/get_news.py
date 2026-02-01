import requests
import json
import time
import re
import os
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from AI.summary_core import summarize_text
def get_fast_news()-> dict:
    """
    获取焦点快速新闻
    return {
        "summary_1": "", # 概览
        "showTime_1": "", # 发布时间
        "code_1": "" # 页面编码
    }
    """
    datas = {}
    url = 'https://np-weblist.eastmoney.com/comm/web/getFastNewsList'

    headers = {
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Connection": "keep-alive",
    "Referer": "https://kuaixun.eastmoney.com/yw.html",
    "Sec-Fetch-Dest": "script",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
    "sec-ch-ua-mobile": "?0"
    }

    params={
    "client": "web",
    "biz": "web_724",
    "fastColumn": "101",
    "sortEnd": "",
    "pageSize": "50",
    "req_trace": str(int(time.time() * 1000)-2),
    "_": str(int(time.time() * 1000)),
    "callback": "jQuery1830666290717303444_1769334831165"
    }


    # 发送GET请求
    response = requests.get(url, headers=headers, params=params)
    # 去掉 JSONP 包装，提取纯 JSON 字符串
    json_text = response.text.strip()
    if json_text.startswith("jQuery"):
        # 找到第一个左括号与最后一个右括号之间的内容
        left = json_text.find("(") + 1
        right = json_text.rfind(")")
        json_text = json_text[left:right]
    data = json.loads(json_text)["data"]["fastNewsList"]
    for idx, item in enumerate(data):
        datas[f"summary_{idx+1}"] = item["summary"]
        datas[f"showTime_{idx+1}"] = item["showTime"]
        datas[f"code_{idx+1}"] = item["code"]
    return datas
def get_fund_news()-> dict:
    """
    获取基金新闻
    return {
        "summary_1": "", # 概览
        "showTime_1": "", # 发布时间
        "code_1": "" # 页面编码
    }
    """
    datas = {}
    url = 'https://np-weblist.eastmoney.com/comm/web/getFastNewsList'

    headers = {
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Connection": "keep-alive",
    "Referer": "https://kuaixun.eastmoney.com/jj.html",
    "Sec-Fetch-Dest": "script",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
    "sec-ch-ua-mobile": "?0"
    }

    # 可配置的请求参数，方便后续灵活调整
    params = {
        "client": "web",                 # 客户端类型
        "biz": "web_724",                # 业务标识
        "fastColumn": "109",             # 快讯栏目 ID
        "sortEnd": "",                   # 翻页游标（空串表示首页）
        "pageSize": "50",                # 每页条数，可按需增减
        "req_trace": str(int(time.time() * 1000)-1),    # 请求追踪 ID，可动态生成
        "_": str(int(time.time() * 1000)),            # 时间戳，防止缓存
        "callback": "jQuery18308641193333793972_1769333926463"  # JSONP 回调函数名，可随机生成
    }


    # 发送GET请求
    response = requests.get(url, headers=headers, params=params)
    # 去掉 JSONP 包装，提取纯 JSON 字符串
    json_text = response.text.strip()
    if json_text.startswith("jQuery"):
        # 找到第一个左括号与最后一个右括号之间的内容
        left = json_text.find("(") + 1
        right = json_text.rfind(")")
        json_text = json_text[left:right]

    data = json.loads(json_text)["data"]["fastNewsList"]
    for idx, item in enumerate(data):
        datas[f"summary_{idx+1}"] = item["summary"]
        datas[f"showTime_{idx+1}"] = item["showTime"]
        datas[f"code_{idx+1}"] = item["code"]
    return datas
def get_page_news(page)-> str:
    """
    获取具体的页面的新闻文章
    :param page: 页面码
    :return: 页面新闻文章数据
    """
    url = f'https://finance.eastmoney.com/a/{page}.html'
    headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Referer": "https://kuaixun.eastmoney.com/yw.html",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-site",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
    "sec-ch-ua-mobile": "?0"
    }
    # 发送GET请求
    response = requests.get(url, headers=headers)
    # 提取页面内容
    page_content = response.text
    page_news = re.search(r'<!--文章主体-->(.*?) <!-- 文尾部其它信息 -->', page_content, re.DOTALL)
    if page_news:
        page_news = page_news.group(1).strip()
    if page_news == None:
        return ""
    #替换</p>为换行符
    page_news = page_news.replace("</p>", "\n")
    #去除html标签
    page_news = re.sub(r'<.*?>', '', page_news)
    page_news = page_news.strip()
    return page_news
def get_multi_page_news(page_code_list: list)-> dict:
    """
    获取多条新闻具体的新闻文章
    return {
        "summary_1": "", # 概览
        "showTime_1": "", # 发布时间
        "code_1": "" # 页面编码
    }
    """
    datas = {}
    for page_code in page_code_list:
        page_news = get_page_news(page_code)
        print(f"总结新闻{page_code}")
        page_news = summarize_text(page_news)
        datas[f"news_{page_code}"] = page_news
    return datas
def get_dongfang_notice_sub(page: int = 1, page_size: int = 10) -> dict:
    """
    获取东方财富基金公告
    :param page: 页码，默认1
    :param page_size: 每页数量，默认10
    :return: 公告列表，格式为 {"total": 总数, "notice": [{"title": 标题, "link": 链接, "date": 日期}, ...]}
    """
    url = 'https://www.dongcaijijin.com/service/article-list-load-dft'

    headers = {
        "Accept": "text/html, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Connection": "keep-alive",
        "Referer": "https://www.dongcaijijin.com/service/xxpl",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua-mobile": "?0"
    }

    params = {
        "tableId": "contentload",
        "p": str(page),
        "pageSize": str(page_size),
        "topic": "xxpl",
        "tablePaging": "xxpl",
        "fundCode": ""
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.encoding = 'utf-8'
        html_content = response.text

        soup = BeautifulSoup(html_content, 'html.parser')

        news_list = []

        li_items = soup.find_all('li')

        for li in li_items:
            a_tag = li.find('a')
            if a_tag:
                title = a_tag.get('title', '').strip()
                link = a_tag.get('href', '').strip()

                span_tag = li.find('span', class_='c999')
                if span_tag:
                    date = span_tag.get_text(strip=True)
                else:
                    date = ''

                if title and link:
                    news_list.append({
                        "title": title,
                        "link": link,
                        "date": date
                    })

        page_count_span = soup.find('span', class_='page-count')
        total = 0
        if page_count_span:
            total_text = page_count_span.get_text(strip=True)
            match = re.search(r'共\s*(\d+)\s*条', total_text)
            if match:
                total = int(match.group(1))

        result = {
            "total": total,
            "page": page,
            "page_size": page_size,
            "notice": news_list
        }

        return result

    except Exception as e:
        return {
            "error": str(e),
            "total": 0,
            "notice": []
        }

def extract_pdf_content(pdf_url: str) -> dict:
    """
    从PDF URL提取文字内容
    :param pdf_url: PDF文件的URL
    :return: {"success": True/False, "content": PDF文字内容, "error": 错误信息}
    """
    try:
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()

        from io import BytesIO
        pdf_file = BytesIO(response.content)

        reader = PdfReader(pdf_file)

        text_content = ""

        for page in reader.pages:
            text_content += page.extract_text() + "\n"

        text_content = text_content.strip()

        if not text_content:
            return {
                "success": False,
                "content": "",
                "error": "PDF内容为空或无法提取文字"
            }

        return {
            "success": True,
            "content": text_content,
            "error": None
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "content": "",
            "error": f"下载PDF失败: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "content": "",
            "error": f"提取PDF内容失败: {str(e)}"
        }

def get_dongfang_notice(page: int = 1, page_size: int = 5) -> dict:
    """
    获取东方财富基金公告并提取PDF内容
    :param page: 页码，默认1
    :param page_size: 每页数量，默认5（因为PDF提取较慢，建议设置较小的值）
    :return: 标题、索引、日期。
    """
    news_result = get_dongfang_notice_sub(page=page, page_size=page_size)

    if "error" in news_result:
        return news_result

    for idx, news_item in enumerate(news_result["notice"], start=1):    
        news_item["index"] = idx
        link = news_item["link"]

        if link.endswith('.pdf'):
            pdf_result = extract_pdf_content(link)
            news_item["pdf_content"] = pdf_result["content"]
            news_item["pdf_extract_success"] = pdf_result["success"]
            news_item["pdf_error"] = pdf_result["error"]
        else:
            news_item["pdf_content"] = ""
            news_item["pdf_extract_success"] = False
            news_item["pdf_error"] = "非PDF文件"
    # 保存到文件
    json_dir = "data/json"
    os.makedirs(json_dir, exist_ok=True)
    with open(f"{json_dir}/dongfang_notice.json", "w", encoding="utf-8") as f:
        json.dump(news_result, f, ensure_ascii=False, indent=2)
    # 简化信息返回，只返回标题、索引、日期
    news_result["notice"] = [{"title": item["title"], "index": item["index"], "date": item["date"]} for item in news_result["notice"]]
    return news_result
def read_dongfang_notice(idxs: list[int] = [])-> dict:
    """
    从文件读取东方财富基金公告并提取PDF内容
    :param idxs: 公告索引列表
    :return: 标题、日期、公告内容
    """
    if not isinstance(idxs, list):
        return "idxs must be a list"
    if not len(idxs) > 0:
        return "idxs must be a non-empty list"
    if not all(isinstance(idx, int) for idx in idxs):
        try:
            idxs = [int(idx) for idx in idxs]
        except ValueError:
            return "idxs must be a list of integers"
    final_result = {}
    # 从新路径读取文件
    json_dir = "data/json"
    with open(f"{json_dir}/dongfang_notice.json", "r", encoding="utf-8") as f:
        news_result = json.load(f)
    # 提取idx对应的标题+日期+公告内容
    for idx in idxs:
        for item in news_result["notice"]:
            if item["index"] == idx:              
                print(f"总结公告{idx}")
                summarize_result = summarize_text(item["pdf_content"])
                final_result[f"notice_{idx}"] = {
                    "title": item["title"],
                    "date": item["date"],
                    "pdf_content": summarize_result
                }

    return final_result

if __name__ == "__main__":
    print(get_notice_with_pdf_content(page=1, page_size=10))
    print("-----------------"*20)
    print(read_notice_with_pdf_content_from_file([1, 2, 3]))
