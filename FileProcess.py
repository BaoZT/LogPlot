
# -*- coding: utf-8 -*-

import sys
import re
import os
import math
import codecs
import re
from PyQt5.QtWidgets import QProgressBar
import numpy as np
import time

class FileProcess:
    # contructor
    def __init__(self, pbar=QProgressBar):
        self.s = np.array([])
        self.v_ato = np.array([])
        self.a = np.array([])
        self.cmdv = np.array([])
        self.level = np.array([])
        self.ceilv = np.array([])
        self.ramp = np.array([])
        self.statmachine = np.array([])
        self.stoperr = -32768
        self.targetstop = 0
        self.stoppos = 0
        self.skip = 0
        self.mtask = 0
        self.filename = ''
        self.pbar = pbar

    def keywordprocess(self, line_info):
        if -1 != line_info.find('@'):
            index_end = line_info.index('@')
            index_start = line_info.index('SC{')
            line_key = line_info[index_start + 3:index_end]  #split good part and sign 'SC{'
        else:
            index_start = line_info.index('SC{')
            line_key = line_info[index_start + 3:]           # split good part and sign 'SC{'
        ato_info = re.split(',| ', line_key)                 # 防护了异常但没有防护空
        try:
            s = int(ato_info[0])
            v = int(ato_info[1])
            cmdv = int(ato_info[2])
            ceilv = int(ato_info[3])
            level = int(ato_info[4])
            ramp  = int(ato_info[8])
            statmachine = int(ato_info[17])

            if int(ato_info[16]) != -32768:
                self.stoperr = int(ato_info[16])
                self.stoppos = int(ato_info[0])
                self.targetstop = int(ato_info[14][:-1])    #因为打印拆分后多一个 } 符号
                self.skip = int(ato_info[20][1:])           #因为打印前面多一个 p
                self.mtask  =int(ato_info[21])
            else:
                pass
            # 添加到队列
            self.s = np.append(self.s, s)
            self.v_ato = np.append(self.v_ato, v)
            self.cmdv = np.append(self.cmdv, cmdv)
            self.ceilv = np.append(self.ceilv, ceilv)
            self.level = np.append(self.level, level)
            self.statmachine = np.append(self.statmachine, statmachine)
            self.ramp = np.append(self.ramp, ramp)
            # 加速度计算处理
            if (len(self.s) > 1) and (len(self.v_ato) > 1):
                delta_s = self.s[len(self.s) - 1] - self.s[len(self.s) - 2]
                # 除零错误
                if delta_s != 0:
                    a = (pow(self.v_ato[len(self.v_ato) - 1], 2) - pow(self.v_ato[len(self.v_ato) - 2], 2))/(2*delta_s)
                    #有效性判断
                    if len(self.a) > 3:
                        if abs(a - self.a[-1]) > 100:       # 加速度突变
                            self.a = np.append(self.a, (self.a[-1] + self.a[-2])/2)
                        else:
                            self.a = np.append(self.a, a)
                    else:
                        self.a = np.append(self.a, a)
                else:
                    self.a = np.append(self.a, 0)
            else:
                self.a = np.append(self.a, 0)
        except Exception as err:
            print('transfer process error:')
            print(err)

    def readkeyword(self, file):
        log = open(file, 'r', encoding='ansi')           # notepad++默认是ANSI编码
        lines = log.readlines()
        cnt = 0
        bar = 0
        bar_cnt = int(len(lines) / 100)
        self.filename = file.split("/")[-1]
        for line in lines:
            # 进度条
            cnt = cnt + 1
            if int(cnt / bar_cnt) == 0:
                bar = bar + 1
                self.pbar.setValue(bar)
            else:
                pass
            try:
                if '@' in line:
                    if line.index('@') > 60:            # 取出前60个字节的内容
                        if 'SC' in line:
                            self.keywordprocess(line)
                        else:
                            pass
                else:
                    if 'SC{' in line:
                        self.keywordprocess(line)
                    else:
                        pass
            except Exception as err:
                print('read_file error:')
                print(err)

    def readkeyword_strategy(self, file):
        log = open(file, 'r', encoding='ansi')      # notepad++默认是ANSI编码
        for line in log.readlines():
            try:
                if 'v_permitted' in line:
                    if '@' in line:
                        if line.index('v_permitted') + 10 < line.index('@'):
                            self.keywordprocess(line)
                        else:
                            pass
                    else:
                        self.keywordprocess(line)
                else:
                    pass
            except Exception as err:
                print('read_file error:')
                print(err)
