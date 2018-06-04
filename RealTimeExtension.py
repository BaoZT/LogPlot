import matplotlib
import serial
import os
import threading
import queue
import time
import re
import numpy as np
import random
from FileProcess import FileProcess
from PyQt5 import QtCore
from ProtocolParse import MVBParse

exit_flag = 0
queueLock = threading.Lock()
workQueue = queue.Queue(10000)
newPaintList = np.zeros([4, 10])      # 新添加的参数
paintList = np.zeros([4, 1000])       # 初始化1000个点用于绘图

value = 0  # 速度值 测试用
random.seed(10)

pat_ato_ctrl = ''
pat_ato_stat = ''
pat_tcms_Stat = ''

class SerialRead(threading.Thread, QtCore.QObject):

    pat_show_singal = QtCore.pyqtSignal(tuple)

    def __init__(self, name, serialport):
        threading.Thread.__init__(self)
        self.name = name
        self.ser = serialport
        super(QtCore.QObject, self).__init__()
        pat_cycle_start = re.compile('---CORE_TARK CY_B (\d+),(\d+).')  # 周期终点匹配
        pat_cycle_end = re.compile('---CORE_TARK CY_E (\d+),(\d+).')
        self.pat_list = FileProcess.create_all_pattern()
        self.pat_list.insert(0, pat_cycle_start)
        self.pat_list.insert(1, pat_cycle_end)
        self.newPaintCnt = 0
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
        self.cycle_num = ''
        self.time_content = ''
        self.fsm = []
        self.sc_ctrl = []
        self.stoppoint = []

    # 串口成功打开才启动此线程
    def run(self):
        # 读取串口内容
        # with open('序列35整理.txt','r') as f:
        while not exit_flag:
            s = time.time()
            # 有数据就读取
            try:
                # time.sleep(0.01)
                # line = f.readline()
                line = self.ser.readline().decode('ansi').rstrip()    # 串口设置
                queueLock.acquire()
                if not workQueue.full():
                    workQueue.put(line)
                    self.paintProcess(line)
                    queueLock.release()
                    # print('in-%f'%(time.time() - s))
                else:
                    queueLock.release()
                    print('queue is full!')
                    # 处理画图信息
            except Exception as err:
                    print(err)

    def paintProcess(self, line):

        # 控车信息，显示信息，周期信息等
        # 匹配速度曲线信息
        result = self.pat_research(line)
        sc_ctrl = result[3]
        if sc_ctrl != []:  # 如果匹配成功
            newPaintList[0, self.newPaintCnt] = sc_ctrl[1]
            newPaintList[1, self.newPaintCnt] = sc_ctrl[2]
            newPaintList[2, self.newPaintCnt] = sc_ctrl[3]
            newPaintList[3, self.newPaintCnt] = sc_ctrl[4]
            self.newPaintCnt += 1
        else:
            pass

        if self.newPaintCnt == 10:
            paintList[:, 10:1000] = paintList[:, 0:990]
            paintList[:, 0:10] = newPaintList[:, 0:10]

            # 清除列表
            self.newPaintCnt = 0

            # 实时line匹配内容

    def pat_research(self, line):
        update_flag = 0
        # 解析基本参数，相对于离线解析，模板中增加了周期开始和结束的识别
        # 所以模板序号
        if self.pat_list[0].findall(line):
            temp = self.pat_list[0].findall(line)[0]
            self.cycle_num = temp[1]
            update_flag = 1
        elif self.pat_list[2].findall(line):
            self.time_content = self.pat_list[2].findall(line)[0]  # time 信息直接返回
            update_flag = 1
        elif self.pat_list[3].findall(line):
            self.fsm = self.pat_list[3].findall(line)[0]
            update_flag = 1
        elif self.pat_list[4].findall(line):
            self.sc_ctrl = self.pat_list[4].findall(line)[0]
            update_flag = 1
        elif self.pat_list[5].findall(line):
            self.stoppoint = self.pat_list[5].findall(line)[0]
            update_flag = 1
        elif self.mvb_research(line):
            update_flag = 1
        elif self.pat_list[7].findall(line):
            update_flag == 1
            l = re.split(',', line)
            temp = tuple(l[1:])          # 保持与其他格式一致，从SP2后截取
            try:
                if int(temp[13]) == 1:   # 去除nid——packet是第13个字节
                    self.gfx_flag = 1
                else:
                    self.gfx_flag = 0    # 包含真正过分相及错误数据
            except Exception as err:
                print('gfx_err ')
        result = (self.cycle_num, self.time_content, self.fsm, self.sc_ctrl, self.stoppoint,
                  self.ato2tcms_ctrl, self.ato2tcms_stat, self.tcms2ato_stat,
                  self.gfx_flag)
        # 发射信号
        if update_flag == 1:
            self.pat_show_singal.emit(result)
        else:
            pass
        return result

        # 解析MVB内容

    def mvb_research(self, line):
        global pat_ato_ctrl
        global pat_ato_stat
        global pat_tcms_stat
        tmp = ''
        parse_flag = 0
        if pat_ato_ctrl in line:
            if '@' in line:
                pass
            else:
                tmp = line[10:]  # 还有一个冒号需要截掉
                self.ato2tcms_ctrl = self.mvbParser.ato_tcms_parse(1025, tmp)
                if self.ato2tcms_ctrl != []:
                    parse_flag = 1
        elif pat_ato_stat in line:
            if '@' in line:
                pass
            else:
                tmp = line[10:]
                self.ato2tcms_stat = self.mvbParser.ato_tcms_parse(1041, tmp)
                if self.ato2tcms_stat != []:
                    parse_flag = 1
        elif pat_tcms_stat in line:
            if '@' in line:
                pass
            else:
                tmp = line[10:]
                self.tcms2ato_stat = self.mvbParser.ato_tcms_parse(1032, tmp)
                if self.tcms2ato_stat != []:
                    parse_flag = 1
        return parse_flag


class RealPaintWrite(threading.Thread):

    def __init__(self, filepath=str, filenamefmt=str, portname=str):
        threading.Thread.__init__(self, )
        self.filepath = filepath  # 记录文件路径
        self.logFile = filepath + 'ATO记录中' + str(int(time.time())) + '.txt'  # 纪录写入文件
        self.logBuff = []
        self.filenamefmt = filenamefmt  # 文件格式化命名
        self.portname = portname

    # 串口成功打开才启动该线程
    def run(self):
        # 打开文件等待写入logFile
        with open(self.logFile, 'w') as f:

            while not exit_flag:
                try:
                    s = time.time()
                    queueLock.acquire()
                    if not workQueue.empty():
                        line = workQueue.get()
                        self.fileWrite(line, f)
                        queueLock.release()
                    else:
                        queueLock.release()
                        time.sleep(1)  # 队列为空等1s
                    # print('out-%f' % (time.time() - s))
                except Exception as err:
                    print(err)
            # 清空缓存
            self.fileFlush(f)
            # 线程停止
            f.close()
            tmp = self.fileRename()
            os.rename(self.logFile, self.filepath + tmp)


    # 按行写入文件
    def fileWrite(self, line, f):
        self.logBuff.append(line)
        if len(self.logBuff) == 2000:
            for item in self.logBuff:
                f.write(item + '\n')
            # 写完后清空
            self.logBuff = []
        else:
            pass

    # 立即写入用于关断时候
    def fileFlush(self, f):
        for item in self.logBuff:
            f.write(item + '\n')  # 由于记录中本身有回车，去掉\r\n

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