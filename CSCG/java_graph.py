# coding=utf-8
import zipfile
from multiprocessing import Pool
from .findImports import findImports
from .filter_3rd_from_graph import filter_3rd_single
import json
import os
import sys
import random
import time

sys.path.append('..')
from lexical_analysis.FileUtil import FileUtil
from lexical_analysis.TestLexer import TestLexer
from lexical_analysis.load_3rd_party import load_3rd_lib_dot, load_3rd_lib
from config import MaxToken, MainDirMaxToken, MaxNodes, ts_min

class java_graph:
    filename = ''
    JavaZipFilePath = []
    JavaZipFile = None
    filelist = {}       # key为节点的以.分隔的类名，value为statistics里对应的key
    filelist_path = []   # 在开始时，filelist_path是一个列表，按文件字母顺序排序好;在完成统计后，filelist_path转换成一个字典，key为文件路径，value为所属节点的名称
    call_graph = {}
    token_results = {}
    _3rd_party = []
    _3rd_party_path = []
    statistic = {}              #文件树
    paths_in_3rd = []  # 将全部的文件路径分为两部分，这里仅保存在3rd中的，
    paths_not_in_3rd = []
    separate = 1


    def __init__(self, filename, java_zip_filepath, _3rd_party_file, min_k=1):
        self.filename = filename
        self.JavaZipFilePath = java_zip_filepath
        self.filelist = []
        self.filelist_path = []
        self.call_graph = {}
        self.token_results = {}
        self._3rd_party = load_3rd_lib_dot(_3rd_party_file)
        self._3rd_party_path = load_3rd_lib(_3rd_party_file)
        self.remove_duplicate_3rd()
        self.statistic = {}
        self.paths_in_3rd = []       # 将全部的文件路径分为两部分，这里仅保存在3rd中的，
        self.paths_not_in_3rd = []
        self.separate = min_k
        try:
            self.JavaZipFile = zipfile.ZipFile(self.JavaZipFilePath, 'r')
        except Exception as e:
            print(e)
            return
        filelist = self.JavaZipFile.namelist()
        for _file in filelist:
            if _file[-1] == '/' or not _file.endswith('.java'):    # 去掉所有的文件夹路径
                continue
            self.filelist.append(_file[12:-5].replace('/', '.'))  # 去掉文件开头的'src/sources/'
            self.filelist_path.append(_file)
        self.filelist_filter_path = set(self.filelist_path)
        # print(filename, self.filelist)

    # 去掉三方库中可能互相包含的项，仅保留最大的路径
    def remove_duplicate_3rd(self):
        removes = set()
        for path in self._3rd_party_path:
            for path_ in self._3rd_party_path:
                if path.startswith(path_) and path != path_:
                    removes.add(path)
                    break
        for path in removes:
            self._3rd_party_path.remove(path)

        removes = set()
        for path in self._3rd_party:
            for path_ in self._3rd_party:
                if path.startswith(path_) and path != path_:
                    removes.add(path)
                    break
        for path in removes:
            self._3rd_party.remove(path)

    # 获取一个java文件的全部父路径
    def get_root_node(self, filepath):
        root_ = filepath[:-len(filepath.split('/')[-1])-1]
        return root_

    # 向上取整的除法
    def division(self, devidend, divisor):
        if devidend % divisor == 0:
            return int(devidend / divisor)
        else:
            return int(devidend / divisor) + 1

    def get_next_node(self, file_name, now_node):
        if not now_node.endswith('/'):
            now_node = now_node[:-len(now_node.split('.')[-1])-1] + '/'
        file_name_ = file_name[len(now_node):]
        tokens = file_name_.split('/')
        if len(tokens) > 1:
            return now_node + tokens[0] + '/'
        else:
            return now_node

    def init_statistic(self):
        self.statistic = {}
        for file in self.filelist_path:
            root_ = self.get_next_node(file, 'src/sources/')
            if root_ not in self.statistic:
                self.statistic[root_] = []
            self.statistic[root_].append(file)

    # 程序开始提取graph前，先执行合并节点，以减少节点规模
    def filter_file(self):
        self.paths_in_3rd = []       # 将全部的文件路径分为两部分，这里仅保存在3rd中的，
        self.paths_not_in_3rd = []
        for file in self.filelist_path:
            for dir in self._3rd_party_path:
                if file.startswith(dir):
                    self.paths_in_3rd.append(file)
                    break
        for file in self.filelist_path:
            if file not in self.paths_in_3rd:
                self.paths_not_in_3rd.append(file)
        #
        self.paths_not_in_3rd.sort()
        self.paths_in_3rd.sort()
        self.filelist_path.sort()
        self.separate = max(self.separate, int(self.division(len(self.paths_not_in_3rd) + len(self._3rd_party_path), MaxNodes)))
        self.separate = min(self.separate, int((len(self.paths_not_in_3rd) + len(self._3rd_party_path)) / ts_min))
        self.separate = max(self.separate, 1)
        # self.separate = 1

        # 初始化self.statistics，初始值没每个根目录下文件为一个node，若有
        self.init_statistic()
        while True:
            # print('----')
            # print(self.statistic.keys())
            next_node = self.find_next_split()
            # print(next_node)
            if not next_node.endswith('/'):
                break
            # print(next_node)
            # print(self.statistic.keys())
            # print(self.statistic[list(self.statistic.keys())[-1]])
            # print(next_node, len(self.statistic[next_node]), self.separate)
            # print('----------', len(list(self.statistic.keys())))
            # print('----------',len(list(self.statistic.keys())),self.statistic.keys())
            # 被分裂的节点是三方库节点，则确保当前数量不足ts_min，分裂后允许稍微超过ts_min
            if self.in_3rd(next_node):
                if len(self.statistic) >= ts_min:
                    break
            # 若被分裂节点已经只包含一个文件，则说明已经每个文件为一个节点了
            if len(self.statistic[next_node]) == 1:
                break
            # success为是否成功分裂，若分裂后数量超过MaxNodes，则会返回False，分裂结束
            success = self.split_node(next_node)
            # print('---', self.statistic.keys())
            # print(len(self.statistic))
            if not success:
                break
        self.transform_statistics()
        self.filelist_path = {}
        self.filelist = {}
        for key in self.statistic:
            for value in self.statistic[key]:
                self.filelist_path[value] = key
                self.filelist[self.transform2classname(value)] = key
        # 不会执行，若执行，则说明出现错误
        return True

    def transform_statistics(self):
        keys = list(self.statistic.keys())
        for key in keys:
            values = self.statistic[key]
            self.statistic.pop(key)
            self.statistic[self.transform2classname(key)] = values


    def find_next_split(self):
        max_node = list(self.statistic.keys())[0]
        for key in self.statistic:
            # 不能继续分裂的节点结尾为.数字，可分隔的节点结尾为/
            if key == max_node or not key.endswith('/'):
                continue
            # 首先判断是否有一方文件数已经为1，即无法再次分裂，若有，则分裂不为1的节点

            if (len(self.statistic[max_node]) <= 1 or len(self.statistic[key]) <= 1) and (len(self.statistic[max_node]) != len(self.statistic[key])):
                if len(self.statistic[max_node]) < len(self.statistic[key]):
                    max_node = key
                continue
            # 如果一方在三方库中，另一方不在，则分裂不在三方库中的
            elif self.in_3rd(max_node) != self.in_3rd(key):
                if self.in_3rd(max_node) == True:
                    max_node = key
                continue
            # 选择文件数量较多的分裂
            elif len(self.statistic[max_node]) != len(self.statistic[key]):
                if len(self.statistic[max_node]) < len(self.statistic[key]):
                    max_node = key
                continue
            # 选择标签数量较少的，即更顶级的进行分裂，后面的选择规则，只是为了保证每次运行时被分裂的都一样
            elif len(max_node.split('/')) != len(key.split('/')):
                if len(max_node.split('/')) > len(key.split('/')):
                    max_node = key
                continue
            # 选择标签更短的进行合并
            elif len(max_node) != len(key):
                if len(max_node) > len(key):
                    max_node = key
                continue
            # 选择音序靠前的分裂
            else:
                if max_node > key:
                    max_node = key
                continue
        return max_node

    # self.filelist_path是排好序的，故分裂后，每个node中的文件是有序的
    def split_node(self, node):
        next_nodes = {}
        # 先视作有文件夹来分裂
        for file_name in self.statistic[node]:
            root_ = self.get_next_node(file_name, node)
            # 若有文件查找下一级节点为自己，则下一级节点回node
            if root_ not in next_nodes:
                next_nodes[root_] = []
            next_nodes[root_].append(file_name)
        # print(next_nodes.keys())
        # 若所有文件都未被分开，则全部为java文件，按照每separate个分一组，以"node/序号"命名
        if len(next_nodes) == 1 and list(next_nodes.keys())[0] == node:
            next_nodes = {}
            if len(self.statistic[node]) == self.separate:
                separate = self.separate
            elif self.division(len(self.statistic[node]), MaxNodes + 1 -len(self.statistic)) > self.separate:
                separate = self.division(len(self.statistic[node]), MaxNodes + 1 -len(self.statistic))
            else:
                separate = self.separate
            # print(separate, len(self.statistic))
            for i in range(self.division(len(self.statistic[node]), separate)):
                next_nodes[node.strip('/') + '.' + str(i)] = self.statistic[node][i*separate: (i+1)*separate]
                # print(self.statistic[node][i*separate: (i+1)*separate])
            # raise Exception
        # print(next_nodes.keys())
        # 分裂后节点数量大于MaxNodes，则不分裂
        if len(next_nodes) + len(self.statistic) - 1 <= MaxNodes:
            if len(next_nodes) == 1 and node.startswith(list(next_nodes.keys())[0]):
                return False
            self.statistic.pop(node)
            for key in next_nodes:
                self.statistic[key] = next_nodes[key]
            if len(self.statistic) >= MaxNodes:
                return False
            return True
        else:
            return False

    def parse_package(self, packagepath):
        # print(packagepath)
        imports_return = set()
        tokens = []
        # if packagepath.endswith('/'):
        #     need_same_package = False
        #     print(packagepath)
        # else:
        #     need_same_package = True
        try:
            int(packagepath.split('.')[-1])
            need_same_package = True
        except:
            need_same_package = False

        for filepath in self.statistic[packagepath]:
            import_, tokens_ = self.parse_file(filepath, need_same_package=need_same_package)
            imports_return = imports_return | import_
            tokens += tokens_

        if len(tokens) > MaxToken:
            random.shuffle(tokens)
            tokens = tokens[:MaxToken]

        return imports_return, tokens

    def parse_file(self, filepath, need_same_package=True):
        imports_return = set()

        _class = self.transform2classname(filepath)
        fi = self.JavaZipFile.open(filepath)
        string, state = FileUtil.readFile(fi)
        # 提取当前文档的全部token,并保存到self.token_results
        testLexer = TestLexer(string)
        tokens = testLexer.analyse(include_ann=False)
        # if _class not in self.token_results:
        #     self.token_results[_class] = tokens
        # 获取java文件中全部import的文件
        _findImports = findImports(string)
        imports = _findImports.find_java_imports()
        for _import in imports:
            if _import.endswith('*'):
                for __file in self.filelist:
                    if _import[:-1].startswith(__file):
                        imports_return.add(__file)
                        break
                    elif __file.startswith(_import[:-1]):
                        imports_return.add(__file)
            else:
                if _import in self.filelist:
                    imports_return.add(_import)
        # 当前包内的调用通过单词匹配近似实现，首先获取import部分结束后的全部单词，与其他同package的java文件名进行匹配，匹配上则认为其调用了该java
        if need_same_package:
            idents = set(_findImports.get_idents_except_import())
            same_package_files = self.find_same_package(_class, self.filelist)
            for __file in same_package_files:
                # 文件名去掉.java视为public class的名称
                class_name = __file.split('.')[-1]
                if class_name in idents:
                    imports_return.add(__file)
                    # print(imports)
        # raise Exception
        # print(imports_return)
        return imports_return, tokens

    # 总入口
    def analyze(self):
        # 生成self.filelist_filter_path
        while True:
            status = self.filter_file()
            if status:
                break
        # print(self.filename, self.statistic)
        print(self.filename, 'node after merge:', len(self.statistic), 'file all:', len(self.filelist_path), 'not in 3rd:', len(self.paths_not_in_3rd), 'merge every:', self.separate)
        time_start = time.time()
        for key in self.statistic:
            imports_, tokens = self.parse_package(key)
            for import_ in imports_:
                value = self.filelist[import_]
                if value != key:
                    self.add2call_graph(key, value)
            self.token_results[key] = tokens
            time_now = time.time()
            if time_now - time_start > 40000:
                print(self.filename, 'time out!')
                break
        # print(len(self.token_results))
        count_edge = 0
        max = 0
        max_node = 0
        for key in self.call_graph:
            count_edge += len(self.call_graph[key])
            if len(self.call_graph[key]) > max:
                max = len(self.call_graph[key])
                max_node = key
        print(self.filename, 'node after merge:', len(self.filelist_path), 'file all:', len(self.filelist_path), 'edge count: ', count_edge, max, max_node)
        return self.call_graph, self.token_results

    def add_key(self, _file):
        if _file not in self.call_graph:
            self.call_graph[_file] = []

    def add2call_graph(self, _file, _import):
        # if _file == _import:
        #     return
        # else:
        self.add_key(_file)
        if _import not in self.call_graph[_file]:
            self.call_graph[_file].append(_import)
        # self.call_graph[_file].append(_import)

    def dump_call2file(self, filepath):
        string_out = json.dumps(self.call_graph)
        # print(string_out)
        fo = open(filepath, 'w+')
        fo.write(string_out)
        fo.close()

    # 过滤三方库节点的token
    def dump_call_token(self, filepath):
        string = json.dumps(self.token_results)
        fo = open(filepath, 'w+')
        fo.write(string)
        fo.close()

    def find_same_package(self, _file, _files):
        filename = _file.split('.')[-1]
        path = _file[:len(_file) - len(filename)]
        same_package_files = []
        for __file in _files:
            if __file.startswith(path) and __file != _file:
                same_package_files.append(__file)
        return same_package_files

    # 去掉文件开头的'src/sources/'，并替换/为.
    def transform2classname(self, file_path):
        if file_path.endswith('.java'):
            return file_path[12:-5].replace('/', '.')
        else:
            return file_path[12:].strip('/').replace('/', '.')

    # 判断是否在三方库中
    def in_3rd(self, _class):
        for __3rd_party in self._3rd_party_path:
            if _class.startswith(__3rd_party):
                return True
        return False


def get_java_graph_single(log_info, filename, java_zip_filepath, java_graph_file_filter, _3rd_party_file, token_file_path, min_k=1):
    # print(filename)
    # print(java_zip_filepath)
    # print(out_file)
    # 若三个输出文件均已存在，则不重新执行
    if not os.path.exists(java_graph_file_filter) or not os.path.exists(token_file_path):
        _java_graph = java_graph(filename, java_zip_filepath, _3rd_party_file, min_k=min_k)
        # eventlet.monkey_patch()
        _java_graph.analyze()
        # if not os.path.exists(java_graph_file):
        # print('----')
        _java_graph.dump_call2file(java_graph_file_filter)
        _java_graph.dump_call_token(token_file_path)
        # filter_3rd_single(call_graph, java_graph_file_filter, _3rd_party_file, token_results, token_file_path, filter_type=filter_type)

    print(log_info)


def get_cscg_dataset(dataset_name, java_zip_source_path, out_file_path, _3rd_party_root, token_file_root, min_k=1, total_process=8):
    print('Start extract java graph: ' + dataset_name)
    filelist = os.listdir(java_zip_source_path)
    pool = Pool(processes=total_process)
    for i in range(len(filelist)):
        if not filelist[i].endswith('.apk.zip'):
            continue
        java_zip_filepath = java_zip_source_path + filelist[i]
        if filelist[i].endswith('.apk.zip'):
            out_file_filter = out_file_path + 'filter-cscg-' + filelist[i][:-8]
            token_file_path = token_file_root + filelist[i][:-8] + '.tokenClassSet'
            _3rd_party_file = _3rd_party_root + filelist[i][:-8] + '.3rd'
        else:
            print('Only support ".apk.zip" file, not including ' + filelist[i] + '!')
            raise Exception
        log_info = 'Getting Java call graph: ' + java_zip_source_path + ', count: ' +str(i) + ', total: ' + str(len(filelist))
        pool.apply_async(get_java_graph_single, (log_info, filelist[i][:-4], java_zip_filepath, out_file_filter, _3rd_party_file, token_file_path, min_k))
        # get_java_graph_single(log_info, filelist[i][:-4], java_zip_filepath, out_file, out_file_filter, _3rd_party_file, token_file_path, filter_type, min_k)
    pool.close()
    pool.join()

