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
from MVBParserWin import Ui_MainWindow as MVBParserWin
from MeasureWin import Ui_MainWindow as MeasureWin
from C3ATORecordTranslator import Ui_Dialog as C3ATOTransferWin

matplotlib.use("Qt5Agg")  # 声明使用QT5
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from TCMSParse import MVBParse
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

pat_ato_ctrl = 0
pat_ato_stat = 0
pat_tcms_stat = 0


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
    serUpdateSingal = QtCore.pyqtSignal()  # 串口设置更新信号

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
        self.saveName = ''  # 根据设置生成文件名
        lbl_ato_ctrl = QtWidgets.QLabel(u'ATO控制信息(16进制)')
        lbl_ato_stat = QtWidgets.QLabel(u'ATO状态信息(16进制)')
        lbl_tcms_stat = QtWidgets.QLabel(u'车辆状态信息(16进制)')

        self.led_ato_ctrl = QtWidgets.QLineEdit('D10')
        self.led_ato_stat = QtWidgets.QLineEdit('D11')
        self.led_tcms_stat = QtWidgets.QLineEdit('D12')

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
        # 组合文件名
        self.mvbPortSingal.emit()
        self.close()


# mvb解析器
class MVBParserDlg(QtWidgets.QMainWindow, MVBParserWin):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/MVBParser.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        self.setWindowTitle(u'MVB协议解析')
        self.parser = MVBParse()
        self.actionMVBParserAct.triggered.connect(self.ParserMVB)
        # 名字
        self.ato_ctrl_name = ['帧头', '包序号', '端口号', 'ATO心跳', 'ATO有效', '牵引制动状态', '牵引控制量', '制动控制量', '保持制动施加',
                              '开左/右门', '恒速命令', '恒速目标速度', 'ATO启动灯']
        self.ato_stat_name = ['帧头', '包序号', '端口号', 'ATO心跳', 'ATO故障', '公里标', '隧道入口距离', '隧道长度', 'ATO速度']
        self.tcms_stat_name = ['帧头', '包序号', '端口号', 'TCMS心跳', '门模式', 'ATO有效命令反馈', '牵引制动命令状态字反馈', '牵引控制量反馈',
                               '制动控制量反馈', 'ATO保持制动施加反馈', '开左/右门命令反馈', '恒速反馈', '车门状态', '空转打滑',
                               '编组信息', '车重', '动车组允许', '主断路器状态', '门允许选择', '不允许状态字']

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
                num = int(tmp_text[6:8] + tmp_text[4:6], 16)
                if num == pat_ato_stat:
                    form = self.parser.mvb_ato2tcms_status
                    type_name = 'ATO状态信息'
                    field_name = self.ato_stat_name
                elif num == pat_ato_ctrl:
                    form = self.parser.mvb_ato2tcms_ctrl
                    type_name = 'ATO控制信息'
                    field_name = self.ato_ctrl_name
                elif num == pat_tcms_stat:
                    form = self.parser.mvb_tcms2ato_status
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
                    field_value.insert(2, tmp_text[6:8] + tmp_text[4:6])

                    field_result = self.result_analysis(field_value, num)

                    self.show_parser_result(type_name, field_name, field_value, field_result)

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
            field_result.append('类型,错误%s' % field_value[0])

        field_result.append(str(int(field_value[1], 16)))
        field_result.append(str(int(field_value[2], 16)))
        # 控制命令
        if num == pat_ato_ctrl:
            field_result.append(str(int(tmp[0], 16)))  # 控制命令心跳
            if tmp[1] == 'AA':
                field_result.append('有效')  # ATO有效
            elif tmp[1] == '00':
                field_result.append('无效')
            else:
                field_result.append('异常值%s' % tmp[1])

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
                field_result.append('异常值%s' % tmp[2])

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
                field_result.append('异常值%s' % tmp[5])
            # 开左门/右门
            if tmp[6][0] == 'C' and tmp[6][1] == 'C':
                field_result.append('开左/右有效')
            elif tmp[6][0] == '0' and tmp[6][1] == 'C':
                field_result.append('左无动作，右开门')
            elif tmp[6][0] == 'C' and tmp[6][1] == '0':
                field_result.append('右无动作，左开门')
            elif tmp[6][0] == '0' and tmp[6][1] == '0':
                field_result.append('左右门无动作')
            else:
                field_result.append('异常%s' % tmp[6][0])
            # 恒速命令
            if tmp[7] == 'AA':
                field_result.append('启动')
            elif tmp[7] == '00':
                field_result.append('取消')
            else:
                field_result.append('异常值%s' % tmp[7])
            # 恒速目标速度
            field_result.append(str(int(tmp[8], 16)))
            # ATO启动灯
            if tmp[9] == 'AA':
                field_result.append('亮')
            elif tmp[9] == '00':
                field_result.append('灭')
            else:
                field_result.append('异常值%s' % tmp[9])
        # ATO2TCMS 状态信息
        if num == pat_ato_stat:
            field_result.append(str(int(tmp[0], 16)))  # 状态命令心跳
            if tmp[1] == 'AA':
                field_result.append('无故障')  # ATO故障
            elif tmp[1] == '00':
                field_result.append('故障')
            else:
                field_result.append('异常值%s' % tmp[1])  # ATO故障
            if tmp[2] == 'FFFFFFFF':
                field_result.append('无效值')
            else:
                field_result.append(str(int(tmp[2], 16)) + 'm')  # 公里标
            if tmp[3] == 'FFFF':
                field_result.append('无效值')
            else:
                field_result.append(str(int(tmp[3], 16)) + 'm')  # 隧道入口
            if tmp[4] == 'FFFF':
                field_result.append('无效值')
            else:
                field_result.append(str(int(tmp[4], 16)) + 'm')  # 隧道长度
            field_result.append(str(int(tmp[5], 16) / 10) + 'km/h')  # ato速度
        # TCMS2ATO 状态信息
        if num == pat_tcms_stat:
            field_result.append(str(int(tmp[0], 16)))  # TCMS状态命令心跳
            # 门模式
            if tmp[1][0] == 'C':
                field_result.append('MM有效,AM无效')
            elif tmp[1][0] == '3':
                field_result.append('AM有效,MM无效')
            elif tmp[1][0] == '0':
                field_result.append('MM无效,AM无效')
            else:
                field_result.append('异常值%s' % tmp[1][0])
            # ATO启动灯
            if tmp[1][1] == '3':
                field_result[len(field_result) - 1] = field_result[len(field_result) - 1] + ',启动灯有效'
            elif tmp[1][1] == '0':
                field_result[len(field_result) - 1] = field_result[len(field_result) - 1] + ',启动灯无效'
            else:
                field_result[len(field_result) - 1] = field_result[len(field_result) - 1] + '异常值' + tmp[1][1]

            # ATO有效反馈
            if tmp[2] == 'AA':
                field_result.append('有效')
            elif tmp[2] == '00':
                field_result.append('无效')
            else:
                field_result.appendt('异常值%s' % tmp[2])

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
                field_result.append('异常值%s' % tmp[3])

            # 牵引反馈
            field_result.append(str(int(tmp[4], 16)))
            # 制动反馈
            field_result.append(str(int(tmp[5], 16)))
            # 保持制动施加
            if tmp[6] == 'AA':
                field_result.append('有效')
            elif tmp[6] == '00':
                field_result.append('无效')
            else:
                field_result.append('异常值%s' % tmp[6])
            # 左门反馈，右门反馈
            if tmp[7][0] == 'C' and tmp[7][1] == 'C':
                field_result.append('左/右门有效')
            elif tmp[7][0] == '0' and tmp[7][1] == 'C':
                field_result.append('左门无效,右门有效')
            elif tmp[7][0] == 'C' and tmp[7][1] == '0':
                field_result.append('左门有效,右门无效')
            elif tmp[7][0] == '0' and tmp[7][1] == '0':
                field_result.append('左/右门无效')
            else:
                field_result.append('异常值%s' % tmp[7][0])
            # 恒速反馈
            if tmp[8] == 'AA':
                field_result.append('有效')
            elif tmp[8] == '00':
                field_result.append('无效')
            else:
                field_result.append('异常值%s' % tmp[8])
            # 车门状态
            if tmp[9] == 'AA':
                field_result.append('关')
            elif tmp[9] == '00':
                field_result.append('开')
            else:
                field_result.append('异常值%s' % tmp[9])
            # 空转打滑
            if tmp[10][0] == 'A' and tmp[10][1] == 'A':
                field_result.append('空转,打滑')
            elif tmp[10][0] == '0' and tmp[10][1] == 'A':
                field_result.append('打滑')
            elif tmp[10][0] == 'A' and tmp[10][1] == '0':
                field_result.append('空转')
            elif tmp[10][0] == '0' and tmp[10][1] == '0':
                field_result.append('未发生')
            else:
                field_result.append('异常值%s' % tmp[10][0])
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
                field_result.append('异常值%s' % tmp[11])
            # 车重
            field_result.append(str(int(tmp[12], 16)))
            # 动车组允许
            if tmp[13] == 'AA':
                field_result.append('允许')
            elif tmp[13] == '00':
                field_result.append('不允许')
            else:
                field_result.append('异常值%s' % tmp[13])

            # 主断状态
            if tmp[14] == 'AA':
                field_result.append('闭合')
            elif tmp[14] == '00':
                field_result.append('断开')
            else:
                field_result.append('异常值%s' % tmp[14])
            # ATP允许 人工允许
            if tmp[15] == 'C0':
                field_result.append('atp有效,人工无效')
            elif tmp[15] == '30':
                field_result.append('atp无效，人工有效')
            elif tmp[15] == '00':
                field_result.append('atp和人工均无效')
            else:
                field_result.append('异常值%s' % tmp[15])
            # 不允许状态字
            str_tcms = ''
            str_raw = ['未定义', '至少有一个车辆空气制动不可用|', 'CCU存在限速保护|', 'CCU自动施加常用制动|',
                       '车辆施加紧急制动EB或紧急制动UB|', '保持制动被隔离|',
                       'CCU判断与ATO通信故障(CCU监测到ATO生命信号32个周期(2s)不变化)|', '预留|']
            if tmp[16] == '00':
                field_result.append('正常')
            else:
                val_field = int(tmp[16], 16)
                for cnt in range(7, -1, -1):
                    if val_field & (1 << cnt) != 0:
                        str_tcms = str_tcms + str_raw[cnt]
                field_result.append('异常原因:%s' % str_tcms)

        return field_result

    # 显示最终结果
    def show_parser_result(self, data_type=str, field_name=list, field_value=list, field_result=list):
        self.treeWidget.clear()
        root = QtWidgets.QTreeWidgetItem(self.treeWidget)
        root.setText(0, data_type)
        # 开始生成
        if len(field_name) == len(field_result) and len(field_name) == len(field_value):
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

        self.OpenButton.clicked.connect(self.PlotSet)

        self.plot_cycle_time.setValue(1)
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
        self.realtime_plot_set_signal.emit(self.plot_cycle_time.value(), plot_flag)
        self.close()


# 定义画板类适配于后期应用
class Figure_Canvas(FigureCanvas):

    def __init__(self, parent=None):
        self.fig = matplotlib.figure.Figure()
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)  # 初始化父类函数


# 控车测量设置类
class Ctrl_MeasureDlg(QtWidgets.QMainWindow, MeasureWin):

    # 初始化，获取加载后的处理信息
    def __init__(self, parent=None, ob=FileProcess.FileProcess):
        self.log = ob
        super().__init__(parent)
        self.setupUi(self)
        self.sp = Figure_Canvas()  # 这是继承FigureCanvas的子类，使用子窗体widget作为父
        self.ctrlAccTable = QtWidgets.QTableWidget()
        l = QtWidgets.QVBoxLayout(self.widget)
        l.addWidget(self.sp)
        l.addWidget(self.ctrlAccTable)
        self.acc_table_format()
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/acc.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        self.setWindowTitle(u'ATO曲线测量器')
        self.resize(500, 600)

    # 设置加速度显示表
    def acc_table_format(self):
        self.ctrlAccTable.setRowCount(4)
        self.ctrlAccTable.setColumnCount(3)
        self.ctrlAccTable.setHorizontalHeaderLabels(['控车曲线分类', '估计加速度', '单位'])

    # 重置索引从到右，统一鼠标点击顺序
    def set_segment_idx(self, idx_start=int, idx_end=int, ):
        # 根据索引大小关系获取实际序列
        if idx_start <= idx_end:
            pass
        else:
            idx_start, idx_end = idx_end, idx_start  # 当终点比起点更靠前，互换转为正常顺序
        return idx_start, idx_end

    # 计算所有加速度 可以输入原始索引，兼容已经转换
    def comput_all_acc_extimate(self, idx_start=int, idx_end=int):
        [idx_start, idx_end] = self.set_segment_idx(idx_start, idx_end)

        x_list = self.log.cycle[idx_start:idx_end]
        y_vato_list = self.log.v_ato[idx_start:idx_end]
        y_atppmtv_list = self.log.atp_permit_v[idx_start:idx_end]
        y_atocmdv_list = self.log.cmdv[idx_start:idx_end]
        y_atpcmdvlist = self.log.ceilv[idx_start:idx_end]
        # 计算加速度
        vato_acc_est = self.get_estimate_acc(x_list, y_vato_list)
        atppmtv_acc_est = self.get_estimate_acc(x_list, y_atppmtv_list)
        atocmdv_acc_est = self.get_estimate_acc(x_list, y_atocmdv_list)
        atpcmdv_acc_est = self.get_estimate_acc(x_list, y_atpcmdvlist)

        return [atppmtv_acc_est, atpcmdv_acc_est, atocmdv_acc_est, vato_acc_est]

    # 获取速度并计算加速度,用于绘图
    def comput_vato_acc_estimate_plot(self, idx_start=int, idx_end=int, cmd=int):

        [idx_start, idx_end] = self.set_segment_idx(idx_start, idx_end)
        # 获取段
        x_list = self.log.cycle[idx_start:idx_end]
        y_list = self.log.v_ato[idx_start:idx_end]
        # 走行距离
        s_sim = self.log.s[idx_end] - self.log.s[idx_start]
        v_sim = self.log.v_ato[idx_end] - self.log.v_ato[idx_start]
        # 计算拟合的加速度
        [a_sim, p_sim] = self.get_estimate_acc(x_list, y_list)  # 一次多项式拟合，相当于线性拟合

        return [v_sim, s_sim, a_sim, x_list, y_list, p_sim]

    # 获取速度并计算加速度
    def get_estimate_acc(self, x_raw=list, y_raw=list):
        z = np.polyfit(x_raw, y_raw, 1)  # 一次多项式拟合，相当于线性拟合
        a_sim = z[0] * 10  # 获取估计加速度,由于时间单位是100ms所以乘以10,后者是函数
        p_sim = np.poly1d(z)
        print(p_sim)  # 打印拟合表达式
        return [a_sim, p_sim]

    # 用于绘制估计加速度曲线
    def measure_plot(self, idx_start=int, idx_end=int, cmd=int):
        estimate_a_tuple = 0

        estimate_a_tuple = self.comput_vato_acc_estimate_plot(idx_start, idx_end, cmd)
        v_sim = estimate_a_tuple[0]
        s_sim = estimate_a_tuple[1]
        a_sim = estimate_a_tuple[2]  # 加速度已经转为cm/s^2
        x_list = estimate_a_tuple[3]
        y_list = estimate_a_tuple[4]
        # 计算估计曲线
        y_list_sim = estimate_a_tuple[5](x_list)
        # 计算表格
        acc_all = self.comput_all_acc_extimate(idx_start, idx_end)

        item_name = ['ATP允许速度', 'ATP命令速度', 'ATO命令速度', '实际速度']
        item_unit = ['cm/s^2', 'cm/s^2', 'cm/s^2', 'cm/s^2']
        for idx, name in enumerate(item_name):
            i_content_name = QtWidgets.QTableWidgetItem(name)
            i_content_name.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            i_content_unit = QtWidgets.QTableWidgetItem(item_unit[idx])
            i_content_unit.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            i_content_value = QtWidgets.QTableWidgetItem(str(acc_all[idx][0]))
            i_content_value.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            self.ctrlAccTable.setItem(idx, 0, i_content_name)
            self.ctrlAccTable.setItem(idx, 1, i_content_value)
            self.ctrlAccTable.setItem(idx, 2, i_content_unit)

        self.sp.ax.plot(x_list, y_list_sim, color='purple')
        self.sp.ax.plot(x_list, y_list, color='deeppink', marker='.', markersize=0.2)
        str_asim = '预估加速度:%.*f cm/s^2\n' % (3, a_sim)
        str_cycle_num = '测量时间:%.*f s\n' % (3, (idx_end - idx_start) / 10.0)
        str_s_sim = 'ATO走行距离:%d cm\n' % int(s_sim)
        str_v_sim = 'ATO速度变化:%d cm/s' % (v_sim)

        str_show = str_asim + str_cycle_num + str_s_sim + str_v_sim
        props = dict(boxstyle='round', facecolor='pink', alpha=0.15)
        if a_sim > 0:
            self.sp.ax.text(0.1, 0.95, str_show, transform=self.sp.ax.transAxes, fontsize=10, verticalalignment='top',
                            bbox=props)
        else:
            self.sp.ax.text(0.48, 0.95, str_show, transform=self.sp.ax.transAxes, fontsize=10, verticalalignment='top',
                            bbox=props)


# 控车网络时延显示类
class Train_Com_MeasureDlg(QtWidgets.QMainWindow, MeasureWin):

    # 初始化，获取加载后的处理信息
    def __init__(self, parent=None, ob=FileProcess.FileProcess):
        self.log = ob
        super().__init__(parent)
        self.setupUi(self)
        self.sp = Figure_Canvas(self.widget)  # 这是继承FigureCanvas的子类，使用子窗体widget作为
        self.trainComTable = QtWidgets.QTableWidget()
        l = QtWidgets.QVBoxLayout(self.widget)
        self.sp.mpl_toolbar = NavigationToolbar(self.sp, self.widget)  # 传入FigureCanvas类或子类实例，和父窗体

        # l.addWidget(self.trainComTable)
        l.addWidget(self.sp)
        l.addWidget(self.sp.mpl_toolbar)
        self.acc_table_format()
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/BZT.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        self.setWindowTitle(u'车辆通信时延观测器')
        self.resize(500, 600)
        # 初始化内容
        self.ato2tcms_tb_ctrl = []
        self.tcms2ato_tb_fbk = []
        self.cycle_ord = []  # 为了使得绘图由周期信息，考虑到某个周期可能没有输入只有输出，所以需要人工组合，使得输入保持
        self.mvbdialog = MVBPortDlg()

    # 设置显示表显示表
    def acc_table_format(self):
        self.trainComTable.setRowCount(4)
        self.trainComTable.setColumnCount(3)
        self.trainComTable.setHorizontalHeaderLabels(['统计项目', '时延', '单位'])

    # 计算所有牵引制动及反馈情况情况
    def comput_all_ctrl_info(self):

        pat_ato_ctrl = 'MVB[' + str(int(self.mvbdialog.led_ato_ctrl.text(), 16)) + ']'
        pat_ato_stat = 'MVB[' + str(int(self.mvbdialog.led_ato_stat.text(), 16)) + ']'
        pat_tcms_stat = 'MVB[' + str(int(self.mvbdialog.led_tcms_stat.text(), 16)) + ']'
        tb_stat = ''
        tb_fbk = ''
        # 读取该周期内容
        try:
            for idx in range(len(self.log.cycle)):
                ato_ctrl_flag = 0  # 这个标志用于当该周期里既有车辆反馈又有ATO输出时才认为成功
                tcms_fbk_flag = 0
                for line in self.log.cycle_dic[self.log.cycle[idx]].raw_analysis_lines:
                    if pat_ato_ctrl in line:
                        if '@' in line:
                            pass
                        else:
                            real_idx = line.find('MVB[')
                            tmp = line[real_idx + 28:real_idx + 42].split()  # 取出命令字段中的牵引制动及命令
                            tb_stat = tmp[0]
                            t_cmd = tmp[1] + tmp[2]
                            b_cmd = tmp[3] + tmp[4]
                            ato_ctrl_flag = 1
                    elif pat_tcms_stat in line:
                        if '@' in line:
                            pass
                        else:
                            real_idx = line.find('MVB[')
                            tmp = line[real_idx + 31:real_idx + 45].split()  # 还有一个冒号需要截掉
                            tb_fbk = tmp[0]
                            t_fbk = tmp[1] + tmp[2]
                            b_fbk = tmp[3] + tmp[4]
                            tcms_fbk_flag = 1
                if ato_ctrl_flag and tcms_fbk_flag:
                    if tb_stat == 'AA':
                        self.ato2tcms_tb_ctrl.append(int(t_cmd, 16))
                    elif tb_stat == '55':
                        self.ato2tcms_tb_ctrl.append(0 - int(b_cmd, 16))
                    elif tb_stat == 'A5':
                        self.ato2tcms_tb_ctrl.append(0)
                    else:
                        print('mvb delay plot compute err!')
                        self.ato2tcms_tb_ctrl.append(0)

                    if tb_fbk == 'AA':
                        self.tcms2ato_tb_fbk.append(int(t_fbk, 16))
                    elif tb_fbk == '55':
                        self.tcms2ato_tb_fbk.append(0 - int(b_fbk, 16))
                    elif tb_fbk == 'A5':
                        self.tcms2ato_tb_fbk.append(0)
                    else:
                        print('mvb delay plot compute err!')
                        self.tcms2ato_tb_fbk.append(0)

                    # 获取周期信息
                    self.cycle_ord.append(self.log.cycle[idx])
        except Exception as err:
            print(err)

    # 用于绘制估计加速度曲线
    def measure_plot(self):
        self.comput_all_ctrl_info()
        self.sp.ax.plot(self.cycle_ord, self.ato2tcms_tb_ctrl,label='ATO输出MVB命令', color='blue', marker='.', markersize=0.5)
        self.sp.ax.plot(self.cycle_ord, self.tcms2ato_tb_fbk, label='TCMS反馈MVB命令',color='green', marker='.', markersize=0.5)
        self.ax1 = self.sp.ax.twinx()
        self.ax1.plot(self.log.cycle, self.log.v_ato, color='red', marker='.', markersize=0.5)
        self.tb_cursor = SnaptoCursor(self.sp, self.sp.ax, self.cycle_ord, self.ato2tcms_tb_ctrl)  # 初始化一个光标
        self.tb_cursor.reset_cursor_plot()
        self.sp.mpl_connect('motion_notify_event', self.tb_cursor.mouse_move)
        self.tb_cursor.move_signal.connect(self.cusor_plot)
        self.sp.ax.set_xlim(self.cycle_ord[0], self.cycle_ord[len(self.cycle_ord) - 1])  # 默认与不带光标统一的显示范围
        self.sp.ax.set_ylim(-17000, 17000)
        self.sp.ax.legend(loc='upper right')
        self.sp.ax.grid(which='both',linestyle='-')

    # 光标跟随
    def cusor_plot(self, idx):
        self.sp.ax.texts.clear()
        str_ato_cycle = '当前系统周期:%d \n' % (self.cycle_ord[idx])
        str_ato_v = '当前系统速度:%dcm/s\n' % (self.log.v_ato[idx])
        str_ato_ctrl = 'ATO输出牵引制动值:%d \n' % (self.ato2tcms_tb_ctrl[idx])
        str_tcms_fbk = '车辆反馈牵引制动值:%d ' % (self.tcms2ato_tb_fbk[idx])
        str_show = str_ato_cycle + str_ato_v +  str_ato_ctrl + str_tcms_fbk
        props = dict(boxstyle='round', facecolor='pink', alpha=0.15)

        self.sp.ax.text(0.03, 0.97, str_show, transform=self.sp.ax.transAxes, fontsize=10, verticalalignment='top',
                        bbox=props)


# C3ATO记录板转义工具类
class C3ATO_Transfer_Dlg(QtWidgets.QDialog, C3ATOTransferWin):
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
        # 当前执行状态机
        self.latestChoosedState = 0   # 用于记录最近一次有效的文件选择，0=无效，1=单文件，2=多文件，3=批量文件
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
        if self.latestChoosedState == 1:
            self.SingleFileTrans(self.singleFile)       # 处理单文件路径
        elif self.latestChoosedState == 2:
            self.MultiFileTrans(self.multiFileList)     # 处理文件列表
        elif self.latestChoosedState == 3:
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
        self.barAllAdd = C3ATO_Transfer_Dlg.ComputEBarAllAdd(fileList)
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
            dstPath = C3ATO_Transfer_Dlg.CheckAndCreateTransDir(self.oldBatchDir)     # 创建镜像的转义文件路径
        except Exception as err:
            print(err)
        self.textC3ATOProcess.append('Info：'+'文件遍历!')
        self.barAllAdd = C3ATO_Transfer_Dlg.ComputEBarAllAdd(fileList)
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
        if self.latestChoosedState < 2:
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
    def ComputEBarAllAdd(fileList=list):
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
        self.RsetDlgPanel()
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
            self.latestChoosedState = 0
            self.textC3ATOProcess.append('Info： 没有选择文件！')
        else:
            self.latestChoosedState = 1
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
        self.RsetDlgPanel()
        temp = '/'
        # 若之前选择过，列表非空
        if not self.oldMultiDirPath:
            filepath = QtWidgets.QFileDialog.getOpenFileNames(self, '选择多个文件', 'c:/', "txt files(*.txt *.log)")
        else:
            filepath = QtWidgets.QFileDialog.getOpenFileNames(self, '选择多个文件', self.oldMultiDirPath,
                                                              "txt files(*.txt *.log)")

        pathList = filepath[0]  # 取出多文件的列表地址
        if not pathList:  # 没有选择文件
            self.latestChoosedState = 0
            self.textC3ATOProcess.append('Info： 没有选择文件！')
        else:
            self.latestChoosedState = 2
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
        self.RsetDlgPanel()
        temp = '/'
        # 若之前选择过，列表非空
        if not self.oldBatchDir:
            path = QtWidgets.QFileDialog.getExistingDirectory(self, '选择文件目录', 'c:/')
        else:
            path = QtWidgets.QFileDialog.getExistingDirectory(self, '选择文件目录', self.oldBatchDir)
        # 更新记录路径
        self.oldBatchDir = path
        if not path:  # 没有选择文件路径
            self.latestChoosedState = 0
            self.textC3ATOProcess.append('Info： 没有选择文件！')
        else:
            self.latestChoosedState = 3
            # 更新前初始化，文件列表
            self.dirFileList = []
            self.GetFileList(self.dirFileList, path, '.txt')
            for f in self.dirFileList:
                self.textC3ATOProcess.append(f)  # 显示路径
            self.textC3ATOProcess.append('Info：共选择（*.txt）文件 %d 个！' % (len(self.dirFileList)))

    def RsetDlgPanel(self):
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
                C3ATO_Transfer_Dlg.GetFileList(fileList, fullPath, fileType)
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
                    C3ATO_Transfer_Dlg.CopyFileDir(basePath, dstPath)
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
        shutil.copytree(src_path, dst_path, symlinks=False, ignore=None, copy_function=C3ATO_Transfer_Dlg.CopyFunc,
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
