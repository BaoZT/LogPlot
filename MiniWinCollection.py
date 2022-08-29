#!/usr/bin/env python
# encoding: utf-8

'''
@author:  Baozhengtang
@license: (C) Copyright 2017-2020, Author Limited.
@contact: baozhengtang@gmail.com
@software: LogPlot
@file: MiniWinCollection.py
@time: 2018/6/3 9:45
@desc: 主要用于聚集主窗口中弹出的临时小窗口，包括工具和设置
'''
import matplotlib

from CycleInfo import Ui_MainWindow as CycleWin
from MsgParse import Atp2atoParse, Atp2atoProto
from ProtoParserWin import Ui_MainWindow as ParserWin
from MeasureWin import Ui_MainWindow as MeasureWin
from C3atoRecordTranslator import Ui_Dialog as C3ATOTransferWin

matplotlib.use("Qt5Agg")  # 声明使用QT5
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from TcmsParse import Ato2TcmsCtrl, Ato2TcmsState, MVBFieldDic, MVBParse, Tcms2AtoState, DisplayMVBField
from PyQt5 import QtWidgets, QtCore, QtGui
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from KeyWordPlot import SnaptoCursor
from Transfer2Debug import TransRecord       # 导入转义函数
import FileProcess
import serial
import serial.tools.list_ports
import time
import re
import os
import shutil
import numpy as np
from threading import Thread
from ConfigInfo import ConfigFile


# 周期界面类
class Cyclewindow(QtWidgets.QMainWindow, CycleWin):
    def __init__(self):
        super(Cyclewindow, self).__init__()
        self.setupUi(self)
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/BZT.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        self.icon_from_file()
        self.actionCycleSave.triggered.connect(self.save_log)
        self.actionCopy.triggered.connect(self.copy_cliperboard)

    # 事件处理函数，向指定路径中写入该周期
    def save_log(self, str_list=list):
        filepath = QtWidgets.QFileDialog.getSaveFileName(self, "Save file", "d:/", "txt files(*.txt)")
        if filepath != ('', ''):
            f = open(filepath[0], "w")
            f.write(str(self.textEdit.toPlainText()))
            f.close()
            self.statusBar.showMessage(filepath[0] + "成功保存该周期！")
        else:
            pass

    # 事件处理函数，复制当前周期内容
    def copy_cliperboard(self):
        cliper = QtWidgets.QApplication.clipboard()
        cliper.setText(str(self.textEdit.toPlainText()))
        self.statusBar.showMessage("成功复制周期！")

    # 用于将图标资源文件打包
    def icon_from_file(self):
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":IconFiles/copy.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionCopy.setIcon(icon)

        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":IconFiles/save.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionCycleSave.setIcon(icon1)


# 串口设置类
class SerialDlg(QtWidgets.QDialog):
    serUpdateSingal = QtCore.pyqtSignal(serial.Serial)  # 串口设置更新信号

    def __init__(self, parent=None):
        super(SerialDlg, self).__init__(parent)
        self.saveName = ''  # 根据设置生成文件名
        SerialCOMLabel = QtWidgets.QLabel(u'串口号')
        self.SerialCOMComboBox = QtWidgets.QComboBox()
        self.SerialCOMComboBox.addItems(self.Port_List())
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/BZT.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)

        SerialBaudRateLabel = QtWidgets.QLabel(u'波特率')
        self.SerialBaudRateComboBox = QtWidgets.QComboBox()
        self.SerialBaudRateComboBox.addItems(
            ['100', '300', '600', '1200', '2400', '4800', '9600', '14400', '19200', '38400', '56000', '57600', '115200',
             '230400', '380400', '460800', '920600'])
        self.SerialBaudRateComboBox.setCurrentIndex(13)

        SerialDataLabel = QtWidgets.QLabel(u'数据位')
        self.SerialDataComboBox = QtWidgets.QComboBox()
        self.SerialDataComboBox.addItems(['5', '6', '7', '8'])
        self.SerialDataComboBox.setCurrentIndex(3)

        SerialSTOPBitsLabel = QtWidgets.QLabel(u'停止位')
        self.SerialStopBitsComboBox = QtWidgets.QComboBox()
        self.SerialStopBitsComboBox.addItems(['1', '1.5', '2'])
        self.SerialStopBitsComboBox.setCurrentIndex(0)

        SerialParityLabel = QtWidgets.QLabel(u'奇偶校验位')
        self.SerialParityComboBox = QtWidgets.QComboBox()
        self.SerialParityComboBox.addItems(['NONE', 'EVEN', 'ODD', 'MARK', 'SPACE'])
        self.SerialParityComboBox.setCurrentIndex(0)

        self.filenamelbl = QtWidgets.QLabel('保存文件名')
        self.filenameLine = QtWidgets.QLineEdit('ATO%Y%M%D%h%m%s%N.txt')
        self.filenameLine.setMaximumWidth(123)
        self.info = QtWidgets.QLabel('说明:设置ATO记录保存文件名，其中%Y-年，%M-\n月，%D-日，%h-时，%m-分，%s-秒，%N-串口号')
        nameLayout = QtWidgets.QHBoxLayout()
        nameLayout.addWidget(self.filenamelbl)
        nameLayout.addWidget(self.filenameLine)
        infoLayout = QtWidgets.QVBoxLayout()
        infoLayout.addLayout(nameLayout)
        infoLayout.addWidget(self.info)

        self.OpenButton = QtWidgets.QPushButton(u'确定')
        self.CloseButton = QtWidgets.QPushButton(u'取消')

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.addWidget(self.OpenButton)
        buttonLayout.addWidget(self.CloseButton)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(SerialCOMLabel, 0, 0)
        layout.addWidget(self.SerialCOMComboBox, 0, 1)
        layout.addWidget(SerialBaudRateLabel, 1, 0)
        layout.addWidget(self.SerialBaudRateComboBox, 1, 1)
        layout.addWidget(SerialDataLabel, 2, 0)
        layout.addWidget(self.SerialDataComboBox, 2, 1)
        layout.addWidget(SerialSTOPBitsLabel, 3, 0)
        layout.addWidget(self.SerialStopBitsComboBox, 3, 1)
        layout.addWidget(SerialParityLabel, 4, 0)
        layout.addWidget(self.SerialParityComboBox, 4, 1)

        mainlayout = QtWidgets.QVBoxLayout()
        mainlayout.addLayout(layout)
        mainlayout.addLayout(infoLayout)
        mainlayout.addLayout(buttonLayout)

        self.setLayout(mainlayout)
        self.setWindowTitle(u'串口调试工具')

        self.OpenButton.clicked.connect(self.OpenSerial)
        self.CloseButton.clicked.connect(self.CloseSerial)
        # 获取COM号列表

    def Port_List(self):
        Com_List = []
        port_list = list(serial.tools.list_ports.comports())
        for port in port_list:
            Com_List.append(port[0])
        return Com_List

    # 取消设置
    def CloseSerial(self):
        self.close()

    # 打开设置串口
    def OpenSerial(self):
        self.handle = serial.Serial(timeout=0.2)
        self.handle.port = self.SerialCOMComboBox.currentText()
        self.handle.baudrate = self.SerialBaudRateComboBox.currentText()
        self.handle.bytesize = int(self.SerialDataComboBox.currentText())
        ParityValue = self.SerialParityComboBox.currentText()
        self.handle.parity = ParityValue[0]
        self.handle.stopbits = int(self.SerialStopBitsComboBox.currentText())
        self.serUpdateSingal.emit(self.handle)
        # 组合文件名
        self.close()
        return self.handle

# mvb端口设置类
class MVBPortDlg(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(MVBPortDlg, self).__init__(parent)
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/BZT.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        self.saveName = ''  # 根据设置生成文件名
        lbl_ato_ctrl = QtWidgets.QLabel(u'ATO控制信息(16进制)')
        lbl_ato_stat = QtWidgets.QLabel(u'ATO状态信息(16进制)')
        lbl_tcms_stat = QtWidgets.QLabel(u'车辆状态信息(16进制)')
        self.cfg = ConfigFile()
        self.cfg.readConfigFile()

        self.led_ato_ctrl = QtWidgets.QLineEdit(hex(self.cfg.mvb_config.ato2tcms_ctrl_port)[2:])
        self.led_ato_stat = QtWidgets.QLineEdit(hex(self.cfg.mvb_config.ato2tcms_state_port)[2:])
        self.led_tcms_stat = QtWidgets.QLineEdit(hex(self.cfg.mvb_config.tcms2ato_state_port)[2:])

        layout = QtWidgets.QGridLayout()
        layout.addWidget(lbl_ato_ctrl, 0, 0)
        layout.addWidget(self.led_ato_ctrl, 0, 1)
        layout.addWidget(lbl_ato_stat, 1, 0)
        layout.addWidget(self.led_ato_stat, 1, 1)
        layout.addWidget(lbl_tcms_stat, 2, 0)
        layout.addWidget(self.led_tcms_stat, 2, 1)

        self.OpenButton = QtWidgets.QPushButton(u'确定')
        self.CloseButton = QtWidgets.QPushButton(u'取消')

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.addWidget(self.OpenButton)
        buttonLayout.addWidget(self.CloseButton)

        mainlayout = QtWidgets.QVBoxLayout()
        mainlayout.addLayout(layout)
        mainlayout.addLayout(buttonLayout)

        self.OpenButton.clicked.connect(self.OpenMVB)
        self.CloseButton.clicked.connect(self.CloseMVB)

        self.setLayout(mainlayout)
        self.setWindowTitle(u'mvb端口解析')

    # 取消设置
    def CloseMVB(self):
        self.close()

    # 打开mvb串口
    def OpenMVB(self):
        # 获取配置情况重新写入 
        self.cfg.mvb_config.ato2tcms_ctrl_port = int(self.led_ato_ctrl.text(), 16)
        self.cfg.mvb_config.ato2tcms_state_port =  int(self.led_ato_stat.text(), 16)
        self.cfg.mvb_config.tcms2ato_state_port =  int(self.led_tcms_stat.text(), 16)
        self.cfg.writeConfigFile()
        self.close()

# mvb解析器
class MVBParserDlg(QtWidgets.QMainWindow, ParserWin):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/MVBParser.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        self.setWindowTitle(u'MVB协议解析')
        self.parser = MVBParse()
        self.actionParse.triggered.connect(self.parseMVB)
        self.a2tCtrl = Ato2TcmsCtrl()
        self.a2tStat = Ato2TcmsState()
        self.t2aStat = Tcms2AtoState()
       
    def parseMVB(self):
        inputLine = self.textEdit.toPlainText()
        try:
            mvbLine = re.sub('\s+', '', inputLine)
            [self.a2tCtrl,self.a2tStat, self.t2aStat] = self.parser.parseProtocol(mvbLine)
            self.showParserRst(self.a2tCtrl,self.a2tStat, self.t2aStat)
        except Exception as err:
            reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                                                      "错误",
                                                      "注意:数据异常或非16进制数据",
                                                      QtWidgets.QMessageBox.Yes)

    def showParserRst(self, a2t_ctrl=Ato2TcmsCtrl, a2tStat=Ato2TcmsState, t2aStat=Tcms2AtoState):
        self.treeWidget.clear()
        root = QtWidgets.QTreeWidgetItem(self.treeWidget)
        if a2t_ctrl.updateflag:
            root.setText(0, "ATO控制信息")
            DisplayMVBField.disNameOfTreeWidget(a2t_ctrl,root, MVBFieldDic)     
        elif a2tStat.updateflag:
            root.setText(0, "ATO状态信息")
            DisplayMVBField.disNameOfTreeWidget(a2tStat,root, MVBFieldDic)     
        elif t2aStat.updateflag:
            root.setText(0, "TCMS状态信息")
            DisplayMVBField.disNameOfTreeWidget(t2aStat,root, MVBFieldDic)     


class ATPParserDlg(QtWidgets.QMainWindow, ParserWin):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/ATPParser.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        self.setWindowTitle(u'ATP-ATO协议解析')
        self.parser = Atp2atoParse()
        self.actionParse.triggered.connect(self.parseAtp2atoProto)
        self.msg = Atp2atoProto()
    
    def parseAtp2atoProto(self):
        inputLine = self.textEdit.toPlainText()
        try:
            mvbLine = re.sub('\s+', '', inputLine)
            self.msg = self.parser.msgParse(mvbLine)
            self.showParserRst(self.msg)
        except Exception as err:
            reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                                                      "错误",
                                                      "注意:数据异常或非16进制数据",
                                                      QtWidgets.QMessageBox.Yes)
    def showParserRst(self, msg=Atp2atoProto):
        self.treeWidget.clear()
        root = QtWidgets.QTreeWidgetItem(self.treeWidget)
        if msg.nid_packet == 250:
            root.setText(0, "ATP->ATO通信消息")
        else:
            root.setText(0, "ATO->ATO通信消息")
        msgTree = QtWidgets.QTreeWidgetItem(root)
        msgTree.setText(1,"消息号")
        msgTree.setText(2, str(msg.nid_msg))
        msgTree.setText(3, "ATP-ATO通信消息固定ID=45")

        msgTree = QtWidgets.QTreeWidgetItem(root)
        msgTree.setText(1,"消息长度")
        msgTree.setText(3, "全部消息长度,单位字节")
        msgTree.setText(2, str(msg.l_msg))

        msgTree = QtWidgets.QTreeWidgetItem(root)
        msgTree.setText(1,"信息包号")
        msgTree.setText(2, str(msg.nid_packet))
        msgTree.setText(3, "标识ATP-ATO通信方向")
        
        msgTree = QtWidgets.QTreeWidgetItem(root)
        msgTree.setText(1,"信息包长度")
        msgTree.setText(2, str(msg.l_packet))
        msgTree.setText(3, "信息包长度（包含所有子信息包）,单位比特")

        root2 = QtWidgets.QTreeWidgetItem(self.treeWidget)
        root2.setText(0, "SP2")

# UTC时间解析器
class UTCTransferDlg(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(UTCTransferDlg, self).__init__(parent)
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/UTCParser.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)

        utctime = QtWidgets.QLabel(u'UTC时间值')
        loctime = QtWidgets.QLabel(u'日历时间值')

        self.utc = QtWidgets.QLineEdit('')
        self.local = QtWidgets.QLineEdit('')

        layout = QtWidgets.QGridLayout()
        layout.addWidget(utctime, 0, 0)
        layout.addWidget(self.utc, 0, 1)
        layout.addWidget(loctime, 1, 0)
        layout.addWidget(self.local, 1, 1)

        self.OpenButton = QtWidgets.QPushButton(u'确定')

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.addWidget(self.OpenButton)

        mainlayout = QtWidgets.QVBoxLayout()
        mainlayout.addLayout(layout)
        mainlayout.addLayout(buttonLayout)

        self.OpenButton.clicked.connect(self.push_btn_utc)

        self.setLayout(mainlayout)
        self.setWindowTitle(u'UTC时间转换器')

    def push_btn_utc(self):
        tmp = self.utc.text()
        try:
            self.local.setText(self.transfer_utc(tmp))
        except Exception as err:
            reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                                                      "错误",
                                                      "注意：UTC时间有误，请修改",
                                                      QtWidgets.QMessageBox.Yes)

    def transfer_utc(self, t=str):
        ltime = time.localtime(int(t))
        timeStr = time.strftime("%Y-%m-%d %H:%M:%S", ltime)
        return timeStr


# 实时绘图设置类
class RealTimePlotDlg(QtWidgets.QDialog, QtCore.QObject):
    realtime_plot_set_signal = QtCore.pyqtSignal(int, bool)

    def __init__(self, parent=None):
        super(RealTimePlotDlg, self).__init__(parent)
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/BZT.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)

        plot_cycle = QtWidgets.QLabel('绘图周期')
        is_plot_flag = QtWidgets.QLabel('是否绘图')

        self.plot_cycle_time = QtWidgets.QSpinBox()
        self.plot_flag = QtWidgets.QCheckBox()

        layout = QtWidgets.QGridLayout()
        layout.addWidget(plot_cycle, 0, 0)
        layout.addWidget(self.plot_cycle_time, 0, 1)
        layout.addWidget(is_plot_flag, 1, 0)
        layout.addWidget(self.plot_flag, 1, 1)

        self.OpenButton = QtWidgets.QPushButton(u'确定')

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.addWidget(self.OpenButton)

        mainlayout = QtWidgets.QVBoxLayout()
        mainlayout.addLayout(layout)
        mainlayout.addLayout(buttonLayout)

        self.OpenButton.clicked.connect(self.plot_set)

        self.plot_cycle_time.setValue(1)
        self.plot_flag.setChecked(True)
        self.resize(180, 80)

        self.setLayout(mainlayout)
        self.setWindowTitle(u'实时绘图设置')

    def plot_set(self):
        plot_flag = False
        if self.plot_flag.isChecked():
            plot_flag = True
        else:
            plot_flag = False
        self.realtime_plot_set_signal.emit(self.plot_cycle_time.value(), plot_flag)
        self.close()


# 定义画板类适配于后期应用
class MeasureFigureCanvas(FigureCanvas):

    def __init__(self, parent=None):
        self.fig = matplotlib.figure.Figure()
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)  # 初始化父类函数


# 控车测量设置类
class CtrlMeasureDlg(QtWidgets.QMainWindow, MeasureWin):

    # 初始化，获取加载后的处理信息
    def __init__(self, parent=None, logObj=FileProcess.FileProcess):
        self.log = logObj
        super().__init__(parent)
        self.setupUi(self)
        self.sp = MeasureFigureCanvas()  # 这是继承FigureCanvas的子类，使用子窗体widget作为父
        self.ctrlAccTable = QtWidgets.QTableWidget()
        l = QtWidgets.QVBoxLayout(self.widget)
        l.addWidget(self.sp)
        l.addWidget(self.ctrlAccTable)
        self.accTableFormat()
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/acc.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        self.setWindowTitle(u'ATO曲线测量器')
        self.resize(800, 500)

    # 设置加速度显示表
    def accTableFormat(self):
        self.ctrlAccTable.setRowCount(4)
        self.ctrlAccTable.setColumnCount(3)
        self.ctrlAccTable.setHorizontalHeaderLabels(['控车曲线分类', '估计加速度', '单位'])
        self.ctrlAccTable.setColumnWidth(1, 200)

    # 重置索引从到右，统一鼠标点击顺序
    @staticmethod
    def setSegmentIdx(idx_start=int, idx_end=int, ):
        # 根据索引大小关系获取实际序列
        if idx_start <= idx_end:
            pass
        else:
            idx_start, idx_end = idx_end, idx_start  # 当终点比起点更靠前，互换转为正常顺序
        return idx_start, idx_end

    # 计算所有加速度 可以输入原始索引，兼容已经转换
    def computeAllAccEstimate(self, idx_start=int, idx_end=int):
        [idx_start, idx_end] = self.setSegmentIdx(idx_start, idx_end)

        # 获取所有周期对应的系统时间作为时间轴-将系统时间改为百毫秒
        time_HMS_list = [self.log.cycle_dic[idx].ostime_start/100 for idx in self.log.cycle[idx_start:idx_end]]
        y_vato_list = self.log.v_ato[idx_start:idx_end]
        y_atppmtv_list = self.log.atp_permit_v[idx_start:idx_end]
        y_atocmdv_list = self.log.cmdv[idx_start:idx_end]
        y_atpcmdvlist = self.log.ceilv[idx_start:idx_end]
        # 计算加速度
        vato_acc_est = self.getEstimateAcc(time_HMS_list, y_vato_list)
        atppmtv_acc_est = self.getEstimateAcc(time_HMS_list, y_atppmtv_list)
        atocmdv_acc_est = self.getEstimateAcc(time_HMS_list, y_atocmdv_list)
        atpcmdv_acc_est = self.getEstimateAcc(time_HMS_list, y_atpcmdvlist)

        return [atppmtv_acc_est, atpcmdv_acc_est, atocmdv_acc_est, vato_acc_est]

    # 获取速度并计算加速度,用于绘图
    def computeVatoAccEstimatePlot(self, idx_start=int, idx_end=int, cmd=int):

        [idx_start, idx_end] = self.setSegmentIdx(idx_start, idx_end)
        # 获取段
        x_list = self.log.cycle[idx_start:idx_end]
        y_list = self.log.v_ato[idx_start:idx_end]
        # 走行距离
        s_sim = self.log.s[idx_end] - self.log.s[idx_start]
        v_sim = self.log.v_ato[idx_end] - self.log.v_ato[idx_start]
        # 计算拟合的加速度 将单位转换为百毫秒-这样100ms/200ms等周期均可适应
        time_HMS_list = [self.log.cycle_dic[idx].ostime_start/100 for idx in self.log.cycle[idx_start:idx_end]]
        [a_sim, p_sim] = self.getEstimateAcc(time_HMS_list, y_list)  # 一次多项式拟合，相当于线性拟合

        return [v_sim, s_sim, a_sim, x_list, time_HMS_list, y_list, p_sim]

    # 获取速度并计算加速度
    @staticmethod
    def getEstimateAcc(x_raw=list, y_raw=list):
        z = np.polyfit(x_raw, y_raw, 1)  # 一次多项式拟合，相当于线性拟合
        a_sim = z[0] * 10 # 获取估计加速度量纲转为s
        p_sim = np.poly1d(z)
        print(p_sim)  # 打印拟合表达式
        return [a_sim, p_sim]

    # 用于绘制估计加速度曲线
    def measurePlot(self, idx_start=int, idx_end=int, cmd=int):

        estimate_a_tuple = self.computeVatoAccEstimatePlot(idx_start, idx_end, cmd)
        v_sim = estimate_a_tuple[0]
        s_sim = estimate_a_tuple[1]
        a_sim = estimate_a_tuple[2]  # 加速度已经转为cm/s^2
        x_list = estimate_a_tuple[3]
        x_time_HMS_list =  estimate_a_tuple[4]
        y_list = estimate_a_tuple[5]
        # 计算拟合点
        y_list_sim = estimate_a_tuple[6](x_time_HMS_list)
        # 计算表格
        acc_all = self.computeAllAccEstimate(idx_start, idx_end)
        # 测量时间
        interval = self.log.cycle_dic[self.log.cycle[idx_end]].ostime_start-self.log.cycle_dic[self.log.cycle[idx_start]].ostime_start

        item_name = ['ATP允许速度', 'ATP命令速度', 'ATO命令速度', '实际速度']
        item_unit = ['cm/s^2', 'cm/s^2', 'cm/s^2', 'cm/s^2']
        for idx, name in enumerate(item_name):
            i_content_name = QtWidgets.QTableWidgetItem(name)
            i_content_name.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            i_content_unit = QtWidgets.QTableWidgetItem(item_unit[idx])
            i_content_unit.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            i_content_value = QtWidgets.QTableWidgetItem(str("%.3f" % (acc_all[idx][0])))
            i_content_value.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            self.ctrlAccTable.setItem(idx, 0, i_content_name)
            self.ctrlAccTable.setItem(idx, 1, i_content_value)
            self.ctrlAccTable.setItem(idx, 2, i_content_unit)

        self.sp.ax.plot(x_time_HMS_list, y_list_sim, color='purple')
        self.sp.ax.plot(x_time_HMS_list, y_list, color='deeppink', marker='.', markersize=0.2)
        str_asim = '拟合加速度:%.*fcm/s^2\n' % (2, a_sim)
        str_cycle_num = '测量时间:%.*fs\n' % (2, interval / 1000) # 转换为秒
        str_s_sim = 'ATO走行距离:%dcm\n' % int(s_sim)
        str_v_sim = 'ATO速度变化:%dcm/s' % (v_sim)

        str_show = str_asim + str_cycle_num + str_s_sim + str_v_sim
        props = dict(boxstyle='round', facecolor='pink', alpha=0.15)
        if a_sim > 0:
            self.sp.ax.text(0.1, 0.90, str_show, transform=self.sp.ax.transAxes, fontsize=10, verticalalignment='top',
                            bbox=props)
        else:
            self.sp.ax.text(0.48, 0.95, str_show, transform=self.sp.ax.transAxes, fontsize=10, verticalalignment='top',
                            bbox=props)


# 控车网络时延显示类
class TrainComMeasureDlg(QtWidgets.QMainWindow, MeasureWin):
    # 初始化，获取加载后的处理信息
    def __init__(self, parent=None, ob=FileProcess.FileProcess):
        self.log = ob
        super().__init__(parent)
        self.setupUi(self)
        self.sp = MeasureFigureCanvas(self.widget)  # 这是继承FigureCanvas的子类，使用子窗体widget作为
        self.trainComTable = QtWidgets.QTableWidget()
        l = QtWidgets.QVBoxLayout(self.widget)
        self.sp.mpl_toolbar = NavigationToolbar(self.sp, self.widget)  # 传入FigureCanvas类或子类实例，和父窗体
        self.mvbParser = MVBParse()
        #l.addWidget(self.trainComTable)
        l.addWidget(self.sp)
        l.addWidget(self.sp.mpl_toolbar)
        self.accTableFormat()
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/BZT.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        self.setWindowTitle(u'车辆通信时延观测器')
        self.resize(500, 600)
        self.a2tCtrl = Ato2TcmsCtrl()
        self.t2aStat = Tcms2AtoState()
        # 初始化内容
        self.atoCtrlCmdList = []
        self.tcmsCtrlFbList = []
        self.unifyCycleList = []  # 为了使得绘图由周期信息，考虑到某个周期可能没有输入只有输出，所以需要人工组合，使得输入保持
        self.mvbdialog = MVBPortDlg()

    # 设置显示表显示表
    def accTableFormat(self):
        self.trainComTable.setRowCount(4)
        self.trainComTable.setColumnCount(3)
        self.trainComTable.setHorizontalHeaderLabels(['统计项目', '时延', '单位'])

    # 计算所有牵引制动及反馈情况情况
    def computAllCtrlInfo(self):
        # 读取该周期内容
        try:
            for idx in range(len(self.log.cycle)):
                for line in self.log.cycle_dic[self.log.cycle[idx]].raw_analysis_lines:
                    if '@' in line:
                        pass
                    elif 'MVB[' in line:# 前提条件
                        match = self.cfg.reg_config.pat_mvb.findall(line)
                        if match:
                            [self.a2tCtrl, nouse, self.t2aStat] = self.mvbParser.parseProtocol(match[0])
                    else:
                        pass

                # 既有车辆反馈又有ATO输出时才认为成功        
                if self.a2tCtrl.updateflag and self.t2aStat.updateflag:
                    if self.a2tCtrl.track_brake_cmd == 0xAA:
                        self.atoCtrlCmdList.append(self.a2tCtrl.track_value)
                    if self.a2tCtrl.track_brake_cmd == 0x55:
                        self.atoCtrlCmdList.append(0 - self.a2tCtrl.track_value)
                    elif self.a2tCtrl.track_brake_cmd == 0xA5:
                        self.atoCtrlCmdList.append(0)
                    else:
                        print('mvb ctrl delay plot compute err!')

                    if self.t2aStat.track_brack_cmd_feedback == 0xAA:
                        self.tcmsCtrlFbList.append(self.t2aStat.track_value_feedback)
                    if self.t2aStat.track_brack_cmd_feedback == 0x55:
                        self.tcmsCtrlFbList.append(0 - self.t2aStat.brake_value_feedback)
                    elif self.t2aStat.track_brack_cmd_feedback == 0xA5:
                        self.tcmsCtrlFbList.append(0)
                    else:
                        print('mvb fb delay plot compute err!')
                    # 获取周期信息
                    self.unifyCycleList.append(self.log.cycle[idx])
        except Exception as err:
            print('mvb delay statistics plot line process err!')

    # 用于绘制估计加速度曲线
    def measurePlot(self):
        self.computAllCtrlInfo()
        self.sp.ax.plot(self.unifyCycleList, self.atoCtrlCmdList,label='ATO输出MVB命令', color='blue', marker='.', markersize=0.5)
        self.sp.ax.plot(self.unifyCycleList, self.tcmsCtrlFbList, label='TCMS反馈MVB命令',color='green', marker='.', markersize=0.5)
        self.ax1 = self.sp.ax.twinx()
        self.ax1.plot(self.log.cycle, self.log.v_ato, color='red', marker='.', markersize=0.5)
        self.tb_cursor = SnaptoCursor(self.sp, self.sp.ax, self.unifyCycleList, self.atoCtrlCmdList)  # 初始化一个光标
        self.tb_cursor.reset_cursor_plot()
        self.sp.mpl_connect('motion_notify_event', self.tb_cursor.mouse_move)
        self.tb_cursor.move_signal.connect(self.cursorPlot)
        self.sp.ax.set_xlim(self.unifyCycleList[0], self.unifyCycleList[len(self.unifyCycleList) - 1])  # 默认与不带光标统一的显示范围
        self.sp.ax.set_ylim(-17000, 17000)
        self.sp.ax.legend(loc='upper right')
        self.sp.ax.grid(which='both',linestyle='-')

    # 光标跟随
    def cursorPlot(self, idx):
        self.sp.ax.texts.clear()
        str_ato_cycle = '当前系统周期:%d \n' % (self.unifyCycleList[idx])
        str_ato_v = '当前系统速度:%dcm/s\n' % (self.log.v_ato[idx])
        str_ato_ctrl = 'ATO输出牵引制动值:%d \n' % (self.atoCtrlCmdList[idx])
        str_tcms_fbk = '车辆反馈牵引制动值:%d ' % (self.tcmsCtrlFbList[idx])
        str_show = str_ato_cycle + str_ato_v +  str_ato_ctrl + str_tcms_fbk
        props = dict(boxstyle='round', facecolor='pink', alpha=0.15)

        self.sp.ax.text(0.03, 0.97, str_show, transform=self.sp.ax.transAxes, fontsize=10, verticalalignment='top',
                        bbox=props)


# C3ATO记录板转义工具类
class C3ATOTransferDlg(QtWidgets.QDialog, C3ATOTransferWin):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # 设置图标和标题
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/translator.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        self.setWindowTitle(u'C3ATO记录板转义工具')
        self.barCurC3ATOProcess.setValue(0)
        self.barAllC3ATOProcess.setValue(0)
        self.resize(700, 400)
        # 单文件路径，记录用于下次快速定位
        self.singleFile = ''
        self.oldSingleDirPath = ''  # 单文件选择路径
        self.multiFileList = []
        self.oldMultiDirPath = ''   # 多文件选择路径
        self.dirFileList = []
        self.oldBatchDir = ''       # 批量处理选择路径
        self.barAllAdd = 100
        # 当前执行状态机
        self.latestChooseState = 0   # 用于记录最近一次有效的文件选择，0=无效，1=单文件，2=多文件，3=批量文件
        self.barAllNum = 0.0
        # 事件绑定
        self.btnSingleFileTrans.clicked.connect(self.ChooseSingleDlg)
        self.btnMultiFileTrans.clicked.connect(self.ChooseMultiDlg)
        self.btnDirFileTrans.clicked.connect(self.ChooseDirDlg)
        self.btnCancel.clicked.connect(self.close)
        self.btnOK.clicked.connect(self.BeginTransProcess)
        # 初始化转义器
        self.translator = TransRecord()
        self.translator.FileTransOnePercentSingal.connect(self.ShowFileBarProgress)
        self.translator.FileTransCompleteSingal.connect(self.ShowAllFileBarProgress)
        self.translator.FileTransErrSingal.connect(self.ShowErrInTextEdit)

    def BeginTransProcess(self):
        """
        点击确认按钮后，执行转义处理
        :return:
        """
        # 处理内容
        if self.latestChooseState == 1:
            self.SingleFileTrans(self.singleFile)       # 处理单文件路径
        elif self.latestChooseState == 2:
            self.MultiFileTrans(self.multiFileList)     # 处理文件列表
        elif self.latestChooseState == 3:
            self.BatchFileTrans(self.dirFileList)       # 处理文件列表
        else:
            self.textC3ATOProcess.append("Info：无有效选择文件！ 不执行")

    def SingleFileTrans(self, filePath=str):
        """
        单文件转义处理，负责调用转义函数并触发进度条
        :param filePath: 待转义文件路径
        :return:
        """
        self.barAllC3ATOProcess.setValue(100)
        self.textC3ATOProcess.append('Info：' + '文件转义!')
        trans_file = filePath.replace('.txt', '_trans.txt')  # 计算转换后的文件名称，只有文件发生变化
        # 对每个转换文件过程创建线程
        thList = []
        t = Thread(target=self.translator.TransContent, args=(filePath, trans_file))  # 添加内容
        t.name = '线程：' + trans_file
        thList.append(t)
        # 开启线程
        threadAct = Thread(target=self.ThreadManage, args=(thList,))  # 添加内容
        threadAct.start()

    def MultiFileTrans(self, fileList=list):
        """
        文件列表转义，负责转义处理和触发进度条
        :param fileList: 转义的多文件路径列表
        :return:
        """
        self.textC3ATOProcess.append('Info：'+'文件遍历!')
        self.barAllAdd = C3ATOTransferDlg.ComputeEBarAllAdd(fileList)
        # 创建线程池
        thList = []
        # 对于多文件选择，在当前目录直接完成
        for recordFile in fileList:
            # 按照之前创建目录规则，创建新的文件名
            trans_file = recordFile.replace('.txt', '_trans.txt')   # 计算转换后的文件名称，只有文件发生变化
            # 对每个转换文件过程创建线程
            t = Thread(target=self.translator.TransContent, args=(recordFile, trans_file))  # 添加内容
            t.name = '线程：' + trans_file
            thList.append(t)
        # 开启线程
        threadAct = Thread(target=self.ThreadManage, args=(thList,))  # 添加内容
        threadAct.start()

    def BatchFileTrans(self, fileList=list):
        """
        批量转义列表文件，转义并处理进度条
        :param fileList: 批量转义的文件列表
        :return:
        """
        try:
            dstPath = C3ATOTransferDlg.CheckAndCreateTransDir(self.oldBatchDir)     # 创建镜像的转义文件路径
        except Exception as err:
            print(err)
        self.textC3ATOProcess.append('Info：'+'文件遍历!')
        self.barAllAdd = C3ATOTransferDlg.ComputeEBarAllAdd(fileList)
        # 创建线程池
        thList = []
        # 对于多文件选择，在当前目录直接完成
        for recordFile in fileList:
            # 按照之前创建目录规则，创建新的文件名
            transFile = recordFile.replace(self.oldBatchDir, dstPath)      # 先替换镜像顶级目录内容
            dstFile = transFile.replace('.txt', '_trans.txt')              # 计算转换后的文件名称，只有文件发生变化
            # 对每个转换文件过程创建线程
            t = Thread(target=self.translator.TransContent, args=(recordFile, dstFile))  # 添加内容
            t.name = '线程' + dstFile
            thList.append(t)
        # 开启线程
        threadAct = Thread(target=self.ThreadManage, args=(thList,))  # 添加内容
        threadAct.start()

    def ShowFileBarProgress(self, num):
        self.barCurC3ATOProcess.setValue(num)

    def ShowAllFileBarProgress(self):
        if self.latestChooseState < 2:
            self.barAllC3ATOProcess.setValue(100)
        else:
            self.barAllNum = self.barAllNum + self.barAllAdd
            self.barAllC3ATOProcess.setValue(int(self.barAllNum))

    def ShowErrInTextEdit(self, err=str):
        err = "<font face='宋体' size='3' color='#4D4DFF'>" + err + "</font>"
        self.textC3ATOProcess.append(err)

    def ThreadManage(self, thList=list):
        self.textC3ATOProcess.append('Info：'+'开启线程!')
        # 开启线程
        for th in thList:
            msg = 'Info：' + th.name
            self.textC3ATOProcess.append("<font face='宋体' size='3' color='red'>" + "<b>" + msg + "</b> "+"</font>")
            # 启动线程
            th.setDaemon(True)
            th.start()
            th.join()

    @staticmethod
    def ComputeEBarAllAdd(fileList=list):
        """
        根据选择的文件列表，计算单个文件所占的进度条长度
        :param fileList: 文件列表
        :return: 单个文件占计数（小数）
        """
        # 计算文件个数
        allNum = len(fileList)
        if allNum:
            return 100/allNum   # 考虑到数量可能比100大或小，这里可能是小数
        else:
            return 100

    def ChooseSingleDlg(self):
        """
        选择单个文件的方法
        :return: 单文件路径
        """
        # 重置界面
        self.ResetDlgPanel()
        temp = '/'
        # 若之前选择过，列表非空
        if not self.oldSingleDirPath:
            filepath = QtWidgets.QFileDialog.getOpenFileName(self, '选择单个文件', 'c:/', "txt files(*.txt *.log)")
        else:
            filepath = QtWidgets.QFileDialog.getOpenFileName(self, '选择单个文件', self.oldSingleDirPath,
                                                             "txt files(*.txt *.log)")
        # 取出文件地址
        path = filepath[0]
        if path == '':  # 没有选择文件
            self.latestChooseState = 0
            self.textC3ATOProcess.append('Info： 没有选择文件！')
        else:
            self.latestChooseState = 1
            name = path.split("/")[-1]  # 文件名称，预留
            self.oldSingleDirPath = temp.join(path.split("/")[-1])  # 纪录上一次的文件路径
            self.singleFile = path
            self.ledC3ATOPath.setText(path)

    def ChooseMultiDlg(self):
        """
        选择多个文件的方法
        :return: 多个文件的文件列表
        """
        # 重置界面
        self.ResetDlgPanel()
        temp = '/'
        # 若之前选择过，列表非空
        if not self.oldMultiDirPath:
            filepath = QtWidgets.QFileDialog.getOpenFileNames(self, '选择多个文件', 'c:/', "txt files(*.txt *.log)")
        else:
            filepath = QtWidgets.QFileDialog.getOpenFileNames(self, '选择多个文件', self.oldMultiDirPath,
                                                              "txt files(*.txt *.log)")

        pathList = filepath[0]  # 取出多文件的列表地址
        if not pathList:  # 没有选择文件
            self.latestChooseState = 0
            self.textC3ATOProcess.append('Info： 没有选择文件！')
        else:
            self.latestChooseState = 2
            name = pathList[0].split("/")[-1]  # 取文件列表中第一个文件的地址作为下次读取地址
            self.oldMultiDirPath = temp.join(pathList[0].split("/")[:-1])  # 取第一个文件所在目录作为下次选择结果
            self.multiFileList = pathList
            self.ledC3ATOPath.setText(self.oldMultiDirPath)
            for f in self.multiFileList:
                self.textC3ATOProcess.append(f)  # 显示路径
            self.textC3ATOProcess.append('Info：共选择（*.txt）文件 %d 个！' % len(self.multiFileList))

    def ChooseDirDlg(self):
        """
        选择目录的对话框，向下搜索获取所有文件
        :return: 多个文件的文件列表
        """
        # 重置界面
        self.ResetDlgPanel()
        temp = '/'
        # 若之前选择过，列表非空
        if not self.oldBatchDir:
            path = QtWidgets.QFileDialog.getExistingDirectory(self, '选择文件目录', 'c:/')
        else:
            path = QtWidgets.QFileDialog.getExistingDirectory(self, '选择文件目录', self.oldBatchDir)
        # 更新记录路径
        self.oldBatchDir = path
        if not path:  # 没有选择文件路径
            self.latestChooseState = 0
            self.textC3ATOProcess.append('Info： 没有选择文件！')
        else:
            self.latestChooseState = 3
            # 更新前初始化，文件列表
            self.dirFileList = []
            self.GetFileList(self.dirFileList, path, '.txt')
            for f in self.dirFileList:
                self.textC3ATOProcess.append(f)  # 显示路径
            self.textC3ATOProcess.append('Info：共选择（*.txt）文件 %d 个！' % (len(self.dirFileList)))

    def ResetDlgPanel(self):
        """
        当数据加载完成后，重置界面
        :return:
        """
        self.barCurC3ATOProcess.setValue(0)
        self.barAllC3ATOProcess.setValue(0)
        self.textC3ATOProcess.clear()

    @staticmethod
    def GetFileList(fileList, rootPath, fileType=None):
        """
        根据输入的根路径，向下递归搜索文件名
        :param fileList: 输出的文件列表
        :param rootPath: 输入的查询父目录
        :param fileType: 查询文件的后缀名
        :return:
        """
        files = os.listdir(rootPath)
        for fileName in files:
            fullPath = os.path.join(rootPath, fileName)
            if os.path.isdir(fullPath):
                C3ATOTransferDlg.GetFileList(fileList, fullPath, fileType)
            else:
                if fileType:  # 如果指定文件后缀
                    if fileType == fullPath[-len(fileType):]:  # 检查后缀名
                        fileList.append(fullPath)
                    else:
                        pass
                        # print(fullPath)
                else:
                    # 如果不指定则添加所有
                    fileList.append(fullPath)
                    print(fullPath)
        return fileList

    @staticmethod
    def CheckAndCreateTransDir(basePath=str):
        """
        根据传入路径创建对应的转义路径，根目录用_Trans后缀识别，所有子目录一致
        :param basePath: 基础目录
        :return: 创建的转义目录
        """
        # 定位上一级路径
        supPath = '/'.join(basePath.split("/")[:-1])
        mateDirs = os.listdir(supPath)    # 获取同一级目录
        curDirName = basePath.split("/")[-1]
        dstPath = '/'.join([supPath, basePath.split("/")[-1] + '_Trans'])  # 仅针对路径最后值调整，防止整体替换出现的错误
        # 当已经存在转义路径时直接退出
        if curDirName + '_Trans' in mateDirs:
            pass
        else:
            if os.path.isdir(basePath):
                try:
                    # 创建镜像的转义路径
                    C3ATOTransferDlg.CopyFileDir(basePath, dstPath)
                except Exception as err:
                    print(err)
        return dstPath

    @staticmethod
    def CopyFileDir(src_path=str, dst_path=str, include_file=bool):
        """
        将指定的路径子目录复制到指定路径下（指定是否包含文件）
        :param src_path: 被复制源路径
        :param dst_path: 复制到目的路径
        :param include_file: 是否复制文件
        :return: 无
        """
        # 检查是否要拷贝
        shutil.copytree(src_path, dst_path, symlinks=False, ignore=None, copy_function=C3ATOTransferDlg.CopyFunc,
                        ignore_dangling_symlinks=True)

    @staticmethod
    def CopyFunc(src, dst, *, follow_symlinks=True):
        # 重写copy函数，用于拷贝目录或拷贝文件
        # 可以参考copy2和copy函数，复制所有文件和状态
        # 如果输入路径是目录，首先创建目标目录
        if os.path.isdir(src):
            dst_path = os.path.join(dst, os.path.basename(dst))  # 定义目的基础目录
            # 这里不复制文件和状态
            # 所以只复制了文件路径
        return dst
