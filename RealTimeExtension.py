import os
import queue
import re
import threading
import time

import numpy as np
from PyQt5 import QtCore

from FileProcess import FileProcess
from ProtocolParse import MVBParse

exit_flag = 0
queueLock = threading.Lock()
workQueue = queue.Queue(10000)
real_curve_buff = 10                                 # 每次绘图话添加的点数
real_curve_all_buff = 10000                          # 每次绘画总点数
newPaintList = np.zeros([5, real_curve_buff])        # 新添加的参数
paintList = np.zeros([5, real_curve_all_buff])                     # 初始化1000个点用于绘图

pat_ato_ctrl = ''
pat_ato_stat = ''
pat_tcms_Stat = ''


class SerialRead(threading.Thread, QtCore.QObject):

    def __init__(self, name, serialport):
        threading.Thread.__init__(self)
        self.name = name
        self.ser = serialport
        super(QtCore.QObject, self).__init__()

    # 串口成功打开才启动此线程
    def run(self):
        # 读取串口内容
        #with open('10291540-Serial-COM39.log') as f:
        while not exit_flag:
            # 有数据就读取
            try:
                #line = f.readline().rstrip()
                #time.sleep(0.01)
                line = self.ser.readline().decode('ansi', errors='ignore').rstrip()  # 串口设置，测试时注释
            except UnicodeDecodeError as err:
                print("serial read err")
                print(err)
            # 若队列未满，则继续加入
            if not workQueue.full():
                try:
                    workQueue.put(line, block=True)   # 必须读到数据
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
        pat_cycle_start = re.compile('---CORE_TARK CY_B (\d+),(\d+).')  # 周期终点匹配
        pat_cycle_end = re.compile('---CORE_TARK CY_E (\d+),(\d+).')
        self.pat_list = FileProcess.create_all_pattern()
        self.pat_list.insert(0, pat_cycle_start)
        self.pat_list.insert(1, pat_cycle_end)
        self.pat_plan = FileProcess.creat_plan_pattern()  # 计划解析模板
        # 周期开始时间
        self.cycle_os_time = 0
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
        # MVB 解析模板
        self.pat_ato_ctrl = ''
        self.pat_ato_stat = ''
        self.pat_tcms_Stat = ''

        self.mvbParser = MVBParse()
        self.ato2tcms_ctrl = []
        self.ato2tcms_stat = []
        self.tcms2ato_stat = []
        # 静态变量
        self.gfx_flag = 0
        self.cycle_num = '0'
        self.time_content = ''
        self.fsm = []
        self.sc_ctrl = []
        self.stoppoint = []
        self.sp2_real = ()
        self.sp5_real = ()
        self.sp131_real = ()
        # io 信息
        self.io_in_real = ()
        self.io_out_real = []
        # btm信息
        self.sp7_real = ()
        # 测速测距
        self.sdu_ato = []
        self.sdu_atp = []
        self.state_machine = 0  # 测速测距检查使用的状态机

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
                    self.fileWrite(line, f)
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

    # 模板识别
    def pat_research(self, line):
        update_flag = 0
        # 解析基本参数，相对于离线解析，模板中增加了周期开始和结束的识别
        # 所以模板序号
        if self.pat_list[0].findall(line):
            temp = self.pat_list[0].findall(line)[0]
            self.cycle_num = temp[1]
            self.cycle_os_time = int(temp[0])  # 当周期系统时间
            update_flag = 1
        elif self.pat_list[2].findall(line):
            self.time_content = self.pat_list[2].findall(line)[0]  # time 信息直接返回
            update_flag = 1
        elif self.pat_list[3].findall(line):
            self.fsm = self.pat_list[3].findall(line)[0]
            update_flag = 1
        elif self.pat_list[4].findall(line):
            self.sc_ctrl = self.pat_list[4].findall(line)[0]
            if self.sp2_real:
                self.sc_ctrl = self.sc_ctrl[:4] + (self.sp2_real[11],) + self.sc_ctrl[4:]  # tuple拼接
            else:
                self.sc_ctrl = self.sc_ctrl[:4] + ('32768',) + self.sc_ctrl[4:]
            update_flag = 1
        elif self.pat_list[5].findall(line):
            self.stoppoint = self.pat_list[5].findall(line)[0]
            update_flag = 1
        elif self.mvb_research(line):
            update_flag = 1
        elif self.pat_list[8].findall(line):  # 这是SP2的正则解析情况
            update_flag = 1
            sp2 = re.split(',', line[:-1])  # 删除最后一个回车字符,按照逗号分隔
            # 检查长度
            temp = tuple(sp2[1:])  # 保持与其他格式一致，从SP2后截取
            try:
                if len(temp) == 26:  # 包括包序号在内一共长度是27个
                    self.sp2_real = temp
                    if int(self.sp2_real[13]) == 1:  # 去除nid——packet是第13个字节
                        self.gfx_flag = 1
                    else:
                        self.gfx_flag = 0  # 包含真正过分相及错误数据
            except Exception as err:
                print('gfx_err ')
        elif self.pat_list[9].findall(line):  # 这是SP5的正则解析情况
            update_flag = 1
            self.sp5_real = self.pat_list[9].findall(line)[0]
        elif self.pat_list[14].findall(line):  # 这是SP131的正则解析情况
            update_flag = 1
            self.sp131_real = self.pat_list[14].findall(line)[0]
        # 生成信号结果
        result = (self.cycle_num, self.time_content, self.fsm, self.sc_ctrl, self.stoppoint,
                  self.ato2tcms_ctrl, self.ato2tcms_stat, self.tcms2ato_stat,
                  self.gfx_flag, self.sp2_real, self.sp5_real, self.sp131_real)
        # 发射信号
        if update_flag == 1:
            self.pat_show_signal.emit(result)
        # 匹配计划，内部使用独立信号
        self.plan_research(line, self.cycle_num)
        # io 独立信号
        self.pat_io_research(line)
        # btm独立信号
        self.pat_btm_research(line)
        # 测速测距识别
        self.pat_sdu_research(line)
        # 返回用于画图
        return result

    # 测速测距识别
    def pat_sdu_research(self, line):
        result = ()
        # 查找或清空
        if self.pat_list[30].findall(line):
            self.sdu_atp = self.pat_list[30].findall(line)[0]
            self.state_machine = 1
            # 查找或清空
        if self.pat_list[29].findall(line):
            self.sdu_ato = self.pat_list[29].findall(line)[0]
            # 如果已经收到了sdu_ato
            if self.state_machine == 1:
                self.state_machine = 2    # 置状态机为2.收到ATP
        # 组合数据,前面安装时间和周期
        result = (self.sdu_ato, self.sdu_atp)

        # 收集到sdu_ato和sdu_atp, 终止状态机，发送信号清空
        if self.state_machine == 2:
            self.sdu_show_signal.emit(result)
            self.state_machine = 0
            self.sdu_ato = []
            self.sdu_atp = []
        else:
            pass

    # IO查询
    def pat_io_research(self, line):
        result = ()
        update_flag = 0
        # 查找或清空
        if self.pat_list[27].findall(line):
            self.io_in_real = self.pat_list[27].findall(line)[0]
            update_flag = 1
        else:
            self.io_in_real = ()
        # 查找或清空
        if self.pat_list[28].findall(line):
            self.io_out_real = self.pat_list[28].findall(line)[0]
            update_flag = 1
        else:
            self.io_out_real = ()
        # 组合数据,前面安装时间和周期
        result = (self.cycle_num, self.time_content, self.io_in_real, self.io_out_real)
        # 发送信号
        if update_flag == 1:
            self.io_show_signal.emit(result)
        else:
            pass

    # btm查询
    def pat_btm_research(self, line):
        if len(self.sp2_real) == 26:
            mile_stone = self.sp2_real[23]    # 获取公里标，逗号分隔后，除去nid后第22个
        else:
            mile_stone = ''
        result = ()
        update_flag = 0
        # 解析基本参数，相对于离线解析，模板中增加了周期开始和结束的识别
        # 所以模板序号
        if self.pat_list[11].findall(line):
            self.sp7_real = self.pat_list[11].findall(line)[0]
            update_flag = 1
        else:
            pass
        # 组合数据
        result = (self.time_content, self.sp7_real, mile_stone)
        # 发送信号
        if update_flag == 1:
            self.sp7_show_signal.emit(result)
        else:
            pass

    # 解析MVB内容
    def mvb_research(self, line):
        global pat_ato_ctrl
        global pat_ato_stat
        global pat_tcms_stat
        real_idx = 0  # 对于记录打印到同一行的情况，首先要获取实际索引
        tmp = ''
        parse_flag = 0
        if pat_ato_ctrl in line:
            if '@' in line:
                pass
            else:
                real_idx = line.find('MVB[')
                tmp = line[real_idx + 10:]  # 还有一个冒号需要截掉
                self.ato2tcms_ctrl = self.mvbParser.ato_tcms_parse(1025, tmp)
                if self.ato2tcms_ctrl:
                    parse_flag = 1
        elif pat_ato_stat in line:
            if '@' in line:
                pass
            else:
                real_idx = line.find('MVB[')
                tmp = line[real_idx + 10:]  # 还有一个冒号需要截掉
                self.ato2tcms_stat = self.mvbParser.ato_tcms_parse(1041, tmp)
                if self.ato2tcms_stat:
                    parse_flag = 1
        elif pat_tcms_stat in line:
            if '@' in line:
                pass
            else:
                real_idx = line.find('MVB[')
                tmp = line[real_idx + 10:]  # 还有一个冒号需要截掉
                self.tcms2ato_stat = self.mvbParser.ato_tcms_parse(1032, tmp)
                if self.tcms2ato_stat:
                    parse_flag = 1
        return parse_flag

    # 提取计划内容
    def plan_research(self, line, cycle_num):
        update_flag = 0
        ret_plan = ()
        temp_utc = ''
        temp_transfer_list = []
        # 提高解析效率,当均更新时才发送信号
        if '[RP' in line:
            if self.pat_plan[0].findall(line):
                self.rp1 = self.pat_plan[0].findall(line)[0]
                update_flag = 1

            elif self.pat_plan[1].findall(line):
                self.rp2 = self.pat_plan[1].findall(line)[0]
                update_flag = 1

            elif self.pat_plan[2].findall(line):
                # 当周期改变时清除，只存储同一周期的
                if int(cycle_num) != int(self.plan_in_cycle):
                    self.rp2_list = []
                    # 替换其中UTC时间
                    temp_transfer_list = self.Comput_Plan_Content(self.pat_plan[2].findall(line)[0])
                    self.rp2_list.append(tuple(temp_transfer_list))
                    self.plan_in_cycle = cycle_num
                else:
                    # 替换其中的UTC时间
                    temp_transfer_list = self.Comput_Plan_Content(self.pat_plan[2].findall(line)[0])
                    self.rp2_list.append(tuple(temp_transfer_list))
                    update_flag = 1

            elif self.pat_plan[3].findall(line):
                self.rp3 = self.pat_plan[3].findall(line)[0]
                update_flag = 1

            elif self.pat_plan[4].findall(line):
                self.rp4 = self.pat_plan[4].findall(line)[0]
                if int(self.rp4[1]) != 0:
                    self.time_plan_remain = int(self.rp4[1]) - self.cycle_os_time
                if int(self.rp4[2]) != 0:
                    self.time_plan_count = int(self.rp4[2]) - self.cycle_os_time
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
    def Comput_Plan_Content(self, t=tuple):
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
