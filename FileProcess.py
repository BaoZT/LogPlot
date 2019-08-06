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
from PyQt5.QtWidgets import QProgressBar
from PyQt5 import QtCore
from ProtocolParse import MVBParse
import numpy as np
import threading
import time

pat_ato_ctrl = ''
pat_ato_stat = ''
pat_tcms_stat = ''


# 周期类定义
class CycleLog(object):
    def __init__(self):      # 存储的是读取的内容
        # 周期文本索引号
        self.cycle_start_idx = 0
        self.cycle_end_idx = 0
        # 周期系统时间信息
        self.ostime_start = 0
        self.ostime_end = 0
        self.duringtime = 0
        # 主断及分相说明
        self.break_status = 0
        self.gfx_flag = 0
        # mvb消息解析
        self.ato2tcms_stat = []
        self.ato2tcms_ctrl = []
        self.tcms2ato_stat = []
        # 控制信息相关
        self.control = ()
        self.fsm = ()
        self.time = ''
        self.cycle_num = 0
        self.cycle_all_info = []    # 存储当周期所有信息，二次处理
        self.cycle_sp_dict = {}     # 存储每个
        # 周期属性
        self.cycle_property = 0     # 1=序列完整，2=序列尾部缺失
        # 停车点
        self.stoppoint = []
        # IO信息
        self.io_in = ()
        self.io_out = []


# 文件处理类定义
class FileProcess(threading.Thread):
    # contructor
    def __init__(self, pbar=QProgressBar):
        # 线程处理
        threading.Thread.__init__(self)
        self.daemon = True
        self.mvbParser = MVBParse()
        # 序列初始化
        self.cycle = np.array([])
        self.s = np.array([])
        self.v_ato = np.array([])
        self.a = np.array([])
        self.cmdv = np.array([])
        self.level = np.array([])
        self.real_level = np.array([])
        self.output_level = np.array([])
        self.ceilv = np.array([])
        self.atp_permit_v = np.array([])
        self.statmachine = np.array([])
        self.v_target = np.array([])
        self.targetpos = np.array([])
        self.stoppos = np.array([])
        self.ma = np.array([])
        self.ramp = np.array([])
        self.adjramp = np.array([])     # 增加等效坡度
        self.skip = np.array([])
        self.mtask = np.array([])
        self.platform = np.array([])
        self.stoperr = -32768
        self.stop_error = []
        self.filename = ''
        self.pbar = pbar
        # 文件读取结果
        self.lines = []
        self.cycle_dic = {}
        # 主断及分相是保持的变化才变
        self.break_status = 0
        self.gfx_flag = 0
        # 读取耗时
        self.time_use = []

    def run(self):
        try:
            iscycleok = 0
            islistok = 1
            isok = 2
            start = time.clock()
            iscycleok = self.create_cycle_dic()                         # 创建了周期字典
            print('Create cycle dic!')
            t1 = time.clock() - start
            start = time.clock()                                        # 更新计时起点
            islistok = self.create_ctrl_cycle_list()                    # 解析周期内容
            print('Add and analysis dic content')
            t2 = time.clock() - start
            if iscycleok == 1:
                isok = islistok                # 当解析到周期时，返回实际解析结果, 2=无周期无结果，1=有周期无控车，0=有周期有控车
            elif iscycleok == 0:
                isok = 2                       # 当没有周期
            else:
                isok = iscycleok               # 当出现重新启机时，返回启机行号
            self.time_use = [t1, t2, isok]
        except Exception as err:
            print(err)
            print('err in log process!')

    def get_time_use(self):
        return self.time_use

    # 每次读取文件前都重置变量
    def reset_vars(self):
        self.cycle = np.array([])
        self.s = np.array([])
        self.v_ato = np.array([])
        self.a = np.array([])
        self.cmdv = np.array([])
        self.level = np.array([])
        self.real_level = np.array([])
        self.output_level = np.array([])
        self.ceilv = np.array([])
        self.atp_permit_v = np.array([])
        self.statmachine = np.array([])
        self.v_target = np.array([])
        self.targetpos = np.array([])
        self.stoppos = np.array([])
        self.ma = np.array([])
        self.ramp = np.array([])
        self.adjramp = np.array([])
        self.skip = np.array([])
        self.mtask = np.array([])
        self.platform = np.array([])
        self.stoperr = -32768
        self.stop_error = []
        # 文件读取结果
        self.filename = ''
        self.lines = []
        self.cycle_dic = {}
        # 主断及分相是保持的变化才变
        self.break_status = 0
        self.gfx_flag = 0
        # 读取耗时
        self.time_use = []
        # 文件读取结果
        self.lines = []
        self.cycle_dic = {}
        # 重置进度条

    # 输入： 文件路径
    def readkeyword(self, file):
        self.reset_vars()  # 重置所有变量
        with open(file, 'r', encoding='utf-8',errors='ignore') as log:    # notepad++默认是ANSI编码,简洁且自带关闭
            self.lines = log.readlines()
            self.filename = file.split("/")[-1]
        log.close()                                      # 关闭文件

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
                    raw_start = self.lines[begin_idx].split(',')   # 分隔系统时间和周期号,如果打印残缺就会合并周期
                    cycle_start = int(raw_start[1].split('----')[0])
                    break
                except Exception as err:
                    print(err)
            else:
                begin_idx = begin_idx - 1
        # 文件结束位置
        while end_idx < len(self.lines)-1:
            if '---CORE_TARK CY_E' in self.lines[end_idx]:      # 分隔周期结束的时间和周期号
                try:
                    raw_end = self.lines[end_idx].split(',')
                    cycle_end = int(raw_end[1].split('---')[0])
                    break
                except Exception as err:
                    print(err)
            else:
                end_idx = end_idx + 1
        # 边界是否只包含一个周期
        if cycle_end != -2 and cycle_start != -1:
            # 周期号一致
            if cycle_start == cycle_end:     # 搜索成功周期
                cycle_num = cycle_start
            else:
                if abs(cycle_end-index) < abs(index-cycle_start):  # 更接近end周期号
                    cycle_num = cycle_end
                else:
                    cycle_num = cycle_start
        elif cycle_end == -2 and cycle_start != -1:  # 记录末尾，搜到头，没有搜索到结尾
            end_idx = -1
        elif cycle_end != -2 and cycle_start == -1:  # 记录开始，搜到尾，没有搜到头
            begin_idx = -1
        else:
            begin_idx = -1                           # 头尾都找不到，空记录
            end_idx = -1
        return begin_idx, end_idx, cycle_num

    # <核心函数>
    # 搜索文本划分所有的周期，生成周期字典
    def create_cycle_dic(self):
        restart_idx = 0
        restart_flag = 0
        ret = 0
        # 创建周期号模板
        patlist = self.create_all_pattern()
        pat_cycle_end = re.compile('---CORE_TARK CY_E (\d+),(\d+).')  # 周期起点匹配，括号匹配取出ostime和周期号，最后可以任意匹配
        pat_cycle_start = re.compile('---CORE_TARK CY_B (\d+),(\d+).')# 周期终点匹配
        bar_flag = 0
        content_flag = 0
        # 计算进度条判断
        cnt = 0
        bar = 0
        bar_cnt = int(len(self.lines) / 50)
        if bar_cnt == 0:
            self.pbar.setValue(50)     # 文本很短，直接赋值进度条
            bar_flag = 0
        else:
            bar_flag = 1
        # 开始遍历
        length = len(self.lines)
        for index, line in enumerate(self.lines):
            # 如果有启机过程立即判断
            if '############' in line:        # 非0情况下说明有重新启机，返回行号
                restart_idx = index
                restart_flag = 1
            # 进度条计算
            if bar_flag == 1:
                cnt = cnt + 1
                if int(cnt % bar_cnt) == 0:
                    bar = bar + 1
                    self.pbar.setValue(bar)
                else:
                    pass
            # 搜索周期
            s_r = pat_cycle_start.findall(line)
            e_r = pat_cycle_end.findall(line)
            if (s_r != []) or (e_r != []):              # 是周期边界
                # 找到周期开始
                if s_r != []:
                    s_r_list = list(s_r[0])
                    # 未搜索到周期终点时找到起点
                    if content_flag == 1:                       # 如果之前已经置1但没有置回，没有找到周期结尾，下周期开始
                        c.cycle_end_idx = index - 1             # 强制结束上个周期
                        c.ostime_end = 0                        # 0代表未搜索到
                        c.cycle_all_info = self.lines[c.cycle_start_idx: c.cycle_end_idx]
                        c.cycle_property = 2                    # 未找到终点
                        # 添加周期到字典
                        if self.check_cycle_exist(c, restart_flag):
                            return restart_idx
                        else:
                            self.cycle_dic[c.cycle_num] = c
                        content_flag = 0                        # 结束一个周期的统计
                        # 同时开始新周期的统计
                        c = CycleLog()
                        c.cycle_start_idx = index
                        c.ostime_start = int(s_r_list[0])       # 格式0是系统时间
                        c.cycle_num = int(s_r_list[1])          # 格式1是周期号
                        content_flag = 1                        # 开始本周期的搜寻内容
                    else:
                        # 创建一个周期对象，从记录第一个完整周期开始记录
                        c = CycleLog()
                        c.cycle_start_idx = index
                        c.ostime_start = int(s_r_list[0])             # 格式0是系统时间
                        c.cycle_num = int(s_r_list[1])                # 格式1是周期号
                        content_flag = 1                              # 开始周期的搜寻内容
                elif e_r != []:
                    if content_flag == 0:                             # 从来没有起点,丢弃
                        pass
                    else:
                        e_r_list = list(e_r[0])
                        if int(e_r_list[1]) == c.cycle_num:  # 找到匹配周期，s_r 和 e_r 每周期都更新可能空，要与记录值比较
                            c.cycle_end_idx = index
                            c.ostime_end = int(e_r_list[0])           # 找到完整周期
                            if index == length-1:
                                c.cycle_all_info = self.lines[c.cycle_start_idx:]  # 列表末尾包含当前行
                            else:
                                c.cycle_all_info = self.lines[c.cycle_start_idx: c.cycle_end_idx + 1]  # 包含当前行
                            c.cycle_property = 1                      # 完整周期
                            content_flag = 0                          # 不在寻找该周期内容
                            # 添加周期到字典
                            if self.check_cycle_exist(c, restart_flag):
                                return restart_idx
                            else:
                                self.cycle_dic[c.cycle_num] = c
            elif content_flag == 1:
                ret = 1     # 有周期!!!
                r = self.match_log_packet_contect(c, line, patlist)
                if r == 0:  # 如果不成功，才继续
                    r = self.match_log_basic_content(c, line, patlist)
            else:
                # 属于记录开始和结尾残损周期，不记录丢弃
                pass
        return ret

    # 根据构建模板，对字符串分解后周期基本要素填充
    # <输入> line 待查找字符串
    # <输入> c    已经确定周期边界的周期对象，待填充内容
    # <输入> pat_list 模板列表
    # <输出> ret  解析1=成功，0=失败
    def match_log_basic_content(self, c=CycleLog, line=str, pat_list=list):
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
    def match_log_packet_contect(self, c=CycleLog, line=str, pat_list=list):
        ret = 1
        # 先无条件设置状态
        c.gfx_flag = self.gfx_flag
        c.break_status = self.break_status
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
        if '[P->O]SP' in line:
            # ATP->ATO数据包匹配过程
            if pat_sp0.findall(line):
                c.cycle_sp_dict[0] = pat_sp0.findall(line)[0]
            elif pat_sp1.findall(line):
                c.cycle_sp_dict[1] = pat_sp1.findall(line)[0]
            elif pat_sp2.findall(line):
                try:
                    if 'syn len = 0.' in line:
                        pass
                    else:
                        l = re.split(',', line)
                        c.cycle_sp_dict[2] = tuple(l[1:])  # 保持与其他格式一致，从SP2后截取
                        if int(c.cycle_sp_dict[2][13]) == 1:             # 去除nid——packet是第13个字节
                            c.gfx_flag = 1
                            self.gfx_flag = 1
                        else:
                            c.gfx_flag = 0
                            self.gfx_flag = 0
                except Exception as err:
                    print('gfx_err ')
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
            self.mvb_research(c, line)
        elif '[DOOR]' in line or '[MSG]' in line:
            if pat_io_in.findall(line):
                c.io_in = pat_io_in.findall(line)[0]
            elif pat_io_out.findall(line):
                c.io_out = pat_io_out.findall(line)
        else:
            ret = 0
        return ret

    # 创建构建模板序列
    # <输出> 返回模板列表
    @staticmethod
    def create_all_pattern():
        pat_list = []
        # 北京时间
        pat_time = re.compile('time:(\d+-\d+-\d+ \d+:\d+:\d+)')
        # ATO模式转换条件
        pat_fsm = re.compile('FSM{(\d) (\d) (\d) (\d) (\d) (\d)}sg{(\d) (\d) (\d+) (\d+) (\w+) (\w+)}ss{(\d+) (\d)}')
        pat_sc = re.compile('SC{(\d+) (\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (\d+) (\d+) (-?\d+) (-?\d+)}t (\d+) (\d+) (\d+)'
                            ' (\d+),(\d+)} f (-?\d+) (\d+) (\d+) (-?\w+)} p(\d+) (\d+)}CC')
        pat_stop = re.compile('stoppoint:jd=(\d+) ref=(\d+) ma=(\d+)')

        # ATP->ATO 数据包
        pat_sp0 = re.compile('\[P->O\]SP0,')
        pat_sp1 = re.compile('\[P->O\]SP1,')
        pat_sp2 = re.compile('\[P->O\]SP2,')
        pat_sp5 = re.compile('\[P->O\]SP5,.*\s(\d),.*\s(\w+),.*\s(\w+),.*\s(-?\d+),.*\s(\d+),.*\s(\d+),.*\s(\d+),'
                             '.*\s(\d+),.*\s(\d+),.*\s(\d)')    # 因为有下划线所以不支持\w了
        pat_sp6 = re.compile('\[P->O\]SP6,')
        pat_sp7 = re.compile('\[P->O\]SP7,\w*?\s?(\d+),\w*?\s?(\d+),\w*?\s?(-?\d+),\w*?\s?(\d+),\w*?\s?(\d+),'
                             '\w*?\s?(\d+),\w*?\s?(\d+),\w*?\s?(\d+),\w*?\s?(\d+)')

        pat_sp8 = re.compile('\[P->O\]SP8,\w*?\s?(\d),\w*?\s?(\d+),\w*?\s?(\d),\w*?\s?(\w+),\w*?\s?(\w+),'
                             '\w*?\s?(\d), \w*?\s?(\d)')
        pat_sp9 = re.compile('\[P->O\]SP9,')
        # ATO->ATP 数据包
        pat_sp131 = re.compile('\[O->P\]SP131:\w*?\s?(\d),\w*?\s?(\d),\w*?\s?(\d),\w*?\s?(-?\d+),\w*?\s?(\d),\w*?\s?(\d)'
                               ',\w*?\s?(\d),\w*?\s?(\d)')      # 最后一个padding不判断
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
        pat_io_out = re.compile('\[MSG\](OPEN+\s[LR])')

        # 添加列表
        pat_list = [pat_time, pat_fsm, pat_sc, pat_stop, pat_sp0, pat_sp1, pat_sp2, pat_sp5, pat_sp6, pat_sp7,
                    pat_sp8, pat_sp9, pat_sp131, pat_sp130, pat_sp132, pat_sp134, pat_c41, pat_c43, pat_c2,
                    pat_p27, pat_p21, pat_c42, pat_c44, pat_c45, pat_c46, pat_io_in, pat_io_out]

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
        temp_delta_v = np.array([])
        temp_delta_s = np.array([])
        # 计算分子分母
        temp_delta_v = 0.5*(self.v_ato[1:]**2 - self.v_ato[:-1]**2)
        temp_delta_s = self.s[1:] - self.s[:-1]
        # 加速度计算处理
        for idx, item in enumerate(temp_delta_s):
            if item == 0:
                self.a = np.append(self.a, 0)
            else:
                self.a = np.append(self.a, temp_delta_v[idx]/item)
        # 由于是差值计算，最后补充一个元素
        self.a = np.append(self.a, 0)

    # 计算ATP允许速度序列，只能从SP2包中获取
    # <输出> 返回ATP允许处理结果
    def get_atp_permit_v(self):
        c_num = 0
        temp_p = 1
        c_num_start = 0

        # 遍历周期
        if len(self.cycle_dic.keys()) != 0:
            for ctrl_item in self.cycle_dic.keys():
                # print('Comput ATP Permit %d len %d' % (ctrl_item,len(self.atp_permit_v)))
                if self.cycle_dic[ctrl_item].control:  # 如果该周期中有控车信息
                    c_num = self.cycle_dic[ctrl_item].cycle_num     # 获取周期号
                    # 如果有数据包
                    if 2 in self.cycle_dic[ctrl_item].cycle_sp_dict.keys():
                        temp_p = int(self.cycle_dic[ctrl_item].cycle_sp_dict[2][11])
                        self.atp_permit_v = np.append(self.atp_permit_v, temp_p)    # 添加
                    else:
                        # 首次获取，当周期无SP2
                        if temp_p == 1:
                            # 向前取5个周期,且字典存在
                            if c_num > 5 and ((c_num - 5) in self.cycle_dic.keys()):
                                c_num_start = c_num - 5
                                # 遍历周期
                                for c in range(c_num_start, c_num):
                                    # 如果有数据包
                                    if 2 in self.cycle_dic[c].cycle_sp_dict.keys():
                                        temp_p = int(self.cycle_dic[c].cycle_sp_dict[2][11].strip())      # 非首次投入ATO周期，无SP2包
                                        print('ato cycle no sp2, find before aom!')
                                        break
                                    else:
                                        pass
                            else:
                                pass    # 直接添加1
                            self.atp_permit_v = np.append(self.atp_permit_v, temp_p)  # 添加
                            temp_p = 0  # 清除作为标志，表明已经非首次
                        else:
                            self.atp_permit_v = np.append(self.atp_permit_v, self.atp_permit_v[-1])
                else:
                    pass
        else:
            print('no ato ctrl,no atp permit v')
        # print('get atp permit v ok %d, %d'%(len(self.v_ato),len(self.atp_permit_v)))

    # <核心函数>
    # 建立ATO控制信息和周期的关系字典
    def create_ctrl_cycle_list(self):
        ret = 2                                            # 用于标记创建结果,2=无周期无结果，1=有周期无控车，0=有周期有控车
        cnt = 0
        bar = 50
        bar_flag = 0
        bar_cnt = int(len(self.cycle_dic.keys()) / 50)
        if bar_cnt == 0:
            self.pbar.setValue(100)
            bar_flag = 0
        else:
            bar_flag = 1
        # 遍历周期
        if len(self.cycle_dic.keys()) != 0:
            for ctrl_item in self.cycle_dic.keys():
                if self.cycle_dic[ctrl_item].control:                                           # 如果该周期中有控车信息
                    self.cycle = np.append(self.cycle, self.cycle_dic[ctrl_item].cycle_num)     # 获取周期号
                else:
                    pass
                # 对外显示进度
                if bar_flag == 1:
                    cnt = cnt + 1
                    if int(cnt % bar_cnt) == 0:
                        bar = bar + 1
                        self.pbar.setValue(bar)
                    else:
                        pass
            ret = 1     # 有周期，不一定有控车
        else:
            ret = 2
        # 如果没有周期则不执行
        if ret != 2:
            # 如果进入过AOR或者AOM
            if len(self.cycle) > 0:         # self.cycle是一个迭代器，不能和[]进行比较
                # 生成控制矩阵
                l = len(list(self.cycle_dic[self.cycle[0]].control))                      # 不妨用第一个计算控制队列数量
                mat = np.zeros((len(self.cycle), l))
                # 计算矩阵
                for idx in range(len(self.cycle)):
                    temp = list(self.cycle_dic[self.cycle[idx]].control)                  # 按周期索引取控制信息，妨不连续
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
                self.platform = mat[:, 17]
                # 停车误差
                self.stop_error = mat[:, 15]
                # 通过办客
                self.skip = mat[:, 19]
                self.mtask = mat[:, 20]
                print('Slip Ctrl Matrix')
                # 计算加速度
                self.comput_acc()
                print('Comput Train Acc')
                # 获取ATP允许速度序列
                print('Comput ATP Permit V')
                self.get_atp_permit_v()
                ret = 0
            else:
                ret = 1
        return ret

    # 检查是否该周期已经存在,都有控车，异常，手动分解。
    # <输出> 0=不存在，1=存在
    def check_cycle_exist(self, c=CycleLog, restart=int):
        ret = 0
        if restart == 1:        # 已经重启过且重启前后都有控车信息
            if c.cycle_num in self.cycle_dic.keys() and self.cycle_dic[c.cycle_num].control and c.control:
                ret = 1
        return ret

    # 解析MVB数据
    # 返回解析结果 0=无，1=更新
    def mvb_research(self, c=CycleLog, line=str):
        global pat_ato_ctrl
        global pat_ato_stat
        global pat_tcms_stat
        real_idx = 0            # 对于记录打印到同一行的情况，首先要获取实际索引
        tmp = ''
        parse_flag = 0
        try:
            if pat_ato_ctrl in line:
                if '@' in line:
                    pass
                else:
                    real_idx = line.find('MVB[')
                    tmp = line[real_idx+10:]  # 还有一个冒号需要截掉
                    c.ato2tcms_ctrl = self.mvbParser.ato_tcms_parse(1025, tmp)       # 这里仅仅适配解析模块，端口号抽象
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
                            self.break_status = 0
                            c.break_status = 0         # 闭合
                        elif c.tcms2ato_stat[14] == '00':
                            self.break_status = 1
                            c.break_status = 1          # 主断路器断开
                    parse_flag = 1
        except Exception as err:
            print(err)
        return parse_flag

    # <已废弃>
    # 处理控车参数用于绘图，生成关键列表
    # 输入：ATO控车行
    def keywordprocess(self, line_info):
        if -1 != line_info.find('@'):
            index_end = line_info.index('@')
            index_start = line_info.index('SC{')
            line_key = line_info[index_start + 3:index_end]  # split good part and sign 'SC{'
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
            #增加位置信息
            v_target = int(ato_info[10])
            targetpos = int(ato_info[11])
            ma = int(ato_info[12])
            stoppos = int(ato_info[14][:-1])  # 因为打印拆分后多一个 } 符号
            skip = int(ato_info[20][1:])  # 因为打印前面多一个 p
            mtask = int(ato_info[21][0])
            # 停车误差
            if int(ato_info[16]) != -32768:
                self.stoperr = int(ato_info[16])
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
            # 运动相对量
            self.v_target = np.append(self.v_target, v_target)
            self.targetpos = np.append(self.targetpos, targetpos)
            self.stoppos = np.append(self.stoppos, stoppos)
            self.ma = np.append(self.ma, ma)
            self.skip = np.append(self.skip,skip)
            self.mtask = np.append(self.mtask, mtask)
            # 加速度计算处理
            if (len(self.s) > 1) and (len(self.v_ato) > 1):
                delta_s = self.s[len(self.s) - 1] - self.s[len(self.s) - 2]
                # 除零错误
                if delta_s != 0:
                    a = (pow(self.v_ato[len(self.v_ato) - 1], 2) - pow(self.v_ato[len(self.v_ato) - 2], 2))/(2*delta_s)
                    # 有效性判断
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

    # <已废弃>
    # 搜索SC所在行
    # 输入： 文件路径
    def read_findkeyword(self, file):
        log = open(file, 'r', encoding='ansi')           # notepad++默认是ANSI编码
        self.lines = log.readlines()
        cnt = 0
        bar = 0
        bar_cnt = int(len(self.lines) / 50)
        self.filename = file.split("/")[-1]
        # 遍历所有的记录
        for idx, line in enumerate(self.lines):
            # 解析记录中每行的内容
            try:
                if '@' in line:
                    if line.index('@') > 140:            # 取出前130个字节的内容,在冗余10个
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
            # 进度条计算
            cnt = cnt + 1
            if int(cnt % bar_cnt) == 0:
                bar = bar + 1
                self.pbar.setValue(bar)
            else:
                pass