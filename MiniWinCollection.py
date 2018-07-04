#!/usr/bin/env python

# encoding: utf-8

'''

@author:  Baozhengtang

@license: (C) Copyright 2017-2018, Author Limited.

@contact: baozhengtang@gmail.com

@software: LogPlot

@file: MiniWinCollection.py

@time: 2018/6/3 9:45

@desc: 主要用于聚集主窗口中弹出的临时小窗口，包括工具和设置

'''
from MVBParser import Ui_MainWindow as MVBParserWin
from ProtocolParse import MVBParse
from PyQt5 import QtWidgets, QtCore, QtGui
import serial
import serial.tools.list_ports
import datetime
import time
import re

pat_ato_ctrl = 0
pat_ato_stat = 0
pat_tcms_stat = 0


# 串口设置类
class SerialDlg(QtWidgets.QDialog):

    serUpdateSingal = QtCore.pyqtSignal()           # 串口设置更新信号

    def __init__(self, parent=None):
        super(SerialDlg, self).__init__(parent)
        self.saveName = ''      # 根据设置生成文件名
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
        nameLayout.addWidget(self.filenameLine )
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
        self.ser = serial.Serial()
        self.ser.port = self.SerialCOMComboBox.currentText()
        self.ser.baudrate = self.SerialBaudRateComboBox.currentText()
        self.ser.bytesize = int(self.SerialDataComboBox.currentText())
        ParityValue = self.SerialParityComboBox.currentText()
        self.ser.parity = ParityValue[0]
        self.ser.stopbits = int(self.SerialStopBitsComboBox.currentText())
        # 组合文件名

        self.close()
        self.serUpdateSingal.emit()


# mvb端口设置类
class MVBPortDlg(QtWidgets.QDialog):

    mvbPortSingal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(MVBPortDlg, self).__init__(parent)
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/BZT.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        self.saveName = ''      # 根据设置生成文件名
        lbl_ato_ctrl = QtWidgets.QLabel(u'ATO控制信息(16进制)')
        lbl_ato_stat = QtWidgets.QLabel(u'ATO状态信息(16进制)')
        lbl_tcms_stat = QtWidgets.QLabel(u'车辆状态信息(16进制)')

        self.led_ato_ctrl = QtWidgets.QLineEdit('D10')
        self.led_ato_stat = QtWidgets.QLineEdit('D11')
        self.led_tcms_stat = QtWidgets.QLineEdit('D12')

        layout = QtWidgets.QGridLayout()
        layout.addWidget(lbl_ato_ctrl, 0, 0)
        layout.addWidget(self.led_ato_ctrl , 0, 1)
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
        # 组合文件名
        self.mvbPortSingal.emit()
        self.close()


# mvb解析器
class MVBParserDlg(QtWidgets.QMainWindow, MVBParserWin):
    def __init__(self):
        super(MVBParserDlg, self).__init__()
        self.setupUi(self)
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/BZT.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        self.setWindowTitle(u'MVB协议解析')
        self.parser = MVBParse()
        self.actionMVBParserAct.triggered.connect(self.ParserMVB)
        # 名字
        self.ato_ctrl_name = ['帧头','包序号','端口号','ATO心跳','ATO有效','牵引制动状态','牵引控制量','制动控制量','保持制动施加',
                              '开左/右门','恒速命令','恒速目标速度','ATO启动灯']
        self.ato_stat_name = ['帧头','包序号','端口号','ATO心跳','ATO故障','公里标','隧道入口距离','隧道长度','ATO速度']
        self.tcms_stat_name = ['帧头','包序号','端口号','TCMS心跳','门模式','ATO有效命令反馈','牵引制动命令状态字反馈','牵引控制量反馈',
                               '制动控制量反馈','ATO保持制动施加反馈','开左/右门命令反馈','恒速反馈','车门状态','空转打滑',
                               '编组信息','车重','动车组允许','主断路器状态','门允许选择','不允许状态字']

    def ParserMVB(self):
        global pat_ato_ctrl
        global pat_ato_stat
        global pat_tcms_stat
        err_flag = 0
        field_value = []
        field_name = []
        field_result = []
        adder = 0
        num = 0
        type_name = ''
        tmp = self.textEdit.toPlainText()
        try:
            tmp_text = re.sub('\s+', '', tmp)
            for item in tmp_text:
                v = int(item, 16)
            # 如果有帧头
            if len(tmp_text) > 8:
                # 小端模式
                num = int(tmp_text[6:8]+tmp_text[4:6], 16)
                if num == pat_ato_stat:
                    form = self.parser.mvb_ato2tcms_status
                    type_name = 'ATO状态信息'
                    field_name = self.ato_stat_name
                elif num == pat_ato_ctrl:
                    form = self.parser.mvb_ato2tcms_ctrl
                    type_name = 'ATO控制信息'
                    field_name = self.ato_ctrl_name
                elif num == pat_tcms_stat:
                    form =self.parser.mvb_tcms2ato_status
                    type_name = '车辆状态信息'
                    field_name = self.tcms_stat_name
                else:
                    err_flag = 1
                # 计算剪切
                if err_flag == 0:
                    # 根据格式列表切片按字节8位
                    for item in form:
                        field_value.append(tmp_text[adder:adder + 2 * item])
                        adder += 2 * item

                        try:
                            tmp = int(tmp_text[adder:adder + 2 * item], 16)
                        except Exception as err:
                            err_flag = 1
                            print(err)
                    field_value.remove(field_value[0])
                    field_value.insert(0, tmp_text[0:2])
                    field_value.insert(1, tmp_text[2:4])
                    field_value.insert(2, tmp_text[6:8]+tmp_text[4:6])

                    field_result = self.result_analysis(field_value, num)

                    self.show_parser_result(type_name, field_name, field_value, field_result )

        except Exception as err:
            reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                                                      "错误",
                                                      "注意：数据异常或非16进制数据",
                                                      QtWidgets.QMessageBox.Yes)
        # 校验结束开始解析

    # 根据结果解析
    def result_analysis(self, field_value=list, num=int):
        global pat_ato_ctrl
        global pat_ato_stat
        global pat_tcms_stat
        field_result = []
        # 除去开头的帧头等
        tmp = field_value[3:]
        if field_value[0] == '01':
            field_result.append('类型:发送数据帧')
        elif field_value[0] == '03':
            field_result.append('类型,接收数据')
        else:
            field_result.append('类型,错误%s'%field_value[0])

        field_result.append(str(int(field_value[1],16)))
        field_result.append(str(int(field_value[2],16)))
        # 控制命令
        if num == pat_ato_ctrl:
            field_result.append(str(int(tmp[0], 16)))     # 控制命令心跳
            if tmp[1] == 'AA':
                field_result.append('有效')                   # ATO有效
            elif tmp[1] == '00':
                field_result.append('无效')
            else:
                field_result.append('异常值%s'%tmp[1])

            # 牵引制动状态
            if tmp[2] == 'AA':
                field_result.append('牵引')
            elif tmp[2] == '55':
                field_result.append('制动')
            elif tmp[2] == 'A5':
                field_result.append('惰行')
            elif tmp[2] == '00':
                field_result.append('无命令')
            else:
                field_result.append('异常值%s'%tmp[2])

            # 牵引控制量
            field_result.append(str(int(tmp[3], 16)))
            # 制动控制量
            field_result.append(str(int(tmp[4], 16)))
            # 保持制动施加
            if tmp[5] == 'AA':
                field_result.append('施加')
            elif tmp[5] == '00':
                field_result.append('无效')
            else:
                field_result.append('异常值%s'%tmp[5])
            # 开左门/右门
            if tmp[6][0] == 'C' and tmp[6][1] == 'C':
                field_result.append('开左/右有效')
            elif tmp[6][0] == '0'and tmp[6][1] == 'C':
                field_result.append('左无动作，右开门')
            elif tmp[6][0] == 'C'and tmp[6][1] == '0':
                field_result.append('右无动作，左开门')
            elif tmp[6][0] == '0'and tmp[6][1] == '0':
                field_result.append('左右门无动作')
            else:
                field_result.append('异常%s'%tmp[6][0])
            # 恒速命令
            if tmp[7] == 'AA':
                field_result.append('启动')
            elif tmp[7] == '00':
                field_result.append('取消')
            else:
                field_result.append('异常值%s'%tmp[7])
            # 恒速目标速度
            field_result.append(str(int(tmp[8],16)))
            # ATO启动灯
            if tmp[9] == 'AA':
                field_result.append('亮')
            elif tmp[9] == '00':
                field_result.append('灭')
            else:
                field_result.append('异常值%s'%tmp[9])
        # ATO2TCMS 状态信息
        if num == pat_ato_stat:
            field_result.append(str(int(tmp[0], 16)))        # 状态命令心跳
            if tmp[1] == 'AA':
                field_result.append('无故障')       # ATO故障
            elif tmp[1] == '00':
                field_result.append('故障')
            else:
                field_result.append('异常值%s'%tmp[1])      # ATO故障
            if tmp[2] == 'FFFFFFFF':
                field_result.append('无效值')
            else:
                field_result.append(str(int(tmp[2], 16))+'m')   # 公里标
            if tmp[3] == 'FFFF':
                field_result.append('无效值')
            else:
                field_result.append(str(int(tmp[3], 16))+'m')       # 隧道入口
            if tmp[4] == 'FFFF':
                field_result.append('无效值')
            else:
                field_result.append(str(int(tmp[4], 16))+'m')       # 隧道长度
            field_result.append(str(int(tmp[5], 16)/10)+'km/h')       # ato速度
        # TCMS2ATO 状态信息
        if num == pat_tcms_stat:
            field_result.append(str(int(tmp[0], 16)))     # TCMS状态命令心跳
            # 门模式
            if tmp[1][0] == 'C':
                field_result.append('MM有效,AM无效')
            elif tmp[1][0] == '3':
                field_result.append('AM有效,MM无效')
            elif tmp[1][0] == '0':
                field_result.append('MM无效,AM无效')
            else:
                field_result.append('异常值%s'%tmp[1][0])
            # ATO启动灯
            if tmp[1][1] == '3':
                field_result[len(field_result) - 1] = field_result[len(field_result)-1]+',启动灯有效'
            elif tmp[1][1] == '0':
                field_result[len(field_result) - 1] = field_result[len(field_result) - 1] + ',启动灯有效'
            else:
                field_result[len(field_result) - 1] = field_result[len(field_result) - 1] + '异常值'+tmp[1][1]

            # ATO有效反馈
            if tmp[2] == 'AA':
                field_result.append('有效')
            elif tmp[2] == '00':
                field_result.append('无效')
            else:
                field_result.appendt('异常值%s'%tmp[2])

            # 牵引制动反馈
            if tmp[3] == 'AA':
                field_result.append('牵引')
            elif tmp[3] == '55':
                field_result.append('制动')
            elif tmp[3] == 'A5':
                field_result.append('惰行')
            elif tmp[3] == '00':
                field_result.append('无命令')
            else:
                field_result.append('异常值%s'%tmp[3])

            # 牵引反馈
            field_result.append(str(int(tmp[4],16)))
            # 制动反馈
            field_result.append(str(int(tmp[5],16)))
            # 保持制动施加
            if tmp[6] == 'AA':
                field_result.append('有效')
            elif tmp[6] == '00':
                field_result.append('无效')
            else:
                field_result.append('异常值%s'%tmp[6])
            # 左门反馈，右门反馈
            if tmp[7][0] == 'C'and tmp[7][1] == 'C':
                field_result.append('左/右门有效')
            elif tmp[7][0] == '0'and tmp[7][1] == 'C':
                field_result.append('左门无效,右门有效')
            elif tmp[7][0] == 'C' and tmp[7][1] == '0':
                field_result.append('左门有效,右门无效')
            elif tmp[7][0] == '0' and tmp[7][1] == '0':
                field_result.append('左/右门无效')
            else:
                field_result.append('异常值%s'%tmp[7][0])
            # 恒速反馈
            if tmp[8] == 'AA':
                field_result.append('有效')
            elif tmp[8] == '00':
                field_result.append('无效')
            else:
                field_result.append('异常值%s'%tmp[8])
            # 车门状态
            if tmp[9] == 'AA':
                field_result.append('关')
            elif tmp[9] == '00':
                field_result.append('开')
            else:
                field_result.append('异常值%s'%tmp[9])
            # 空转打滑
            if tmp[10][0] == 'A' and tmp[10][1] == 'A':
                field_result.append('空转,打滑')
            elif tmp[10][0] == '0' and tmp[10][1] == 'A':
                field_result.append('打滑')
            elif tmp[10][0] == 'A'and tmp[10][1] == '0':
                field_result.append('空转')
            elif tmp[10][0] == '0'and tmp[10][1] == '0':
                field_result.append('未发生')
            else:
                field_result.append('异常值%s'%tmp[10][0])
            # 编组信息
            tmp_units = int(tmp[11], 16)
            if tmp_units == 1:
                field_result.append('8编组')
            elif tmp_units == 2:
                field_result.append('8编重连')
            elif tmp_units == 3:
                field_result.append('16编组')
            elif tmp_units == 4:
                field_result.append('18编组')
            else:
                field_result.append('异常值%s'%tmp[11])
            # 车重
            field_result.append(str(int(tmp[12],16)))
            # 动车组允许
            if tmp[13] == 'AA':
                field_result.append('允许')
            elif tmp[13] == '00':
                field_result.append('不允许')
            else:
                field_result.append('异常值%s'%tmp[13])

            # 主断状态
            if tmp[14] == 'AA':
                field_result.append('闭合')
            elif tmp[14] == '00':
                field_result.append('断开')
            else:
                field_result.append('异常值%s'%tmp[14])
            # ATP允许 人工允许
            if tmp[15] == 'C0':
                field_result.append('atp有效,人工无效')
            elif tmp[15] == '30':
                field_result.append('atp无效，人工有效')
            elif tmp[15] == '00':
                field_result.append('atp和人工均无效')
            else:
                field_result.append('异常值%s'%tmp[15])
            # 不允许状态字
            if tmp[16] == '00':
                field_result.append('正常')
            else:
                field_result.append('异常%s'%tmp[16])

        return field_result

    # 显示最终结果
    def show_parser_result(self, data_type=str, field_name=list, field_value=list, field_result=list):
        self.treeWidget.clear()
        root = QtWidgets.QTreeWidgetItem(self.treeWidget)
        root.setText(0, data_type)
        # 开始生成
        if len(field_name)==len(field_result) and len(field_name)==len(field_value):
            for idx, item in enumerate(field_name):
                item_field = QtWidgets.QTreeWidgetItem(root)  # 以该数据包作为父节点
                item_field.setText(1, field_name[idx])
                item_field.setText(2, field_value[idx])
                item_field.setText(3, field_result[idx])
        self.treeWidget.expandAll()


# UTC时间解析器
class UTCTransferDlg(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(UTCTransferDlg, self).__init__(parent)
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/BZT.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
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

        self.OpenButton.clicked.connect(self.PushBtnUTC)

        self.setLayout(mainlayout)
        self.setWindowTitle(u'UTC时间转换器')

    def PushBtnUTC(self):
        tmp = self.utc.text()
        try:
            self.local.setText(self.TransferUTC(tmp))
        except Exception as err:
            reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                                                      "错误",
                                                      "注意：UTC时间有误，请修改",
                                                      QtWidgets.QMessageBox.Yes)

    def TransferUTC(self, t=str):
        ltime = time.localtime(int(t))
        timeStr = time.strftime("%Y-%m-%d %H:%M:%S", ltime)
        return timeStr


# 实时绘图设置类
class RealTimePlotDlg(QtWidgets.QDialog, QtCore.QObject):

    realtime_plot_set_signal = QtCore.pyqtSignal(int,bool)

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

        self.OpenButton.clicked.connect(self.PlotSet)

        self.plot_cycle_time.setValue(3)
        self.plot_flag.setChecked(True)
        self.resize(180, 80)

        self.setLayout(mainlayout)
        self.setWindowTitle(u'实时绘图设置')

    def PlotSet(self):
        plot_flag = False
        if self.plot_flag.isChecked():
            plot_flag = True
        else:
            plot_flag = False
        self.realtime_plot_set_signal.emit(self.plot_cycle_time.value(),plot_flag)
        self.close()

