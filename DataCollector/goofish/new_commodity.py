import requests
import json
import hashlib
import time
from urllib.parse import quote, quote_plus
import pandas as pd
class Goofish:
    def __init__(self):
        self.d_token = '05e8d93405e1620d2bd8b30b2311f8c1'
        self.appKey = '34839810'
        self.url = 'https://h5api.m.goofish.com/h5/mtop.taobao.idlemtopsearch.pc.search/1.0/'
    def _get_cookie(self):
        return {
            "cookie2": "112077391417d3e06df63a76c1668277",
            "cna": "hEsPIqOYRjMBASQJimILIgdK",
            "_samesite_flag_": "true",
            "t": "93e64f0af4ee8562751b637afba9c5bb",
            "_tb_token_": "7e95e5369d336",
            "xlly_s": "1",
            "mtop_partitioned_detect": "1",
            "_m_h5_tk": "05e8d93405e1620d2bd8b30b2311f8c1_1770560584077",
            "_m_h5_tk_enc": "d27ed94af94e0264e2169d8e6dcbd801",
            "isg": "BOXl0Rxu4GwoFQSwMgJnoMPX9KEfIpm0LW0xnufK2pwr_gVwr3KphIOXjGKIfrFs",
            "tfstk": "gzwjXIN7SEYjBPsAWESyRnHl5iM63gWUkhiTxlp2XxHYXAZTjVuq_VPW5zUu_ou4Q7g_yzgxgSrNCzzurrr4blKsXzkxsSuZuVM_jysP89WUmoDi9w7FLO89D8MiWOkOaYUm4Ec589WUm164xtbUgJgi8cotBmh9BLISvcHtDVpOV4nsxCdTWAI5VcixDIdxBbH-0mHtWPHOVu3ofAnTWAI724mtBCQI4IgYcGt522WGcMErPdpTF0QiJo6vdmyScjgLD-99BMnjG2ExPZgs6gh8jfwMjdGaDW4ivrLA5V272-FLJaRqkWi_Y5adbImr1-DSW-BHA4ebf8G0aEdxAxgj9-UJxMrS67wS3-QMturSkXMza_bq_xabt2cAZa4_VqzThbLfzVPU4-h7JaJ7SfNT3YeAy9syfpuC0IA6VXvtV2S5VCAMT9E1XWWJXnGxq0JPVgTfsjnoV2S5VCAiM0mPagsWl1f.."
        }
    def _get_headers(self):
        return {
            "accept": "application/json",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.goofish.com",
            "priority": "u=1, i",
            "referer": "https://www.goofish.com/",
            "sec-ch-ua-mobile": "?0",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0"
        }
    def _get_data(self, keyword):
        # 编码搜索词
        data_dict = {
            "pageNumber": 1,
            "keyword": keyword,
            "fromFilter": False,
            "rowsPerPage": 30,
            "sortValue": "",
            "sortField": "",
            "customDistance": "",
            "gps": "",
            "propValueStr": {},
            "customGps": "",
            "searchReqFromPage": "pcSearch",
            "extraFilterValue": "{}",
            "userPositionJson": "{}"
        }
        return 'data=' + quote(json.dumps(data_dict, ensure_ascii=False))
    def _calculate_sign(self, timestamp, keyword):
        data_dict = {
            "pageNumber": 1,
            "keyword": keyword,
            "fromFilter": False,
            "rowsPerPage": 30,
            "sortValue": "",
            "sortField": "",
            "customDistance": "",
            "gps": "",
            "propValueStr": {},
            "customGps": "",
            "searchReqFromPage": "pcSearch",
            "extraFilterValue": "{}",
            "userPositionJson": "{}"
        }
        c_data = json.dumps(data_dict, ensure_ascii=False)
        sign_str = self.d_token + "&" + timestamp + "&" + self.appKey + "&" + c_data
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    def _get_params(self, keyword):
        timestamp = str(int(time.time() * 1000))
        sign_value = self._calculate_sign(timestamp, keyword)
        
        return {
            "jsv": "2.7.2",
            "appKey": self.appKey,
            "t": timestamp,
            "sign": sign_value,
            "v": "1.0",
            "type": "originaljson",
            "accountSite": "xianyu",
            "dataType": "json",
            "timeout": "20000",
            "api": "mtop.taobao.idlemtopsearch.pc.search",
            "sessionOption": "AutoLoginOnly",
            "spm_cnt": "a21ybx.search.0.0",
            "spm_pre": "a21ybx.search.searchInput.0"
        }
    def _parse_response(self, response):
      try:
        result = {}
        data = response.json()
        if not data.get('ret')[0] == "SUCCESS::调用成功":
          return "error"
        commodity_list = data.get('data').get('resultList', [])
        if commodity_list == []:
          return []
        for idx,commodity in enumerate(commodity_list):
          info = {}
          # 总商品信息
          pre = commodity.get('data').get('item').get('main').get('exContent')
          # 获取价格
          prc = pre.get('price')
          price = ""
          for i in prc:
            price += i.get('text','')
          # 获取商品名称
          title = pre.get('title','')

          # 批量添加商品信息
          info['area'] = pre.get('area','')
          info['price'] = price
          info['title'] = title
          result[idx] = info
        return result

      except:
        return "error"
    def search(self, keyword):
        headers = self._get_headers()
        data = self._get_data(keyword)
        params = self._get_params(keyword)
        cookie = self._get_cookie()
        response = requests.post(self.url, headers=headers, data=data, params=params, cookies=cookie)
        return self._parse_response(response)
    def show_commodity(self, commodity):
        result = self.search(commodity)
        df = pd.DataFrame()
        df['地区'] = [i['area'] for i in result.values()]
        df['价格'] = [i['price'] for i in result.values()]
        df['商品名称'] = [i['title'] for i in result.values()]
        return df
if __name__ == "__main__":
    searcher = Goofish()
    result = searcher.show_commodity('iphone')
    print(result)
