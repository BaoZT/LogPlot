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
import copy
import numpy as np
from PyQt5.QtWidgets import QProgressBar
from PyQt5 import QtCore
from ConfigInfo import ConfigFile
from MainWinDisplay import InerIoInfo, InerIoInfoParse, InerRunningPlanInfo, InerRunningPlanParse, InerSduInfo, InerSduInfoParse, ProgressBarDisplay
from MsgParse import Atp2atoParse, Atp2atoProto
from TcmsParse import Ato2TcmsCtrl, Ato2TcmsState, MVBParse, Tcms2AtoState 


# 周期类定义
class CycleLog(object):
    __slots__ = ['cycle_start_idx', 'cycle_end_idx', 'ostime_start', 'ostime_end',  'control', 
    'fsm', 'time', 'cycle_num', 'cycle_sp_dict',"msg_atp2ato",'a2t_ctrl','a2t_stat','t2a_stat',
    'rpInfo','ioInfo','sduInfo','raw_analysis_lines', 'stoppoint', 'file_begin_offset',
    'file_end_offset',  'cycle_property']

    def __init__(self, ):  # 存储的是读取的内容
        # 周期文本索引号
        self.cycle_start_idx = 0
        self.cycle_end_idx = 0
        # 周期系统时间信息
        self.ostime_start = 0
        self.ostime_end = 0
        # 控制信息相关
        self.control = ()
        self.fsm = ()
        self.time = ''
        self.cycle_num = 0
        self.cycle_sp_dict = {}  
        # 协议存储
        self.msg_atp2ato = Atp2atoProto()
        self.a2t_ctrl = Ato2TcmsCtrl()
        self.a2t_stat = Ato2TcmsState()
        self.t2a_stat = Tcms2AtoState()
        # 内部计划信息
        self.rpInfo = InerRunningPlanInfo()
        # 内部速传信息
        self.sduInfo = InerSduInfo()
        # 内部IO信息
        self.ioInfo = InerIoInfo()
        # 二次解析原始记录
        self.raw_analysis_lines = []
        # 停车点
        self.stoppoint = ()
        # 当周期所有信息，使用File指针读取减少内存占用
        self.file_begin_offset = 0
        self.file_end_offset = 0
        # 周期属性
        self.cycle_property = 0  # 1=序列完整，2=序列尾部缺失



# 文件处理类定义
class FileProcess(threading.Thread, QtCore.QObject):
    bar_show_signal = QtCore.pyqtSignal(int)
    end_result_signal = QtCore.pyqtSignal(bool)
    __slots__ = ['daemon','atp2atoParser','rpParser', 'mvbParser','sduParser', 'ioParser', 
    'cycle', 's', 'v_ato', 'a', 'cmdv', 'level', 'real_level', 'output_level','ceilv', 
    'atp_permit_v','statmachine','v_target', 'targetpos', 'stoppos', 'ma', 'ramp', 'adjramp',
    'skip', 'mtask', 'platform', 'stoperr','stop_error', 'cycle_dic','time_use', 'file_lines_count',
    'file_path', 'filename']

    # constructors
    def __init__(self, file_path_in):
        # 线程处理
        super(QtCore.QObject, self).__init__()  ## 必须这样实例化？ 而不是父类？？？统一认识
        threading.Thread.__init__(self)
        self.daemon = True
        self.mvbParser = MVBParse()
        self.atp2atoParser = Atp2atoParse()
        self.rpParser = InerRunningPlanParse()
        self.sduParser = InerSduInfoParse()
        self.ioParser = InerIoInfoParse()
        self.cfg = ConfigFile()
        self.cfg.readConfigFile()
        self.bar = ProgressBarDisplay()
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
            print('Create cycle dic! rst:%d'%iscycleok)
            t1 = time.clock() - start
            start = time.clock()  # 更新计时起点
            islistok = self.createCtrlCycleList()  # 解析周期内容
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
        self.stop_error = list()
        # 文件读取结果
        self.cycle_dic = dict()
        # 读取耗时
        self.time_use = list()
        # 文件总行数
        self.file_lines_count = 0

    # 输入:文件路径
    def readkeyword(self, file_path):
        ret = 0            # 函数返回值，切割结果
        self.reset_vars()  # 重置所有变量
        with open(file_path, 'r', encoding='ansi', errors='ignore') as log:  # notepad++默认是ANSI编码,简洁且自带关闭
            self.file_lines_count = self.bufcount(log)  # 获取文件总行数
            print("Read line num %d"%self.file_lines_count)
            try:
                ret = self.create_cycle_dic_dync(log)
            except IndexError as err:
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
    
    # 周期创建后处理
    def cycleCreateProcess(self):
        # 创建周期后应重置ATP/ATO解析模块解析结果
        # 文件中可能有多个ATP/ATO消息时需要均解析，直到所有P->以及O->P解析完成后周期结束才能重置
        # 因为不同消息中可能带有差异项的包，需要在一个周期内均保留解析结果，在周期头或周期尾重置
        Atp2atoParse.resetMsg(self.atp2atoParser.msg_obj)
        # MVB总是覆盖解析
        self.mvbParser.resetPacket()
        # 每周期重置更新标志
        self.rpParser.reset()
        # 重置测速测距
        self.sduParser.reset()
        # 重置IO信息
        self.ioParser.reset()

    # <核心函数>
    # 使用自动迭代获取结果并记录周期偏移字节
    def create_cycle_dic_dync(self, f):
        """
        根据传入的文件句柄，动态解析信息记录周期的地址，用于打印查询
        注意:1. 函数能够检查获取完整的周期
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
        # 设置每次读取行数
        last_cycle_end_offset = f.tell()                # 初始化最近一次周期结束的指针偏移量
        # 计算进度条判断
        self.bar.setBarStat(0, 70, self.file_lines_count)
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
            # 进度条
            self.barRun()
            # 搜索周期
            s_r = self.cfg.reg_config.pat_cycle_start.findall(line)
            e_r = self.cfg.reg_config.pat_cycle_end.findall(line)
            # 检查是否周期头
            if s_r:
                s_r_list = list(s_r[0])                # 获取匹配的元组，转为列表
                # 检查状态机
                if content_search_state == 0 or content_search_state == 1:  # 未知或搜头状态下搜到周期头
                    c = CycleLog()
                    self.cycleCreateProcess()
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
                    self.cycleCreateProcess()
                    c.file_begin_offset = cur_line_head_offset   # 获取周期头文件偏移量
                    c.ostime_start = int(s_r_list[0])  # 格式0是系统时间
                    c.cycle_num = int(s_r_list[1])     # 格式1是周期号
                    content_search_state = 2           # 开始周期尾继续搜寻内容
            elif e_r:
                e_r_list = list(e_r[0])                # 获取匹配的元组，转为列表
                # 头部残缺情况，直接生成周期
                if content_search_state == 0 or content_search_state ==1:
                    c = CycleLog()
                    self.cycleCreateProcess()
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
                    if not self.match_log_packet_contect(c, line):
                        # 每一行只能有一种结果，当无数据包，才继续
                        self.match_log_basic_content(c, line)
                else:
                    pass                                          # 属于文件开始、结尾或重新统计残损周期，不记录丢弃

            # 更新下一行读取的记录起点
            cur_line_head_offset = cur_line_tail_offset
        return ret

    # 根据构建模板，对字符串分解后周期基本要素填充
    # <输入> line 待查找字符串
    # <输入> c    已经确定周期边界的周期对象，待填充内容
    # <输入> pat_list 模板列表
    # <输出> ret  解析1=存在匹配数据，0=无匹配数据
    def match_log_basic_content(self, c=CycleLog, line=str):
        ret = 1
        # 匹配查找
        match = self.cfg.reg_config.pat_time.findall(line)
        if match:
            c.time = str(match[0])
        else:
            match = self.cfg.reg_config.pat_fsm.findall(line)
            if match:
                c.fsm = match[0]
            else:
                match = self.cfg.reg_config.pat_stoppoint.findall(line)
                if match:
                    c.stoppoint = match[0]
                else:
                    match = self.cfg.reg_config.pat_ctrl.findall(line)
                    if match:
                        c.control = match[0]
                    else:
                        ret = 0
        return ret

    # <待完成>根据构建模板，对字符串分解后周期数据包进行填充
    # <输入> line 待查找字符串
    # <输入> c    已经确定周期边界的周期对象，待填充内容
    # <输入> pat_list 模板列表
    # <输出> ret  解析1=成功，0=失败
    def match_log_packet_contect(self, c=CycleLog, line=str):
        ret = 1
        # 数据包识别,提高效率
        if '[P->O]' in line:
            match = self.cfg.reg_config.pat_p2o.findall(line)
            if match:
                msg_line = match[0]
                c.msg_atp2ato = copy.deepcopy(self.atp2atoParser.msgParse(msg_line))
        elif '[O->P]' in line:
            match = self.cfg.reg_config.pat_o2p.findall(line)
            if match:
                msg_line = match[0]
                c.msg_atp2ato =  copy.deepcopy(self.atp2atoParser.msgParse(msg_line))
        elif 'MVB[' in line:
            match = self.cfg.reg_config.pat_mvb.findall(line)
            if match:
                [c.a2t_ctrl, c.a2t_stat, c.t2a_stat] = copy.deepcopy(self.mvbParser.parseProtocol(match[0]))
        elif 'v&p' in line:
            c.sduInfo =  copy.deepcopy(self.sduParser.sduInfoStringParse(line, c.ostime_start))
        elif '[RP' in line:
            c.rpInfo = copy.deepcopy(self.rpParser.rpStringParse(line,c.ostime_start))
        elif '[DOOR]' in line or '[MSG]' in line:
            c.ioInfo = copy.deepcopy(self.ioParser.ioStringParse(line))
        else:
            ret = 0
        return ret

    # 计算相邻周期加速度变化
    # <输出> 返回加速度处理结果
    def comput_acc(self):
        temp_delta_v = np.array([], np.int16)
        temp_delta_s = np.array([], np.uint32)
        # 计算分子分母
        temp_delta_v = 0.5 * (self.v_ato[1:] ** 2 - self.v_ato[:-1] ** 2)
        temp_delta_s = self.s[1:] - self.s[:-1]
        # 进度条
        self.bar.setBarStat(81, 4, len(temp_delta_s))
        # 加速度计算处理
        for idx, item in enumerate(temp_delta_s):
            self.barRun()
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
        # 进度条
        self.bar.setBarStat(85, 10, len(self.cycle_dic.keys()))
        # 遍历周期
        if len(self.cycle_dic.keys()) != 0:
            try:
                for ctrl_item in self.cycle_dic.keys():
                    # 进度条计算
                    self.barRun()
                    # ATP允许速度计算
                    if self.cycle_dic[ctrl_item].control:  # 如果该周期中有控车信息
                        c = self.cycle_dic[ctrl_item].cycle_num  # 获取周期号
                        # 如果有数据包
                        if self.cycle_dic[c].msg_atp2ato.sp2_obj.updateflag:
                            last_atp_pmv =self.cycle_dic[c].msg_atp2ato.sp2_obj.v_permitted
                        else:
                            # 上来就控车时就没有允许速度，首次获取，当周期无SP2
                            if not self.cycle_dic[c].msg_atp2ato.sp2_obj.updateflag or first_find_pmv_flag:
                                # 首先尝试寻找向前取20个周期,且字典存在,检查最远边界
                                if c_num > 20 and ((c_num - 20) in self.cycle_dic.keys()):
                                    c_num_end = c_num - 20
                                    # 遍历周期
                                    for c in range(c_num, c_num_end, -1):    # 逆序寻找，找最近的
                                        # 首先检测是否存在该周期，可能出现丢周期的情况，检查每个周期
                                        if c in self.cycle_dic.keys():
                                            # 如果有SP2数据
                                            if self.cycle_dic[c].msg_atp2ato.sp2_obj.updateflag:
                                                last_atp_pmv = self.cycle_dic[c].msg_atp2ato.sp2_obj.v_permitted  # 非首次投入ATO周期，无SP2包
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

    # <核心函数>
    # 建立ATO控制信息和周期的关系字典
    def createCtrlCycleList(self):
        ret = 2  # 用于标记创建结果,2=无周期无结果，1=有周期无控车，0=有周期有控车
        self.bar.setBarStat(70, 10, len(self.cycle_dic.keys()))
        # 遍历周期
        if len(self.cycle_dic.keys()) != 0:
            for ctrl_item in self.cycle_dic.keys():
                if self.cycle_dic[ctrl_item].control:  # 如果该周期中有控车信息
                    self.cycle = np.append(self.cycle, self.cycle_dic[ctrl_item].cycle_num)  # 获取周期号
                else:
                    pass
                # 对外显示进度
                self.barRun()
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

 
    # 进度条处理函数
    def barRun(self):
        percent = self.bar.barMovingCompute()
        if percent:
            self.bar_show_signal.emit(percent)
        else:
            pass

    # 打印函数
    def Log(self, msg=str, fun=str, lino=int):
        if str == type(msg):
            print(msg + ',File:"' + __file__ + '",Line' + str(lino) +
                  ', in' + fun)
        else:
            print(msg)


if __name__ == "__main__":
    x = InerRunningPlanInfo()
    path = r"F:\04-ATO Debug Data\SYLOG\ATO2022828105649COM14.txt"
    fd  = FileProcess(path)
    fd.readkeyword(path)
    print("end read!")