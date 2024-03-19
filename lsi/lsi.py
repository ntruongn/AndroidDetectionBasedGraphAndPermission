# coding=utf-8
from .TFIDF import TFIDF_model, getTFIDF_src_file, loadTFIDF_model, calculate_tfidf
import os
from gensim import corpora, models
from .read_data import read_filetype_old_name
import codecs
import json
import sys
sys.path.append('..')
from config import num_topics
from config import num_topics, total_process_single_core
from multiprocessing import Pool


def lsi_train(name, train_file, TFIDF_dict_path, dict_corpus, TFIDF_model_path, TFIDF_corpus_path, LSI_model_path, LSI_corpus_path, token_root, type='lsi', no_below=25, no_above=0.5):
    # print(name, train_file, TFIDF_dict_path, dict_corpus, TFIDF_model_path, TFIDF_corpus_path, token_root, type)
    
    if type == 'lsi':
        dictionary, tfidf, corpus_tfidf = TFIDF_model(name, train_file, TFIDF_dict_path, dict_corpus, TFIDF_model_path, TFIDF_corpus_path, token_root, type=type, no_below=no_below, no_above=no_above)
        filelist, atype = read_filetype_old_name(train_file)
    else:
        dictionary, tfidf, corpus_tfidf, atype = TFIDF_model(name, train_file, TFIDF_dict_path, dict_corpus, TFIDF_model_path, TFIDF_corpus_path, token_root, type=type)
        filelist = None
    # dictionary = corpora.Dictionary.load(TFIDF_dict_path)
    # corpus_tfidf = corpora.MmCorpus(TFIDF_corpus_path)
    # print(corpus_tfidf)
    # print(LSI_model_path)
    # print(LSI_corpus_path)
    if os.path.exists(LSI_model_path) and (os.path.exists(LSI_corpus_path) and type == 'lsi'):
        print('LSI model and corpus already exits: ' + name)
        return
    print("Load tfidf finish: " + name)
    if os.path.exists(LSI_model_path):
        lsi = models.LsiModel.load(LSI_model_path)
        print('LSI model already exits: ' + name)
    else:
        lsi = models.LsiModel(corpus_tfidf, id2word=dictionary, num_topics=num_topics)
        print("Lsi model finish: " + name)
        lsi.save(LSI_model_path)
        print("Save lsi model finish: " + name)
    
    # print(corpus_tfidf)
    # print(lsi)

    corpus_lsi = lsi[corpus_tfidf]
    print("Corpus lsi: " + name)
    # TODO
    # filelist, atype = read_filetype_old_name(train_file)
    # 若type不是lsi，则filelist为None，saveLsiResult则不保存filelist的内容
    if type == 'lsi':
        saveLsiResult(atype, corpus_lsi, LSI_corpus_path, filelist)
    else:
        saveLsiFeature(atype, corpus_lsi, LSI_corpus_path, type=type)
    print("Save lsi result finish: " + name)


# 用来保存lsi特征，filelist不是None时保存lsi类型的特征，是None时，用来保存graph的lsi特征
def saveLsiResult(atype, corpus_lsi, file_out, filelist=None):
    print(file_out)
    fo = open(file_out, "w+")
    i = 0
    for doc in corpus_lsi:
        if filelist == None:
            fo.write(str(atype[i]) + ',')
        else:
            fo.write(filelist[i] + ',' + str(atype[i]) + ',')
        j = 0
        k = 0
        while (j < num_topics):
            if (k < len(doc) and j == doc[k][0]):
                fo.write(str(doc[k][1]) + ' ')
                j += 1
                k += 1
            else:
                # print('error:' + str(j))
                fo.write(str('0.0000') + ' ')
                j += 1
        fo.write('\n')
        i += 1
    fo.close()


# 在type不是lsi时调用，用来按照apk文件为单位，保存每个类或函数的lsi特征,此时atype保存为类或函数名列表
# 第一个'_'前为apk文件名，'_'后为类或函数名
def saveLsiFeature(atype, corpus_lsi, LSI_feature_path, type='cscg'):
    # 先清空LSI_feature_path下的文件
    if type == 'cscg':
        filetype = '.lsiClassSet'
    else:
        filetype = '.lsiCall'
    os.system('rm ' + LSI_feature_path + '*' + filetype)
    for i in range(len(atype)):
        key = atype[i]
        apk_file = key.split('$$', 1)[0].split('/')[-1]
        if apk_file.endswith('.tokenJava') or apk_file.endswith('.tokenCall'):
            apk_file = apk_file[:-10]
        elif apk_file.endswith('tokenClassSet'):
            apk_file = apk_file[:-14]
        _class = key.split('$$', 1)[1]
        fo = open(LSI_feature_path + apk_file + filetype, 'a+')
        doc = corpus_lsi[i]
        fo.write(_class + ',')
        j = 0
        k = 0
        while (j < 500):
            if (k < len(doc) and j == doc[k][0]):
                fo.write(str(doc[k][1]) + ' ')
                j += 1
                k += 1
            else:
                # print('error:' + str(j))
                fo.write(str('0.0000') + ' ')
                j += 1
        fo.write('\n')
        fo.close()


def lsi_test(dataset_name, test_file, TFIDF_dict_path, TFIDF_model_path, LSI_model_path, LSI_corpus_path, token_root, type='lsi'):
    if not os.path.exists(TFIDF_dict_path) or not os.path.exists(TFIDF_model_path) or not os.path.exists(LSI_model_path):
        print(TFIDF_dict_path, TFIDF_model_path, LSI_model_path)
        print('Donot find all model path, please first train the lsi model!')
        return
    if os.path.exists(LSI_corpus_path) and type == 'lsi':
        print('LSI Corpus already exits: ' + dataset_name)
        return
    print('Corpus lsi for test start: ' + dataset_name)
    corpus_tfidf, atype = getTFIDF_src_file(test_file, token_root, TFIDF_dict_path, TFIDF_model_path, type=type)
    print('Corpus tfidf for test finished: ' + dataset_name)
    lsi = models.LsiModel.load(LSI_model_path)
    print('Load LSI model for test finished: ' + dataset_name)
    corpus_lsi = lsi[corpus_tfidf]
    print('Corpus lsi for test finished: ' + dataset_name)
    if type == 'lsi':
        filelist, atype = read_filetype_old_name(test_file)
        saveLsiResult(atype, corpus_lsi, LSI_corpus_path, filelist)
    else:
        saveLsiFeature(atype, corpus_lsi, LSI_corpus_path, type=type)


def lsi_test_cscg(dataset_name, test_file, TFIDF_dict_path, TFIDF_model_path, LSI_model_path, LSI_corpus_path, token_root, type='cscg'):
    if not os.path.exists(TFIDF_dict_path) or not os.path.exists(TFIDF_model_path) or not os.path.exists(LSI_model_path):
        print(TFIDF_dict_path, TFIDF_model_path, LSI_model_path)
        print('Donot find all model path, please first train the lsi model!')
        return
    print('Corpus lsi for test start: ' + dataset_name)
    # 加载LSI模型

    fi = open(test_file, 'r')
    index = 0
    pool = Pool(processes=total_process_single_core)
    for line_ in fi.readlines():
        index += 1
        filename = line_.split(' ')[0].replace('.apk', '')
        filepath = token_root + filename + '.tokenClassSet'
        savepath = LSI_corpus_path + filename + '.lsiClassSet'
        # print(filepath, savepath)
        # lsi_test_single_file(filename, filepath, savepath, TFIDF_dict_path, TFIDF_model_path, LSI_model_path, index,)
        pool.apply_async(lsi_test_single_file, (filename, filepath, savepath, TFIDF_dict_path, TFIDF_model_path, LSI_model_path, index,))

    pool.close()
    pool.join()


def load_lsi_model(TFIDF_dict_path, TFIDF_model_path, LSI_model_path):
    dictionary, tfidf = loadTFIDF_model(TFIDF_dict_path, TFIDF_model_path)
    lsi = models.LsiModel.load(LSI_model_path)
    return dictionary, tfidf, lsi


def lsi_test_single_file(filename, filepath, savepath, TFIDF_dict_path, TFIDF_model_path, LSI_model_path, index):
    # filename: 待提取的文件名
    # LSI_corpus_path: 保存节点LSI特征文件的路径
    # token_root: 分词结果的存储路径
    # dictionary, tfidf, lsi: LSI模型的三个模型文件
    print('Start process file number: ' + str(index) + ', filename: ' + filename)
    dictionary, tfidf, lsi = load_lsi_model(TFIDF_dict_path, TFIDF_model_path, LSI_model_path)
    texts = []
    atype = []
    fi = open(filepath, 'r')
    line = fi.readline().strip('\n').strip(' ')
    _json = json.loads(line)
    for key in _json:
        texts.append(_json[key])
        atype.append(str(key))

    corpus_tfidf = calculate_tfidf(texts, dictionary, tfidf)
    corpus_lsi = lsi[corpus_tfidf]
    # print(atype, corpus_lsi)
    # raise Exception
    save_LSI_CSCG(atype, corpus_lsi, savepath)
    # raise Exception
    print('Finish process file number: ' + str(index) + ', filename: ' + filename)


def save_LSI_CSCG(atype, corpus_lsi, savepath):
    fo = open(savepath, 'w+')
    for i in range(len(atype)):
        _class = atype[i]

        doc = corpus_lsi[i]
        fo.write(_class + ',')
        j = 0
        k = 0
        while (j < 500):
            if (k < len(doc) and j == doc[k][0]):
                fo.write(str(doc[k][1]) + ' ')
                j += 1
                k += 1
            else:
                # print('error:' + str(j))
                fo.write(str('0.0000') + ' ')
                j += 1
        fo.write('\n')
    fo.close()