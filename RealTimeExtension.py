import pickle
import os
import queue
import threading
import time
import numpy as np
from PyQt5 import QtCore
import serial
from MainWinDisplay import InerIoInfo, InerIoInfoParse, InerRunningPlanInfo, InerRunningPlanParse, InerSduInfo, InerSduInfoParse
from MsgParse import Ato2tsrsParse, Atp2atoParse, Tsrs2atoParse
from TcmsParse import Ato2TcmsCtrl, Ato2TcmsState, MVBParse, Tcms2AtoState
from ConfigInfo import ConfigFile

_sentinel = object()                                 # Object that signals shutdown
workQueue = queue.Queue(10000)
real_curve_buff = 50                                 # 每次绘图话添加的点数
real_curve_all_buff = 50000                          # 每次绘画总点数
newPaintList = np.zeros([5, real_curve_buff],dtype=int)        # 新添加的参数
paintList = np.zeros([5, real_curve_all_buff],dtype=int)       # 初始化1000个点用于绘图

class SerialRead(threading.Thread, QtCore.QObject):

    def __init__(self, name, serialHandle=serial.Serial):
        threading.Thread.__init__(self)
        self.name = name
        self.handle = serialHandle
        self.handle.set_buffer_size(4096)
        self.runningFlag = False
        super(QtCore.QObject, self).__init__()

    # 串口成功打开才启动此线程
    def run(self):
        while self.runningFlag:
            # 有数据就读取
            try:
                lineBytes = self.handle.read_until()  # 串口设置，测试时注释 默认终止符\n
            except UnicodeDecodeError as err:
                print("serial read unicode error!")
            # 若队列未满，则继续加入:
            if not workQueue.full():
                workQueue.put(pickle.loads(pickle.dumps(lineBytes)), block=False, timeout=0.1)   # 必须读到数据
            else:
                time.sleep(0.1)
        # 发送停止信号
        workQueue.put(_sentinel)

    
    # 允许线程
    def setThreadEnabled(self, en=bool):
        self.runningFlag = en
        if en:
            pass
        elif self.handle and self.handle.is_open:
            self.handle.cancel_read()
            time.sleep(0.1)
            self.handle.reset_input_buffer()
            self.handle.flush()
            self.handle.close()
        else:
            pass

class RealPaintWrite(threading.Thread, QtCore.QObject):

    patShowSignal = QtCore.pyqtSignal(tuple)
    planShowSignal = QtCore.pyqtSignal(InerRunningPlanInfo, int)
    ioShowSignal = QtCore.pyqtSignal(str,str,InerIoInfo)
    sduShowSignal = QtCore.pyqtSignal(InerSduInfo)
    mvbShowSignal = QtCore.pyqtSignal(Ato2TcmsCtrl, Ato2TcmsState, Tcms2AtoState)

    def __init__(self, filepath=str, filefmt=str, portname=str):
        threading.Thread.__init__(self, )
        super(QtCore.QObject, self).__init__()
        self.portname = portname
        self.filepath = filepath  # 记录文件路径
        self.logFile = filepath + 'ATO记录中' + str(int(time.time())) + '.txt'  # 纪录写入文件
        self.logBuff = ''
        self.filename = self.getFileNameFromFmt(filefmt)  # 文件格式化命名
        self.cfg = ConfigFile()
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
        self.ato2tsrsParser = Ato2tsrsParse()
        self.tsrs2atoParser = Tsrs2atoParse()
        # 解析结果
        self.a2tCtrlObj  = None
        self.a2tStatObj  = None
        self.t2aStatObj  = None
        self.atpatoMsgObj= None
        self.sduInfoObj  = None
        self.rpInfoObj   = None
        self.ioInfoObj   = None
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

    def newCyclePreProcess(self):
        # 创建周期后应重置ATP/ATO解析模块解析结果
        # 文件中可能有多个ATP/ATO消息时需要均解析，直到所有P->以及O->P解析完成后周期结束才能重置
        # 因为不同消息中可能带有差异项的包，需要在一个周期内均保留解析结果，在周期头或周期尾重置
        self.atp2atoParser.resetMsg()
        # MVB总是覆盖解析
        self.mvbParser.resetPacket()
        # 每周期重置更新标志
        self.rpParser.reset()
        # 重置测速测距
        self.sduInfoParser.reset()
        # 重置IO信息
        self.ioInfoParser.reset()
        # 重置ATO-TSRS消息
        self.ato2tsrsParser.resetMsg()
        self.tsrs2atoParser.resetMsg()

    # 串口成功打开才启动该线程
    def run(self):
        # 打开文件等待写入logFile
        with open(self.logFile, 'w', encoding='utf-8') as f:
            while True:
                if not workQueue.empty():
                    lineBytes = workQueue.get(block=False, timeout=0.1)
                    # 收到信号进行停止
                    if lineBytes is _sentinel:
                        break
                    else:
                        lineText = lineBytes.decode('gbk', errors='ignore').strip()
                        # 防止数据处理过程中被刷新
                        self.fileWrite(lineText, f) # 测试时关闭
                        self.lineProcessPaint(lineText)
                else:
                    time.sleep(0.1)
            # 清空缓存
            self.fileFlush(f)
        os.rename(self.logFile, self.filepath + self.filename)

    # 按行写入文件
    def fileWrite(self, line, f):
        try:
            f.write(line+'\n')
        except Exception as err:
            print('write info err' + str(time.time()))
            print(err)

    # 立即写入用于关断时候
    def fileFlush(self, f):
        # 目前预留不使用文件缓存
        for item in self.logBuff:
            f.write(item+'\n')
        f.flush()
        print("file exit flush!")

    # 每次测试完后重命名文件
    def getFileNameFromFmt(self, fmt=str):
        # 保存文件，立即更新文件名
        stuctLocTime = time.localtime(time.time())
        try:
            fmt = fmt.replace('%Y', str(stuctLocTime.tm_year), 1)
            fmt = fmt.replace('%M', str(stuctLocTime.tm_mon), 1)
            fmt = fmt.replace('%D', str(stuctLocTime.tm_mday), 1)
            fmt = fmt.replace('%h', str(stuctLocTime.tm_hour), 1)
            fmt = fmt.replace('%m', str(stuctLocTime.tm_min), 1)
            fmt = fmt.replace('%s', str(stuctLocTime.tm_sec), 1)
            fmt = fmt.replace('%N', self.portname, 1)
        except Exception as err:
            fmt = 'ATO' + str(stuctLocTime.tm_year) + str(stuctLocTime.tm_mon) + str(
                stuctLocTime.tm_mday) \
                          + str(stuctLocTime.tm_hour) + str(stuctLocTime.tm_min) + str(
                stuctLocTime.tm_sec) \
                          + self.portname
        return fmt

    # 处理和绘图
    def lineProcessPaint(self, line):
        # 更新绘制情况
        self.paintArrayUpdate()

        # 匹配速度曲线信息
        if self.patCycleCommonResearch(line):
            return  

        # 匹配MVB信息
        if self.patMvbResearch(line):
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
                else:
                    match = self.cfg.reg_config.pat_fsm.findall(line)
                    if match:
                        self.fsm = match[0]
                    else:
                        match = self.cfg.reg_config.pat_ctrl.findall(line)
                        if match:
                            self.sc_ctrl = match[0]
                            # 允许速度处理
                            self.sc_ctrl = self.sc_ctrl[:4] + (str(self.atp2atoParser.msg_obj.sp2_obj.v_permitted),) + self.sc_ctrl[4:]  # tuple拼接
                        else:
                            match = self.cfg.reg_config.pat_p2o.findall(line)
                            if match:
                                self.atp2atoParser.msgParse(match[0])
                            else:
                                match = self.cfg.reg_config.pat_o2p.findall(line)
                                if match:
                                    self.atp2atoParser.msgParse(match[0])
                                else:
                                    match = self.cfg.reg_config.pat_a2t.findall(line)
                                    if match:
                                        self.ato2tsrsParser.msgParse(match[0])
                                    else:
                                        match = self.cfg.reg_config.pat_t2a.findall(line)
                                        if match:
                                            self.tsrs2atoParser.msgParse(match[0])
                                        else:
                                            match = self.cfg.reg_config.pat_stoppoint.findall(line)
                                            if match:
                                                self.stoppoint = match[0]
                                            else:
                                                pass
        # 发射信号
        if update_flag == True:
            # 生成信号结果
            result = (self.cycle_os_time_start, self.cycleNumStr, self.timeContentStr, 
            self.fsm, self.sc_ctrl, self.stoppoint,
            self.atp2atoParser.msg_obj,self.mvbParser.tcms2ato_state_obj, self.time_statictics,
            self.ato2tsrsParser.msg_obj, self.tsrs2atoParser.msg_obj)
            self.patShowSignal.emit(pickle.loads(pickle.dumps(result)))
            del result
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
        if 'v&p' in line:
            self.sduInfoParser.sduInfoStringParse(line, cycleTime)
            updateflag = self.sduInfoParser.sduInfo.updateflag
        # 收集到sdu_ato和sdu_atp
        if updateflag:
            self.ioInfoObj = pickle.loads(pickle.dumps(self.sduInfoParser.sduInfo))
            self.sduShowSignal.emit(self.ioInfoObj)
        else:
            pass
        return updateflag

    # IO查询
    def patIoInfoResearch(self, line):
        updateflag = False
        self.ioInfoParser.ioStringParse(line)
        # 发送信号
        if self.ioInfoParser.ioInfo.updateflagIn == True or self.ioInfoParser.ioInfo.updateflagOut:
            self.ioInfoObj =  pickle.loads(pickle.dumps(self.ioInfoParser.ioInfo))
            self.ioShowSignal.emit(self.cycleNumStr, self.timeContentStr, self.ioInfoObj)
            updateflag = True
        else:
            pass
        return updateflag

    # 解析MVB内容
    def patMvbResearch(self, line):
        updateflag = False
        # 前提条件
        if 'MVB[' in line:
            match = self.cfg.reg_config.pat_mvb.findall(line)
            if match:
                [a2tCtrl, a2tStat, t2aStat ] = self.mvbParser.parseProtocol(match[0])
                updateflag = True
                # 当匹配成功时拷贝
                if self.mvbParser.ato2tcms_ctrl_obj.updateflag or \
                    self.mvbParser.ato2tcms_state_obj.updateflag or \
                    self.mvbParser.tcms2ato_state_obj.updateflag:

                    self.a2tCtrlObj = pickle.loads(pickle.dumps(a2tCtrl))
                    self.a2tStatObj = pickle.loads(pickle.dumps(a2tStat))
                    self.t2aStatObj = pickle.loads(pickle.dumps(t2aStat))
                    self.mvbShowSignal.emit(self.a2tCtrlObj,self.a2tStatObj, self.t2aStatObj)
        return updateflag

    # 提取计划内容
    def patPlanResearch(self, line=str, osTime=int):
        updateflag = False
        # 提高解析效率,当均更新时才发送信号
        if '[RP' in line:
            self.rpParser.rpStringParse(line, osTime)
            updateflag = self.rpParser.rpInfo.updateflag
        # 发送信号
        if updateflag:
            self.rpInfoObj = pickle.loads(pickle.dumps(self.rpParser.rpInfo))
            self.planShowSignal.emit(self.rpInfoObj, osTime)
        else:
            pass
        # 返回用于指示解析结果
        return updateflag

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
            

