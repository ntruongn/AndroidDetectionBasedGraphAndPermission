# coding=utf-8
import os
from multiprocessing import Pool
from config import get_lsi_config, get_cscg_config, get_graph_config
from config import total_process_multi_core, total_process_single_core, ts_max, min_k_tmp_file
from lsi.lsi import lsi_train, lsi_test_cscg
from CSCG.calculate_min_k import calculate_min_k
from CSCG.java_graph import get_cscg_dataset
from GAT.create_graph_dataset import create_graph_files

program_root = os.getcwd()
# Add apktool environment variables
os.environ["PATH"] = program_root + '/tools/apktool/' + ":" + os.environ["PATH"]
# Add jadx environment variables
os.environ["PATH"] = program_root + '/tools/jadx/build/jadx/bin/' + ":" + os.environ["PATH"]

# Build the graph based on the import relationship of the java file, which is equivalent to the calling relationship of the public class, and retain a certain 3rd library so that if the number of nodes after filtering is less than 100, try to add it to as close to 100 as possible
def class_set_call_graph(dataset):
    # dataset_name The name of the dataset,
    # java_path The storage path of the original java code compressed package,
    # java_graph_path saves the path of class-set call graph calling relationship,
    # _3rd_path The storage path of third-party library files,
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
    # pool = Pool(processes=2)
    # 19. Generate node feature vectors of the training set
    lsi_test_cscg(dataset, train_file, TFIDF_dict_path, TFIDF_model_path, LSI_model_path, LSI_corpus_path, token_root, type='cscg')
    # pool.apply_async(lsi_test_cscg, (dataset, train_file, TFIDF_dict_path, TFIDF_model_path, LSI_model_path, LSI_corpus_path, token_root, 'cscg'))

    # 20. Generate node feature vectors of the test set
    lsi_test_cscg(dataset, test_file, TFIDF_dict_path, TFIDF_model_path, LSI_model_path, LSI_corpus_path_test, token_root, type='cscg')
    # pool.apply_async(lsi_test_cscg, (dataset, test_file, TFIDF_dict_path, TFIDF_model_path, LSI_model_path, LSI_corpus_path_test, token_root, 'cscg'))
    # pool.close()
    # pool.join()

    # To prevent it from taking too much time to read broken files when adjusting parameters multiple times, save the CSCG into a large file first.
    pool = Pool(processes=2)

    # 21. Read the input graph source file of PSCN
    train_file, test_file, LSI_corpus_path, LSI_corpus_path_test, graph_file_root, model_root, permission_feature_path, lsi_fearue_file, lsi_fearue_file_test = get_graph_config(dataset)

    # 22. Generate the graph file of the training set
    # create_graph_files(train_file, graph_file_root, LSI_corpus_path, model_root, lsi_fearue_file, permission_feature_path=permission_feature_path, type='cscg', apktool_root_path=apktool_root_path, add_root=False)
    pool.apply_async(create_graph_files, (train_file, graph_file_root, LSI_corpus_path, model_root, lsi_fearue_file, permission_feature_path, 'cscg', apktool_root_path, False))

    # 23. Generate the graph file of the test set
    # create_graph_files(test_file, graph_file_root, LSI_corpus_path_test, model_root, lsi_fearue_file_test, permission_feature_path=permission_feature_path, type='cscg',  apktool_root_path=apktool_root_path)
    pool.apply_async(create_graph_files, (test_file, graph_file_root, LSI_corpus_path_test, model_root, lsi_fearue_file_test, permission_feature_path, 'cscg', apktool_root_path, False))
    pool.close()
    pool.join()

if __name__ == '__main__':
    dataset = 'AMD_AndroZoo_demo'
    class_set_call_graph(dataset)

