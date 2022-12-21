import math
import requests
import os
import time
import re
import random
import threading
import configparser
import json
import sys

thread_lock=threading.BoundedSemaphore(value=5)

# cookies 影响数量
cookies={}

keyword = ''

sleepTime = 3

down_info = {

}

build=2

proxies={}

mode='safe'

order='date'

dir_path=''

json_path=''

referer = 'https://www.pixiv.net/artworks/{}'

img_list = []

down_list = []

headers_download={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Accept': 'image / webp, * / *',
    'Referer': referer
}

headers_search={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
    'Connection': 'keep-alive',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Host': 'www.pixiv.net'
}

headers_inf={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0',
    'Connection': 'keep-alive',
    'Accept': 'image / webp, * / *'
}

def coo_regulay(cookie):
    coo = {}
    if cookie != '':
        for k_v in cookie.split("; "):
            k,v = k_v.split("=", 1)
            coo[k.strip()] = v.replace('"','')
    return coo

# 读取配置文件
def read_ini():
    global proxies
    global cookies
    global sleepTime
    global thread_lock
    global mode
    global order
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    if os.path.exists('config.ini'):
        port = config.get('Network', 'port')
        proxies = {
            'https':'127.0.0.1:{}'.format(port),
            'http':'127.0.0.1:{}'.format(port)
        }
        cookies = coo_regulay(config.get('Network', 'cookie'))
        sleepTime = int(config.get('Base', 'max_sleep_time'))
        max_thread = int(config.get('Base', 'max_thread'))
        if max_thread >= 2:
            thread_lock = threading.BoundedSemaphore(value=max_thread)
        else:
            thread_lock = threading.BoundedSemaphore(value=5)
        mode = config.get('Base', 'down_type')
        order = config.get('Base', 'order_type')
    else:
        print(r'未找到配置文件"config.ini"，初始化中')
        # TODO: 说明txt文件生成，（存在想法--先生成txt文件,然后直接修改后缀)
        port=input('请输入端口号(必填), 填入无效端口号则无法下载\n')
        cookies=input('请输入cookie(选填), 影响部分及r18图片下载\n')
        try:
            config.add_section("Network")
            config.set("Network", "cookie", cookies.replace('%','%%'))
            config.set("Network", "port", port)
            config.add_section("Base")
            config.set("Base", "max_sleep_time", "3")
            config.set("Base", "max_thread", "10")
            config.set("Base", "down_type","safe")
            config.set("Base", "order_type","date")
            config.write(open("config.ini", "w"))
        except configparser.DuplicateOptionError:
            input('初始化ini文件失败, 请按任意键退出')
            sys.exit()
        
def update_cookie(newCookie):
    global cookies
    cookies = newCookie.replace('%','%%')
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    config.set("Network", "cookie", cookies)
    config.write(open("config.ini", "w"))

def get_total_page(keyword):
    global down_info
    global mode
    search_url = r'https://www.pixiv.net/ajax/search/artworks/{}?word={}&order=date&mode={}&p={}&s_mode=s_tag&type=all&lang=zh'.format(keyword,keyword,mode,1)
    try:
        response=requests.get(search_url,headers=headers_search,proxies=proxies,cookies=cookies)
        html=response.text
        list=re.findall(r'"total":(.*?),',html,re.S)
        total = float(list[0])
        if total > 0:
            total_page = int(math.ceil(total / 60.0))
            print("{} 全部图片数量为 {}, 共{}页".format(keyword, total, total_page))
            if mode == 'all':
                down_info['aTotalImg'] = int(total)
                down_info['aMaxPage'] = total_page
            elif mode == 'safe':
                down_info['sTotalImg'] = int(total)
                down_info['sMaxPage'] = total_page
            else:
                down_info['rTotalImg'] = int(total)
                down_info['rMaxPage'] = total_page
            try:
                with open(json_path, "w") as outfile:
                    json.dump(down_info, outfile)
            except:
                print('写入信息失败')
            return int(total), total_page
        else:
            return 0, 0
    except Exception as e:
        return -1, -1

def get_page_img_info(page: int):
    global down_info
    global img_list
    global mode
    search_url = r'https://www.pixiv.net/ajax/search/artworks/{}?word={}&order=date&mode={}&p={}&s_mode=s_tag&type=all&lang=zh'
    print("当前正在获取第{}页图片信息\n".format(page))
    try:
        # print(search_url.format(keyword, keyword, mode, page))
        response=requests.get(search_url.format(keyword, keyword, mode, page),headers=headers_search,proxies=proxies,cookies=cookies)
        html=response.text
        id=re.findall(r'"id":"(.*?)"',html,re.S)
        pageCount=re.findall(r'"pageCount":(.*?),"',html,re.S)
        tags=re.findall(r'"tags":\[(.*?)\]', html, re.S)
        for index in zip(id,pageCount,tags):
            photo_id=r'https://www.pixiv.net/artworks/{}'.format(index[0])
            isSafe=True
            if index[2]:
                tag = re.findall(r'R-18', index[2])
                if tag:
                    isSafe = False
            if photo_id not in img_list:
                info = {
                    'url': photo_id,
                    'num': index[1],
                    'safe': isSafe,
                    'id': index[0]
                }
                img_list.append(photo_id)
                down_info['imgInfo'].append(info)
                # print(info)
        if mode == 'all':
            down_info['aSuccessPages'].append(page)
        elif mode == 'safe':
            down_info['sSuccessPages'].append(page)
        else:
            down_info['rSuccessPages'].append(page)
        try:
            with open(json_path, "w") as outfile:
                json.dump(down_info, outfile)
        except:
            print('写入图片信息失败')
        time.sleep(random.uniform(0,sleepTime))
        thread_lock.release()
    except Exception as e:
        print('获取 第{}页 {} 图片信息失败'.format(page, keyword))
        time.sleep(random.uniform(0,sleepTime))
        thread_lock.release()


def search_inf(keyword):
    global down_info
    global img_list
    global order
    oldTotalImg = 0
    oldMaxPage = 0
    if mode == 'all':
        oldTotalImg = down_info['aTotalImg']
        oldMaxPage = down_info['aMaxPage']
    elif mode == 'safe':
        oldTotalImg = down_info['sTotalImg']
        oldMaxPage = down_info['sMaxPage']
    else:
        oldTotalImg = down_info['rTotalImg']
        oldMaxPage = down_info['rMaxPage']
    totalImg, total_page = get_total_page(keyword=keyword)

    if totalImg == 0:
        input("您搜索的图片为空，结束")
        sys.exit()
    elif total_page == -1:
        input("获取页数出错,请检查端口号或cookie")
        sys.exit()
    
    success = []
    if mode == 'all':
        success = down_info['aSuccessPages']
    elif mode == 'safe':
        success = down_info['sSuccessPages']
    else:
        success = down_info['rSuccessPages']
    if totalImg == len(down_info['imgInfo']):
        print('当前图片网址数据已为最新')
        return
    if totalImg > 0:
        for item in down_info['imgInfo']:
            img_list.append(item['url'])
   
        start_index = 1
        end_index = total_page + 1
        step = 1
        if order == 'date_d':
            start_index = total_page
            end_index = 0
            step = -1
        
        for page in range(start_index, end_index, step):
            if page in success:
                if totalImg > oldTotalImg and oldMaxPage == page :
                    thread_lock.acquire()
                    t1 = threading.Thread(target=get_page_img_info, args=(page,))
                    t1.start()
            else:
                thread_lock.acquire()
                t1 = threading.Thread(target=get_page_img_info, args=(page,))
                t1.start()

def get_inf(id,inf_url):
    try:
        img_info_url = r'https://www.pixiv.net/ajax/illust/{}/pages?lang=zh'.format(id)
        img_response = requests.get(img_info_url, headers=headers_inf,proxies=proxies,cookies=cookies)
        img_html=img_response.text
        down_list = []
        list = re.findall(r'"original":"(.*?)"',img_html,re.S)
        for url in list:
            down_list.append(url.replace('\\/','/'))
        # print(down_list)
        return down_list
    except Exception as e:
        print('获取id: {} 作品详细信息失败'.format(id))
        return []

def down_pic(down_url,id,isSafe):
    try:
        pic_name=down_url.split('/')[-1]
        headers_download['Referer']=referer.format(id)
        down_response=requests.get(down_url,headers=headers_download,proxies=proxies,cookies=cookies)
        img_path=''
        if isSafe:
            img_path = r'{}/safe/{}'.format(dir_path,pic_name)
        else:
            img_path = r'{}/r18/{}'.format(dir_path,pic_name)
        with open(img_path,'wb')as down:
            down.write(down_response.content)
        print('{}图片获取完成'.format(pic_name))
    except Exception as e:
        print('{}图片获取失败'.format(pic_name))

def down_page(id,web,isSafe):
    try:
        global down_list
        list = get_inf(id, r'{}'.format(web))
        for down_url in list:
            if down_url.split('/')[-1] in down_list:
                print('{}已存在，略过'.format(down_url.split('/')[-1]))
                continue
            print('{}开始下载'.format(down_url.split('/')[-1]))
            down_pic(down_url, id, isSafe)
        thread_lock.release()
        time.sleep(random.uniform(0, sleepTime))
    except Exception as e:
        thread_lock.release()

def sortKeyId(dict):
    return dict['id']

def sortImgInfo():
    global down_info
    global order
    down_info['imgInfo'].sort(reverse=(order == 'date_d'), key=sortKeyId)

def getImage(keyword):
    global down_info
    global dir_path
    if not down_info['imgInfo']:
        print('未有图片相关信息，将开始获取信息')
        search_inf(keyword)
        time.sleep(10)
        print('结束获取\n开始下载图片')
        getImage(keyword)
    else:
        sortImgInfo()
        if os.path.exists(r'{}/safe'.format(dir_path)) == False:
            os.mkdir(r'{}/safe'.format(dir_path))
        if os.path.exists(r'{}/r18'.format(dir_path)) == False:
            os.mkdir(r'{}/r18'.format(dir_path))
        down_list = os.listdir(r'{}/safe'.format(dir_path))
        down_list.extend(os.listdir(r'{}/r18'.format(dir_path)))
        save_lists ={}
        for list in down_list:
            save_inf = list.split('_')[0]
            if save_inf not in save_lists:
                save_lists[save_inf] = 1
            else:
                save_lists[save_inf] = save_lists[save_inf] + 1
        for item in down_info['imgInfo']:
            # print(item)
            id=item['id']
            if id in save_lists and int(item['num'])==save_lists[id]:
                print('{}存在且图片数量相等，跳过'.format(id))
                continue
            else:
                # down_page(index[0],index[1])
                thread_lock.acquire()
                t1 = threading.Thread(target=down_page, args=(id, item['url'], item['safe']))
                t1.start()

if __name__ == '__main__':
    read_ini()
    keyword = input('请输入关键词:\n')
    do=input('获取图片网址输入1，下载图片输入2:\n')
    # keyword = '后藤一里'
    # do = 1
    # 更新有问题，会受限于输入的长度..等ui后处理
    # if int(do) == 3:
    #     newCookie = input('请输入cookie:\n')
    #     update_cookie(newCookie)
    #     print('cookie更新完成,请选择接下来的操作')
    #     do=input('获取图片网址输入1，下载图片输入2:\n')

    dir_path = r'image/{}'.format(keyword)
    json_path = r'image/{}/down_info.json'.format(keyword)
    if os.path.exists(dir_path) == False:
        os.makedirs(dir_path)
    if os.path.exists(json_path):
        with open(json_path) as f:
            down_info = json.load(f)
        json_build = down_info['build']
        if json_build < build:
            # 后续旧版本json信息 更新
            pass
    else:
        down_info = {
            'build': build,
            'keywork': keyword,
            'aTotalImg': 0,
            'aMaxPage': 0,
            'aSuccessPages': [],
            'sTotalImg': 0,
            'sMaxPage': 0,
            'sSuccessPages': [],
            'rTotalImg': 0,
            'rMaxPage': 0,
            'rSuccessPages': [],
            'imgInfo': [],
        }
        with open(json_path, "w") as outfile:
            json.dump(down_info, outfile)

    if(int(do)==1):
        search_inf(keyword)
        print('结束信息结束\n开始下载图片')
        time.sleep(10)
        getImage(keyword)
    elif int(do)==2:
        getImage(keyword)
