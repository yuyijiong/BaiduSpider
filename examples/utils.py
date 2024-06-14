# 导入BaiduSpider
from baiduspider import BaiduSpider
from baiduspider.models.baike import BaikeResult
from baiduspider.models.zhidao import ZhidaoResult
from baiduspider.models.web import WebResult, WebNormal, WebBaike, WebBlog, WebCalc, WebGitee, WebMusic, \
    WebTieba, WebVideo, WebNews
import re
from bs4 import BeautifulSoup, Tag
from urllib.parse import unquote
from datetime import datetime
from scrapy.spiders import Rule
from collections import OrderedDict
from scrapy.linkextractors import LinkExtractor
import requests
from scrapy.item import Field, Item

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
import time
import platform
import os
import json
import warnings

# 通过浏览器获取真实url
def get_real_url(url: str, driver=None):
    #等待时间5秒
    driver.get(url)
    url = driver.current_url
    #获取当前网页的html
    html = driver.page_source
    return url,html


# 对返回的结果进行url重定向，获取真实url
def update_real_url(result: WebResult,driver_path=None) -> WebResult:
    option = webdriver.EdgeOptions()
    option.add_argument('--no-sandbox')  # 沙箱机制
    option.add_argument('--headless')  # 无界面模式
    option.add_argument('--disable-gpu')  # 禁用gpu
    option.add_argument('--hide-scrollbars')  # 隐藏滚动条, 应对一些特殊页面
    #获取当前文件的路径
    script_path = os.path.abspath(__file__)

    #如果是linux
    if 'Linux' in platform.platform():
        option.binary_location = '/usr/bin/microsoft-edge'
        if driver_path is None:
            driver_path =os.path.join(os.path.dirname(script_path),'edge驱动linux/msedgedriver_120')
        else:
            driver_path = driver_path
        print("尝试使用edge驱动:",driver_path)
    elif 'Windows' in platform.platform():
        if driver_path is None:
            driver_path = os.path.join(os.path.dirname(script_path), 'edge驱动win/msedgedriver_120.exe')
        else:
            driver_path = driver_path
        print("尝试使用edge驱动:",driver_path)
    else:
        raise Exception('不支持的操作系统')
    # 打开浏览器
    service = ChromeService(executable_path=driver_path)
    driver = webdriver.Edge(service=service, options=option)
    driver.implicitly_wait(10)
    driver.set_page_load_timeout(10)
    driver.set_script_timeout(10)

    # 对normal中的每个结果进行重定向
    for normal in result.normal:
        try:
            normal.url,normal.html = get_real_url(normal.url, driver)
        except:
            print("重定向失败，跳过。url为：{}".format(normal.url))

    # 对baike中的结果进行重定向
    if result.baike:
        try:
            result.baike.url,result.baike.html = get_real_url(result.baike.url, driver)
        except:
            print("百科重定向失败，跳过。url为：{}".format(result.baike.url))


    # 对blog中的结果进行重定向
    if result.blog:
        result.blog.url,result.blog.html = get_real_url(result.blog.url, driver)
    # 对calc中的结果进行重定向
    if result.calc:
        result.calc.url,result.calc.html = get_real_url(result.calc.url, driver)
    # 对gitee中的结果进行重定向
    if result.gitee:
        result.gitee.url,result.gitee.html = get_real_url(result.gitee.url, driver)
    # 对music中的结果进行重定向
    if result.music:
        result.music.url,result.music.html = get_real_url(result.music.url, driver)
    # 对tieba中的结果进行重定向
    if result.tieba:
        result.tieba.url,result.tieba.html = get_real_url(result.tieba.url, driver)
    # 对video中的结果进行重定向
    if result.video:
        result.video.url,result.video.html = get_real_url(result.video.url, driver)
    # 对news中的结果进行重定向
    if result.news:
        for news in result.news:
            news.url,news.html = get_real_url(news.url, driver)

    # 关闭浏览器
    driver.quit()

    return result


class EncyclopediaItem(Item):
    name = Field()  # 此词条名称
    name_en = Field()  # 英文名称
    name_other = Field()  # 其他名称
    original_url = Field()  # 词条链接
    summary = Field()  # 简介
    source_site = Field()  # 词条来源网站
    edit_number = Field()  # 词条被编辑次数
    fetch_time = Field()  # 词条抓取时间
    update_time = Field()  # 词条更新时间
    item_tag = Field()  # 词条分类标签
    thumbnail_url = Field()  # 词条缩率图url
    album_url = Field()  # 词条缩率图url
    keywords_url = Field()  # 此词条内容所包含的其他词条
    polysemous = Field()  # 多义词，本词条不包含任何内容

    text_content = Field()  # 正文内容，是一个dict
    basic_info = Field()  # 属性内容，是一个dict
    text_image = Field()  # 正文内容中包含的图片dict


class BaiduBaikeParser():
    proxy_mode = 0  # not use proxy
    base_url = "https://baike.baidu.com"
    allowed_domains = ['baike.baidu.com']
    rules = (
        Rule(LinkExtractor(allow=('https://baike.baidu.com/item/',)), callback='parse', follow=True),
    )

    def parse(self, html,url):
        basic_info_dict = OrderedDict()  # 词条基本信息值
        content_h2_dict = OrderedDict()  # 词条正文内容值
        img_dict = OrderedDict()  # 表示子标题中出现的图片url
        items = EncyclopediaItem()  # 基础信息


        soup = BeautifulSoup(html, "html.parser")
        # 词条是否为多义词
        items['polysemous'] = '/view/10812277.htm' in html
        # 词条url
        items['original_url'] = unquote(url)
        # 词条名称
        name = soup.title.get_text()
        items['name'] = name.split('_百度百科')[0] if name else None
        # name = soup.find('dd', attrs={'class': 'lemmaWgt-lemmaTitle-title'}).find('h1')
        # items['name'] = name.get_text() if name else None
        # 百科解释
        summary = soup.find('div', attrs={'class': 'lemma-summary'})
        items['summary'] = re.sub(r'\r|\n', '', summary.get_text()) if summary else None
        # 词条来源
        items['source_site'] = '百度百科'
        # 词条被编辑次数
        desc_text = soup.find('dl', attrs={'class': 'side-box lemma-statistics'})
        edit_number = re.compile(r'编辑次数：([\d]+)次').findall(desc_text.get_text())[0] if desc_text else None
        items['edit_number'] = int(edit_number) if edit_number else 1
        # 词条最近更新时间
        latest = soup.find('span', attrs={'class': 'j-modified-time'})
        items['update_time'] = latest.get_text().replace('（', '').replace('）', '') if latest else None
        # 词条抓取时间
        items['fetch_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 词条的分类标签（路径）
        item_tag = soup.find('dd', attrs={'id': 'open-tag-item'})
        items['item_tag'] = re.sub(r'\r|\n|\s', '', item_tag.get_text()) if item_tag else None
        # 词条缩率图链接
        thumbnail_url = soup.find('div', attrs={'class': 'summary-pic'})
        items['thumbnail_url'] = thumbnail_url.find('img').get('src') if thumbnail_url else None
        # 获得下一步需要采集的关键词
        kw_urls = list()
        for tag_obj in soup.findAll('div', attrs={'class': 'para'}):
            try:
                kw_urls.append(unquote(tag_obj.find('a', attrs={'target': '_blank'}).get('href')))
            except (AttributeError, TypeError):
                pass
        items['keywords_url'] = list(set(filter(lambda x: 'item' in x, kw_urls)))
        # 词条的简要简介
        items['name_en'] = None
        items['name_other'] = None
        basic_info_item_name = soup.findAll('dt', attrs={'class': 'basicInfo-item name'})
        basic_info_item_value = soup.findAll('dd', attrs={'class': 'basicInfo-item value'})
        for basic_info in zip(basic_info_item_name, basic_info_item_value):
            dict_key = ''.join(basic_info[0].get_text(strip=True).split())
            dict_value = basic_info[1].get_text(strip=True).strip()
            if '英文名称' == dict_key:
                items['name_en'] = dict_value
            elif dict_key in ['外文名', '外文名称']:
                items['name_other'] = dict_value
            else:
                basic_info_dict[dict_key] = dict_value

        # 找到第一个class为para-title且class为level-2的div标签
        sibling = soup.find('div', attrs={'class': lambda x: x and 'para-title' in x and 'level-2' in x})

        # 如果没有二级标题，那么就是正文
        if not sibling:
            h2_title = '正文'
            content_h2_dict[h2_title] = ''
            img_dict[h2_title] = list()
            for para in soup.find_all('div', attrs={'class': 'para'}):
                content_h2_dict[h2_title] += '<p>' + re.sub(r'\r|\n', '', para.get_text()) + '</p>'
                try:
                    img_url = para.find('img').get('data-src')
                    if img_url:
                        img_dict[h2_title].append(img_url)
                except AttributeError:
                    pass

        # 如果有二级标题，分别获取每个二级标题下的内容
        else:
            while sibling is not None:
                if 'para-title level-2' in str(sibling):
                    h2_title = sibling.find('h2', attrs={'class': 'title-text'}).get_text('$$').split('$$')[-1]  # h2标题
                    content_h2_dict[h2_title] = ''
                    img_dict[h2_title] = list()
                # elif 'para' in str(sibling):
                elif 'para-title level-3' in str(sibling):
                    # 3级标题名称
                    content_h2_dict[h2_title] += '<h3>' + sibling.find('h3').get_text('$$').split('$$')[-1] + '</h3>'
                elif 'class=\"para' in str(sibling):
                    # 对应的正文内容
                    content_h2_dict[h2_title] += '<p>' + re.sub(r'\r|\n', '', sibling.get_text()).strip() + '</p>'
                    try:
                        img_url = sibling.find('img').get('data-src')
                        if img_url:
                            img_dict[h2_title].append(img_url)
                    except AttributeError:
                        pass
                try:
                    sibling = next(sibling.next_siblings)
                except StopIteration:
                    sibling = None
        # 参考资料
        try:
            reference_key = soup.find('dt', attrs={'class': 'reference-title'}).get_text()
            reference_value = ''
            reference_urls = []
            lis = soup.find('ul', attrs={'class': 'reference-list'}).find_all('li')
            for index, li in enumerate(lis):
                reference_value += '<p>'.format(index) + re.sub(r'\r|\n', '', li.get_text()) + '</p>'
                url = li.find('a', attrs={'rel': 'nofollow'})
                if url:
                    reference_urls.append(self.base_url + url.get('href'))
            content_h2_dict[reference_key] = reference_value if reference_value else None
            img_dict[reference_key] = reference_urls
        except (AttributeError, TypeError):
            pass
        # 词条图册链接
        album_url = soup.find('div', attrs={'class': 'album-list'})
        if album_url:
            album_url = album_url.find('a', attrs={'class': 'more-link'}).get('href')
        items['album_url'] = self.base_url + album_url if album_url else None
        # 简要信息
        items['basic_info'] = basic_info_dict
        # 正文内容
        items['text_content'] = content_h2_dict
        # 正文中包含的图片
        items['text_image'] = img_dict
        # print(items['name'], items['polysemous'])
        return items  # 深拷贝的目的是默认浅拷贝item会在后面的pipelines传递过程中会出现错误，比如串数据了


# 根据url获取百度百科内容
def get_baike_content(baike:WebBaike, headers=None):
    url=baike.url
    if hasattr(baike,'html'):
        html=baike.html
    else:
        # 获取response
        res = requests.get(url, headers=headers,timeout=10)
        res.encoding = 'utf-8'
        html=res.text
        res.close()
    # 实例化爬虫
    spider = BaiduBaikeParser()
    # 解析
    item = spider.parse(html,url)

    return item


# 将百度百科内容转换为文本
def baike_content_to_text(item: EncyclopediaItem, keep_reference=True):
    # 将name、name_en、name_other转换为文本
    name_text = '/'.join(name for name in [item['name'], item['name_en'], item['name_other']] if name)

    # 将summary转换为文本
    summary_text = str(item['summary'])

    # 将basic_info转换为文本
    basic_info = item['basic_info']
    basic_info_text = ''
    for key, value in basic_info.items():
        basic_info_text += key + ': ' + value + '\n'

    # 将text_content转换为文本
    text_content = item['text_content']
    text_content_text = ''
    for key, value in text_content.items():
        # 不包括参考资料或学术论文
        if keep_reference == False and key == '参考资料' or key == '学术论文':
            continue
        text_content_text += key + ': ' + value + '\n'

    # 将text拼接
    text = "名称: " + name_text + "\n\n" + "简介: " + summary_text + "\n\n" + "基本信息: " + basic_info_text + "\n\n" + "正文: " + text_content_text + "\n\n"

    # 删除所有 [数字]\xa0
    # text=re.sub(r'\[\d+\]\xa0','',text)

    return text


# 根据网页的摘要，获取全文中最相关的段落
def get_most_relevant_paragraph(item: WebNormal, headers=None,select_rele_paragraph=False):
    def longest_common_subsequence(str1, str2):
        m = len(str1)
        n = len(str2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if str1[i - 1] == str2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        return dp[m][n]

    # 计算tag的相关度
    def compute_relevance(tag_text: str, summary: str):
        # 计算最长公共子序列占summary长度加tag_text长度的比例
        lcs = longest_common_subsequence(tag_text, summary)
        return lcs / (len(tag_text) + len(summary) / 10)

    # 获取url
    url = item.url
    # 获取摘要
    summary = item.des
    #获取标题
    title=item.title

    # 获取response
    #如果item有html属性，则直接使用html属性
    if hasattr(item,'html'):
        html=item.html
    else:
        res = requests.get(url, headers=headers,timeout=10)
        res.encoding = 'utf-8'
        html=res.text
        res.close()
    bs = BeautifulSoup(html, 'html.parser')


    #寻找class包含“title”的h1或div。如果找到，且长度大于title，则更新title
    title_tag=bs.find('h1',attrs={'class':lambda x:x and 'title' in x})
    if title_tag:
        if len(title_tag.get_text())>len(title):
            title=title_tag.get_text()

    #寻找class为“article”的div或name为“article”的标签
    article=bs.find('div',attrs={'class':'article'})
    if article:
        text="标题: "+title+"\n\n"+"内容: "+article.get_text()+"\n\n"
        return text
    article=bs.find('article')
    if article:
        text="标题: "+title+"\n\n"+"内容: "+article.get_text()+"\n\n"
        return text

    #寻找class中包含"content"的div
    content=bs.find('div',attrs={'class':lambda x:x and 'content' in x})
    if content:
        text="标题: "+title+"\n\n"+"内容: "+content.get_text()+"\n\n"
        return text

    #寻找class中包含“question”的div和class中包含“answer”的div
    question=bs.find('div',attrs={'class':lambda x:x and 'question' in x})
    answer=bs.find('div',attrs={'class':lambda x:x and 'answer' in x})
    if question and answer:
        text="标题: "+title+"\n\n"+"问题: "+question.get_text()+"\n\n"+"回答: "+answer.get_text()+"\n\n"
        return text

    if select_rele_paragraph:
        # 遍历所有tag，找到最相关的段落
        max_relevance = 0
        most_relevant_tag = None
        for tag in bs.find_all():
            # 如果tag没有文本，跳过
            if not tag.get_text():
                continue
            # 计算tag的相关度
            relevance = compute_relevance(tag.get_text(), summary)
            # 如果相关度大于最大相关度，更新最大相关度和最相关段落
            if relevance >= max_relevance:
                max_relevance = relevance
                most_relevant_tag = tag

        # 如果没有找到最相关段落，返回空字符串
        if not most_relevant_tag:
            return ''

        # 不断获取most_relevant_tag的父节点，直到父节点是div标签
        while most_relevant_tag.name != 'div':
            # 如果父节点没有name，则终止
            if most_relevant_tag.parent:
                most_relevant_tag = most_relevant_tag.parent
            else:
                break

        #如果most_relevant_tag的父节点是div标签，则将父节点作为most_relevant_tag
        if most_relevant_tag.parent and most_relevant_tag.parent.name=='div':
            most_relevant_tag=most_relevant_tag.parent
        if most_relevant_tag.parent and most_relevant_tag.parent.name=='div':
            most_relevant_tag=most_relevant_tag.parent

        #most_relevant_tag中的某个tag如果有style属性，则删除。如果class包含“right”或“left”或“bottom”，也删除
        while True:
            for tag in most_relevant_tag.find_all():
                if tag is None:
                    continue

                if tag.get('style'):
                    tag.decompose()
                    break

                elif tag.get('class'):
                    if 'right' in tag['class'] or 'left' in tag['class'] or 'bottom' in tag['class']:
                        tag.decompose()
                        break
            break

        # 获取tags的文本
        text = most_relevant_tag.get_text()

    else:
        #获取网页的所有文本
        text=bs.get_text()

    return text

#获取杂类网页的文本
def get_other_normal_text(item:WebNormal,headers=None):
    # 获取url
    url = item.url
    #获取标题
    title=item.title

    # 获取response
    #如果item有html属性，则直接使用html属性
    if hasattr(item,'html'):
        html=item.html
    else:
        try:
            res = requests.get(url, headers=headers,timeout=10)
            res.encoding = 'utf-8'
            html=res.text
            res.close()
        except:
            warnings.warn("获取网页失败，跳过。url为：{}".format(url))
            return ''

    bs = BeautifulSoup(html, 'html.parser')

    #寻找class包含“title”的h1或div。如果找到，且长度大于title，则更新title
    title_tag=bs.find('h1',attrs={'class':lambda x:x and 'title' in x})
    if title_tag:
        if len(title_tag.get_text())>len(title):
            title=title_tag.get_text()

    #寻找class为“article”的div或name为“article”的标签
    article=bs.find('div',attrs={'class':'article'})
    if article:
        text="标题: "+title+"\n\n"+"内容: "+article.get_text()+"\n\n"
        return text
    article=bs.find('article')
    if article:
        text="标题: "+title+"\n\n"+"内容: "+article.get_text()+"\n\n"
        return text

    #寻找class中包含"content"的div
    content=bs.find('div',attrs={'class':lambda x:x and 'content' in x})
    if content:
        text="标题: "+title+"\n\n"+"内容: "+content.get_text()+"\n\n"
        return text

    #寻找class中包含“question”的div和class中包含“answer”的div
    question=bs.find('div',attrs={'class':lambda x:x and 'question' in x})
    answer=bs.find('div',attrs={'class':lambda x:x and 'answer' in x})
    if question and answer:
        text="标题: "+title+"\n\n"+"问题: "+question.get_text()+"\n\n"+"回答: "+answer.get_text()+"\n\n"
        return text

    #如果不属于任何类型，则获取网页的所有文本
    text=bs.get_text()
    #把标题加到最前面
    text=title+"\n\n"+text
    return text


# 解析百度知道
def parse_baidu_zhidao(item: WebNormal, headers=None):
    url = item.url
    if hasattr(item,'html'):
        html=item.html
    else:
        res = requests.get(url, headers=headers)
        res.encoding = 'utf-8'
        html=res.text
        res.close()
    bs = BeautifulSoup(html, 'html.parser')

    try:
        # 获取问题,class为“ask-title”的span
        question = bs.find('span', attrs={'class': 'ask-title'}).get_text()
        # 获取答案，id为wgt-best的div下的class为“rich-content-container”的div
        answer = bs.find('div', attrs={'id': 'wgt-best'}).find('div', attrs={'class': 'rich-content-container'}).get_text()
        # 返回文本
        text = "问题: " + question + "\n\n" + "回答: " + answer + "\n\n"
        return text
    except:
        warnings.warn("解析百度知道失败，跳过。url为：{}".format(url))
        return ''

#解析百家号内容
def parse_baijiahao(item: WebNormal, headers=None):
    url = item.url
    res = requests.get(url, headers=headers)
    res.encoding = 'utf-8'
    bs = BeautifulSoup(res.text, 'html.parser')
    res.close()
    # 获取标题,class为“sKHSJ”的div
    title = bs.find('div', attrs={'class': 'sKHSJ'}).get_text()
    # 获取文本，class为“_18p7x”的div
    content = bs.find('div', attrs={'class': '_18p7x'}).get_text()
    # 返回文本
    text = "标题: " + title + "\n\n" + "内容: " + content + "\n\n"
    return text

#解析csdn内容
def parse_csdn(item: WebNormal, headers=None):
    url = item.url
    res = requests.get(url, headers=headers)
    res.encoding = 'utf-8'
    bs = BeautifulSoup(res.text, 'html.parser')
    res.close()
    # 获取标题,class为“title-article”的h1
    title = bs.find('h1', attrs={'class': 'title-article'}).get_text()
    # 获取文本，class为“article_content”的div
    content = bs.find('div', attrs={'class': 'article_content'}).get_text()
    # 返回文本
    text = "标题: " + title + "\n\n" + "网页内容: " + content + "\n\n"
    return text


# 为WebBaike增加一个函数，get_text()
def get_baike_text(self:WebBaike, headers=None) -> str:
    content = get_baike_content(self, headers=headers)
    text = baike_content_to_text(content)
    return text

def get_normal_text(self:WebNormal, headers=None):
    # 获取url
    url = self.url
    # 获取摘要
    summary = self.des
    # 获取网页标题
    title = self.title
    # 如果标题包含“百度知道”，则调用parse_baidu_zhidao
    if '百度知道' in title:
        text= parse_baidu_zhidao(self, headers=headers)
    # 如果包含百度百科，则调用get_baike_content
    elif '百度百科' in title:
        item = get_baike_content(self, headers=headers)
        text= baike_content_to_text(item)
    #如果url中包含“baijiahao”，说明是百家号,则调用parse_baijiahao
    elif 'baijiahao' in url:
        text=parse_baijiahao(self, headers=headers)
    #如果url中包含"blog.csdn",则调用parse_csdn
    elif 'blog.csdn' in url:
        text=parse_csdn(self, headers=headers)
    else:
        # 如果是杂类，则调用get_other_normal_text
        text = get_other_normal_text(self, headers=headers)

    return text


def get_zhidao_text(self, headers=None):
    text = parse_baidu_zhidao(self, headers=headers)
    return text


def add_get_text():
    WebBaike.get_text = get_baike_text
    WebNormal.get_text = get_normal_text
    ZhidaoResult.get_text = get_zhidao_text
