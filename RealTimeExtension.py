import os
import queue
import re
import threading
import time

import numpy as np
from PyQt5 import QtCore

from FileProcess import FileProcess
from MsgParse import Atp2atoParse
from TcmsParse import MVBParse
from ConfigInfo import ConfigFile

exit_flag = 0
queueLock = threading.Lock()
workQueue = queue.Queue(10000)
real_curve_buff = 50                                 # 每次绘图话添加的点数
real_curve_all_buff = 50000                          # 每次绘画总点数
newPaintList = np.zeros([5, real_curve_buff])        # 新添加的参数
paintList = np.zeros([5, real_curve_all_buff])       # 初始化1000个点用于绘图

class SerialRead(threading.Thread, QtCore.QObject):

    def __init__(self, name, serialport):
        threading.Thread.__init__(self)
        self.name = name
        self.ser = serialport
        super(QtCore.QObject, self).__init__()

    # 串口成功打开才启动此线程
    def run(self):
        # 读取文件，测试时打开
        with open('M_L-Serial-COM6-1126170040-序列3-黑山北-阜新.log') as f:
            while not exit_flag:
                # 有数据就读取
                try:
                    #下面两行测试时打开
                    line = f.readline().rstrip()
                    time.sleep(0.0001)
                    # line = self.ser.readline().decode('ansi', errors='ignore').rstrip()  # 串口设置，测试时注释
                except UnicodeDecodeError as err:
                    print("serial read err")
                    print(err)
                # 若队列未满，则继续加入
                if not workQueue.full():
                    try:
                        workQueue.put(line)   # 必须读到数据
                    except Exception as err:
                        print(err)
                else:
                    print("recv queue full!")


class RealPaintWrite(threading.Thread, QtCore.QObject):

    pat_show_signal = QtCore.pyqtSignal(tuple)
    plan_show_signal = QtCore.pyqtSignal(tuple)      # 计划显示使用的信号
    io_show_signal = QtCore.pyqtSignal(tuple)
    sp7_show_signal = QtCore.pyqtSignal(tuple)
    sdu_show_signal = QtCore.pyqtSignal(tuple)

    def __init__(self, filepath=str, filenamefmt=str, portname=str):
        threading.Thread.__init__(self, )
        super(QtCore.QObject, self).__init__()
        self.filepath = filepath  # 记录文件路径
        self.logFile = filepath + 'ATO记录中' + str(int(time.time())) + '.txt'  # 纪录写入文件
        self.logBuff = []
        self.filenamefmt = filenamefmt  # 文件格式化命名
        self.portname = portname
        self.cfg = ConfigFile()
        pat_cycle_start = re.compile('---CORE_TARK CY_B (\d+),(\d+).')  # 周期终点匹配
        pat_cycle_end = re.compile('---CORE_TARK CY_E (\d+),(\d+).')
        self.pat_list = FileProcess.create_all_pattern()
        self.pat_list.insert(0, pat_cycle_start)
        self.pat_list.insert(1, pat_cycle_end)
        self.pat_plan = FileProcess.creat_plan_pattern()  # 计划解析模板
        # 周期开始时间
        self.cycle_os_time_start = 0
        self.cycle_os_time_end = 0
        # 计划
        self.rp1 = ()
        self.rp2 = ()
        self.rp2_list = []
        self.rp3 = ()
        self.rp4 = ()
        self.plan_in_cycle = '0'  # 主要用于周期识别比较，清理列表
        self.newPaintCnt = 0
        self.time_plan_remain = 0
        self.time_plan_count = 0

        self.mvbParser = MVBParse()
        self.atp2atoParser = Atp2atoParse()
        self.a2t_ctrl = None
        self.a2t_stat = None
        self.t2a_stat = None
        # 静态变量
        self.cycle_num = '0'
        self.count = 0
        self.last_mean = 0
        self.max_slot_cycle = 0
        self.max_slot = 0
        self.mean_slot = 0
        self.min_slot = 0
        self.time_content = ''
        self.fsm = []
        self.sc_ctrl = []
        self.stoppoint = []
        self.sp2_real = ()
        self.sp5_real = ()
        self.sp131_real = ()
        self.time_statictics = ()
        # io 信息
        self.io_in_real = ()
        self.io_out_real = []
        # btm信息
        self.sp7_real = ()
        # 测速测距
        self.sdu_ato = ()
        self.sdu_atp = ()
        self.state_machine = 0  # 测速测距检查使用的状态机用于匹配ATP/ATO速度

    # 串口成功打开才启动该线程
    def run(self):
        # 打开文件等待写入logFile
        with open(self.logFile, 'w') as f:
            while not exit_flag:
                if not workQueue.empty():
                    try:
                        line = workQueue.get_nowait()
                    except Exception as err:
                        print(err)
                    # 防止数据处理过程中被刷新
                    #queueLock.acquire()
                    #self.fileWrite(line, f) # 测试时关闭
                    self.paintProcess(line)
                    #queueLock.release()
                else:
                    time.sleep(0.1)
            # 清空缓存
            self.fileFlush(f)
            # 线程停止
            f.close()
            tmp = self.fileRename()
            os.rename(self.logFile, self.filepath + tmp)

    # 按行写入文件
    def fileWrite(self, line, f):
        try:
            f.write(line+'\n')   # 重新添加回车写入
        except Exception as err:
            print('write info err' + str(time.time()))
            print(err)

    # 立即写入用于关断时候
    def fileFlush(self, f):
        for item in self.logBuff:
            f.write(item)  # 由于记录中本身有回车，去掉\r\n
        f.flush()
        print("file exit flush!")

    # 每次测试完后重命名文件
    def fileRename(self):
        # 保存文件，立即更新文件名
        stuctLocTime = time.localtime(time.time())
        tmpfilename = self.filenamefmt
        try:
            tmpfilename = tmpfilename.replace('%Y', str(stuctLocTime.tm_year), 1)
            tmpfilename = tmpfilename.replace('%M', str(stuctLocTime.tm_mon), 1)
            tmpfilename = tmpfilename.replace('%D', str(stuctLocTime.tm_mday), 1)
            tmpfilename = tmpfilename.replace('%h', str(stuctLocTime.tm_hour), 1)
            tmpfilename = tmpfilename.replace('%m', str(stuctLocTime.tm_min), 1)
            tmpfilename = tmpfilename.replace('%s', str(stuctLocTime.tm_sec), 1)
            tmpfilename = tmpfilename.replace('%N', self.portname, 1)
        except Exception as err:
            tmpfilename = 'ATO' + str(stuctLocTime.tm_year) + str(stuctLocTime.tm_mon) + str(
                stuctLocTime.tm_mday) \
                          + str(stuctLocTime.tm_hour) + str(stuctLocTime.tm_min) + str(
                stuctLocTime.tm_sec) \
                          + self.portname
        return tmpfilename

    #生成计算曲线和调用模板匹配
    def paintProcess(self, line):
        # 控车信息，显示信息，周期信息等
        # 匹配速度曲线信息
        result = self.pat_research(line)
        sc_ctrl = result[3]
        if sc_ctrl:  # 如果匹配成功
            newPaintList[0, self.newPaintCnt] = sc_ctrl[1]   # 当前速度
            newPaintList[1, self.newPaintCnt] = sc_ctrl[2]   # ATO命令速度
            newPaintList[2, self.newPaintCnt] = sc_ctrl[3]   # ATP命令速度
            newPaintList[3, self.newPaintCnt] = sc_ctrl[4]   # ATP允许速度
            newPaintList[4, self.newPaintCnt] = sc_ctrl[6]   # 输出级位
            self.newPaintCnt += 1
        else:
            pass

        if self.newPaintCnt == real_curve_buff:
            paintList[:, real_curve_buff:real_curve_all_buff] = paintList[:, 0:real_curve_all_buff - real_curve_buff]
            paintList[:, 0:real_curve_buff] = newPaintList[:, 0:real_curve_buff]
            # 清除列表
            self.newPaintCnt = 0
            # 实时line匹配内容
        
        if self.plan_research(line, self.cycle_num): # 匹配计划，内部使用独立信号
            return 
        if self.pat_io_research(line): # io 独立信号
            return
        if self.pat_btm_research(line): # btm独立信号
            return
        if self.pat_sdu_research(line): # 测速测距识别
            return

    # 模板识别
    def pat_research(self, line):
        update_flag = False
        # 所有匹配模板
        match = self.cfg.reg_config.pat_cycle_start.findall(line)
        if match:
            self.cycle_num = match[0][1]
            self.cycle_os_time_start = int(match[0][0])  # 当周期系统开始时间
            update_flag = True
        else:
            match = self.cfg.reg_config.pat_cycle_end.findall(line)
            if match:
                self.cycle_os_time_end = int(match[0][0])  # 当周期系统结束时间
                self.time_statictics = self.statictics_cycle_time(match[0][1])
                update_flag = True
            else:
                match = self.cfg.reg_config.pat_time.findall(line)
                if match:
                    self.time_content = match[0]  # time 信息直接返回
                    update_flag = True
                else:
                    match = self.cfg.reg_config.pat_fsm.findall(line)
                    if match:
                        self.fsm = match[0]
                        update_flag = True
                    else:
                        match = self.cfg.reg_config.pat_ctrl.findall(line)
                        if match:
                            self.sc_ctrl = match[0]
                            # 允许速度处理
                            self.sc_ctrl = self.sc_ctrl[:4] + (str(self.atp2atoParser.msg_obj.sp2_obj.v_permitted),) + self.sc_ctrl[4:]  # tuple拼接
                            update_flag = True
                        else:
                            match = self.cfg.reg_config.pat_p2o.findall(line)
                            if match:
                                # 当解析到时重置所有
                                Atp2atoParse.resetMsg(self.atp2atoParser.msg_obj)
                                self.atp2atoParser.msgParse(match[0])
                                update_flag = True
                            else:
                                match = self.cfg.reg_config.pat_o2p.findall(line)
                                if match:
                                    # 当解析到时重置所有
                                    Atp2atoParse.resetMsg(self.atp2atoParser.msg_obj)
                                    self.atp2atoParser.msgParse(match[0])
                                    update_flag = True
                                else:
                                    match = self.cfg.reg_config.pat_stoppoint.findall(line)
                                    if match:
                                        self.stoppoint = match[0]
                                        update_flag = True
                                    elif self.mvb_research(line):
                                        update_flag = True
                                    else:
                                        pass

        # 生成信号结果
        result = (self.cycle_num, self.time_content, self.fsm, self.sc_ctrl, self.stoppoint,
                  self.a2t_ctrl, self.a2t_stat, self.t2a_stat,self.atp2atoParser.msg_obj, self.time_statictics)
        # 发射信号
        if update_flag == 1:
            self.pat_show_signal.emit(result)

        # 返回用于画图
        return result

    # 测速测距识别
    def pat_sdu_research(self, line):
        result = ()
        update_flag = False
        # 查找或清空
        atp_sdu_match = self.cfg.reg_config.pat_atp_sdu.findall(line)
        if atp_sdu_match:
            self.sdu_atp = atp_sdu_match[0]
            self.state_machine = 1
            # 查找或清空
        ato_sdu_match = self.cfg.reg_config.pat_ato_sdu.findall(line)
        if ato_sdu_match:
            self.sdu_ato = ato_sdu_match[0]
            # 如果已经收到了sdu_ato
            if self.state_machine == 1:
                self.state_machine = 2    # 置状态机为2.收到ATP
        # 组合数据,前面安装时间和周期
        result = (self.sdu_ato, self.sdu_atp)

        # 收集到sdu_ato和sdu_atp, 终止状态机，发送信号清空
        if self.state_machine == 2:
            self.sdu_show_signal.emit(result)
            update_flag = True
            self.state_machine = 0
            self.sdu_ato = ()
            self.sdu_atp = ()
        else:
            pass
        return update_flag

    # IO查询
    def pat_io_research(self, line):
        result = ()
        update_flag = False
        # 查找或清空
        if self.pat_list[27].findall(line):
            self.io_in_real = self.pat_list[27].findall(line)[0]
            update_flag = True
        else:
            self.io_in_real = ()
        # 查找或清空
        if self.pat_list[28].findall(line):
            self.io_out_real = self.pat_list[28].findall(line)[0]
            update_flag = True
        else:
            self.io_out_real = ()
        # 组合数据,前面安装时间和周期
        result = (self.cycle_num, self.time_content, self.io_in_real, self.io_out_real)
        # 发送信号
        if update_flag == True:
            self.io_show_signal.emit(result)
        else:
            pass
        return update_flag

    # btm查询
    def pat_btm_research(self, line):
        if len(self.sp2_real) == 26:
            mile_stone = self.sp2_real[23]    # 获取公里标，逗号分隔后，除去nid后第22个
        else:
            mile_stone = ''
        result = ()
        update_flag = False
        # 解析基本参数，相对于离线解析，模板中增加了周期开始和结束的识别
        # 所以模板序号
        if self.pat_list[11].findall(line):
            self.sp7_real = self.pat_list[11].findall(line)[0]
            update_flag = True
        else:
            pass
        # 组合数据
        result = (self.time_content, self.sp7_real, mile_stone)
        # 发送信号
        if update_flag == True:
            self.sp7_show_signal.emit(result)
        else:
            pass
        return update_flag

    # 解析MVB内容
    def mvb_research(self, line):
        parse_flag = 0
        # 前提条件
        if 'MVB[' in line:
            [self.a2t_ctrl,self.a2t_stat, self.t2a_stat] = self.mvbParser.parseProtocol(line)
            if self.a2t_ctrl.updateflag or self.a2t_stat.updateflag or self.t2a_stat.updateflag:
                parse_flag = 1
        return parse_flag

    # 提取计划内容
    def plan_research(self, line, cycle_num):
        update_flag = 0
        ret_plan = ()
        temp_transfer_list = []
        # 提高解析效率,当均更新时才发送信号
        if '[RP' in line:
            if self.cfg.reg_config.pat_rp1.findall(line):
                self.rp1 = self.cfg.reg_config.pat_rp1.findall(line)[0]
                update_flag = 1

            elif self.cfg.reg_config.pat_rp2.findall(line):
                self.rp2 = self.cfg.reg_config.pat_rp2.findall(line)[0]
                update_flag = 1

            elif self.cfg.reg_config.pat_rp2_cntent.findall(line):
                # 当周期改变时清除，只存储同一周期的
                if int(cycle_num) != int(self.plan_in_cycle):
                    self.rp2_list = []
                    # 替换其中UTC时间
                    temp_transfer_list = self.Comput_Plan_Content(self.cfg.reg_config.pat_rp2_cntent.findall(line)[0])
                    self.rp2_list.append(tuple(temp_transfer_list))
                    self.plan_in_cycle = cycle_num
                else:
                    # 替换其中的UTC时间
                    temp_transfer_list = self.Comput_Plan_Content(self.cfg.reg_config.pat_rp2_cntent.findall(line)[0])
                    self.rp2_list.append(tuple(temp_transfer_list))
                    update_flag = 1

            elif self.cfg.reg_config.pat_rp3.findall(line):
                self.rp3 = self.cfg.reg_config.pat_rp3.findall(line)[0]
                update_flag = 1

            elif self.cfg.reg_config.pat_rp4.findall(line):
                self.rp4 = self.cfg.reg_config.pat_rp4.findall(line)[0]
                if int(self.rp4[1]) != 0:
                    self.time_plan_remain = int(self.rp4[1]) - self.cycle_os_time_start
                if int(self.rp4[2]) != 0:
                    self.time_plan_count = int(self.rp4[2]) - self.cycle_os_time_start
                update_flag = 1
            else:
                pass
            ret_plan = (self.rp1, (self.rp2, self.rp2_list), self.rp3, self.rp4,
                        self.time_plan_remain, self.time_plan_count)
        else:
            pass
        # 发送信号
        if update_flag == 1:
            self.plan_show_signal.emit(ret_plan)
        else:
            pass
        # 返回用于指示解析结果
        return update_flag

    # 解析utc
    @staticmethod
    def TransferUTC(t=str):
        try:
            ltime = time.localtime(int(t))
            timeStr = time.strftime("%H:%M:%S", ltime)
        except Exception as err:
            print('plan transfer t err ：'+ t)
            print(err)
        return timeStr

    # 解析转化计划
    def Comput_Plan_Content(self, t="tuple"):
        # 替换其中的UTC时间
        temp_transfer_list = [''] * len(t)
        for idx, item in enumerate(t):
            if idx in [2, 4, 6]:
                temp_transfer_list[idx] = self.TransferUTC(t[idx])
            elif idx == 7:
                if t[idx] == '1':
                    temp_transfer_list[idx] = '通过'
                elif t[idx] == '2':
                    temp_transfer_list[idx] = '到发'
                else:
                    temp_transfer_list[idx] = '错误'
            elif idx == 8:
                if t[idx] == '1':
                    temp_transfer_list[idx] = '办客'
                elif t[idx] == '2':
                    temp_transfer_list[idx] = '不办客'
                else:
                    temp_transfer_list[idx] = '错误'
            else:
                temp_transfer_list[idx] = t[idx]
        return temp_transfer_list

    # 统计ATO周期的运行时间, None不更新
    def statictics_cycle_time(self, cycle_num):
        if int(cycle_num) != int(self.cycle_num):
            return None
        else:
            curr_slot = (self.cycle_os_time_end - self.cycle_os_time_start)
            self.count = self.count + 1
            self.mean_slot = self.last_mean + ((curr_slot - self.last_mean)/self.count)
            self.last_mean = self.mean_slot
            if curr_slot > self.max_slot:
                self.max_slot = curr_slot
                self.max_slot_cycle = int(cycle_num)
            if curr_slot < self.min_slot:
                self.min_slot = curr_slot
        
        return (self.mean_slot, self.max_slot, self.max_slot_cycle, self.min_slot, self.count)
            

