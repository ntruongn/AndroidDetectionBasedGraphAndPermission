# coding=utf-8
import os
from LiteRadar.filter_dex import filter_dex
from config import get_apk_path
from config import total_process_single_core

program_root = os.getcwd()
# Add apktool environment variables
os.environ["PATH"] = program_root + '/tools/apktool/' + ":" + os.environ["PATH"]
# Add jadx environment variables
os.environ["PATH"] = program_root + '/tools/jadx/build/jadx/bin/' + ":" + os.environ["PATH"]


# Preprocess the original APK file, including decompilation, third-party library filtering, etc., and run it under python2.7
def literadar(dataset):
    # 1. Get the configuration of the dataset
    apk_path, manifest_path, dex_path, java_path, _3rd_path, permission_path, token_path, filelist_train, filelist_test, filelist_train_filter, filelist_test_filter = get_apk_path(dataset)
    print(apk_path, _3rd_path, total_process_single_core)
    # 2.Use LiteRadar to obtain the third-party library of each apk file and run it under python2.7
    filter_dex(apk_path, _3rd_path, total_process_single_core)

if __name__ == '__main__':
    dataset = 'AMD_AndroZoo_demo'
    literadar(dataset)