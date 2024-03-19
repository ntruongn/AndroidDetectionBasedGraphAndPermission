# coding=utf-8
import codecs
import json
import os
import random
import sys
sys.path.append('..')
from config import MaxToken


def read_filetype_old_name(src_filepath):
    atype = []
    filelist = []
    fi = open(src_filepath, 'r')
    for line in fi.readlines():
        filelist.append(line.strip('\n').split(' ')[0])
        atype.append(line.strip('\n').split(' ')[1])
    fi.close()
    return filelist, atype


def read_filetype_full_path(src_filepath, token_root, type='lsi'):
    atype = []
    filelist = []
    fi = open(src_filepath, 'r')
    for line in fi.readlines():
        if type == 'lsi':
            filename = token_root + line.strip('\n').split(' ')[0] + '.tokenResult'
        elif type == 'cscg':
            filename = token_root + line.strip('\n').split(' ')[0][:-4] + '.tokenClassSet'
        else:
            print('Only support lsi and cscg, not include ' + type + '!')
            raise Exception
        filelist.append(filename)
        atype.append(line.strip('\n').split(' ')[1])
    fi.close()
    return filelist, atype


# type取值有3中，其中
# 1. 默认值'lsi'表示每个tokens文件为一个token集合
# 2. 'java_graph'和'call_graph'表示每个token文件中为一个json，key为java类名或函数名，每个value为一个token集合
# 仅当type为'lsi'时，atype与texts一一对应，表示数据的标签，
# 否则texts每行为apk文件中一个类或一个函数对应的token集合，atype表示texts对应的类或函数名，用文件名 + '_' + 类或函数名表示
def read_texts(src_filepath, token_root, type='lsi', batch=False):
    # 读取文件列表
    texts = []
    filelist, atype = read_filetype_full_path(src_filepath, token_root, type)
    # 读取每个样本的tokens
    count_file = 0
    count_no_exist = 0
    # 当type不是lsi，则atype表示类或函数名，先清空，后append
    if not type == 'lsi':
        atype = []
    for filepath in filelist:
        count_file += 1
        print(filepath)

        if count_file % 200 == 0:
            print('Already read file count: ' + str(count_file) + ', total: ' + str(len(filelist)))

        if not os.path.exists(filepath):
            print('File not exist: ' + filepath)
            count_no_exist += 1
            continue

        fi = open(filepath, 'r', encoding='utf8')
        line = fi.readline().strip('\n').strip(' ')
        fi.close()
        if type == 'lsi':
            tokens = line.split(' ')
            if len(tokens) > MaxToken:
                random.shuffle(tokens)
            tokens = tokens[:MaxToken]
            texts.append(tokens)
        else:
            _json = json.loads(line)
            for key in _json:
                texts.append(_json[key])
                atype.append(filepath + '$$' + str(key))
    print('File not exist count: ' + str(count_no_exist))
    return texts, atype

# type取值有3中，其中
# 1. 默认值'lsi'表示每个tokens文件为一个token集合
# 2. 'java_graph'和'call_graph'表示每个token文件中为一个json，key为java类名或函数名，每个value为一个token集合
# 仅当type为'lsi'时，atype与texts一一对应，表示数据的标签，
# 否则texts每行为apk文件中一个类或一个函数对应的token集合，atype表示texts对应的类或函数名，用文件名 + '_' + 类或函数名表示
def read_texts_batch(src_filepath, token_root, type='lsi', batch=False):
    # 读取文件列表
    texts = []
    filelist, atype = read_filetype_full_path(src_filepath, token_root, type)
    # 读取每个样本的tokens
    count_file = 0
    count_no_exist = 0
    # 当type不是lsi，则atype表示类或函数名，先清空，后append
    if not type == 'lsi':
        atype = []
    for filepath in filelist:
        count_file += 1
        print(filepath)

        if count_file % 200 == 0:
            print('Already read file count: ' + str(count_file) + ', total: ' + str(len(filelist)))
            if batch:
                yield texts, atype
                texts = []
        if not os.path.exists(filepath):
            print('File not exist: ' + filepath)
            count_no_exist += 1
            continue

        fi = open(filepath, 'r', encoding='utf8')
        line = fi.readline().strip('\n').strip(' ')
        fi.close()
        if type == 'lsi':
            tokens = line.split(' ')
            if len(tokens) > MaxToken:
                random.shuffle(tokens)
            tokens = tokens[:MaxToken]
            texts.append(tokens)
        else:
            _json = json.loads(line)
            for key in _json:
                texts.append(_json[key])
                atype.append(filepath + '$$' + str(key))
    print('File not exist count: ' + str(count_no_exist))

    if batch:
        print(len(texts), len(atype))
        yield texts, atype

