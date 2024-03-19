# coding=utf-8
import os

root =  os.path.join(os.getcwd(), 'dataset/preprocessing/')
# root1 needs to be placed on the solid state drive
root1 = os.path.join(os.getcwd(), 'dataset/preprocessing/')
data_root_path = os.path.join(os.getcwd(), 'dataset/')
apktool_root_path = root + 'apk_tool/'
java_root_path = root + 'java/'
_3rd_root_path = root + '3rd/'
permission_feature_path = root + 'permission/'
token_path_root = root + 'tokenResult/'
cscg_root_path = root + 'class_set_call_graph/'
token_class_set_root_path = root + 'tokenClassSet/'
java_src_tmp_path = root1 + 'java_src_tmp'
model_path_prefix = root + 'model/'
filelist_root = os.path.join(os.getcwd(), 'data/')
ts_max = 1500
ts_min = 100
# The number of child processes that support multi-core scheduling, such as apktool, jadx, etc.
total_process_multi_core = 8
# The number of child processes that do not support multi-core scheduling, such as CSCG construction, etc.
total_process_single_core = 100
MainDirMaxToken = 30000
MaxToken = 100000
MaxNodes = 1800
num_topics = 500
min_k_tmp_file = 'CSCG/min_k_tmp.txt'

tfidf_dict_para = {
    'AMD_AndroZoo_demo':   {'no_below': 1,
                            'no_above':  0.5},
    'AMD_AndroZoo':        {'no_below': 50,
                            'no_above':  0.3},
    'Drebin_AndroZoo':     {'no_below': 40,
                            'no_above':  0.5},
    'VirusShare_Apkpure':  {'no_below': 100,
                            'no_above':  0.5}
}

def get_apk_path(dataset):
    dataset_path_prefix = dataset + '/'
    apk_path = data_root_path + dataset_path_prefix
    manifest_path = apktool_root_path + dataset_path_prefix + 'manifest/'
    dex_path = apktool_root_path + dataset_path_prefix + 'dex/'
    java_path = java_root_path + dataset_path_prefix
    _3rd_path = _3rd_root_path + dataset_path_prefix
    permission_path = permission_feature_path + dataset_path_prefix
    token_path = token_path_root + dataset_path_prefix
    filelist_train = filelist_root + dataset + '_train.filelist'
    filelist_test = filelist_root + dataset + '_test.filelist'
    filelist_train_filter = filelist_root + dataset + '_train.filter'
    filelist_test_filter = filelist_root + dataset + '_test.filter'

    for path in [apk_path, manifest_path, dex_path, java_path, _3rd_path, permission_path, token_path]:
        if not os.path.exists(path):
            os.system("mkdir -p " + path)
    return apk_path, manifest_path, dex_path, java_path, _3rd_path, permission_path, token_path, filelist_train, filelist_test, filelist_train_filter, filelist_test_filter


# 2. 'cscg' indicates the configuration of extracting lsi from class-set
def get_lsi_config(dataset, type='lsi'):
    dataset_path_prefix = dataset + '/'
    train_file = filelist_root + dataset + '_train.filter'
    test_file = filelist_root + dataset + '_test.filter'
    if type == 'lsi':
        token_root = token_path_root + dataset_path_prefix
        model_root = model_path_prefix + dataset_path_prefix  # ['model_root']
    elif type == 'cscg':
        token_root = token_class_set_root_path + dataset_path_prefix
        model_root = model_path_prefix + dataset_path_prefix  # ['model_root']
    else:
        print('Only support "lsi" and "csbd", not include ' + type + '!')
        raise Exception
    if not os.path.exists(model_root):
        os.system('mkdir -p ' + model_root)
    TFIDF_dict_path = model_root + 'black_white_asm.dict'  # ['TFIDF_dict']
    dict_corpus = model_root + 'black_white_corpus.dict'  # ['dict_corpus']
    TFIDF_model = model_root + 'tfidf.model'  # ['TFIDF_model']
    TFIDF_corpus_path = model_root + 'black_white_corpus_tfidf.mm'  # ['TFIDF_corpus']
    LSI_model_path = model_root + 'lsi.model'  # ['LSI_model_path']
    no_below = tfidf_dict_para[dataset]['no_below']
    no_above = tfidf_dict_para[dataset]['no_above']

    if type == 'lsi':
        LSI_corpus_path = model_root + 'lsi_result.txt'  # ['LSI_corpus']
        LSI_corpus_path_test = model_root + 'lsi_result_test.txt'  # ['LSI_corpus_test']
    else:
        LSI_corpus_path = model_root + 'lsi_result/'  # ['LSI_corpus']
        LSI_corpus_path_test = model_root + 'lsi_result_test/'  # ['LSI_corpus_test']
        if not os.path.exists(LSI_corpus_path):
            os.mkdir(LSI_corpus_path)
        if not os.path.exists(LSI_corpus_path_test):
            os.mkdir(LSI_corpus_path_test)
    apktool_root = apktool_root_path + dataset_path_prefix

    return train_file, test_file, TFIDF_dict_path, dict_corpus, TFIDF_model, TFIDF_corpus_path, LSI_model_path, LSI_corpus_path, LSI_corpus_path_test, token_root, apktool_root, no_below, no_above

def get_xgboost_config(dataset_name):
    model_root = model_path_prefix + dataset_name + '/'
    LSI_Permission_file = model_root + 'lsi_permission.txt'  # ['LSI_Permission_file']
    LSI_per_xgboost_model = model_root + 'lsi_permission_xgboost.model'  # ['lsi_per_xgboost_model']
    LSI_corpus_path = model_root + 'lsi_result.txt'  # ['LSI_corpus']
    LSI_corpus_path_test = model_root + 'lsi_result_test.txt'  # ['LSI_corpus_test']
    LSI_Permission_file_test = model_root + 'lsi_permission_test.txt'  # ['LSI_Permission_file_test']
    permission_path = permission_feature_path + dataset_name +'/'
    return LSI_Permission_file, LSI_Permission_file_test, LSI_per_xgboost_model, LSI_corpus_path, LSI_corpus_path_test, permission_path


def get_cscg_config(dataset):
    dataset_path_prefix = dataset + '/'
    java_path = java_root_path + dataset_path_prefix
    java_graph_path = cscg_root_path + dataset_path_prefix
    _3rd_path = _3rd_root_path + dataset_path_prefix
    token_java_path = token_class_set_root_path + dataset_path_prefix

    for path in [java_path, java_graph_path, _3rd_path, token_java_path]:
        if not os.path.exists(path):
            os.system("mkdir -p " + path)

    return java_path, java_graph_path, _3rd_path, token_java_path


def get_graph_config(dataset):
    train_file = filelist_root + dataset + '_train.filter'
    test_file = filelist_root + dataset + '_test.filter'
    model_root = model_path_prefix + dataset + '/'  # ['model_root']
    graph_path = cscg_root_path + dataset + '/'

    if not os.path.exists(model_root):
        os.system('mkdir -p ' + model_root)
    LSI_corpus_path = model_root + 'lsi_result/'  # ['LSI_corpus']
    LSI_corpus_path_test = model_root + 'lsi_result_test/'  # ['LSI_corpus_test']
    if not os.path.exists(LSI_corpus_path):
        os.mkdir(LSI_corpus_path)
    if not os.path.exists(LSI_corpus_path_test):
        os.mkdir(LSI_corpus_path_test)
    train_lsi_fearue_file = model_root + 'lsi_result.txt'
    test_lsi_fearue_file = model_root + 'lsi_result_test.txt'
    permission_root = permission_feature_path + dataset + '/'
    return train_file, test_file, LSI_corpus_path, LSI_corpus_path_test, graph_path, model_root, permission_root, train_lsi_fearue_file, test_lsi_fearue_file
