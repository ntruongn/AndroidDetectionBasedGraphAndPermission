import os
import json
import csv
import subprocess
from multiprocessing import Pool

def virustotal_process(filepath, apikey,outfile):
    print(filepath, apikey)
    cmd = "curl --request POST --url 'https://www.virustotal.com/vtapi/v2/file/scan' --form 'apikey=" + apikey + "' --form 'file=@" + filepath+"'"
    # cmd += ' > ' + outfile
    print(cmd)
    result = subprocess.getoutput(cmd)
    print(result)
    return result


def load_api_key(apifile):
    fi = open(apifile, 'r')
    keys = []
    for line in fi.readlines():
        keys.append(line.strip())
    return keys

# 将文件移动到旧路径
def get_md5(csv_file):
    fi = open(csv_file, encoding='utf-8')
    md5s = []
    filename = {}
    f_csv = csv.reader(fi)
    number = 0
    for row in f_csv:
        # 去掉csv的表头
        number += 1
        if number == 1:
            continue
        md5s.append(row[2])
        filename[row[2]]=row[3]
    fi.close()
    return md5s, filename


if __name__ == '__main__':
    outroot = '/data2/android_malware_detection/dataset/apkpure/vt/'
    csv_file = '/data2/android_malware_detection/dataset/apkpure/apk_details.csv'
    fileroot = '/data2/android_malware_detection/compare/download/APK_Downloader-master/apk/'

    # pool = Pool(processes=13)
    api_keys = load_api_key('keys.txt')
    md5s, filename = get_md5(csv_file)
    # print(md5s)
    # print(api_keys)
    finish = os.listdir(outroot)
    count = 0
    for md5 in md5s:
        if not (md5 + '.json' in finish) or (os.path.getsize(outroot + md5 + '.json') == 0):
            # print(md5 + ' already finished!')
            continue
        # if os.path.exists(outroot + md5 + '.ok'):
        #     continue
        fi = open(outroot + md5 + '.json')
        if fi.readline().endswith("ng scans\"}"):
            count += 1
            fi.close()
            os.remove(outroot + md5 + '.json')
            # print(md5, filename[md5])
            # filename_ = fileroot + filename[md5]
            #
            # result = virustotal_process(filename_, api_keys[count % 35], outroot + md5 + '.json')
            # fo = open(outroot + md5 + '.ok', 'w')
            # fo.write(result)
            # fo.close()
        else:
            fi.close()
            # print(filename[md5])
        count += 1
        # print(md5, api_keys[count % 35])
        # pool.apply_async(virustotal_process, [md5, api_keys[count % 35], outroot + md5 + '.json',])
    # pool.close()
    # pool.join()