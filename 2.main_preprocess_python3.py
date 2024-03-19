# coding=utf-8
import os
from Decompilation.apktool import apktool
from Decompilation.jar2java import jar2java
from config import get_apk_path, get_lsi_config, get_xgboost_config, get_cscg_config, get_graph_config
from config import total_process_multi_core, total_process_single_core, java_src_tmp_path, ts_max, min_k_tmp_file
from lexical_analysis.extract_token import extract_token
from Permission.permissionExtract import extractPermission
from dataset_construct.create_filelist import create_filelist

program_root = os.getcwd()
# Add apktool environment variables
os.environ["PATH"] = program_root + '/tools/apktool/' + ":" + os.environ["PATH"]
# Add jadx environment variables
os.environ["PATH"] = program_root + '/tools/jadx/build/jadx/bin/' + ":" + os.environ["PATH"]
print(program_root+'/tools/apktool/')

# Preprocess the original APK file, including decompilation, etc., and run it under python3.6
def preproces(dataset):
    apk_path, manifest_path, dex_path, java_path, _3rd_path, permission_path, token_path, filelist_train, filelist_test, filelist_train_filter, filelist_test_filter = get_apk_path(dataset)
    
    # 2. Use apktool to obtain the Androidmanifest.xml and class.dex of each file and run it under python2.7
    apktool(apk_path, manifest_path, dex_path, total_process_multi_core)

    # 3. Use jadx to decompile each class.dex, and package all the decompiled java files to generate a .zip compressed package, which can be run under python3.6
    jar2java(dex_path, java_path, java_src_tmp_path, program_root, total_process_multi_core)
    # 4. Extract the token from each decompiled java file and run it under python3.6
    extract_token(dataset, _3rd_path, java_path, manifest_path, token_path, total_process_single_core)

    # 5. Extract permission characteristics from each manifest file and run it under python3.6
    extractPermission(manifest_path, permission_path)

    # 6. Generate file filelist.txt that records all valid data in each data set, run under python3.6
    create_filelist(filelist_train, filelist_train_filter, _3rd_path, manifest_path, java_path)

    # 7. Generate file filelist.txt that records all valid data in each data set, run under python3.6
    create_filelist(filelist_test, filelist_test_filter, _3rd_path, manifest_path, java_path)

    print('\n'.join([apk_path, manifest_path, dex_path, java_path, _3rd_path, permission_path, token_path, filelist_train, filelist_test, filelist_train_filter, filelist_test_filter]))
if __name__ == '__main__':
    dataset = 'AMD_AndroZoo_demo'
    preproces(dataset)


