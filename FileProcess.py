# -*- coding: utf-8 -*-
"""
文件处理模块，用于原始记录预处理和内容分解解析

本模块提供功能包括文件打开读取，根据预定义的周期类，按照时间周期分解记录生成周期字典，
并解析关键内容作为周期属性填入，特别地对于曲线绘制方面，使用正则表达式匹配出控车信息
矩阵，从而能够以统一的序列访问所有控车关键信息。

相关函数：
- create_cycle_dic(self): 创建周期字典
- match_log_packet_contect(self, c=CycleLog, line=str): 根据记录行解析数据包内容到周期
- match_log_basic_content(self, c=CycleLog, line=str): 根据记录行解析控车等基本信息到周期
- create_ctrl_cycle_list(self): 创建控车列表矩阵
- reset_vars(self): 重置所有列表

"""
import re
import sys
import threading
import time

import numpy as np
from PyQt5.QtWidgets import QProgressBar
from PyQt5 import QtCore

from TCMSParse import MVBParse

pat_ato_ctrl = ''
pat_ato_stat = ''
pat_tcms_stat = ''


# 周期类定义
class CycleLog(object):
    __slots__ = ['cycle_start_idx', 'cycle_end_idx', 'ostime_start', 'ostime_end', 'break_status', \
                'gfx_flag', 'control', 'fsm', 'time', 'cycle_num', 'cycle_sp_dict',\
                'raw_analysis_lines', 'stoppoint', 'io_in', 'io_out', 'file_begin_offset', \
                'file_end_offset',  'cycle_property']

    def __init__(self, ):  # 存储的是读取的内容
        # 周期文本索引号
        self.cycle_start_idx = 0
        self.cycle_end_idx = 0
        # 周期系统时间信息
        self.ostime_start = 0
        self.ostime_end = 0
        # 主断及分相说明
        self.break_status = 0
        self.gfx_flag = 0
        # 控制信息相关
        self.control = ()
        self.fsm = ()
        self.time = ''
        self.cycle_num = 0
        self.cycle_sp_dict = {}  # 数据包存储数据
        # 二次解析原始记录
        self.raw_analysis_lines = []
        # 停车点
        self.stoppoint = ()
        # IO信息
        self.io_in = ()
        self.io_out = ()
        # 当周期所有信息，使用File指针读取减少内存占用
        self.file_begin_offset = 0
        self.file_end_offset = 0
        # 周期属性
        self.cycle_property = 0  # 1=序列完整，2=序列尾部缺失


# 文件处理类定义
class FileProcess(threading.Thread, QtCore.QObject):
    bar_show_signal = QtCore.pyqtSignal(int)
    end_result_signal = QtCore.pyqtSignal(bool)
    __slots__ = ['daemon', 'mvbParser', 'cycle', 's', 'v_ato', 'a', 'cmdv', 'level', 'real_level', 'output_level',\
                'ceilv', 'atp_permit_v','statmachine', 'v_target', 'targetpos', 'stoppos', 'ma', 'ramp', 'adjramp',\
                'skip', 'mtask', 'platform', 'stoperr','stop_error', 'cycle_dic', 'cur_break_status', 'cur_gfx_flag', \
                'time_use', 'file_lines_count', 'file_path', 'filename']

    # constructors
    def __init__(self, file_path_in):
        # 线程处理
        super(QtCore.QObject, self).__init__()  ## 必须这样实例化？ 而不是父类？？？统一认识
        threading.Thread.__init__(self)
        self.daemon = True
        self.mvbParser = MVBParse()
        # 序列初始化
        self.cycle = np.array([], dtype=np.uint32)
        self.s = np.array([], dtype=np.uint32)
        self.v_ato = np.array([], dtype=np.int16)
        self.a = np.array([], dtype=np.float16)
        self.cmdv = np.array([], dtype=np.int16)
        self.level = np.array([], dtype=np.int8)
        self.real_level = np.array([], dtype=np.int8)
        self.output_level = np.array([], dtype=np.int8)
        self.ceilv = np.array([], dtype=np.int16)
        self.atp_permit_v = np.array([], dtype=np.int16)
        self.statmachine = np.array([], dtype=np.uint8)
        self.v_target = np.array([], dtype=np.int16)
        self.targetpos = np.array([], dtype=np.uint32)
        self.stoppos = np.array([], dtype=np.uint32)
        self.ma = np.array([], dtype=np.uint32)
        self.ramp = np.array([], dtype=np.int8)
        self.adjramp = np.array([], dtype=np.int8)  # 增加等效坡度
        self.skip = np.array([], dtype=np.uint8)
        self.mtask = np.array([], dtype=np.uint8)
        self.platform = np.array([], dtype=np.uint8)
        self.stoperr = -32768
        self.stop_error = []
        # 文件读取结果
        self.cycle_dic = {}
        # 主断及分相是保持的变化才变
        self.cur_break_status = 0
        self.cur_gfx_flag = 0
        # 读取耗时
        self.time_use = []
        # 文件总行数
        self.file_lines_count = 0
        # 文件名
        self.file_path = file_path_in
        self.filename = file_path_in.split("/")[-1]

    def run(self):
        try:
            iscycleok = 0
            islistok = 1
            isok = 2
            start = time.clock()
            iscycleok = self.readkeyword(self.file_path)
            print('Create cycle dic!')
            t1 = time.clock() - start
            start = time.clock()  # 更新计时起点
            islistok = self.create_ctrl_cycle_list()  # 解析周期内容
            print('Add and analysis dic content')
            t2 = time.clock() - start
            if iscycleok == 1:
                isok = islistok  # 当解析到周期时，返回实际解析结果, 2=无周期无结果，1=有周期无控车，0=有周期有控车
            elif iscycleok == 0:
                isok = 2  # 当没有周期
            else:
                isok = iscycleok  # 当出现重新启机时，返回启机行号
            self.time_use = [t1, t2, isok]
            # 发送结束信号
            self.end_result_signal.emit(True)
        except Exception as err:
            print('err in log process! ')
            self.Log(err, __name__, sys._getframe().f_lineno)
            self.end_result_signal.emit(True)

    def get_time_use(self):
        return self.time_use

    # 每次读取文件前都重置变量
    def reset_vars(self):
        self.cycle = np.array([], dtype=np.uint32)
        self.s = np.array([], dtype=np.uint32)
        self.v_ato = np.array([], dtype=np.int16)
        self.a = np.array([], dtype=np.float16)
        self.cmdv = np.array([], dtype=np.int16)
        self.level = np.array([], dtype=np.int8)
        self.real_level = np.array([], dtype=np.int8)
        self.output_level = np.array([], dtype=np.int8)
        self.ceilv = np.array([], dtype=np.int16)
        self.atp_permit_v = np.array([], dtype=np.int16)
        self.statmachine = np.array([], dtype=np.uint8)
        self.v_target = np.array([], dtype=np.int16)
        self.targetpos = np.array([], dtype=np.uint32)
        self.stoppos = np.array([], dtype=np.uint32)
        self.ma = np.array([], dtype=np.uint32)
        self.ramp = np.array([], dtype=np.int8)
        self.adjramp = np.array([], dtype=np.int8)  # 增加等效坡度
        self.skip = np.array([], dtype=np.uint8)
        self.mtask = np.array([], dtype=np.uint8)
        self.platform = np.array([], dtype=np.uint8)
        self.stoperr = -32768
        self.stop_error = []
        # 文件读取结果
        self.cycle_dic = {}
        # 主断及分相是保持的变化才变
        self.cur_break_status = 0
        self.cur_gfx_flag = 0
        # 读取耗时
        self.time_use = []
        # 文件总行数
        self.file_lines_count = 0

    # 输入： 文件路径
    def readkeyword(self, file_path):
        ret = 0            # 函数返回值，切割结果
        self.reset_vars()  # 重置所有变量
        with open(file_path, 'r', encoding='ansi', errors='ignore') as log:  # notepad++默认是ANSI编码,简洁且自带关闭
            self.file_lines_count = self.bufcount(log)  # 获取文件总行数
            print("Read line num %d"%self.file_lines_count)
            try:
                ret = self.create_cycle_dic_dync(log)
            except Exception as err:
                print(err)
        return ret

    # 获取文件行数
    @staticmethod
    def bufcount(f):
        lines = 0
        buf_size = 1024 * 1024
        read_f = f.read  # loop optimization
        buf = read_f(buf_size)
        while buf:
            lines += buf.count('\n')
            buf = read_f(buf_size)
        f.seek(0, 0)   # back to head
        return lines

    @staticmethod
    def dump(obj):
        """
        获取obj对象内所有的属性并打印
        :param obj: 对象
        :return: None
        """
        for attr in dir(obj):
            print("  obj.%s = %r" % (attr, getattr(obj, attr)))

    # <核心函数>
    # 使用自动迭代获取结果并记录周期偏移字节
    def create_cycle_dic_dync(self, f):
        """
        根据传入的文件句柄，动态解析信息记录周期的地址，用于打印查询
        注意：1. 函数能够检查获取完整的周期
             2. 函数能够检测并获取 头部缺失尾部存在 的残存单个周期, 按照尾标记周期
             3. 函数能够检测并获取 尾部缺失头部存在 的残存单个周期， 按照头部标记周期
             4. 对于连续连续出现的尾部缺失和头部缺失，导致周期合并的情况，逻辑上无法判断，全部丢弃
        :param f: 文件句柄
        :return: 周期分割结果
        """
        ret = 0
        content_search_state = 0   # 周期搜索状态，0=未知，1=搜索周期头，2=搜索周期尾
        restart_idx = 0   # 软件重启的行号
        restart_flag = 0  # 软件重启标志
        # 创建周期号模板
        pat_list = self.create_all_pattern()
        pat_extend_list = self.create_extend_pattern()
        pat_cycle_end = re.compile('---CORE_TARK CY_E (\d+),(\d+).')  # 周期起点匹配，括号匹配取出ostime和周期号，最后可以任意匹配
        pat_cycle_start = re.compile('---CORE_TARK CY_B (\d+),(\d+).')  # 周期终点匹配
        # 设置每次读取行数
        last_cycle_end_offset = f.tell()                # 初始化最近一次周期结束的指针偏移量
        # 计算进度条判断
        cnt = 0
        bar = 0
        bar_cnt = int(self.file_lines_count / 70)
        if bar_cnt == 0:
            self.bar_show_signal.emit(70)  # 文本很短，直接赋值进度条
            bar_flag = 0
        else:
            bar_flag = 1
        # 记录当前行的文件指针偏移量
        cur_line_head_offset = 0        # 定义初始文件索引
        cur_line_tail_offset = 0
        # 当前行号
        index = 0
        # 使用自动迭代器调用方法
        for line in f:
            # 计算行尾字节
            cur_line_tail_offset = cur_line_tail_offset + len(line.encode('ansi')) + 1 # 和读取采用的编码一致,
            # 调试发现，使用计算的字节，对于换行符'\n'每次虽然读取一个字节，但是f.tell(）获取的文件指针却会跳跃一个字节
            #  目前未知原因，为了适应该情况，每次读取单行计算后，将文件字节偏移量加+1来保持与tell()一致
            index = index + 1                                     # 计算当前行号，用于重启行号反馈
            # 如果有启机过程立即判断
            if '################' in line:            # 存在重启记录行号，用于后面判断是否需要手动分割
                restart_idx = index
                restart_flag = 1
            # 可计算的进度条
            if bar_flag == 1:
                cnt = cnt + 1
                if int(cnt % bar_cnt) == 0:
                    bar = bar + 1
                    self.bar_show_signal.emit(bar)
                else:
                    pass
            # 搜索周期
            s_r = pat_cycle_start.findall(line)
            e_r = pat_cycle_end.findall(line)
            # 检查是否周期头
            if s_r:
                s_r_list = list(s_r[0])                # 获取匹配的元组，转为列表
                # 检查状态机
                if content_search_state == 0 or content_search_state == 1:  # 未知或搜头状态下搜到周期头
                    c = CycleLog()
                    c.file_begin_offset = cur_line_head_offset   # 获取周期头文件偏移量
                    c.ostime_start = int(s_r_list[0])  # 格式0是系统时间
                    c.cycle_num = int(s_r_list[1])     # 格式1是周期号
                    content_search_state = 2           # 开始周期尾继续搜寻内容！
                else:                                  # 搜索周期尾时搜到周期头，结束上一周期
                    c.file_end_offset = cur_line_head_offset   # 残尾周期的结束偏移
                    c.ostime_end = 0                   # 0为特殊值，代表未搜索到
                    c.cycle_property = 2               # 设置该周期属性，尾部缺失
                    # 添加周期时检查唯一性，否则立即返回
                    if self.check_cycle_exist(c, restart_flag):    # 假如已存在ATO控制的
                        return restart_idx
                    else:
                        self.cycle_dic[c.cycle_num] = c
                    # 同时开始新周期的统计
                    c = CycleLog()
                    c.file_begin_offset = cur_line_head_offset   # 获取周期头文件偏移量
                    c.ostime_start = int(s_r_list[0])  # 格式0是系统时间
                    c.cycle_num = int(s_r_list[1])     # 格式1是周期号
                    content_search_state = 2           # 开始周期尾继续搜寻内容
            elif e_r:
                e_r_list = list(e_r[0])                # 获取匹配的元组，转为列表
                # 头部残缺情况，直接生成周期
                if content_search_state == 0 or content_search_state ==1:
                    c = CycleLog()
                    c.file_begin_offset = last_cycle_end_offset  # 获取上次或初始化的周期结束的文件偏移量
                    c.file_end_offset = cur_line_tail_offset     # 获取尾部文件偏移量
                    c.ostime_start = 0                           # 格式0是系统时间，0为特殊值，未知
                    c.cycle_num = int(e_r_list[1])               # 格式1是周期号
                    c.cycle_property = 3                         # 设置该周期属性，头部缺失
                    content_search_state = 1                     # 开始下一次周期头搜索工作
                else:                                            # 搜索周期尾时找到，状态机是2
                    if int(e_r_list[1]) == c.cycle_num:          # 找到匹配周期，s_r 和 e_r 每周期都更新可能空，要与记录值比较
                        c.file_end_offset = cur_line_tail_offset           # 获取周期结束偏移量
                        c.ostime_end = int(e_r_list[0])          # 找到完整周期
                        c.cycle_property = 1                     # 完整周期
                        content_search_state = 1                 # 置状态机为未知，重新搜索
                        # 添加周期到字典
                        if self.check_cycle_exist(c, restart_flag):
                            return restart_idx
                        else:
                            self.cycle_dic[c.cycle_num] = c
                    else:
                        content_search_state = 0                      # 置状态机为未知，重新搜索
                # 更新最近一次周期尾的偏移量
                last_cycle_end_offset = cur_line_tail_offset          # 当前周期偏移，下次首部丢失，获取周期内容用
            else:
                # 只有搜索尾部时解析，搜索头部属于周期间不处理
                if content_search_state == 2:
                    ret = 1                                       # 有周期!!!
                    result = self.match_log_packet_contect(c, line, pat_list, pat_extend_list)
                    if result == 0:                               # 每一行只能有一种结果，当无数据包，才继续
                        result = self.match_log_basic_content(c, line, pat_list, pat_extend_list)
                else:
                    pass                                          # 属于文件开始、结尾或重新统计残损周期，不记录丢弃
            # 更新下一行读取的记录起点
            cur_line_head_offset = cur_line_tail_offset
        return ret

    # 根据构建模板，对字符串分解后周期基本要素填充
    # <输入> line 待查找字符串
    # <输入> c    已经确定周期边界的周期对象，待填充内容
    # <输入> pat_list 模板列表
    # <输出> ret  解析1=成功，0=失败
    def match_log_basic_content(self, c=CycleLog, line=str, pat_list=list, pat_extend_list=list):
        # 北京时间
        ret = 1
        pat_time = pat_list[0]
        # ATO模式转换条件
        pat_fsm = pat_list[1]
        pat_sc = pat_list[2]
        pat_stop = pat_list[3]
        # 匹配查找
        if pat_time.findall(line):
            c.time = str(pat_time.findall(line)[0])
        elif pat_fsm.findall(line):
            c.fsm = pat_fsm.findall(line)[0]
        elif pat_stop.findall(line):
            c.stoppoint = pat_stop.findall(line)[0]
        elif pat_sc.findall(line):
            c.control = pat_sc.findall(line)[0]
        else:
            ret = 0
        return ret

    # <待完成>根据构建模板，对字符串分解后周期数据包进行填充
    # <输入> line 待查找字符串
    # <输入> c    已经确定周期边界的周期对象，待填充内容
    # <输入> pat_list 模板列表
    # <输出> ret  解析1=成功，0=失败
    def match_log_packet_contect(self, c=CycleLog, line=str, pat_list=list, pat_extend_list=list):
        ret = 1
        # 先无条件设置状态
        c.gfx_flag = self.cur_gfx_flag
        c.break_status = self.cur_break_status
        # 扩展表达式C2ATO
        pat_c2ato_p1 = pat_extend_list[0]
        # ATP->ATO 数据包
        pat_sp0 = pat_list[4]
        pat_sp1 = pat_list[5]
        pat_sp2 = pat_list[6]
        pat_sp5 = pat_list[7]
        pat_sp6 = pat_list[8]
        pat_sp7 = pat_list[9]

        pat_sp8 = pat_list[10]
        pat_sp9 = pat_list[11]
        # ATO->ATP 数据包
        pat_sp131 = pat_list[12]
        pat_sp130 = pat_list[13]
        pat_sp132 = pat_list[14]
        pat_sp134 = pat_list[15]
        # ATO->TSRS 数据包
        pat_c41 = pat_list[16]
        pat_c43 = pat_list[17]
        pat_c2 = pat_list[18]
        pat_p27 = pat_list[19]
        pat_p21 = pat_list[20]
        pat_c42 = pat_list[21]
        # TSRS->ATO
        pat_c44 = pat_list[22]
        pat_c45 = pat_list[23]
        pat_c46 = pat_list[24]
        # io info
        pat_io_in = pat_list[25]
        pat_io_out = pat_list[26]

        # 数据包识别,提高效率
        if '[P->O]' in line:
            # ATP->ATO数据包匹配过程
            if pat_sp0.findall(line):
                c.cycle_sp_dict[0] = pat_sp0.findall(line)[0]
            elif pat_sp1.findall(line):
                c.cycle_sp_dict[1] = pat_sp1.findall(line)[0]
            elif pat_sp2.findall(line):
                try:
                    l = re.split(',', line)
                    if len(tuple(l[1:])) == 26:  # 出去nid_packet一共是26个数字
                        c.cycle_sp_dict[2] = tuple(l[1:])  # 保持与其他格式一致，从SP2后截取
                        if int(c.cycle_sp_dict[2][13]) == 1:  # 去除nid——packet是第13个字节
                            c.gfx_flag = 1
                            self.cur_gfx_flag = 1
                        else:
                            c.gfx_flag = 0
                            self.cur_gfx_flag = 0
                except Exception as err:
                    print('gfx err')
                    self.Log(err, __name__, sys._getframe().f_lineno)
            # 兼容C2ATO内容
            elif pat_c2ato_p1.findall(line):
                c.cycle_sp_dict[1001] = pat_c2ato_p1.findall(line)[0]  # C2ATO数据包ID增加1000，用于区分高铁ATO数据包
                if int(c.cycle_sp_dict[1001][9]) == 1:  # 去除nid——packet是第13个字节
                    c.gfx_flag = 1
                    self.cur_gfx_flag = 1
                else:
                    c.gfx_flag = 0
                    self.cur_gfx_flag = 0
            elif pat_sp5.findall(line):
                c.cycle_sp_dict[5] = pat_sp5.findall(line)[0]
            elif pat_sp6.findall(line):
                c.cycle_sp_dict[6] = pat_sp6.findall(line)[0]
            elif pat_sp7.findall(line):
                c.cycle_sp_dict[7] = pat_sp7.findall(line)[0]
            elif pat_sp8.findall(line):
                c.cycle_sp_dict[8] = pat_sp8.findall(line)[0]
            elif pat_sp9.findall(line):
                c.cycle_sp_dict[9] = pat_sp9.findall(line)[0]
        # ATO-ATP/TSRS数据包匹配过程
        elif '[O->P]SP' in line:
            if pat_sp130.findall(line):
                c.cycle_sp_dict[130] = pat_sp130.findall(line)[0]
            elif pat_sp131.findall(line):
                c.cycle_sp_dict[131] = pat_sp131.findall(line)[0]
            elif pat_sp132.findall(line):
                c.cycle_sp_dict[132] = pat_sp132.findall(line)[0]
            elif pat_sp134.findall(line):
                c.cycle_sp_dict[134] = pat_sp134.findall(line)[0]
        elif '[T->A]C' in line or '[T->A]P' in line:
            if pat_c42.findall(line):
                c.cycle_sp_dict[42] = pat_c42.findall(line)[0]
            elif pat_c44.findall(line):
                c.cycle_sp_dict[44] = pat_c44.findall(line)[0]
            elif pat_p27.findall(line):
                c.cycle_sp_dict[27] = pat_p27.findall(line)[0]
            elif pat_p21.findall(line):
                c.cycle_sp_dict[21] = pat_p21.findall(line)[0]
            elif pat_c2.findall(line):
                c.cycle_sp_dict[202] = pat_c2.findall(line)[0]  # 重名包加200区分
            elif pat_c41.findall(line):
                c.cycle_sp_dict[41] = pat_c41.findall(line)[0]
        elif '[A->T]C' in line:
            if pat_c43.findall(line):
                c.cycle_sp_dict[43] = pat_c43.findall(line)[0]
            elif pat_c46.findall(line):
                c.cycle_sp_dict[46] = pat_c46.findall(line)[0]
            elif pat_c45.findall(line):
                c.cycle_sp_dict[45] = pat_c45.findall(line)[0]
        elif 'MVB[' in line:
            c.raw_analysis_lines.append(line)
        elif 'v&p' in line:
            c.raw_analysis_lines.append(line)
        elif '[RP' in line:
            c.raw_analysis_lines.append(line)
        elif '[DOOR]' in line or '[MSG]' in line:
            if pat_io_in.findall(line):
                c.io_in = pat_io_in.findall(line)[0]
            elif pat_io_out.findall(line):
                c.io_out = pat_io_out.findall(line)[0]
        else:
            ret = 0
        return ret

    # 创建C2ATO识别模板
    # <输出> 返回C2ATO模板
    @staticmethod
    def create_extend_pattern():
        pat_list = []
        pat_c2ato_p1 = re.compile('\[P->O\]P1:pmt\s?(-?\d),ldoorp(\d),\s?rdoorp(\d),tv(\d+),ts(\d+),s(\d+),v(\d+),'
                                  'pv(\d+),d_ma(\d+),\s?gfx_cmd(\d),gfx_s(\d+),m_low_frequency(\d+),'
                                  'atp_stop_err(-?\d+)')
        pat_list = [pat_c2ato_p1]

        return pat_list

    # 创建构建模板序列
    # <输出> 返回模板列表
    @staticmethod
    def create_all_pattern():
        pat_list = []
        # 北京时间
        pat_time = re.compile('time:(\d+-\d+-\d+ \d+:\d+:\d+)')
        # ATO模式转换条件
        pat_fsm = re.compile('FSM{(\d) (\d) (\d) (\d) (\d) (\d)}sg{(\d) (\d) (\d+) (\d+) (\w+) (\w+)}ss{(\d+) (\d)}')
        pat_sc = re.compile(
            'SC{(\d+) (\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (\d+) (\d+) (-?\d+) (-?\d+)}t (\d+) (\d+) (\d+)'
            ' (\d+),(\d+)} f (-?\d+) (\d+) (\d+) (-?\w+)} p(\d+) (\d+)}CC')
        pat_stop = re.compile('stoppoint:jd=(\d+) ref=(\d+) ma=(\d+)')

        # ATP->ATO 数据包
        pat_sp0 = re.compile('\[P->O\]SP0,')
        pat_sp1 = re.compile('\[P->O\]SP1,')
        pat_sp2 = re.compile('\[P->O\]SP2,')
        pat_sp5 = re.compile('\[P->O\]SP5,.*\s(\d),.*\s(\w+),.*\s(\w+),.*\s(-?\d+),.*\s(\d+),.*\s(\d+),.*\s(\d+),'
                             '.*\s(\d+),.*\s(\d+),.*\s(\d)')  # 因为有下划线所以不支持\w了
        pat_sp6 = re.compile('\[P->O\]SP6,')
        pat_sp7 = re.compile('\[P->O\]SP7,\w*?\s?(\d+),\w*?\s?(\d+),\w*?\s?(-?\d+),\w*?\s?(\d+),\w*?\s?(\d+),'
                             '\w*?\s?(\d+),\w*?\s?(\d+),\w*?\s?(\d+),\w*?\s?(\d+)')

        pat_sp8 = re.compile('\[P->O\]SP8,\w*?\s?(\d),\w*?\s?(\d+),\w*?\s?(\d),\w*?\s?(\w+),\w*?\s?(\w+),'
                             '\w*?\s?(\d), \w*?\s?(\d)')
        pat_sp9 = re.compile('\[P->O\]SP9,')
        # ATO->ATP 数据包
        pat_sp131 = re.compile(
            '\[O->P\]SP131:\w*?\s?(\d),\w*?\s?(\d),\w*?\s?(\d),\w*?\s?(-?\d+),\w*?\s?(\d),\w*?\s?(\d)'
            ',\w*?\s?(\d),\w*?\s?(\d)')  # 最后一个padding不判断
        pat_sp130 = re.compile('\[O->P\]SP130:\w*?\s?(\d),\w*?\s?(\d),\w*?\s?(-?\d+),\w*?\s?(\d),'
                               '\w*?\s?(\d)')
        pat_sp132 = re.compile('\[O->P\]SP132:')
        pat_sp134 = re.compile('\[O->P\]SP134:')
        # ATO->TSRS 数据包
        pat_c41 = re.compile('\[T->A\]C41')
        pat_c43 = re.compile('\[T->A\]C43')
        pat_c2 = re.compile('\[T->A\]C2')
        pat_p27 = re.compile('\[T->A\]P27')
        pat_p21 = re.compile('\[T->A\]P21')
        pat_c42 = re.compile('\[T->A\]C42')
        # TSRS->ATO
        pat_c44 = re.compile('\[A->T\]C44')
        pat_c45 = re.compile('\[A->T\]C45')
        pat_c46 = re.compile('\[A->T\]C46')

        # IO IN的信息
        pat_io_in = re.compile('\[DOOR\]IO_IN_(\w+)=(\d)')
        # 匹配多个表达式时，或符号|两边不能有空格！
        pat_io_out = re.compile("\[MSG\](OPEN\s[LR])|\[MSG\](CLOSE\s[LR])|\[MSG\](OPEN\sPSD[LR])|\[MSG\](CLOSE\sPSD[LR])")
        # sdu 信息
        p_ato_sdu = re.compile('v&p_ato:(\d+),(\d+)')
        p_atp_sdu = re.compile('v&p_atp:(-?\d+),(-?\d+)')

        # 添加列表
        pat_list = [pat_time, pat_fsm, pat_sc, pat_stop, pat_sp0, pat_sp1, pat_sp2, pat_sp5, pat_sp6, pat_sp7,
                    pat_sp8, pat_sp9, pat_sp131, pat_sp130, pat_sp132, pat_sp134, pat_c41, pat_c43, pat_c2,
                    pat_p27, pat_p21, pat_c42, pat_c44, pat_c45, pat_c46, pat_io_in, pat_io_out, p_ato_sdu, p_atp_sdu]

        return pat_list

    # 创建计划模板
    @staticmethod
    def creat_plan_pattern():
        # 计划解析RP1-RP4
        pat_rp1 = re.compile('\[RP1\](-?\d+),(\d+),(\d+),(\d+)')
        pat_rp2 = re.compile('\[RP2\](\d),(\d),(-?\d+),(\d)')
        pat_rp2_comm = re.compile('\[RP2-(\d+)\](\d+),(\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(\d),(\d)')
        pat_rp3 = re.compile('\[RP3\](\d),(\d),(-?\d+),(-?\d+),(\d)')
        pat_rp4 = re.compile('\[RP4\](\d),(-?\d+),(-?\d+),(\d),(\d)')

        return [pat_rp1, pat_rp2, pat_rp2_comm, pat_rp3, pat_rp4]

    # 计算相邻周期加速度变化
    # <输出> 返回加速度处理结果
    def comput_acc(self):
        cnt = 0
        bar = 81
        temp_delta_v = np.array([], np.int16)
        temp_delta_s = np.array([], np.uint32)
        # 计算分子分母
        temp_delta_v = 0.5 * (self.v_ato[1:] ** 2 - self.v_ato[:-1] ** 2)
        temp_delta_s = self.s[1:] - self.s[:-1]
        # 进度条
        bar_cnt = int(len(temp_delta_s) / 4)
        if bar_cnt == 0:
            self.bar_show_signal.emit(85)  # 文本很短，直接赋值进度条
            bar_flag = 0
        else:
            bar_flag = 1
        # 加速度计算处理
        for idx, item in enumerate(temp_delta_s):
            # 进度条计算
            if bar_flag == 1:
                cnt = cnt + 1
                if int(cnt % bar_cnt) == 0:
                    bar = bar + 1
                    self.bar_show_signal.emit(bar)
                else:
                    pass
            # 主逻辑
            if item == 0:
                yield 0
            else:
                yield temp_delta_v[idx] / item
        # 由于是差值计算，最后补充一个元素
        yield 0

    # 计算ATP允许速度序列，只能从SP2包中获取
    # <输出> 返回ATP允许处理结果
    def get_atp_permit_v(self):
        c_num = 0
        first_find_pmv_flag = False
        last_atp_pmv = 0    # 初始化最近的一次ATP允许速度
        c_num_end = 0
        cnt = 0
        bar = 85
        # 进度条
        bar_cnt = int(len(self.cycle_dic.keys()) / 10)
        if bar_cnt == 0:
            self.bar_show_signal.emit(95)  # 文本很短，直接赋值进度条
            bar_flag = 0
        else:
            bar_flag = 1
        # 遍历周期
        if len(self.cycle_dic.keys()) != 0:
            try:
                for ctrl_item in self.cycle_dic.keys():
                    # 进度条计算
                    if bar_flag == 1:
                        cnt = cnt + 1
                        if int(cnt % bar_cnt) == 0:
                            bar = bar + 1
                            self.bar_show_signal.emit(bar)
                        else:
                            pass
                    # ATP允许速度计算
                    if self.cycle_dic[ctrl_item].control:  # 如果该周期中有控车信息
                        c_num = self.cycle_dic[ctrl_item].cycle_num  # 获取周期号
                        # 如果有数据包
                        if 2 in self.cycle_dic[ctrl_item].cycle_sp_dict.keys():
                            last_atp_pmv = int(self.cycle_dic[ctrl_item].cycle_sp_dict[2][11])
                            first_find_pmv_flag = True
                        elif 1001 in self.cycle_dic[ctrl_item].cycle_sp_dict.keys():
                            last_atp_pmv = int(self.cycle_dic[ctrl_item].cycle_sp_dict[1001][7])    # 添加C2ATO
                            first_find_pmv_flag = True
                        else:
                            # 上来就控车时就没有允许速度，首次获取，当周期无SP2
                            if not first_find_pmv_flag:
                                # 首先尝试寻找向前取20个周期,且字典存在,检查最远边界
                                if c_num > 20 and ((c_num - 20) in self.cycle_dic.keys()):
                                    c_num_end = c_num - 20
                                    # 遍历周期
                                    for c in range(c_num, c_num_end, -1):    # 逆序寻找，找最近的
                                        # 首先检测是否存在该周期，可能出现丢周期的情况，检查每个周期
                                        if c in self.cycle_dic.keys():
                                            # 如果有数据包
                                            if 2 in self.cycle_dic[c].cycle_sp_dict.keys():
                                                last_atp_pmv = int(self.cycle_dic[c].cycle_sp_dict[2][11].strip())  # 非首次投入ATO周期，无SP2包
                                                first_find_pmv_flag = True
                                                print('ato cycle no sp2, find before aom!')
                                                break
                                            else:
                                                pass
                                            if 1001 in self.cycle_dic[c].cycle_sp_dict.keys():
                                                last_atp_pmv = int(self.cycle_dic[c].cycle_sp_dict[1001][7].strip())  # 非首次投入ATO周期，无SP2包
                                                first_find_pmv_flag = True
                                                print('ato cycle no sp2, find before aom!')
                                                break
                                            else:
                                                pass
                                        else:   # 若某个周期不存在，直接跳过
                                            pass
                                else:
                                    first_find_pmv_flag = True    # 最近的20周期找不到不再寻找，际上是添加0，就是初始值作为允许速度的特殊值
                            else:
                                pass     # 本周期没找到，使用最近一次的记过
                        # 只要有控车就增加一个数值
                        yield last_atp_pmv
                    else:
                        pass
            except Exception as err:
                print(err)
        else:
            print('no ato ctrl,no atp permit v')
        # print('get atp permit v ok %d, %d'%(len(self.v_ato),len(self.atp_permit_v)))

    # <核心函数>
    # 建立ATO控制信息和周期的关系字典
    def create_ctrl_cycle_list(self):
        ret = 2  # 用于标记创建结果,2=无周期无结果，1=有周期无控车，0=有周期有控车
        cnt = 0
        bar = 70
        bar_flag = 0
        bar_cnt = int(len(self.cycle_dic.keys()) / 10)
        if bar_cnt == 0:
            self.bar_show_signal.emit(80)
            bar_flag = 0
        else:
            bar_flag = 1
        # 遍历周期
        if len(self.cycle_dic.keys()) != 0:
            for ctrl_item in self.cycle_dic.keys():
                if self.cycle_dic[ctrl_item].control:  # 如果该周期中有控车信息
                    self.cycle = np.append(self.cycle, self.cycle_dic[ctrl_item].cycle_num)  # 获取周期号
                else:
                    pass
                # 对外显示进度
                if bar_flag == 1:
                    cnt = cnt + 1
                    if int(cnt % bar_cnt) == 0:
                        bar = bar + 1
                        self.bar_show_signal.emit(bar)
                    else:
                        pass
            ret = 1  # 有周期，不一定有控车
        else:
            ret = 2
        # 如果没有周期则不执行
        if ret != 2:
            # 如果进入过AOR或者AOM
            if len(self.cycle) > 0:  # self.cycle是一个迭代器，不能和[]进行比较
                # 生成控制矩阵
                l = len(list(self.cycle_dic[self.cycle[0]].control))  # 不妨用第一个计算控制队列数量
                mat = np.zeros((len(self.cycle), l))
                # 计算矩阵
                for idx in range(len(self.cycle)):
                    temp = list(self.cycle_dic[self.cycle[idx]].control)  # 按周期索引取控制信息，妨不连续
                    temp_A = temp[:-3]
                    temp_B = temp[-2:]
                    # 复制信息
                    mat[idx, :-3] = temp_A[:]
                    mat[idx, -2:] = temp_B[:]
                # 切割控制信息
                self.s = mat[:, 0]
                self.v_ato = mat[:, 1]
                self.cmdv = mat[:, 2]
                self.ceilv = mat[:, 3]
                self.real_level = mat[:, 4]
                self.level = mat[:, 5]
                self.output_level = mat[:, 5]
                self.ramp = mat[:, 8]
                self.adjramp = mat[:, 9]
                self.statmachine = mat[:, 16]
                # 增加位置信息
                self.v_target = mat[:, 10]
                self.targetpos = mat[:, 11]
                self.ma = mat[:, 12]
                self.stoppos = mat[:, 14]
                self.platform = mat[:, 17]        # 目前使用fsm中的信息，SC中的站台标志先不用，不处理
                # 停车误差
                self.stop_error = mat[:, 15]
                # 通过办客
                self.skip = mat[:, 19]
                self.mtask = mat[:, 20]
                print('Slip Ctrl Matrix')
                self.bar_show_signal.emit(81)
                # 计算加速度
                self.a = np.array(list(self.comput_acc()), dtype=np.float16)
                print('Comput Train Acc')
                # 获取ATP允许速度序列
                print('Comput ATP Permit V')
                self.atp_permit_v = np.array(list(self.get_atp_permit_v()), dtype=np.int16)
                ret = 0
            else:
                ret = 1
        return ret

    # 检查是否该周期已经存在,且有控车，异常，需手动分解。
    # <输出> 0=不存在，1=存在
    def check_cycle_exist(self, c=CycleLog, restart=int):
        ret = 0
        if restart == 1:  # 已经重启过且重启前后都有控车信息
            if c.cycle_num in self.cycle_dic.keys() and self.cycle_dic[c.cycle_num].control:
                ret = 1
        return ret

    # 解析MVB数据
    # 返回解析结果 0=无，1=更新
    def mvb_research(self, c=CycleLog, line=str):
        global pat_ato_ctrl
        global pat_ato_stat
        global pat_tcms_stat
        real_idx = 0  # 对于记录打印到同一行的情况，首先要获取实际索引
        tmp = ''
        parse_flag = 0
        try:
            if pat_ato_ctrl in line:
                if '@' in line:
                    pass
                else:
                    real_idx = line.find('MVB[')
                    tmp = line[real_idx + 10:]  # 还有一个冒号需要截掉
                    c.ato2tcms_ctrl = self.mvbParser.ato_tcms_parse(1025, tmp)  # 这里仅仅适配解析模块，端口号抽象
                    parse_flag = 1
            elif pat_ato_stat in line:
                if '@' in line:
                    pass
                else:
                    real_idx = line.find('MVB[')
                    tmp = line[real_idx + 10:]  # 还有一个冒号需要截掉
                    c.ato2tcms_stat = self.mvbParser.ato_tcms_parse(1041, tmp)
                    parse_flag = 1
            elif pat_tcms_stat in line:
                if '@' in line:
                    pass
                else:
                    real_idx = line.find('MVB[')
                    tmp = line[real_idx + 10:]  # 还有一个冒号需要截掉
                    c.tcms2ato_stat = self.mvbParser.ato_tcms_parse(1032, tmp)
                    if c.tcms2ato_stat != []:
                        if c.tcms2ato_stat[14] == 'AA':
                            self.cur_break_status = 0
                            c.break_status = 0  # 闭合
                        elif c.tcms2ato_stat[14] == '00':
                            self.cur_break_status = 1
                            c.break_status = 1  # 主断路器断开
                    parse_flag = 1
        except Exception as err:
            self.Log(err, __name__, sys._getframe().f_lineno)
        return parse_flag

    # 找出当前行所在的周期，针对单次搜索
    # 输入： 行索引
    # 返回： 该行所在周期[起始索引，终点索引，周期号]
    def find_cycle_border(self, index):
        begin_idx = index
        end_idx = index
        cycle_start = -1
        cycle_end = -2
        cycle_num = -1
        # 文件开始位置
        while begin_idx > 0:
            if '---CORE_TARK CY_B' in self.lines[begin_idx]:
                try:
                    raw_start = self.lines[begin_idx].split(',')  # 分隔系统时间和周期号,如果打印残缺就会合并周期
                    cycle_start = int(raw_start[1].split('----')[0])
                    break
                except Exception as err:
                    self.Log(err, __name__, sys._getframe().f_lineno)
            else:
                begin_idx = begin_idx - 1
        # 文件结束位置
        while end_idx < len(self.lines) - 1:
            if '---CORE_TARK CY_E' in self.lines[end_idx]:  # 分隔周期结束的时间和周期号
                try:
                    raw_end = self.lines[end_idx].split(',')
                    cycle_end = int(raw_end[1].split('---')[0])
                    break
                except Exception as err:
                    self.Log(err, __name__, sys._getframe().f_lineno)
            else:
                end_idx = end_idx + 1
        # 边界是否只包含一个周期
        if cycle_end != -2 and cycle_start != -1:
            # 周期号一致
            if cycle_start == cycle_end:  # 搜索成功周期
                cycle_num = cycle_start
            else:
                if abs(cycle_end - index) < abs(index - cycle_start):  # 更接近end周期号
                    cycle_num = cycle_end
                else:
                    cycle_num = cycle_start
        elif cycle_end == -2 and cycle_start != -1:  # 记录末尾，搜到头，没有搜索到结尾
            end_idx = -1
        elif cycle_end != -2 and cycle_start == -1:  # 记录开始，搜到尾，没有搜到头
            begin_idx = -1
        else:
            begin_idx = -1  # 头尾都找不到，空记录
            end_idx = -1
        return begin_idx, end_idx, cycle_num

    # 打印函数
    def Log(self, msg=str, fun=str, lino=int):
        if str == type(msg):
            print(msg + ',File:"' + __file__ + '",Line' + str(lino) +
                  ', in' + fun)
        else:
            print(msg)
