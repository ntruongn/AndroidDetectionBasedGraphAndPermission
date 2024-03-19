# coding=utf-8
#定义代理ip
import urllib.request
import urllib
import csv
import os
from config import root
import datetime
from multiprocessing import Pool


# 在print内容前加上时间后打印
def time_print(string):
    print(str(datetime.datetime.now()) + ' : ' + string)


def download_apk(url, localfile):
    if os.path.exists(localfile):
        # print('File Exites ' + localfile + '!')
        return 0
    else:
        print(localfile)
        # fo = open('123456.txt', 'a+')
        # fo.write(url + '\n')
        # fo.close()
        print(url)
        return 1
    # proxy_addr="127.0.0.1:1080"
    #创建一个请求

    req=urllib.request.Request(url)
    #添加headers
    my_headers = [
        "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:30.0) Gecko/20100101 Firefox/30.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/537.75.14",
        "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Win64; x64; Trident/6.0)",
        'Mozilla/5.0 (Windows; U; Windows NT 5.1; it; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11',
        'Opera/9.25 (Windows NT 5.1; U; en)',
        'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
        'Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.5 (like Gecko) (Kubuntu)',
        'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.0.12) Gecko/20070731 Ubuntu/dapper-security Firefox/1.5.0.12',
        'Lynx/2.8.5rel.1 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/1.2.9',
        "Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.7 (KHTML, like Gecko) Ubuntu/11.04 Chromium/16.0.912.77 Chrome/16.0.912.77 Safari/535.7",
        "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:10.0) Gecko/20100101 Firefox/10.0 "
    ]
    # agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Maxthon/5.1.2.3000 Chrome/55.0.2883.75 Safari/537.36'
    agent = my_headers[2]

    req.add_header("User-Agent",agent)
    #设置代理
    proxy=urllib.request.ProxyHandler({})
    #创建一个opener
    opener=urllib.request.build_opener(proxy,urllib.request.HTTPHandler)
    #将opener安装为全局
    urllib.request.install_opener(opener)
    #用urlopen打开网页
    data=urllib.request.urlopen(req).read()
    fi = open(localfile, 'wb')
    fi.write(data)
    size = len(data)
    fi.close()
    time_print('Download ' + localfile + ' done!' + ' Size : ' + str(size))

# def download_apk(url, localfile):
#     proxy_addr="127.0.0.1:1080"
#     #创建一个请求
#     req=urllib.request.Request(url)
#     #添加headers
#     req.add_header("User-Agent","Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0")
#     #设置代理
#     proxy=urllib.request.ProxyHandler({'https':proxy_addr})
#     #创建一个opener
#     opener=urllib.request.build_opener(proxy,urllib.request.HTTPHandler)
#     #将opener安装为全局
#     urllib.request.install_opener(opener)
#     #用urlopen打开网页
#     data=urllib.request.urlopen(req).read()
#     fi = open(localfile, 'wb')
#     fi.write(data)
#     fi.close()
#     print('Download ' + localfile + ' done!')

def parse_csv(csvfile):
    f = csv.reader(open(csvfile, 'r',encoding='utf-8'))
    count_un_down = 0
    count = 0
    count_50 = 0
    count_60 = 0
    count_70 = 0
    count_80 = 0
    count_null = 0
    total_size = 0.0
    for i in f:
        app_name = i[0]
        str_category = i[1]
        Latest_Version = i[2]
        Publish_Date = i[3]
        Requirements = i[4]
        app_size_ = i[5]
        apk_filepath = i[6]
        Author = i[7]
        url = i[8]

        if url == 'null' or apk_filepath.endswith('.xapk'):
            continue
        count += 1
        if app_size_.endswith(' GB'):
            app_size = float(app_size_[:-3]) * 1000
            count_50 += 1
            count_60 += 1
            count_70 += 1
            count_80 += 1
        elif app_size_.endswith(' MB'):
            app_size = float(app_size_[:-3])
            if app_size > 50:
                count_50 += 1
            if app_size > 60:
                count_60 += 1
            if app_size > 70:
                count_70 += 1
            if app_size > 80:
                count_80 += 1
        elif app_size_.endswith(' KB'):
            app_size = float(app_size_[:-3])/1000
        elif app_size_ == 'null':
            app_size = 0
            count_null += 1
        else:
            print(i, app_name, app_size_)
            continue
        if app_size <= 50:
            if not os.path.exists(root + 'compare/download/APK_Downloader-master/apk/' + str_category + '/'):
                os.mkdir(root + 'compare/download/APK_Downloader-master/apk/' + str_category + '/')
            try:
                count_un_down += download_apk(url, root + 'compare/download/APK_Downloader-master/apk/' + str_category + '/' + apk_filepath.replace(':', '_').replace('/', '_'))
                # if apk_filepath.replace(':', '_').replace('/', '_').endswith('2020_v6.7.0_apkpure.com.apk'):
                #     print(csvfile)
                #     print(root + 'compare/download/APK_Downloader-master/apk/' + str_category + '/' + apk_filepath.replace(':', '_').replace('/', '_'))
            except Exception as e:
                print(url)
            # print(url)
                # print(e)
            # print(app_size)
            total_size += app_size
    return count, count-count_null-count_50, count-count_null-count_60, count-count_null-count_70, count-count_null-count_80, count-count_null, total_size, count_un_down
    # print(count)

def mv_other(localfiles, filenames):
    for file_ in localfiles:
        if file_ not in filenames:
            print(file_)


if __name__ == '__main__':
    # url = 'https://download.apkpure.com/b/APK/Y29tLm1ha2l5YWoud2l0aF9sdW5hXzJfZjBmZWRmZTA?_fn=2KrYudmE2YrZhSDYp9mE2YXZg9mK2KfYrCDYqNin2YTYrti32YjYp9iqINio2K_ZiNmGINmG2KrigI5fdjcuMy4zX2Fwa3B1cmUuY29tLmFwaw&as=90aa08e5bb6cb875241306dabf95be6a5fd24d8a&ai=1024204038&at=1607617810&_sa=ai%2Cat&k=3888727441b7a094836b8cefc77b54e45fd4f012&_p=Y29tLm1ha2l5YWoud2l0aF9sdW5h&c=1%7CBEAUTY%7CZGV2PUx1bmElMjBBcHAmdD1hcGsmcz0yODUwMDkyJnZuPTcuMy4zJnZjPTI'
    # localfile = 'test1.apk'
    # download_apk(url, localfile)
    # url = 'https://download.apkpure.com/b/APK/Y29tLm1ha2l5YWoud2l0aF9sdW5hXzJfZjBmZWRmZTA?_fn=2KrYudmE2YrZhSDYp9mE2YXZg9mK2KfYrCDYqNin2YTYrti32YjYp9iqINio2K_ZiNmGINmG2KrigI5fdjcuMy4zX2Fwa3B1cmUuY29tLmFwaw&as=90aa08e5bb6cb875241306dabf95be6a5fd24d8a&ai=1024204038&at=1607617810&_sa=ai%2Cat&k=3888727441b7a094836b8cefc77b54e45fd4f012&_p=Y29tLm1ha2l5YWoud2l0aF9sdW5h&c=1%7CBEAUTY%7CZGV2PUx1bmElMjBBcHAmdD1hcGsmcz0yODUwMDkyJnZuPTcuMy4zJnZjPTI'
    # url = "https://download.apkpure.com/b/APK/Y29tLmNhbnZhLmVkaXRvcl8xMjU4NV85OWJiOTU0Ng?_fn=Q2FudmEgR3JhcGhpYyBEZXNpZ24gVmlkZW8gQ29sbGFnZSBMb2dvIE1ha2VyX3YyLjkxLjBfYXBrcHVyZS5jb20uYXBr&as=60c01c3dd655ec623bee6e574dc8a0bb5fd6eaa7&ai=1997563438&at=1607920175&_sa=ai%2Cat&k=df07cfe996221960e01486f68f4c63295fd98d2f&_p=Y29tLmNhbnZhLmVkaXRvcg&c=1%7CART_AND_DESIGN%7CZGV2PUNhbnZhJnQ9YXBrJnM9MzAzMzQ4NDMmdm49Mi45MS4wJnZjPTEyNTg1"
    # localfile = 'test2.apk'
    # download_apk(url, localfile)



    files= os.listdir(root + 'compare/download/APK_Downloader-master/pages/')
    count, count_50, count_60, count_70, count_80, count_null, total_size = 0.0,0.0,0.0,0.0,0.0,0.0,0.0
    for file in files:
        if not file.endswith('.csv'):
            continue
        # print(file)
        # if not file == 'AppMetadata_weather.csv':
        # if not file.startswith('AppMetadata_game'):# == 'AppMetadata_weather.csv':
        #     continue
        count_, count_50_, count_60_, count_70_, count_80_, count_null_, total_size_, count_un_down = parse_csv(root + 'compare/download/APK_Downloader-master/pages/' + file)
        # print(file + ', ',count_, count_50_, count_60_, count_70_, count_80_, count_null_, total_size_)
        count += count_
        count_50 += count_50_
        count_60 += count_60_
        count_70 += count_70_
        count_80 += count_80_
        count_null += count_null_
        total_size += total_size_
        if count_un_down > 0:
            print(file[12:-4])
    print(', ', count, count_50, count_60, count_70, count_80, count_null, total_size)
    # print(parse_csv(root + 'compare/download/APK_Downloader-master/pages/AppMetadata_art_and_design.csv'))