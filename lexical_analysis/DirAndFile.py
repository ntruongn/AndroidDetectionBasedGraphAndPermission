# coding=utf-8
import os
import zipfile
import random
from .load_3rd_party import load_3rd_lib
from .TestLexer import TestLexer
from .FileUtil import FileUtil
import xml.etree.ElementTree as etree
import sys
sys.path.append('..')
from config import MaxToken, MainDirMaxToken


class DirAndFile:
    mainDir = ''
    ThirdPartyResultPath = ''   # 一个数据集中所有样本第三方库存放路径
    JavaResultPath = ''     # 一个数据集中所有样本的java源码压缩包zip存放路径
    ManifestPath = ''       # 一个数据集中所有样本的manifest存放路径
    Filename = ''           # 要解析的apk文件文件名
    outFilePath = ''
    packageList = []        # 之后不需要遍历的文件夹
    tokenResult = []
    JavaZipFile = None

    def __init__(self, ThirdPartyResultPath, JavaResultPath, ManifestPath, Filename, outFilepath):
        # 传入的3个路径包含末尾的'/'
        self.__init_para()
        self.ThirdPartyResultPath = ThirdPartyResultPath
        self.JavaResultPath = JavaResultPath
        self.ManifestPath = ManifestPath
        self.Filename = Filename
        self.outFile = outFilepath + self.Filename + '.tokenResult'
        self.load_3rd()
        self.extractMainDir()
        try:
            self.JavaZipFile = zipfile.ZipFile(JavaResultPath + Filename + '.zip', 'r')
            # self.load_virus_3rd()
        except Exception as e:
            print(e)

    def __init_para(self):
        self.mainDir = ''
        self.ThirdPartyResultPath = ''  # 一个数据集中所有样本第三方库存放路径
        self.JavaResultPath = ''  # 一个数据集中所有样本的java源码压缩包zip存放路径
        self.ManifestPath = ''  # 一个数据集中所有样本的manifest存放路径
        self.Filename = ''  # 要解析的apk文件文件名
        self.outFilePath = ''
        self.packageList = []  # 之后不需要遍历的文件夹
        self.tokenResult = []
        self.JavaZipFile = None

    def load_3rd(self):
        if self.Filename.endswith('.apk'):
            _Filename = self.Filename[:-4]
        else:
            _Filename = self.Filename   # 不应该执行
        _3rd_file_name = self.ThirdPartyResultPath + _Filename + '.3rd'
        if os.path.exists(_3rd_file_name):
            self.packageList += load_3rd_lib(_3rd_file_name)
        else:
            print('No such file: ' + _3rd_file_name)

    # def load_virus_3rd(self, filename='Apkpure_VirusShare.3rd.txt'):
    #     packages = set()
    #     for path in self.JavaZipFile.namelist():
    #         if path.endswith('/'):
    #             packages.add(path)
    #     fi = open(filename, 'r')
    #     for line in fi.readlines():
    #         lib = 'src/sources/' + line.strip()
    #         if lib in packages:
    #             self.packageList.append(lib)

    def extractMainDir(self):
        manifest_file = self.ManifestPath + self.Filename + '/AndroidManifest.xml'
        package = ''
        if os.path.exists(manifest_file):
            try:
                print(manifest_file)
                tree = etree.ElementTree(file=manifest_file)
                root = tree.getroot()
                package = 'src/sources/' + root.attrib['package'].replace('.', '/')
            except Exception as e:
                print("Error occurred: " + manifest_file + '\t' + str(e))
        else:
            print('No such file: ' + manifest_file)

        self.mainDir = package

    # 获取zip文件中, rootPath不可以为空
    def getChildFiles(self, rootPath):
        filelist = []
        for filepath in self.JavaZipFile.namelist():
            if filepath.endswith('/'):
                continue
            elif filepath.startswith(rootPath):
                filelist.append(filepath)
        return filelist

    # 获取除packageList以外全部文件
    def getAllExceptPackageList(self, count_now):
        filelist = []
        for filepath in self.JavaZipFile.namelist():
            if filepath.endswith('/'):
                continue
            found = False
            for package in self.packageList:
                if filepath.startswith(package):
                    found = True
                    break
            if not found:
                filelist.append(filepath)
        # # 如果出掉3rd库后，java文件太少情况下，用于补充部分3rd库进行特征提取
        # for filepath in self.JavaZipFile.namelist():
        #     if len(filelist) + count_now >= 100:
        #         break
        #     if filepath.endswith('/'):
        #         continue
        #     for package in self.packageList:
        #         if package == self.mainDir:
        #             continue
        #         if filepath.startswith(package):
        #             filelist.append(filepath)
        #             break
        return filelist

    # 获取zip中全部文件
    def getAllExceptMainDir(self):
        filelist = []
        for filepath in self.JavaZipFile.namelist():
            if filepath.endswith('/'):
                continue
            filelist.append(filepath)
        return filelist

    # 提取文件夹中的全部token，参数为是否进行筛选
    def extractToken(self, ifRandomSample = True):
        count = 0
        # 先解析主入口下的全部java文件
        if not self.mainDir == '':
            for filepath in self.getChildFiles(self.mainDir):
                string, success = FileUtil.readFile(self.JavaZipFile.open(filepath))

                testLexer = TestLexer(string)
                self.tokenResult += testLexer.analyse()
                count += 1
        # if len(self.tokenResult) >= MainDirMaxToken:
        #     self.tokenResult = self.tokenResult[:MainDirMaxToken]
        # 将主入口目录加入排除列表
        self.packageList.append(self.mainDir)
        # 解析不在packageList里的文件
        for filepath in self.getAllExceptPackageList(count):
            string, success = FileUtil.readFile(self.JavaZipFile.open(filepath))
            testLexer = TestLexer(string)
            self.tokenResult += testLexer.analyse()
            count += 1
        if ifRandomSample and len(self.tokenResult) > MaxToken:        # token太多则进行随机筛选
            random.shuffle(self.tokenResult)
            self.tokenResult = self.tokenResult[:MaxToken]
        return count

    # 提取包含第三方库在内的全部java文件
    def extractTokenAll(self):
        # 先解析主入口下的全部java文件
        if not self.mainDir == '':
            for filepath in self.getChildFiles(self.mainDir):
                string, success = FileUtil.readFile(self.JavaZipFile.open(filepath))
                testLexer = TestLexer(string)
                self.tokenResult += testLexer.analyse()
        # if len(self.tokenResult) >= MainDirMaxToken:
        #     self.tokenResult = self.tokenResult[:MainDirMaxToken]
        # 解析不在packageList里的文件
        for filepath in self.getAllExceptMainDir():
            string, success = FileUtil.readFile(self.JavaZipFile.open(filepath))
            testLexer = TestLexer(string)
            self.tokenResult += testLexer.analyse()
        if len(self.tokenResult) > MaxToken:        # token太多则进行随机筛选
            random.shuffle(self.tokenResult)
            self.tokenResult = self.tokenResult[:MaxToken]

    def writeResult(self):
        try:
            fo = open(self.outFile, 'w+')
            for token in self.tokenResult:
                fo.write(token + ' ')
            fo.write('\n')
        except Exception as e:
            print('Save to file error: ' + self.outFile + '\t' + e)
        fo.close()
        self.JavaZipFile.close()

