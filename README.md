# Chạy code:
1. Cài đặt môi trường
2. Cài đặt một số công cụ cần thiết
    - tools/jadx/build/jadx/bin/jadx
        ```sh
        git clone https://github.com/skylot/jadx.git
        cd jadx
        ./gradlew dist
        ```
    - tools/apktool/apktool
    - zip
    > Check permission to execute

3. Chỉnh sửa file cấu hình `config.py`
4. Thêm bộ dữ liệu mới:
    - Lưu APK trong thư mục `dataset\<tên bộ dữ liệu>\*.apk`
    - Tạo 2 file train test với phần mở rộng là `.filelist` trong thư mục `data`
        ```csv
        00431254B83CE811F05542C61F8B11C607C22470BC3B61BD83524A957CA119D9.apk w
        2783c217ea6dfcdb46ac80c3e2a4099e.apk b
        3ec6ec273ff144bbfb9dfa9e33b5cc3b.apk b
        006439E7D8A65DC7E660B4417BE0537C9FFF772AAAF303570D9D60465566A439.apk w
        in which "w" means malware, and "b" means benign sample. 
        ```
    - Thêm giá trị `no_below`, `no_above` trong file cấu hình, tại biến `tfidf_dict_para`

&ensp;&ensp;&ensp;&ensp;1-5，这5个python文件中的main方法包含数据集名，在运行前需要对应修改。

&ensp;&ensp;&ensp;&ensp;From 1 to 5, the 5 Python files contain the dataset name in the main method, which needs to be modified before running. 


### 2.1. 运行LibRadar (Run LibRadar)
&ensp;&ensp;&ensp;&ensp;由于LibRadar基于Python 2.7实现，较难迁移至Python 3下，选择单独运行 

&ensp;&ensp;&ensp;&ensp;Since LibRadar is implemented based on Python 2.7, it is difficult to run in python 3, we chose to run it separately.

    python2 1.main_literadar_python27.py

&ensp;&ensp;&ensp;&ensp;该部分会生成体积很大的log_libradar.txt, 并在"LiteRadar/Data/Decompiled/"下保留反编译的文件，需要及时清理

&ensp;&ensp;&ensp;&ensp;This part will generate a large log file named "log_libradar.txt", and keep the decompiled files in folder
 "LiteRadar/Data/Decompiled/", which needs to be cleaned up in time.

### 2.2. 运行预处理过程 (Preprocessing)
&ensp;&ensp;&ensp;&ensp;This part includes apktool reverse engineering, jadx decompilation, complete APK token extraction, and permission feature extraction.

&ensp;&ensp;&ensp;&ensp;This part include apktool decompilation, jadx decompilation, token extraction of whole APK file, and permission feature extraction. 

&ensp;&ensp;&ensp;&ensp;Later, in order to ensure that our program can process all data, we filtered the fileslist samples, removed incomplete samples such as third-party libraries and Java source codes, and saved the filtered sample list in "data/". filter" file.

&ensp;&ensp;&ensp;&ensp;After that, to ensure that our code could process all the samples in the dataset, we filter the samples with incomplete third-party library detection results or Java source code,
and save the filtered sample list in the ".filter" file in folder "data/".

    python3 2.main_preprocess_python3.py

### 2.3. 训练LSI模型，并计算完整APK的LSI向量 (LSI model training and LSI vector of whole APK file calculation)
&ensp;&ensp;&ensp;&ensp;This part implements our previous method and serves as the basis for the method of this paper.

&ensp;&ensp;&ensp;&ensp;This is the implements of our previous work, which is the basement of our method in this paper.

    Yucai Song, Yang Chen, Bo Lang, et al. Topic model based android malware detection[C]. International Conference on Security, Privacy and Anonymity in Computation, Communication and Storage, 2019: 384-396.

&ensp;&ensp;&ensp;&ensp;This part first trains the LSI model based on the training set, calculates the LSI features of the training set and the test set, and trains the XGBoost model after splicing with the permission features, and outputs the test results.

&ensp;&ensp;&ensp;&ensp;This part first trains the LSI model with training set, and calculates the LSI vectors of the training and testing datasets. 
And then it trains the XGBoost model after concatenating the LSI vector and permission features, and output the test result.

    python3 3.main_lsi_train_python3.py

### 2.4. CSCG构建 (Construction of CSCG)
&ensp;&ensp;&ensp;&ensp;This part first calculates the min_k of the data set; then builds all CSCG, including node merging, call relationship calculation, and node LSI feature calculation; finally, in order to ensure that multiple parameter adjustments reduce IO usage,
Option to merge the entire data set into a large file to prevent reading a large number of fragmented files for each training.


&ensp;&ensp;&ensp;&ensp;This part first calculates the "min_k" of the dataset. And then it constructs the class-set call graph (CSCG), including node merging,
call relationship calculation and node LSI vector calculation. 
Finally, to reduce the IO usage, we choose to consolidate the entire dataset into large files to prevent reading large number of fragmented files for every training process. 


    python3 4.main_cscg_construct_python3.py

### 2.5. 模型训练与测试 (Model training and testing)
&ensp;&ensp;&ensp;&ensp;This part extracts features from CSCG and performs classification. To adjust the parameters of the model, modify it in "GAT/graph_net.py", usually mainly modify the two parameters "self.args["lr"]" and "self.args["num_heads_per_layer"]", try 0.001 for lr and 0.002, num_heads_per_layer tries 2-8.

&ensp;&ensp;&ensp;&ensp;This part extracts features from CSCG and performs classification. The parameters of the model could be modified in "GAT/graph_net.py" file/
Usually, there are two parameters need to be adjusted, which are  "self.args["lr"]" and "self.args["num_heads_per_layer"]".
For "lr", we try 0.001 and 0.002; and for "num_heads_per_layer", we try 7 number which are from 2 to 8.

    python3 5.main_graph_test_python3.py

## 3. 引用 (Reference)

&ensp;&ensp;&ensp;&ensp;Our paper is currently in the review stage, and details of the paper will be added after acceptance.

&ensp;&ensp;&ensp;&ensp;The paper is now under review, the details of the paper will be supplemented after acceptance. 

## 4. 其他 (Other notices)

&ensp;&ensp;&ensp;&ensp;The current project is a demo built based on a subset of the AMD_AndroZoo data set, and all intermediate files of the demo have been retained.
&ensp;&ensp;&ensp;&ensp;The current project is a demo on a subset of AMD_AndroZoo dataset. All intermediate files of the demo have been reserved.

&ensp;&ensp;&ensp;&ensp;The file of the real data set is too large and cannot be uploaded. Only the corresponding 3 sets of model files are retained.

&ensp;&ensp;&ensp;&ensp;The files of the real datasets is too large, only the corresponding model files of the 3 datasets are reserved. 

&ensp;&ensp;&ensp;&ensp;If you don’t need a demo, you only need to download this folder and make sure the outer path exists.

&ensp;&ensp;&ensp;&ensp;If do not need the demo, it could just download this folder and make sure the outer folders exist.

## 注 (Note)：
&ensp;&ensp;&ensp;&ensp;The current version is compiled based on the original code during the experimental phase. It is not ruled out that there are some bugs and we will fix them later.
&ensp;&ensp;&ensp;&ensp;Our current version of our code may still have some problems, and we will further improve it in the future.

