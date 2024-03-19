# coding=utf-8
import os
from multiprocessing import Pool
from Decompilation.apktool import apktool
from Decompilation.jar2java import jar2java
from LiteRadar.filter_dex import filter_dex
from config import get_apk_path, get_lsi_config, get_xgboost_config, get_cscg_config, get_graph_config
from config import total_process_multi_core, total_process_single_core, java_src_tmp_path, ts_max, min_k_tmp_file
from lexical_analysis.extract_token import extract_token
from Permission.permissionExtract import extractPermission
from dataset_construct.create_filelist import create_filelist
from lsi.lsi import lsi_train, lsi_test
from xgb_classification.combine_lsi_permission import combine_lsi_permission
from xgb_classification.xgboost_clf import train_xgb_model, test_xgb_model
from CSCG.calculate_min_k import calculate_min_k
from CSCG.java_graph import get_cscg_dataset
from GAT.create_graph_dataset import create_graph_files
from GAT.graph_net import graph_model

program_root = os.getcwd()
#Add apktool environment variables
os.environ["PATH"] = program_root + '/tools/apktool/' + ":" + os.environ["PATH"]
#Add jadx environment variables
os.environ["PATH"] = program_root + '/tools/jadx/build/jadx/bin/' + ":" + os.environ["PATH"]

# Preprocess the original APK file, including decompilation, third-party library filtering, etc., run under python2.7
def literadar(dataset):
    # 1. Get the configuration of the data set
    apk_path, manifest_path, dex_path, java_path, _3rd_path, permission_path, token_path, filelist_train, filelist_test, filelist_train_filter, filelist_test_filter = get_apk_path(dataset)

    # 2. Use LiteRadar to obtain the third-party library of each apk file and run it under python2.7
    filter_dex(apk_path, _3rd_path, total_process_multi_core)

# Preprocess the original APK file, including decompilation, third-party library filtering, etc., run under python3.6
def preproces(dataset):
    apk_path, manifest_path, dex_path, java_path, _3rd_path, permission_path, token_path, filelist_train, filelist_test, filelist_train_filter, filelist_test_filter = get_apk_path(dataset)

    # 2. Use apktool to obtain the Androidmanifest.xml and class.dex of each file, and run it under python2.7
    apktool(apk_path, manifest_path, dex_path, total_process_multi_core)
    # 3. Use jadx to decompile each class.dex, and package all the decompiled java files to generate a .zip compressed package, run under python3.6
    jar2java(dex_path, java_path, java_src_tmp_path, program_root, total_process_multi_core)

    # 4. Extract the token from each decompiled java file and run it under python3.6
    extract_token(dataset, _3rd_path, java_path, manifest_path, token_path, total_process_single_core)

    # 5. Extract permission characteristics from each manifest file and run it under python3.6
    extractPermission(manifest_path, permission_path)

    # 6. Generate the file filelist.txt that records all valid data in each data set, and run it under python3.6
    create_filelist(filelist_train, filelist_train_filter, _3rd_path, manifest_path, java_path)

    # 7. Generate the file filelist.txt that records all valid data in each data set, and run it under python3.6
    create_filelist(filelist_test, filelist_test_filter, _3rd_path, manifest_path, java_path)


# Running under python3.6
# Model training using only semantic model and permission features
def lsi_model_train(dataset):
    # 8. Obtain the paths of all files required for lsi model training
    train_file, test_file, TFIDF_dict_path, dict_corpus, TFIDF_model_path, TFIDF_corpus_path, LSI_model_path, LSI_corpus_path, LSI_corpus_path_test, token_root, apktool_root_path, no_below, no_above = get_lsi_config(dataset)

    # 9. Carry out LSI model training, which includes the training of TFIDF model, and generate training feature files.
    lsi_train(dataset, train_file, TFIDF_dict_path, dict_corpus, TFIDF_model_path, TFIDF_corpus_path, LSI_model_path, LSI_corpus_path, token_root, no_below=no_below, no_above=no_above)

    # 10. Generate feature vectors of the test set
    lsi_test(dataset, test_file, TFIDF_dict_path, TFIDF_model_path, LSI_model_path, LSI_corpus_path_test, token_root)

    # 11. Obtain information about the data set and model
    LSI_Permission_file, LSI_Permission_file_test, lsi_per_xgboost_model, LSI_corpus_path, LSI_corpus_path_test, permission_dir_path = get_xgboost_config(dataset)

    # 12. Generate features of the training set after splicing lsi and permission
    combine_lsi_permission(dataset, LSI_corpus_path, permission_dir_path, LSI_Permission_file)

    # 13. Generate LSI and permission splicing features of the test set
    combine_lsi_permission(dataset, LSI_corpus_path_test, permission_dir_path, LSI_Permission_file_test)

    # 14. Train XGBoost model for classification
    train_xgb_model(LSI_Permission_file, lsi_per_xgboost_model)

    # 15. Test the effect of XGBoost model
    test_xgb_model(LSI_Permission_file_test, lsi_per_xgboost_model)


# Build the graph based on the import relationship of the java file, which is equivalent to the calling relationship of the public class, and retain a certain 3rd library so that if the number of nodes after filtering is less than 100, try to add it to as close to 100 as possible
def class_set_call_graph(dataset):
    # dataset_name The name of the dataset,
    # java_path is the storage path of the original java code compressed package,
    # java_graph_path saves the path of class-set call graph calling relationship,
    # _3rd_path is the storage path of third-party library files,
    # token_file_root saves the tokens analyzed by this method for each class-set,
    # min_k The min_k value under this data set
    # 16. Obtain CSCG configuration information
    java_path, java_graph_path, _3rd_path, token_file_root= get_cscg_config(dataset)
    train_file, test_file, TFIDF_dict_path, dict_corpus, TFIDF_model_path, TFIDF_corpus_path, LSI_model_path, LSI_corpus_path, LSI_corpus_path_test, token_root, apktool_root_path, no_below, no_above = get_lsi_config(dataset, type='cscg')

    # 17. Calculate min_k
    min_k = calculate_min_k(dataset, java_path, train_file, ts_max, min_k_tmp_file)

    # 18. Calculate the CSCG call graph and segment the nodes
    get_cscg_dataset(dataset, java_path, java_graph_path, _3rd_path, token_file_root, min_k=min_k, total_process=total_process_single_core)

    # Extract the LSI vector of class-set and save each APK into a file
    pool = Pool(processes=2)
    # 19. Generate node feature vectors of the training set
    # lsi_test(dataset, train_file, TFIDF_dict_path, TFIDF_model_path, LSI_model_path, LSI_corpus_path, token_root, type='cscg')
    pool.apply_async(lsi_test, (dataset, train_file, TFIDF_dict_path, TFIDF_model_path, LSI_model_path, LSI_corpus_path, token_root, 'cscg'))

    # 20. Generate node feature vectors of the test set
    # lsi_test(dataset, test_file, TFIDF_dict_path, TFIDF_model_path, LSI_model_path, LSI_corpus_path_test, token_root, type='cscg')
    pool.apply_async(lsi_test, (dataset, test_file, TFIDF_dict_path, TFIDF_model_path, LSI_model_path, LSI_corpus_path_test, token_root, 'cscg'))
    pool.close()
    pool.join()

    # raise Exception
    # To prevent it from taking too much time to read broken files when adjusting parameters multiple times, save the CSCG into a large file first.
    pool = Pool(processes=2)

    # 21. Read the input graph source file of PSCN
    train_file, test_file, LSI_corpus_path, LSI_corpus_path_test, graph_file_root, model_root, permission_feature_path, lsi_fearue_file, lsi_fearue_file_test = get_graph_config(
        dataset)

    # 22. Generate the graph file of the training set
    # create_graph_files(train_file, graph_file_root, LSI_corpus_path, model_root, lsi_fearue_file, permission_feature_path=permission_feature_path, type='cscg', apktool_root_path=apktool_root_path, add_root=False)
    pool.apply_async(create_graph_files, (train_file, graph_file_root, LSI_corpus_path, model_root, lsi_fearue_file, permission_feature_path, 'cscg', apktool_root_path, False))

    # 23. Generate the graph file of the test set
    # create_graph_files(test_file, graph_file_root, LSI_corpus_path_test, model_root, lsi_fearue_file_test, permission_feature_path=permission_feature_path, type='cscg',  apktool_root_path=apktool_root_path)
    pool.apply_async(create_graph_files, (test_file, graph_file_root, LSI_corpus_path_test, model_root, lsi_fearue_file_test, permission_feature_path, 'cscg', apktool_root_path, False))
    pool.close()
    pool.join()

# The graph is constructed based on the import relationship in Java, which is equivalent to the calling relationship of public class, and a certain 3rd library is retained, so that if the number of nodes after filtering is less than 100, try to add it to as close to 100 as possible
def class_set_call_graph_test():
    # 12. Read the input graph source file of PSCN
    train_file, test_file, LSI_corpus_path, LSI_corpus_path_test, graph_file_root, model_root, permission_feature_path, lsi_fearue_file, lsi_fearue_file_test = get_graph_config(dataset)

    # 15.graph_net training and testing
    graph_model(model_root, dataset)

if __name__ == '__main__':
    dataset = 'AMD_AndroZoo'
    # literadar(dataset)
    preproces(dataset)
    lsi_model_train(dataset)
    class_set_call_graph(dataset)
    class_set_call_graph_test()