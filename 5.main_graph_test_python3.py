# coding=utf-8
import os
from config import get_graph_config
from GAT.graph_net import graph_model

program_root = os.getcwd()
# 添加apktool的环境变量
os.environ["PATH"] = program_root + '/tools/apktool/' + ":" + os.environ["PATH"]
# 添加jadx的环境变量
os.environ["PATH"] = program_root + '/tools/jadx/build/jadx/bin/' + ":" + os.environ["PATH"]


# 基于java文的import关系进行图构建，相当于public class的调用关系，并保留一定的3rd库，使得过滤后节点数量小于100的，尽量补充到接近100
def class_set_call_graph_test():
    # 12.读取PSCN的输入graph源文件
    train_file, test_file, LSI_corpus_path, LSI_corpus_path_test, graph_file_root, model_root, permission_feature_path, lsi_fearue_file, lsi_fearue_file_test = get_graph_config(dataset)

    # 15.graph_net训练测试
    graph_model(model_root, dataset)

if __name__ == '__main__':
    dataset = 'AMD_AndroZoo_demo'
    class_set_call_graph_test()

