# coding=utf-8
import os
from config import get_apk_path, get_lsi_config, get_xgboost_config, get_cscg_config, get_graph_config
from lsi.lsi import lsi_train, lsi_test
from xgb_classification.combine_lsi_permission import combine_lsi_permission
from xgb_classification.xgboost_clf import train_xgb_model, test_xgb_model

program_root = os.getcwd()
# Add apktool environment variables
os.environ["PATH"] = program_root + '/tools/apktool/' + ":" + os.environ["PATH"]
# Add jadx environment variables
os.environ["PATH"] = program_root + '/tools/jadx/build/jadx/bin/' + ":" + os.environ["PATH"]

# Run under python3.6
# Only use semantic model and permission features for model training
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

if __name__ == '__main__':
    dataset = 'AMD_AndroZoo_demo'
    lsi_model_train(dataset)

