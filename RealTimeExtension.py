import os
import queue
import re
import threading
import time

import numpy as np
from PyQt5 import QtCore

from FileProcess import FileProcess
from MainWinDisplay import InerIoInfo, InerIoInfoParse, InerRunningPlanInfo, InerRunningPlanParse, InerSduInfo, InerSduInfoParse
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

    patShowSignal = QtCore.pyqtSignal(tuple)
    planShowSignal = QtCore.pyqtSignal(InerRunningPlanInfo, int)
    ioShowSignal = QtCore.pyqtSignal(str,str,InerIoInfo)
    sduShowSignal = QtCore.pyqtSignal(InerSduInfo)

    def __init__(self, filepath=str, filenamefmt=str, portname=str):
        threading.Thread.__init__(self, )
        super(QtCore.QObject, self).__init__()
        self.filepath = filepath  # 记录文件路径
        self.logFile = filepath + 'ATO记录中' + str(int(time.time())) + '.txt'  # 纪录写入文件
        self.logBuff = []
        self.filenamefmt = filenamefmt  # 文件格式化命名
        self.portname = portname
        self.cfg = ConfigFile()
        pat_cycle_start = self.cfg.reg_config.pat_cycle_start # 周期终点匹配
        pat_cycle_end = self.cfg.reg_config.pat_cycle_end
        self.pat_list = FileProcess.create_all_pattern()
        self.pat_list.insert(0, pat_cycle_start)
        self.pat_list.insert(1, pat_cycle_end)
        # 周期开始时间
        self.cycle_os_time_start = 0
        self.cycle_os_time_end = 0
        self.newPaintCnt = 0
        # 解析相关
        self.ioInfoParser = InerIoInfoParse()
        self.sduInfoParser = InerSduInfoParse()
        self.rpParser = InerRunningPlanParse()
        self.mvbParser = MVBParse()
        self.atp2atoParser = Atp2atoParse()
        # 静态变量
        self.cycleNumStr = '0'
        self.count = 0
        self.last_mean = 0
        self.max_slot_cycle = 0
        self.max_slot = 0
        self.mean_slot = 0
        self.min_slot = 0
        self.timeContentStr = ''
        self.fsm = []
        self.sc_ctrl = []
        self.stoppoint = []
        self.time_statictics = ()
        # io 信息
        self.io_in_real = ()
        self.io_out_real = []
        # 测速测距
        self.sdu_ato = ()
        self.sdu_atp = ()
        self.state_machine = 0  # 测速测距检查使用的状态机用于匹配ATP/ATO速度
    
    def newCyclePreProcess(self):
        # 创建周期后应重置ATP/ATO解析模块解析结果
        # 文件中可能有多个ATP/ATO消息时需要均解析，直到所有P->以及O->P解析完成后周期结束才能重置
        # 因为不同消息中可能带有差异项的包，需要在一个周期内均保留解析结果，在周期头或周期尾重置
        Atp2atoParse.resetMsg(self.atp2atoParser.msg_obj)
        # MVB总是覆盖解析
        self.mvbParser.resetPacket()
        # 每周期重置更新标志
        self.rpParser.reset()
        # 重置测速测距
        self.sduInfoParser.reset()
        # 重置IO信息
        self.ioInfoParser.reset()

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
                    self.lineProcessPaint(line)
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

    # 处理和绘图
    def lineProcessPaint(self, line):
        # 更新绘制情况
        self.paintArrayUpdate()

        # 匹配速度曲线信息
        if self.patCycleCommonResearch(line):
            return    
        # 匹配计划使用独立信号
        if self.patPlanResearch(line, self.cycle_os_time_start): 
            return
        # 匹配IO独立信号 
        if self.patIoInfoResearch(line):
            return
        # 测速测距识别
        if self.patSduInfoResearch(line, self.cycle_os_time_start):
            return

    # 模板识别
    def patCycleCommonResearch(self, line):
        update_flag = False
        # 所有匹配模板
        match = self.cfg.reg_config.pat_cycle_start.findall(line)
        if match:
            self.cycleNumStr = match[0][1]
            self.cycle_os_time_start = int(match[0][0])  # 当周期系统开始时间
            # 新的周期时重置之前的变量
            self.newCyclePreProcess()
            update_flag = True
        else:
            match = self.cfg.reg_config.pat_cycle_end.findall(line)
            if match:
                self.cycle_os_time_end = int(match[0][0])  # 当周期系统结束时间
                self.time_statictics = self.staticticsCycleTime(match[0][1])
                update_flag = True
            else:
                match = self.cfg.reg_config.pat_time.findall(line)
                if match:
                    self.timeContentStr = match[0]  # time 信息直接返回
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
                                self.atp2atoParser.msgParse(match[0])
                                update_flag = True
                            else:
                                match = self.cfg.reg_config.pat_o2p.findall(line)
                                if match:
                                    self.atp2atoParser.msgParse(match[0])
                                    update_flag = True
                                else:
                                    match = self.cfg.reg_config.pat_stoppoint.findall(line)
                                    if match:
                                        self.stoppoint = match[0]
                                        update_flag = True
                                    elif self.patMvbResearch(line):
                                        update_flag = True
                                    else:
                                        pass
        # 发射信号
        if update_flag == True:
            # 生成信号结果
            result = (self.cycleNumStr, self.timeContentStr, self.fsm, self.sc_ctrl, self.stoppoint,
                  self.mvbParser.ato2tcms_ctrl_obj, self.mvbParser.ato2tcms_state_obj, 
                  self.mvbParser.tcms2ato_state_obj,self.atp2atoParser.msg_obj, self.time_statictics)
            self.patShowSignal.emit(result)

        # 返回用于画图
        return update_flag

    # 实时图形绘制
    def paintArrayUpdate(self):
        if self.sc_ctrl:  # 如果匹配成功
            newPaintList[0, self.newPaintCnt] = self.sc_ctrl[1]   # 当前速度
            newPaintList[1, self.newPaintCnt] = self.sc_ctrl[2]   # ATO命令速度
            newPaintList[2, self.newPaintCnt] = self.sc_ctrl[3]   # ATP命令速度
            newPaintList[3, self.newPaintCnt] = self.sc_ctrl[4]   # ATP允许速度
            newPaintList[4, self.newPaintCnt] = self.sc_ctrl[6]   # 输出级位
            self.newPaintCnt += 1
        else:
            pass

        if self.newPaintCnt == real_curve_buff:
            paintList[:, real_curve_buff:real_curve_all_buff] = paintList[:, 0:real_curve_all_buff - real_curve_buff]
            paintList[:, 0:real_curve_buff] = newPaintList[:, 0:real_curve_buff]
            # 清除列表
            self.newPaintCnt = 0

    # 测速测距识别
    def patSduInfoResearch(self, line=str, cycleTime=int):
        updateflag = False
        self.sduInfoParser.sduInfoStringParse(line, cycleTime)
        # 收集到sdu_ato和sdu_atp
        if self.sduInfoParser.sduInfo.updateflag:
            self.sduShowSignal.emit(self.sduInfoParser.sduInfo)
            updateflag = True
        else:
            pass
        return updateflag

    # IO查询
    def patIoInfoResearch(self, line):
        updateflag = False
        self.ioInfoParser.ioStringParse(line)
        # 发送信号
        if self.ioInfoParser.ioInfo.updateflagIn == True or self.ioInfoParser.ioInfo.updateflagOut:
            self.ioShowSignal.emit(self.cycleNumStr, self.timeContentStr, self.ioInfoParser.ioInfo)
            updateflag = True
        else:
            pass
        return updateflag

    # 解析MVB内容
    def patMvbResearch(self, line):
        updateflag = False
        # 前提条件
        if 'MVB[' in line:
            self.mvbParser.parseProtocol(line)
            if self.mvbParser.ato2tcms_ctrl_obj.updateflag or \
                self.mvbParser.ato2tcms_state_obj.updateflag or \
                self.mvbParser.tcms2ato_state_obj.updateflag:
                updateflag = True
        return updateflag

    # 提取计划内容
    def patPlanResearch(self, line=str, osTime=int):
        # 提高解析效率,当均更新时才发送信号
        if '[RP' in line:
            self.rpParser.rpStringParse(line, osTime)
        # 发送信号
        if self.rpParser.rpInfo.updateflag:
            self.planShowSignal.emit(self.rpParser.rpInfo, osTime)
        else:
            pass
        # 返回用于指示解析结果
        return self.rpParser.rpInfo.updateflag

    # 统计ATO周期的运行时间, None不更新
    def staticticsCycleTime(self, cycle_num):
        if int(cycle_num) != int(self.cycleNumStr):
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
            

