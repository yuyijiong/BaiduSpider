# 导入BaiduSpider
import sys
import warnings
import urllib3
urllib3.util.ssl_.DEFAULT_CIPHERS += 'AES256'
try:
    #requests.packages.urllib3.contrib.pyopenssl.DEFAULT_SSL_CIPHER_LIST += 'AES256'
    urllib3.contrib.pyopenssl.DEFAULT_SSL_CIPHER_LIST += 'AES256'
except AttributeError:
    # no pyopenssl support used / needed / available
    pass
from baiduspider import BaiduSpider
from tqdm import tqdm
from utils import add_get_text,update_real_url
import re
import os
import time
from pprint import pprint

#清洗文本，通用
def clean_text_uni_simple(content:str):
    #删除 \□\■
    content = content.replace(' ', '').replace('□', '').replace('■', '')
    #替换长空格为短空格
    content = content.replace(' ', ' ').replace('\u3000', ' ')
    #如果出现两个以上换行符，则最多保留2个
    content=re.sub('[\n\r]{2,}','\n\n',content)
    #如果出现两个以上空格，则最多保留2个
    content=re.sub(' {2,}','  ',content)
    # # -连续出现大于3次，则替换为---
    content = re.sub(r'-{3,}', '---', content)

    return content.strip()

## 根据query获取所有百度内容，返回list
def search_baidu_text(query: str, cookie: str = None, proxies=None, pn=1, max_return_results=None,driver_path=None):
    """
    :param query: 查询语句
    :param cookie: 用户cookie
    :param proxies:  代理
    :param pn:  页码
    :param max_return_results:  最大返回结果数
    :param driver_path:  浏览器驱动路径，用于重定向以获取真实url，避免反爬
    :return:  网页搜索结果的列表，每个元素是一个字典，包含标题、摘要、内容
    """
    # 搜索网页
    spider = BaiduSpider(cookie=cookie)
    headers = spider.headers
    res = spider.search_web(query=query, proxies=proxies, pn=pn,exclude=['music',"related","video"],normal_all=True)
    #如果res.normal为空，则重试
    if len(res.normal)==0:
        warnings.warn("百度搜索结果为空")

    print("百度一共有{}条结果".format(len(res.normal)))

    # res_plain_list只保留max_normal_results个结果
    if max_return_results is not None:
        if len(res.normal) > max_return_results:
            res.normal = res.normal[:max_return_results]
    # 更新真实url
    try:
        res=update_real_url(res)
        print("更新真实url完成")
    except Exception as e:
        warnings.warn("更新真实url失败，使用原始url。失败原因：{}".format(e))

    # 获取普通内容
    result_text_list = []
    for normal in tqdm(res.normal, desc='获取百度普通内容'):
        # 获取网页文本
        try:
            paragraph = normal.get_web_content()
            result_text_list.append({"标题":normal.title,"摘要":normal.des,"内容":clean_text_uni_simple(paragraph)})

        except Exception as e:
            # 判断是否是DEBUG模式
            if os.environ.get('DEBUG') == '1':
                raise
            else:
                warnings.warn("获取普通内容失败")
                print(e)

    return result_text_list

if __name__ == '__main__':
    cookie = "BAIDUID=15F7E03304904E00D27553D33F62B643:FG=1; BIDUPSID=15F7E03304904E00D27553D33F62B643; PSTM=1692619569; BD_UPN=12314753; BDUSS=DNxfkZxTjFtMy0xQUlRYTJreVZFZnctZXM3RGNOdXJyNzJWeUh6RWhWOVZDRjlsRVFBQUFBJCQAAAAAAAAAAAEAAAD59PZpeTEzODU4OTc0NDM3AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFV7N2VVezdlN; BDUSS_BFESS=DNxfkZxTjFtMy0xQUlRYTJreVZFZnctZXM3RGNOdXJyNzJWeUh6RWhWOVZDRjlsRVFBQUFBJCQAAAAAAAAAAAEAAAD59PZpeTEzODU4OTc0NDM3AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFV7N2VVezdlN; H_WISE_SIDS=39841_39935_39937_39933_39938_39732_40010_40024_40042; BDORZ=B490B5EBF6F3CD402E515D22BCDA1598; H_PS_PSSID=40024_40042_40090; H_WISE_SIDS_BFESS=39841_39935_39937_39933_39938_39732_40010_40024_40042; ab_sr=1.0.1_ZWM4NTY5ODUyNDlkNmY4NzAwMGUzNzMyODI3ZGEwZGE5OTFlNTJkZGU0ODI0Mjg0YzY3NjljMWRmNDhmMjQ4ODFhMmMzOWUyZWYxZjk5MGVjMTlkZWZmYTVjZTc4ZTU3MjVhYWI2NzMwNzYzOTEwMmI1MTMxYTVlZjcyNWU3MzAzOTUxZjMxNWIzNjUxZGE1Yzg4ZDcxNjdlNjQzYTlhYg==; BAIDUID_BFESS=15F7E03304904E00D27553D33F62B643:FG=1; delPer=0; BD_CK_SAM=1; PSINO=1; BA_HECTOR=812h042la4818h0l00a52g2lqegt2b1ips28o1t; ZFY=d2BbZR6rUyGbwHTeGQvpufNI3gYPFm3jKY1IuE6Eos8:C; sugstore=1; H_PS_645EC=b339i619h%2FxyZaekw0dkcU%2B%2FhnWdus7POb50%2FhyqaNdUVOX6pSZfZ1RLM8oKLGJ4Jg; COOKIE_SESSION=64766_0_8_9_13_19_0_2_8_9_4_0_64745_0_18_0_1704857737_0_1704857755%7C9%23119482_75_1697804428%7C9; BDSVRTM=0"
    query ='绿茶功效有哪些？'
    result_text_list = search_baidu_text(query=query, cookie=cookie, max_return_results=8 ,driver_path="./edge驱动win/msedgedriver_120.exe")
    pprint(result_text_list)
