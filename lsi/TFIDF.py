# coding=utf-8
import os
from gensim import corpora, models
from .read_data import read_texts, read_texts_batch
import codecs


# 训练得到TFIDF的模型
# type取值有3中，其中
# 1. 默认值'lsi'表示每个tokens文件为一个token集合
# 2. 'java_graph'和'call_graph'表示每个token文件中为一个json，key为java类名或函数名，每个value为一个token集合
# 仅当type为'lsi'时，atype与texts一一对应，表示数据的标签，
# 否则texts每行为apk文件中一个类或一个函数对应的token集合，atype表示texts对应的类或函数名，用文件名 + '_' + 类或函数名表示
# 当type为lsi时，atype可以很容易从train_file中获取，无需层层返回，否则atype需要层层返回，即type不同，返回值数量不同
def TFIDF_model(name, train_file, TFIDF_dict_path, dict_corpus, TFIDF_model_path, TFIDF_corpus_path, token_root, type='lsi', no_below=25, no_above=0.5):
    # 执行corpus计算中会进行TFIDF_dict_path和dict_corpus的检查
    if type == 'lsi':
        dictionary, corpus = gensim_dict_corpus(name, train_file, TFIDF_dict_path, dict_corpus, token_root, type=type, no_below=no_below, no_above=no_above)
        # 无用，只是为了保证atype不是None
        atype = []
    else:
        dictionary, corpus, atype = gensim_dict_corpus(name, train_file, TFIDF_dict_path, dict_corpus, token_root, type=type)
    if os.path.exists(TFIDF_model_path):
        tfidf = models.TfidfModel.load(TFIDF_model_path)
        print('TFIDF model exist: ' + name)
    else:
        tfidf = models.TfidfModel(corpus)
        print('Train tfidf finish: ' + name)
        tfidf.save(TFIDF_model_path)
        print('Save tfidf finish: ' + name)
    if os.path.exists(TFIDF_corpus_path):
        print('TFIDF_corpus exist: ' + name)
        corpus_tfidf = corpora.MmCorpus(TFIDF_corpus_path)
    else:
        corpus_tfidf = tfidf[corpus]
        print('Corpus tfidf finish: ' + name)
        corpora.MmCorpus.serialize(TFIDF_corpus_path, corpus_tfidf)
        print('Save corpus tfidf finish: ' + name)
    if type == 'lsi':
        return dictionary, tfidf, corpus_tfidf
    else:
        return dictionary, tfidf, corpus_tfidf, atype


# type取值有3中，其中
# 1. 默认值'lsi'表示每个tokens文件为一个token集合
# 2. 'java_graph'和'call_graph'表示每个token文件中为一个json，key为java类名或函数名，每个value为一个token集合
# 仅当type为'lsi'时，atype与texts一一对应，表示数据的标签，
# 否则texts每行为apk文件中一个类或一个函数对应的token集合，atype表示texts对应的类或函数名，用文件名 + '_' + 类或函数名表示
# 当type为lsi时，atype可以很容易从train_file中获取，无需层层返回，否则atype需要层层返回，即type不同，返回值数量不同
def gensim_dict_corpus(name, train_file, TFIDF_dict_path, dict_corpus, token_root, type='lsi', no_below=25, no_above=0.5):
    # 如果结果dict和corpus均已存在，则直接load
    if os.path.exists(dict_corpus) and os.path.exists(TFIDF_dict_path):
        dictionary = corpora.Dictionary.load(TFIDF_dict_path)
        print('Dict exist: ' + name)
        corpus = corpora.MmCorpus(dict_corpus)
        print('Corpus exist: ' + name)
        if not type == 'lsi':
            texts, atype = read_texts(train_file, token_root, type=type)
    # 如果存在dict，但不存在corpus，则load dict，并计算corpus
    elif os.path.exists(TFIDF_dict_path):
        texts, atype = read_texts(train_file, token_root, type=type)
        dictionary = corpora.Dictionary.load(TFIDF_dict_path)
        print('Dict exist: ' + name)
        corpus = [dictionary.doc2bow(text) for text in texts]
        print('Corpus finish: ' + name)
        corpora.MmCorpus.serialize(dict_corpus, corpus)
        print('Save corpus finish: ' + name)
    # 如果不存在dict，则认为corpus不应该存在，直接计算dict和corpus
    else:
        # read_texts(train_file, token_root, type=type)
        texts, atype = read_texts(train_file, token_root, type=type, batch=False)
        dictionary = corpora.Dictionary(texts)
        dictionary.filter_extremes(keep_n=100000, no_below=no_below, no_above=no_above)
        # VirusShare_Apkpure : no_below=100, no_above=0.5
        # Drebin_AndroZoo : no_below=40, no_above=0.5
        # AMD_AndroZoo : no_below=50, no_above=0.3
        dictionary.compactify()
        print('Create dict finish: ' + name)
        dictionary.save(TFIDF_dict_path)
        print('Save dict finish: ' + name)
        corpus = [dictionary.doc2bow(text) for text in texts]
        print('Corpus finish: ' + name)
        corpora.MmCorpus.serialize(dict_corpus, corpus)
        print('Save corpus finish: ' + name)
    if type == 'lsi':
        return dictionary, corpus
    else:
        return dictionary, corpus, atype


# 读取数据集列表中的文件，并生成TFIDF向量
def getTFIDF_src_file(src_filepath, token_root, TFIDF_dict_path, TFIDF_model_path, type='lsi'):
    print(src_filepath, token_root, TFIDF_dict_path, TFIDF_model_path, type)
    corpus_tfidf = []
    atype = []
    if type == 'lsi':
        # lsi则一次性读取全部文档内容
        texts, atype = read_texts(src_filepath, token_root, type=type)
        corpus_tfidf += getTFIDF_texts(texts, TFIDF_dict_path, TFIDF_model_path)
    else:
        # CSCG则由于文档内容太多，需要按batch读取字符，并转为TF-IDF向量
        for texts, atype in read_texts_batch(src_filepath, token_root, type=type, batch=True):
            corpus_tfidf += getTFIDF_texts(texts, TFIDF_dict_path, TFIDF_model_path)
        # print('--------------------')
        # print(len(corpus_tfidf))
    return corpus_tfidf, atype



# 输入texts(n个数据的词汇列表的列表)
def getTFIDF_texts(texts, TFIDF_dict_path, TFIDF_model_path):
    dictionary = corpora.Dictionary.load(TFIDF_dict_path)
    tfidf = models.TfidfModel.load(TFIDF_model_path)
    corpus = [dictionary.doc2bow(text) for text in texts]
    corpus_tfidf = tfidf[corpus]
    return corpus_tfidf


def loadTFIDF_model(TFIDF_dict_path, TFIDF_model_path):
    dictionary = corpora.Dictionary.load(TFIDF_dict_path)
    tfidf = models.TfidfModel.load(TFIDF_model_path)
    return dictionary, tfidf


def calculate_tfidf(texts, dictionary, tfidf):
    corpus = [dictionary.doc2bow(text) for text in texts]
    corpus_tfidf = tfidf[corpus]
    return corpus_tfidf

