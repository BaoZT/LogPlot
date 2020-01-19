#!/usr/bin/env python

# encoding: utf-8

import os
import sys
import threading
import time

import numpy as np
import serial
import serial.tools.list_ports
import xlwt
from PyQt5 import QtWidgets, QtCore, QtGui
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar

import FileProcess
import MiniWinCollection
import RealTimeExtension
from KeyWordPlot import Figure_Canvas, SnaptoCursor, Figure_Canvas_R
from LogMainWin import Ui_MainWindow
from MiniWinCollection import MVBPortDlg, SerialDlg, MVBParserDlg, UTCTransferDlg, RealTimePlotDlg, Ctrl_MeasureDlg, \
    Cyclewindow, Train_Com_MeasureDlg
from ProtocolParse import MVBParse
from RealTimeExtension import SerialRead, RealPaintWrite

# 全局静态变量
load_flag = 0  # 区分是否已经加载文件,1=加载且控车，2=加载但没有控车
cursor_in_flag = 0  # 区分光标是否在图像内,初始化为0,in=1，out=2
curve_flag = 1  # 区分绘制曲线类型，0=速度位置曲线，1=周期位置曲线
cur_interface = 0  # 当前界面， 1=离线界面，2=在线界面


# 主界面类
class Mywindow(QtWidgets.QMainWindow, Ui_MainWindow):
    is_cursor_created = 0
    LinkBtnStatus = 0  # 实时按钮状态信息

    # 建立的是Main Window项目，故此处导入的是QMainWindow
    def __init__(self):
        super(Mywindow, self).__init__()
        self.setupUi(self)
        self.initUI()
        self.icon_from_file()
        self.file = ''
        self.savePath = os.getcwd()  # 实时存储的文件保存路径（文件夹）,增加斜线直接添加文件名即可
        self.savefilename = ''  # 实时存储的写入文件名(含路径)
        self.pathlist = []
        self.BTM_cycle = []  # 存储含有BTM的周期号，用于操作计数器间接索引
        self.mode = 0  # 默认0是浏览模式，1是标注模式
        self.ver = '3.0.1'  # 标示软件版本
        self.serdialog = SerialDlg()  # 串口设置对话框，串口对象，已经实例
        self.serport = serial.Serial(timeout=None)  # 操作串口对象

        self.mvbdialog = MVBPortDlg()
        self.comboBox.addItems(self.serdialog.Port_List())  # 调用对象方法获取串口对象
        #self.resize(1300, 700)
        self.setWindowTitle('LogPlot-V' + self.ver)
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/BZT.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        # 离线绘图
        l = QtWidgets.QVBoxLayout(self.widget)
        self.sp = Figure_Canvas(self.widget)  # 这是继承FigureCanvas的子类，使用子窗体widget作为父亲类
        self.sp.mpl_toolbar = NavigationToolbar(self.sp, self.widget)  # 传入FigureCanvas类或子类实例，和父窗体
        l.addWidget(self.sp)
        # l.addWidget(self.sp.mpl_toolbar)

        self.bubble_status = 0  # 控车悬浮气泡状态，0=停靠，1=跟随
        self.tag_latest_pos_idx = 0  # 悬窗最近一次索引，用于状态改变或曲线改变时立即刷新使用，最近一次
        self.pat_plan = FileProcess.FileProcess.creat_plan_pattern()  # 计划解析模板
        self.pat_list = FileProcess.FileProcess.create_all_pattern()  # 获取所有解析模板

        self.ctrl_measure_status = 0  # 控车曲线测量状态，0=初始态，1=测量起始态，2=进行中 ,3=测量终止态
        # 在线绘图
        lr = QtWidgets.QVBoxLayout(self.widget_2)
        self.sp_real = Figure_Canvas_R(self.widget_2)
        lr.addWidget(self.sp_real)  # 必须创造布局并且加入才行
        # 设置BTM表
        self.tableATPBTM.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        # MVB解析面板
        self.mvbParserPage = MVBParse()

        # MVB解析器
        self.mvbparaer = MVBParserDlg()
        # UTC转换器
        self.utctransfer = UTCTransferDlg()
        # 绘图界面设置器
        self.realtime_plot_dlg = RealTimePlotDlg()  # 实时绘图界面设置
        self.realtime_plot_interval = 1  # 默认1s绘图
        self.is_realtime_paint = False  # 实时绘图否
        self.realtime_plot_dlg.realtime_plot_set_signal.connect(self.realtime_plot_set)
        # 实时btm和io
        self.real_io_in_list = []
        self.real_io_out_list = []
        self.real_btm_list = []
        # 实时速传检测
        self.sdu_info_s = [0, 0]  # ato 速传位置， atp速传位置
        self.widget.setFocus()
        self.fileOpen.triggered.connect(self.showDialog)
        self.fileClose.triggered.connect(self.close_figure)
        self.fileSave.triggered.connect(self.sp.mpl_toolbar.save_figure)
        self.actionConfig.triggered.connect(self.sp.mpl_toolbar.configure_subplots)
        self.actionExport.triggered.connect(self.export_ato_ctrl_info)
        self.actionPan.triggered.connect(self.sp.mpl_toolbar.pan)
        self.actionZoom.triggered.connect(self.zoom)
        self.actionEdit.triggered.connect(self.sp.mpl_toolbar.edit_parameters)
        self.actionReset.triggered.connect(self.reset_logplot)
        self.actionHome.triggered.connect(self.home_show)  # 这里home,back,和forward都是父类中实现的
        self.actionBck.triggered.connect(self.sp.mpl_toolbar.back)  # NavigationToolbar2方法
        self.actionFwd.triggered.connect(self.sp.mpl_toolbar.forward)
        self.actionTag.triggered.connect(self.mode_change)
        self.actionView.triggered.connect(self.mode_change)
        self.actionVersion.triggered.connect(self.version_msg)
        self.sp.mpl_connect('button_press_event', self.sp.right_press)
        self.actionPrint.triggered.connect(self.cycle_print)  # 打印周期
        self.actionCS.triggered.connect(self.cmd_change)
        self.actionVS.triggered.connect(self.cmd_change)
        self.actionRealtime.triggered.connect(self.showRealTimeUI)
        self.actionoffline.triggered.connect(self.showOffLineUI)
        self.actionSerSet.triggered.connect(self.showSerSet)
        self.spinBox.valueChanged.connect(self.spin_value_changed)
        self.serdialog.serUpdateSingal.connect(self.updateSerSet)
        self.actionMVB.triggered.connect(self.show_mvb_port_set)
        self.mvbdialog.mvbPortSingal.connect(self.update_mvb_port_pat)
        self.btn_SavePath.clicked.connect(self.showlogSave)
        self.btn_PortLink.clicked.connect(self.btnLinkorBreak)
        self.actionMVBParser.triggered.connect(self.show_mvb_parser)
        self.actionUTC.triggered.connect(self.show_utc_transfer)
        self.action_bubble_dock.triggered.connect(self.set_ctrl_bubble_format)
        self.action_bubble_track.triggered.connect(self.set_ctrl_bubble_format)
        self.action_acc_measure.triggered.connect(self.ctrl_measure)
        self.sp.mpl_connect('button_press_event', self.ctrl_measure_clicked)  # 鼠标单击的测量处理事件
        self.btn_mvb_delay_plot.clicked.connect(self.show_statistics_mvb_delay)
        # 事件绑定
        self.actionBTM.triggered.connect(self.update_event_point)
        self.actionJD.triggered.connect(self.update_event_point)
        self.actionPLAN.triggered.connect(self.update_event_point)
        self.actionWL.triggered.connect(self.update_event_point)
        self.actionRealTimePlot.triggered.connect(self.showRealtimePlotSet)
        # 右边侧栏显示
        self.btn_ato.clicked.connect(self.showOffRight_ATO)
        self.btn_plan.clicked.connect(self.showOffRight_PLAN)
        self.btn_train.clicked.connect(self.showOffRight_MVB)
        self.btn_filetab.clicked.connect(self.showOffRight_FILE)
        self.btn_atp.clicked.connect(self.showoffRight_ATP)
        self.btn_statistics.clicked.connect(self.showoffRight_STATISTICS)
        self.btn_balise.clicked.connect(self.showoffRight_BALISE)
        self.btn_io_info.clicked.connect(self.showoffRight_ato_IO)

        # 窗口设置初始化
        self.showOffLineUI()
        self.filetab_format()
        self.set_label_format()
        self.set_tree_fromat()
        self.model = QtWidgets.QDirModel()
        self.lineEdit.setText(os.getcwd())
        self.treeView.setModel(self.model)
        self.treeView.doubleClicked.connect(self.filetab_clicked)
        self.tableATPBTM.itemClicked.connect(self.BTM_selected_info)
        self.tb_ato_IN.horizontalHeader().setVisible(True)

    def initUI(self):

        self.splitter_5.setStretchFactor(0, 6)
        self.splitter_5.setStretchFactor(1, 4)

        self.splitter_3.setStretchFactor(0, 8)
        self.splitter_3.setStretchFactor(1, 2)
        self.splitter_2.setStretchFactor(0, 7)
        self.splitter_2.setStretchFactor(1, 3)
        self.splitter.setStretchFactor(0, 10)
        self.splitter.setStretchFactor(1, 2)
        self.Exit.setStatusTip('Ctrl+Q')
        self.Exit.setStatusTip('Exit app')
        self.fileOpen.setStatusTip('Ctrl+O')
        self.fileOpen.setStatusTip('Open Log')
        self.set_table_format()
        self.progressBar.setValue(0)
        self.label_2.setText('')
        self.spinBox.setRange(0, 1000000)
        self.action_bubble_track.setChecked(True)
        self.Exit.triggered.connect(QtWidgets.qApp.quit)
        self.CBvato.stateChanged.connect(self.update_up_cure)
        self.CBatpcmdv.stateChanged.connect(self.update_up_cure)
        self.CBlevel.stateChanged.connect(self.update_up_cure)
        self.CBcmdv.stateChanged.connect(self.update_up_cure)
        self.CBacc.stateChanged.connect(self.update_down_cure)
        self.CBramp.stateChanged.connect(self.update_down_cure)
        self.CBatppmtv.stateChanged.connect(self.update_up_cure)

        self.CBvato.stateChanged.connect(self.realtimeLineChoose)
        self.CBatpcmdv.stateChanged.connect(self.realtimeLineChoose)
        self.CBlevel.stateChanged.connect(self.realtimeLineChoose)
        self.CBcmdv.stateChanged.connect(self.realtimeLineChoose)
        # 实时ATP允许速度保留未实现

        self.actionBTM.triggered.connect(self.set_log_event)
        # 如果初始界面实时
        self.fileOpen.setDisabled(True)  # 设置文件读取不可用
        self.cyclewin = Cyclewindow()
        self.realtime_plan_table_format()
        self.show()

    # 事件处理函数，打开文件读取并初始化界面
    def showDialog(self):
        temp = '/'
        global curve_flag
        global load_flag
        if len(self.pathlist) == 0:
            filepath = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', 'd:/', "txt files(*.txt *.log)")
            path = filepath[0]  # 取出文件地址
            if path == '':  # 没有选择文件
                self.statusbar.showMessage('Choose Nothing ！')
            else:
                name = filepath[0].split("/")[-1]
                self.pathlist = filepath[0].split("/")
                self.file = path
                self.statusbar.showMessage(path)
        else:
            self.Log('Init file path', __name__, sys._getframe().f_lineno)
            filepath = temp.join(self.pathlist[:-1])  # 纪录上一次的文件路径
            filepath = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', filepath)
            path = filepath[0]
            name = filepath[0].split("/")[-1]
            # 求出本次路径序列
            templist = filepath[0].split("/")
            self.update_path_changed(templist)
            self.file = path
            self.statusbar.showMessage(path)
        # 当文件路径不为空
        self.reset_logplot()

    # 显示实时界面
    def showRealTimeUI(self):
        global cur_interface
        cur_interface = 2
        self.stackedWidget.setCurrentWidget(self.page_4)
        self.stackedWidget_RightCol.setCurrentWidget(self.stackedWidgetPage1)
        self.fileOpen.setDisabled(True)  # 设置文件读取不可用
        self.btn_plan.setDisabled(True)
        self.btn_train.setDisabled(True)
        self.btn_filetab.setDisabled(True)
        self.btn_atp.setDisabled(True)
        self.btn_filetab.setDisabled(True)
        # 如有转换重置右边列表
        self.actionView.trigger()
        self.tableWidget.clear()
        self.set_table_format()
        self.treeWidget.clear()
        self.tableWidgetPlan_2.clear()
        self.set_tree_fromat()
        self.tb_ato_IN.clear()
        self.tb_ato_OUT.clear()
        self.tb_ato_IN.setHorizontalHeaderLabels(['时间', '周期', '采集信号', '取值'])
        self.tb_ato_IN.setColumnCount(4)
        self.tb_ato_OUT.setHorizontalHeaderLabels(['时间', '周期', '输出信号'])
        self.tb_ato_OUT.setColumnCount(3)
        # 初始化表格
        self.tableATPBTM.clear()
        self.tableATPBTM.setHorizontalHeaderLabels(['时间', '应答器编号', '位置矫正值', '公里标'])
        self.tableATPBTM.setColumnWidth(0, 60)
        self.tableATPBTM.setColumnWidth(1, 80)
        self.tableATPBTM.setColumnWidth(2, 70)
        self.tableATPBTM.setColumnWidth(3, 70)
        self.tableATPBTM.resizeRowsToContents()
        self.tableATPBTM.resizeColumnsToContents()
        self.tableATPBTM.verticalHeader().setVisible(True)
        self.real_btm_list=[]
        self.real_io_out_list=[]
        self.real_io_in_list=[]

    # 显示离线界面
    def showOffLineUI(self):
        global cur_interface
        cur_interface = 1
        self.stackedWidget.setCurrentWidget(self.page_3)
        self.fileOpen.setEnabled(True)  # 设置文件读取可用
        self.stackedWidget_RightCol.setCurrentWidget(self.stackedWidgetPage1)
        self.btn_plan.setEnabled(True)
        self.btn_train.setEnabled(True)
        self.btn_atp.setEnabled(True)
        self.btn_filetab.setEnabled(True)

    # 显示控车情况
    def showOffRight_ATO(self):
        self.stackedWidget_RightCol.setCurrentWidget(self.stackedWidgetPage1)

    # 显示MVB数据
    def showOffRight_MVB(self):
        self.stackedWidget_RightCol.setCurrentWidget(self.page_train)

    # 显示计划情况
    def showOffRight_PLAN(self):
        self.stackedWidget_RightCol.setCurrentWidget(self.page_plan)

    # 显示记录情况
    def showOffRight_FILE(self):
        self.stackedWidget_RightCol.setCurrentWidget(self.stackedWidgetPage2)

    # 显示ATP接口情况
    def showoffRight_ATP(self):
        self.stackedWidget_RightCol.setCurrentWidget(self.page_ATP)

    # 显示应答器信息
    def showoffRight_BALISE(self):
        self.stackedWidget_RightCol.setCurrentWidget(self.page_balise)

    # 显示io统计信息
    def showoffRight_ato_IO(self):
        self.stackedWidget_RightCol.setCurrentWidget(self.page_ato_IO)

    # 显示统计接口情况
    def showoffRight_STATISTICS(self):
        self.stackedWidget_RightCol.setCurrentWidget(self.page_Statistic)

    # 串口设置，应当立即更新
    def showSerSet(self):
        self.serdialog.show()

    # 如果设置窗口应该更新
    def updateSerSet(self):
        self.serport = self.serdialog.ser

    # 主界面的串口显示,立即更新路径
    def showlogSave(self):
        self.savePath = QtWidgets.QFileDialog.getExistingDirectory(directory=os.getcwd())
        self.lineEdit.setText(self.savePath)

    # 实时绘设置
    def showRealtimePlotSet(self):
        self.realtime_plot_dlg.show()

    # 连接或断开按钮
    def btnLinkorBreak(self):
        # 初始化串口
        ser_is_open = 0
        if Mywindow.LinkBtnStatus == 0:
            RealTimeExtension.exit_flag = 0
            Mywindow.LinkBtnStatus = 1
            self.btn_PortLink.setText('断开')
            self.btn_PortLink.setStyleSheet("background: rgb(191, 255, 191);")
            tmpfilename = self.serdialog.filenameLine.text()
            self.update_mvb_port_pat()  # 更新解析用的端口号
            # 按照默认设置，设置并打开串口
            self.serdialog.OpenButton.click()
            self.serport.port = self.comboBox.currentText()
            # 当串口没有打开过
            #ser_is_open = 1   # 测试时打开
            while ser_is_open == 0:
                try:
                    self.serport.open()
                    self.show_message('Info:串口%s成功打开!' % self.serport.port)
                    ser_is_open = 1  # 串口打开
                except Exception as err:
                    reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                                                              "串口异常",
                                                              "注意：打开串口失败，关闭其他占用再尝试！",
                                                              QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Close)
                    # 选择确定继续，否则取消
                    if reply == 16384:
                        pass
                    elif reply == 2097152:
                        break
            if ser_is_open == 1:
                self.savePath = self.lineEdit.text() + '\\'  # 更新路径选择窗口内容
                self.savePath = self.savePath.replace('//', '/')
                self.savePath = self.savePath.replace('/', '\\')
                thRead = SerialRead('COMThread', self.serport)  # 串口数据读取解析线程
                thPaintWrite = RealPaintWrite(self.savePath, tmpfilename, self.serport.port)  # 文件写入线程
                thpaint = threading.Thread(target=self.run_paint)  # 绘图线程
                # 链接显示
                thPaintWrite.pat_show_signal.connect(self.realtime_Content_show)  # 界面显示处理
                thPaintWrite.plan_show_signal.connect(self.realtime_plan_show)  # 局部变量无需考虑后续解绑
                thPaintWrite.sp7_show_signal.connect(self.realtime_btm_show)  # 应答器更新
                thPaintWrite.io_show_signal.connect(self.realtime_io_show)  # io信息更新
                thPaintWrite.sdu_show_signal.connect(self.realtime_sdu_show) # sdu 信息更新
                # 设置线程
                thpaint.setDaemon(True)
                thRead.setDaemon(True)
                thPaintWrite.setDaemon(True)
                # 开启线程
                thPaintWrite.start()
                thRead.start()
                self.is_realtime_paint = True  # 允许绘图

                thpaint.start()
                self.show_message('Info:读取记录及绘图线程启动成功！')
            else:
                # 打开失败设置回去
                self.show_message('Info:读取记录及绘图线程启动失败！')
                Mywindow.LinkBtnStatus = 0
                RealTimeExtension.exit_flag = 1
                self.reatimelbl_defaultshow()
                self.btn_PortLink.setText('连接')
                self.btn_PortLink.setStyleSheet(" background: rgb(238, 86, 63);")

        else:
            Mywindow.LinkBtnStatus = 0
            self.btn_PortLink.setText('连接')
            self.btn_PortLink.setStyleSheet(" background: rgb(238, 86, 63);")
            RealTimeExtension.exit_flag = 1
            self.is_realtime_paint = False
            self.reatimelbl_defaultshow()
            self.serport.close()

            self.show_message('Info:串口关闭!')

    # 界面实时绘图函数
    def run_paint(self):
        while self.is_realtime_paint:
            try:
                time.sleep(self.realtime_plot_interval)  # 绘图线程非常消耗性能，当小于1s直接影响读取和写入
                self.sp_real.realTimePlot()
                self.sp_real.draw()
            except Exception as err:
                self.Log(err, __name__, sys._getframe().f_lineno)
                self.show_message('Error:绘图线程异常！')
                print('thread paint info!' + str(time.time()))
        self.show_message('Info:绘图线程结束!')

    # 界面更新信号槽函数
    def realtime_Content_show(self, result=tuple):
        cycle_num = result[0]
        cycle_time = result[1]
        fsm_list = result[2]
        sc_ctrl = result[3]
        stoppoint = result[4]
        ato2tcms_ctrl = result[5]
        ato2tcms_stat = result[6]
        tcms2ato_stat = result[7]
        gfx_flag = result[8]
        sp2_list = result[9]
        sp5_list = result[10]
        sp131_list = result[11]
        # 显示到侧面
        self.realtime_table_show(cycle_num, cycle_time, sc_ctrl, stoppoint, gfx_flag)
        self.realtime_fsm_show(fsm_list)
        # 显示主界面
        self.realtime_mvb_show(ato2tcms_ctrl, ato2tcms_stat, tcms2ato_stat)
        self.realtime_atp_common_show(sp2_list)
        self.realtime_ato_dmi_show(sp131_list)
        self.realtime_train_data_show(sp5_list)

    # 显示ATP通用信息SP2
    def realtime_atp_common_show(self, sp_tpl):
        if sp_tpl != ():
            # 门允许状态
            if sp_tpl[2].strip() == '1':  # 左门允许
                self.lbl_door_pmt_2.setText('左门允许')
                self.lbl_door_pmt_2.setStyleSheet("background-color: rgb(0, 255, 127);")
            elif sp_tpl[3].strip() == '1':  # 右门允许
                self.lbl_door_pmt_2.setText('右门允许')
                self.lbl_door_pmt_2.setStyleSheet("background-color: rgb(0, 255, 127);")
            else:
                self.lbl_door_pmt_2.setText('无门允许')
                self.lbl_door_pmt_2.setStyleSheet("background-color: rgb(255, 0, 0);")
            # ATP停准停稳状态
            if sp_tpl[16].strip() == '0':
                self.lbl_atp_stop_ok_2.setText('车未停稳')
                self.lbl_atp_stop_ok_2.setStyleSheet("background-color: rgb(255, 0, 0);")
            elif sp_tpl[16].strip() == '1':
                self.lbl_atp_stop_ok_2.setText('停稳未停准')
                self.lbl_atp_stop_ok_2.setStyleSheet("background-color: rgb(0, 200, 127);")
            elif sp_tpl[16].strip() == '2':
                self.lbl_atp_stop_ok_2.setText('停稳停准')
                self.lbl_atp_stop_ok_2.setStyleSheet("background-color: rgb(0, 255, 127);")

            # 是否TSM区
            if sp_tpl[21].strip() == '2147483647' or sp_tpl[21].strip() != '4294967295':
                self.lbl_tsm_2.setText('恒速区')
                self.lbl_tsm_2.setStyleSheet("background-color: rgb(0, 255, 127);")
            else:
                self.lbl_tsm_2.setText('减速区')
                self.lbl_tsm_2.setStyleSheet("background-color: rgb(255, 255, 0);")

            # 是否立折
            if sp_tpl[5].strip() == '1':
                self.lbl_tb_2.setText('立折换端')
                self.lbl_tb_2.setStyleSheet("background-color: rgb(0, 255, 127);")
            else:
                self.lbl_tb_2.setText('非换端')
                self.lbl_tb_2.setStyleSheet("background-color: rgb(170, 170, 255);")

            # 是否切牵引
            if sp_tpl[24].strip() == '1':
                self.lbl_atp_cut_traction_2.setText('ATP切除牵引')
                self.lbl_atp_cut_traction_2.setStyleSheet("background-color:  rgb(255, 0, 0);")
            else:
                self.lbl_atp_cut_traction_2.setText('未切除牵引')
                self.lbl_atp_cut_traction_2.setStyleSheet("background-color: rgb(170, 170, 255);")

            # 是否制动
            if sp_tpl[25].strip() == '1':
                self.lbl_atp_brake_2.setText('ATP施加制动')
                self.lbl_atp_brake_2.setStyleSheet("background-color: rgb(255, 0, 0);")
            else:
                self.lbl_atp_brake_2.setText('未施加制动')
                self.lbl_atp_brake_2.setStyleSheet("background-color: rgb(170, 170, 255);")

            # ATP等级/模式
            if sp_tpl[8].strip() == '1':
                self.lbl_atp_level_2.setText('CTCS 2')

                if sp_tpl[9].strip() == '1':
                    self.lbl_atp_mode_2.setText('待机模式')
                elif sp_tpl[9].strip() == '2':
                    self.lbl_atp_mode_2.setText('完全模式')
                elif sp_tpl[9].strip() == '3':
                    self.lbl_atp_mode_2.setText('部分模式')
                elif sp_tpl[9].strip() == '5':
                    self.lbl_atp_mode_2.setText('引导模式')
                elif sp_tpl[9].strip() == '7':
                    self.lbl_atp_mode_2.setText('目视模式')
                elif sp_tpl[9].strip() == '8':
                    self.lbl_atp_mode_2.setText('调车模式')
                elif sp_tpl[9].strip() == '9':
                    self.lbl_atp_mode_2.setText('隔离模式')
                elif sp_tpl[9].strip() == '10':
                    self.lbl_atp_mode_2.setText('机信模式')
                elif sp_tpl[9].strip() == '11':
                    self.lbl_atp_mode_2.setText('休眠模式')
            elif sp_tpl[8].strip() == '3':
                self.lbl_atp_level_2.setText('CTCS 3')

                if sp_tpl[9].strip() == '6':
                    self.lbl_atp_mode_2.setText('待机模式')
                elif sp_tpl[9].strip() == '0':
                    self.lbl_atp_mode_2.setText('完全模式')
                elif sp_tpl[9].strip() == '1':
                    self.lbl_atp_mode_2.setText('引导模式')
                elif sp_tpl[9].strip() == '2':
                    self.lbl_atp_mode_2.setText('目视模式')
                elif sp_tpl[9].strip() == '3':
                    self.lbl_atp_mode_2.setText('调车模式')
                elif sp_tpl[9].strip() == '10':
                    self.lbl_atp_mode_2.setText('隔离模式')
                elif sp_tpl[9].strip() == '5':
                    self.lbl_atp_mode_2.setText('休眠模式')

            # 显示信息
            if '4294967295' != sp_tpl[23].strip():
                self.led_atp_milestone_2.setText(
                    'K' + str(int(int(sp_tpl[23]) / 1000)) + '+' + str(int(sp_tpl[23]) % 1000))
            else:
                self.led_atp_milestone.setText('未知')
            self.led_stn_center_dis_2.setText(sp_tpl[18].strip() + 'cm')
            self.led_jz_signal_dis_2.setText(sp_tpl[19].strip() + 'cm')
            self.led_cz_signal_dis_2.setText(sp_tpl[20].strip() + 'cm')
            self.led_atp_tsm_dis_2.setText(sp_tpl[21].strip() + 'cm')
            self.led_cz_signal_dis_2.setText(sp_tpl[20].strip() + 'cm')
            self.led_atp_target_dis_2.setText(sp_tpl[7].strip() + 'cm')
            self.led_atp_gfx_dis_2.setText(sp_tpl[14].strip() + 'm')
            self.led_atp_target_v_2.setText(sp_tpl[6].strip() + 'cm/s')
            self.led_atp_ma_2.setText(sp_tpl[12].strip() + 'm')
            self.led_atp_stoperr_2.setText(sp_tpl[17].strip() + 'cm')

    # 显示列车数据内容SP5
    def realtime_train_data_show(self, sp_tpl):
        if sp_tpl != ():
            if sp_tpl[0].strip() == '1':
                self.led_units_2.setText('8编组')
            elif sp_tpl[0].strip() == '2':
                self.led_units_2.setText('16编组')
            elif sp_tpl[0].strip() == '3':
                self.led_units_2.setText('18编组')

            if sp_tpl[9].strip() == '1':
                self.led_driver_strategy_2.setText('正常策略')
            elif sp_tpl[9].strip() == '2':
                self.led_driver_strategy_2.setText('快行策略')
            elif sp_tpl[9].strip() == '3':
                self.led_driver_strategy_2.setText('慢行策略')

            # BTM天线等
            self.led_atp_btm_pos_2.setText(str(int(sp_tpl[3]) * 10) + 'cm')
            self.led_head_foor_dis_2.setText(sp_tpl[4].strip() + 'cm')
            self.led_nid_engine_2.setText(sp_tpl[8].strip())

    # ATO图标实时显示SP131
    def realtime_ato_dmi_show(self, sp_tpl):
        if sp_tpl != ():
            if sp_tpl[6].strip() == '1':
                self.lbl_mvb_link_2.setText('MVB正常')
                self.lbl_mvb_link_2.setStyleSheet("background-color: rgb(0, 255, 127);")
            elif sp_tpl[6].strip() == '2':
                self.lbl_mvb_link_2.setText('MVB中断')
                self.lbl_mvb_link_2.setStyleSheet("background-color: rgb(255, 0, 0);")

            if sp_tpl[4].strip() == '1':
                self.lbl_ato_radio_2.setText('电台正常')
                self.lbl_ato_radio_2.setStyleSheet("background-color: rgb(0, 255, 127);")
            elif sp_tpl[4].strip() == '0':
                self.lbl_ato_radio_2.setText('电台异常')
                self.lbl_ato_radio_2.setStyleSheet("background-color: rgb(255, 0, 0);")

            if sp_tpl[5].strip() == '1':
                self.lbl_ato_session_2.setText('无线中断')
                self.lbl_ato_session_2.setStyleSheet("background-color: rgb(255, 0, 0);")
            elif sp_tpl[5].strip() == '2':
                self.lbl_ato_session_2.setText('正在呼叫')
                self.lbl_ato_session_2.setStyleSheet("background-color: rgb(170, 170, 255);")
            elif sp_tpl[5].strip() == '3':
                self.lbl_ato_session_2.setText('无线连接')
                self.lbl_ato_session_2.setStyleSheet("background-color: rgb(0, 255, 127);")

            if sp_tpl[0].strip() == '1':
                self.lbl_ato_ctrl_stat_2.setText('计划有效')
            else:
                if sp_tpl[7].strip() == '1':
                    self.lbl_ato_ctrl_stat_2.setText('正常策略')
                elif sp_tpl[7].strip() == '2':
                    self.lbl_ato_ctrl_stat_2.setText('快行策略')
                elif sp_tpl[7].strip() == '3':
                    self.lbl_ato_ctrl_stat_2.setText('慢行策略')

    # 显示MVB数据
    def realtime_mvb_show(self, ato2tcms_ctrl=list, ato2tcms_stat=list, tcms2ato_stat=list):
        # ATO2TCMS 控制信息
        try:
            if ato2tcms_ctrl != []:
                self.led_ctrl_hrt.setText(str(int(ato2tcms_ctrl[0], 16)))  # 控制命令心跳
                if ato2tcms_ctrl[1] == 'AA':
                    self.led_ctrl_atovalid.setText('有效')  # ATO有效
                elif ato2tcms_ctrl[1] == '00':
                    self.led_ctrl_atovalid.setText('无效')
                else:
                    self.led_ctrl_atovalid.setText('异常值%s' % ato2tcms_ctrl[1])

                # 牵引制动状态
                if ato2tcms_ctrl[2] == 'AA':
                    self.led_ctrl_tbstat.setText('牵引')
                elif ato2tcms_ctrl[2] == '55':
                    self.led_ctrl_tbstat.setText('制动')
                elif ato2tcms_ctrl[2] == 'A5':
                    self.led_ctrl_tbstat.setText('惰行')
                elif ato2tcms_ctrl[2] == '00':
                    self.led_ctrl_tbstat.setText('无命令')
                else:
                    self.led_ctrl_tbstat.setText('异常值%s' % ato2tcms_ctrl[2])

                # 牵引控制量
                self.led_ctrl_tract.setText(str(int(ato2tcms_ctrl[3], 16)))
                # 制动控制量
                self.led_ctrl_brake.setText(str(int(ato2tcms_ctrl[4], 16)))
                # 保持制动施加
                if ato2tcms_ctrl[5] == 'AA':
                    self.led_ctrl_keepbrake.setText('施加')
                elif ato2tcms_ctrl[5] == '00':
                    self.led_ctrl_keepbrake.setText('无效')
                else:
                    self.led_ctrl_keepbrake.setText('异常值%s' % ato2tcms_ctrl[5])
                # 开左门/右门
                if ato2tcms_ctrl[6][0] == 'C':
                    self.led_ctrl_ldoor.setText('有效')
                elif ato2tcms_ctrl[6][0] == '0':
                    self.led_ctrl_ldoor.setText('无动作')
                else:
                    self.led_ctrl_ldoor.setText('异常%s' % ato2tcms_ctrl[6][0])
                if ato2tcms_ctrl[6][1] == 'C':
                    self.led_ctrl_rdoor.setText('有效')
                elif ato2tcms_ctrl[6][1] == '0':
                    self.led_ctrl_rdoor.setText('无动作')
                else:
                    self.led_ctrl_rdoor.setText('异常%s' % ato2tcms_ctrl[6][1])
                # 恒速命令
                if ato2tcms_ctrl[7] == 'AA':
                    self.led_ctrl_costspeed.setText('启动')
                elif ato2tcms_ctrl[7] == '00':
                    self.led_ctrl_costspeed.setText('取消')
                else:
                    self.led_ctrl_costspeed.setText('异常值%s' % ato2tcms_ctrl[7])
                # 恒速目标速度
                self.led_ctrl_aimspeed.setText(str(int(ato2tcms_ctrl[8], 16)))
                # ATO启动灯
                if ato2tcms_ctrl[9] == 'AA':
                    self.led_ctrl_starlamp.setText('亮')
                elif ato2tcms_ctrl[9] == '00':
                    self.led_ctrl_starlamp.setText('灭')
                else:
                    self.led_ctrl_starlamp.setText('异常值%s' % ato2tcms_ctrl[9])
        except Exception as err:
            self.Log(err, __name__, sys._getframe().f_lineno)
            print(ato2tcms_ctrl)
        # ATO2TCMS 状态信息
        try:
            if ato2tcms_stat != []:
                self.led_stat_hrt.setText(str(int(ato2tcms_stat[0], 16)))  # 状态命令心跳
                if ato2tcms_stat[1] == 'AA':
                    self.led_stat_error.setText('无故障')  # ATO故障
                elif ato2tcms_stat[1] == '00':
                    self.led_stat_error.setText('故障')
                else:
                    self.led_stat_error.setText('异常值%s' % ato2tcms_stat[1])  # ATO故障
                self.led_stat_stonemile.setText(str(int(ato2tcms_stat[2], 16)))  # 公里标
                self.led_stat_tunnelin.setText(str(int(ato2tcms_stat[3], 16)))  # 隧道入口
                self.led_stat_tunnellen.setText(str(int(ato2tcms_stat[4], 16)))  # 隧道长度
                self.led_stat_atospeed.setText(str(int(ato2tcms_stat[5], 16)))  # ato速度
        except Exception as err:
            self.Log(err, __name__, sys._getframe().f_lineno)
            print(ato2tcms_stat)
        # TCMS2ATO 状态信息
        try:
            if tcms2ato_stat != []:
                self.led_tcms_hrt.setText(str(int(tcms2ato_stat[0], 16)))  # TCMS状态命令心跳
                # 门模式
                if tcms2ato_stat[1][0] == 'C':
                    self.led_tcms_mm.setText('有效')
                    self.led_tcms_am.setText('无效')
                elif tcms2ato_stat[1][0] == '3':
                    self.led_tcms_am.setText('有效')
                    self.led_tcms_mm.setText('无效')
                elif tcms2ato_stat[1][0] == '0':
                    self.led_tcms_am.setText('无效')
                    self.led_tcms_mm.setText('无效')
                else:
                    self.led_tcms_mm.setText('异常值%s' % tcms2ato_stat[1][0])
                    self.led_tcms_am.setText('异常值%s' % tcms2ato_stat[1][0])
                # ATO启动灯
                if tcms2ato_stat[1][1] == '3':
                    self.led_tcms_startlampfbk.setText('有效')
                elif tcms2ato_stat[1][1] == '0':
                    self.led_tcms_startlampfbk.setText('无效')
                else:
                    self.led_tcms_startlampfbk.setText('异常值%s' % tcms2ato_stat[1][1])

                # ATO有效反馈
                if tcms2ato_stat[2] == 'AA':
                    self.led_tcms_atovalid_fbk.setText('有效')
                elif tcms2ato_stat[2] == '00':
                    self.led_tcms_atovalid_fbk.setText('无效')
                else:
                    self.led_tcms_atovalid_fbk.setText('异常值%s' % tcms2ato_stat[2])

                # 牵引制动反馈
                if tcms2ato_stat[3] == 'AA':
                    self.led_tcms_fbk.setText('牵引')
                elif tcms2ato_stat[3] == '55':
                    self.led_tcms_fbk.setText('制动')
                elif tcms2ato_stat[3] == 'A5':
                    self.led_tcms_fbk.setText('惰行')
                elif tcms2ato_stat[3] == '00':
                    self.led_tcms_fbk.setText('无命令')
                else:
                    self.led_tcms_fbk.setText('异常值%s' % tcms2ato_stat[3])

                # 牵引反馈
                self.led_tcms_tractfbk.setText(str(int(tcms2ato_stat[4], 16)))
                # 制动反馈
                self.led_tcms_bfbk.setText(str(int(tcms2ato_stat[5], 16)))
                # 保持制动施加
                if tcms2ato_stat[6] == 'AA':
                    self.led_tcms_keepbfbk.setText('有效')
                elif tcms2ato_stat[6] == '00':
                    self.led_tcms_keepbfbk.setText('无效')
                else:
                    self.led_tcms_keepbfbk.setText('异常值%s' % tcms2ato_stat[6])
                # 左门反馈，右门反馈
                if tcms2ato_stat[7][0] == 'C':
                    self.led_tcms_ldoorfbk.setText('有效')
                elif tcms2ato_stat[7][0] == '0':
                    self.led_tcms_ldoorfbk.setText('无效')
                else:
                    self.led_tcms_ldoorfbk.setText('异常值%s' % tcms2ato_stat[7][0])
                if tcms2ato_stat[7][1] == 'C':
                    self.led_tcms_rdoorfbk.setText('有效')
                elif tcms2ato_stat[7][1] == '0':
                    self.led_tcms_rdoorfbk.setText('无效')
                else:
                    self.led_tcms_rdoorfbk.setText('异常值%s' % tcms2ato_stat[7][0])
                # 恒速反馈
                if tcms2ato_stat[8] == 'AA':
                    self.led_tcms_costspeedfbk.setText('有效')
                elif tcms2ato_stat[8] == '00':
                    self.led_tcms_costspeedfbk.setText('无效')
                else:
                    self.led_tcms_costspeedfbk.setText('异常值%s' % tcms2ato_stat[8])
                # 车门状态
                if tcms2ato_stat[9] == 'AA':
                    self.led_tcms_doorstat.setText('关')
                elif tcms2ato_stat[9] == '00':
                    self.led_tcms_doorstat.setText('开')
                else:
                    self.led_tcms_doorstat.setText('异常值%s' % tcms2ato_stat[9])
                # 空转打滑
                if tcms2ato_stat[10][0] == 'A':
                    self.led_tcms_kz.setText('空转')
                elif tcms2ato_stat[10][0] == '0':
                    self.led_tcms_kz.setText('未发生')
                else:
                    self.led_tcms_kz.setText('异常值%s' % tcms2ato_stat[10][0])

                if tcms2ato_stat[10][1] == 'A':
                    self.led_tcms_dh.setText('打滑')
                elif tcms2ato_stat[10][1] == '0':
                    self.led_tcms_dh.setText('未发生')
                else:
                    self.led_tcms_dh.setText('异常值%s' % tcms2ato_stat[10][1])
                # 编组信息
                tmp_units = int(tcms2ato_stat[11], 16)
                if tmp_units == 1:
                    self.led_tcms_nunits.setText('8编组')
                elif tmp_units == 2:
                    self.led_tcms_nunits.setText('8编重连')
                elif tmp_units == 3:
                    self.led_tcms_nunits.setText('16编组')
                elif tmp_units == 4:
                    self.led_tcms_nunits.setText('18编组')
                else:
                    self.led_tcms_nunits.setText('异常值%s' % tcms2ato_stat[11])
                # 车重
                self.led_tcms_weight.setText(str(int(tcms2ato_stat[12], 16)))
                # 动车组允许
                if tcms2ato_stat[13] == 'AA':
                    self.led_tcms_pm.setText('允许')
                elif tcms2ato_stat[13] == '00':
                    self.led_tcms_pm.setText('不允许')
                else:
                    self.led_tcms_pm.setText('异常值%s' % tcms2ato_stat[13])

                # 主断状态
                if tcms2ato_stat[14] == 'AA':
                    self.led_tcms_breakstat.setText('闭合')
                    self.lbl_dcmd.setText('主断闭合')
                    self.lbl_dcmd.setStyleSheet("background-color: rgb(0, 255, 127);")
                elif tcms2ato_stat[14] == '00':
                    self.led_tcms_breakstat.setText('断开')
                    self.lbl_dcmd.setText('主断断开')
                    self.lbl_dcmd.setStyleSheet("background-color: rgb(255, 0, 0);")
                else:
                    self.led_tcms_breakstat.setText('异常值%s' % tcms2ato_stat[14])
                # ATP允许 人工允许
                if tcms2ato_stat[15] == 'C0':
                    self.led_tcms_atpdoorpm.setText('有效')
                    self.led_tcms_mandoorpm.setText('无效')
                elif tcms2ato_stat[15] == '30':
                    self.led_tcms_atpdoorpm.setText('无效')
                    self.led_tcms_mandoorpm.setText('有效')
                elif tcms2ato_stat[15] == '00':
                    self.led_tcms_atpdoorpm.setText('无效')
                    self.led_tcms_mandoorpm.setText('无效')
                else:
                    self.led_tcms_atpdoorpm.setText('异常值%s' % tcms2ato_stat[15])
                    self.led_tcms_mandoorpm.setText('异常值%s' % tcms2ato_stat[15])
                # 不允许状态字
                str_tcms = ''
                str_raw = ['未定义', '至少有一个车辆空气制动不可用|', 'CCU存在限速保护|', 'CCU自动施加常用制动|',
                           '车辆施加紧急制动EB或紧急制动UB|', '保持制动被隔离|',
                           'CCU判断与ATO通信故障(CCU监测到ATO生命信号32个周期(2s)不变化)|', '预留|']
                if tcms2ato_stat[16] == '00':
                    self.led_tcms_pmt_state.setText('正常')
                else:
                    val_field = int(tcms2ato_stat[16], 16)
                    for cnt in range(7, -1, -1):
                        if val_field & (1 << cnt) != 0:
                            str_tcms = str_tcms + str_raw[cnt]
                    self.led_tcms_pmt_state.setText('异常原因:%s' % str_tcms)
        except Exception as err:
            self.Log(err, __name__, sys._getframe().f_lineno)
            print(tcms2ato_stat)

    # 右侧边栏显示
    def realtime_table_show(self, cycle_num=str, cycle_time=str, sc_ctrl=list, stoppoint=list, gfx_flag=int):
        item_value = []
        if sc_ctrl:
            if 1 == int(sc_ctrl[20]):
                str_skip = 'Skip'
            elif 2 == int(sc_ctrl[20]):
                str_skip = 'No'
            else:
                str_skip = 'None'
            if 1 == int(sc_ctrl[21]):
                str_task = 'Task'
            elif 2 == int(sc_ctrl[21]):
                str_task = 'No'
            else:
                str_task = 'None'
            # 装填vato,cmdv,atpcmdv
            item_value.append(str(int(sc_ctrl[1])))  # 当前速度使用int的原因是只有整数精度，不多显示
            item_value.append(str(int(sc_ctrl[2])))  # ATO命令
            item_value.append(str(int(sc_ctrl[3])))  # ATP命令
            item_value.append(str(int(sc_ctrl[4])))  # ATP 允许速速度

            item_value.append(str(int(sc_ctrl[5])))  # 估计级位
            item_value.append(str(int(sc_ctrl[6])))  # 输出级位
            item_value.append(str(int(sc_ctrl[17])))  # 状态机
            item_value.append(str(int(sc_ctrl[0])))  # 当前位置
            item_value.append(str(int(sc_ctrl[11])))  # 目标速度
            item_value.append(str(int(sc_ctrl[12])))  # 目标位置
            item_value.append(str(int(sc_ctrl[13])))  # MA终点
            item_value.append(str(int(sc_ctrl[15])))  # ATO停车点
            item_value.append(str(int(sc_ctrl[16])))  # 停车误差
            for idx3, value in enumerate(item_value):
                self.tableWidget.setItem(idx3, 1, QtWidgets.QTableWidgetItem(value))
            # 除去中间3个，排在第15、16
            self.tableWidget.setItem(16, 1, QtWidgets.QTableWidgetItem(str_skip))
            self.tableWidget.setItem(17, 1, QtWidgets.QTableWidgetItem(str_task))
            item_value.append(str_skip)
            item_value.append(str_task)
        # 停车点统计显示
        if stoppoint != []:
            self.tableWidget.setItem(13, 1, QtWidgets.QTableWidgetItem(str(int(stoppoint[0]))))
            self.tableWidget.setItem(14, 1, QtWidgets.QTableWidgetItem(str(int(stoppoint[1]))))
            self.tableWidget.setItem(15, 1, QtWidgets.QTableWidgetItem(str(int(stoppoint[2]))))

        self.label_2.setText(cycle_time)
        if cycle_num != '':
            self.spinBox.setValue(int(cycle_num))

        if gfx_flag == 1:
            self.lbl_atpdcmd.setText('过分相')
            self.lbl_atpdcmd.setStyleSheet("background-color: rgb(255, 0, 0);")
        else:
            self.lbl_atpdcmd.setText('非过分相')
            self.lbl_atpdcmd.setStyleSheet("background-color: rgb(0, 255, 127);")

    # 更新FSM信息相关
    def realtime_fsm_show(self, fsm_list=list):
        temp = fsm_list[:]
        # 如果解析出来
        if temp != []:
            # ATO模式
            if temp[1] == '1':
                self.lbl_mode.setText('AOS模式')
                self.lbl_mode.setStyleSheet("background-color: rgb(180, 180, 180);")
            elif temp[1] == '2':
                self.lbl_mode.setText('AOR模式')
                self.lbl_mode.setStyleSheet("background-color: rgb(255, 255, 0);")
            elif temp[1] == '3':
                self.lbl_mode.setText('AOM模式')
                self.lbl_mode.setStyleSheet("background-color: rgb(255, 255, 255);")
            else:
                self.lbl_mode.setText('ATO模式')
                self.lbl_mode.setStyleSheet("background-color: rgb(170, 170, 255);")

            # 硬允许
            if temp[2] == '1':
                self.lbl_hpm.setStyleSheet("background-color: rgb(0, 255, 127);")
            else:
                self.lbl_hpm.setStyleSheet("background-color: rgb(255, 0, 0);")

            # 软允许
            if temp[3] == '1':
                self.lbl_pm.setStyleSheet("background-color: rgb(0, 255, 127);")
            else:
                self.lbl_pm.setStyleSheet("background-color: rgb(255, 0, 0);")

            # 动车组允许
            if temp[4] == '1':
                self.lbl_carpm.setStyleSheet("background-color: rgb(0, 255, 127);")
            else:
                self.lbl_carpm.setStyleSheet("background-color: rgb(255, 0, 0);")

            # 自检状态
            if temp[5] == '1':
                self.lbl_check.setStyleSheet("background-color: rgb(0, 255, 127);")
            else:
                self.lbl_check.setStyleSheet("background-color: rgb(255, 0, 0);")

            # 发车指示灯
            if temp[6] == '0':
                self.lbl_lamp.setText('发车灯灭')
            elif temp[6] == '1':
                self.lbl_lamp.setText('发车灯闪')
            elif temp[6] == '2':
                self.lbl_lamp.setText('发车灯亮')

            # 车长
            self.lbl_trainlen.setText('车长' + str(int(temp[9]) / 100) + 'm')

            # 门状态
            if temp[10] == '55':
                self.lbl_doorstatus.setText('门开')
            elif temp[10] == 'AA':
                self.lbl_doorstatus.setText('门关')

            # 低频
            if temp[11] == '0':
                self.lbl_freq.setText('H码')
                self.lbl_freq.setStyleSheet("background-color: rgb(255, 0, 0);")
            elif temp[11] == '2':
                self.lbl_freq.setText('HU码')
                self.lbl_freq.setStyleSheet("background-color: rgb(255, 215, 15);")
            elif temp[11] == '10':
                self.lbl_freq.setText('HB码')
                self.lbl_freq.setStyleSheet("background-color: rgb(163, 22, 43);")
            elif temp[11] == '2A':
                self.lbl_freq.setText('L4码')
                self.lbl_freq.setStyleSheet("background-color: rgb(0, 255, 0);")
            elif temp[11] == '2B':
                self.lbl_freq.setText('L5码')
                self.lbl_freq.setStyleSheet("background-color: rgb(0, 255, 0);")
            elif temp[11] == '25':
                self.lbl_freq.setText('U2S码')
                self.lbl_freq.setStyleSheet("background-color: rgb(255, 255, 0);")
            elif temp[11] == '23':
                self.lbl_freq.setText('UUS码')
                self.lbl_freq.setStyleSheet("background-color: rgb(255, 255, 0);")
            elif temp[11] == '22':
                self.lbl_freq.setText('UU码')
                self.lbl_freq.setStyleSheet("background-color: rgb(255, 255, 0);")
            elif temp[11] == '21':
                self.lbl_freq.setText('U码')
                self.lbl_freq.setStyleSheet("background-color: rgb(255, 255, 0);")
            elif temp[11] == '24':
                self.lbl_freq.setText('U2码')
                self.lbl_freq.setStyleSheet("background-color: rgb(255, 255, 0);")
            elif temp[11] == '26':
                self.lbl_freq.setText('LU码')
                self.lbl_freq.setStyleSheet("background-color: rgb(205, 255, 25);")
            elif temp[11] == '28':
                self.lbl_freq.setText('L2码')
                self.lbl_freq.setStyleSheet("background-color: rgb(0, 255, 0);")
            elif temp[11] == '27':
                self.lbl_freq.setText('L码')
                self.lbl_freq.setStyleSheet("background-color: rgb(0, 255, 0);")
            elif temp[11] == '29':
                self.lbl_freq.setText('L3码')
                self.lbl_freq.setStyleSheet("background-color: rgb(0, 255, 0);")
            # 站台
            if temp[13] == '1':
                self.lbl_stn.setText('站内')
            else:
                self.lbl_stn.setText('站外')

    # 实时操作时更新曲线选择
    def realtimeLineChoose(self):
        global load_flag
        linelist = [0, 0, 0, 0, 0]
        if load_flag == 0:
            if self.CBvato.isChecked():
                linelist[0] = 1
            else:
                linelist[0] = 0
            if self.CBcmdv.isChecked():
                linelist[1] = 1
            else:
                linelist[1] = 0
            if self.CBatpcmdv.isChecked():
                linelist[2] = 1
            else:
                linelist[2] = 0
            if self.CBatppmtv.isChecked():
                linelist[3] = 1
            else:
                linelist[3] = 0
            if self.CBlevel.isChecked():
                linelist[4] = 1
            else:
                linelist[4] = 0
        else:
            pass
        self.sp_real.updatePaintSet(linelist)

    # 显示重置信息
    def reatimelbl_defaultshow(self):
        self.lbl_dcmd.setStyleSheet("background-color: rgb(170, 170, 255);")
        self.lbl_atpdcmd.setStyleSheet("background-color: rgb(170, 170, 255);")
        self.lbl_freq.setStyleSheet("background-color: rgb(170, 170, 255);")
        self.lbl_stn.setStyleSheet("background-color: rgb(170, 170, 255);")
        self.lbl_check.setStyleSheet("background-color: rgb(170, 170, 255);")
        self.lbl_hpm.setStyleSheet("background-color: rgb(170, 170, 255);")
        self.lbl_pm.setStyleSheet("background-color: rgb(170, 170, 255);")
        self.lbl_trainlen.setStyleSheet("background-color: rgb(170, 170, 255);")
        self.lbl_carpm.setStyleSheet("background-color: rgb(170, 170, 255);")
        self.lbl_mode.setStyleSheet("background-color: rgb(170, 170, 255);")

    # 设置计划表格格式
    def realtime_plan_table_format(self):
        self.tableWidgetPlan.verticalHeader().setVisible(False)
        for i in range(8):
            self.tableWidgetPlan.resizeColumnToContents(i)

    # 显示BTM表格
    def realtime_btm_show(self, ret_btm=tuple):
        time = ret_btm[0]
        sp7_show = ret_btm[1]
        mile_stone = ret_btm[2]
        if sp7_show:
            self.real_btm_list.append(sp7_show)
            self.tableATPBTM.setColumnCount(4)
            self.tableATPBTM.setRowCount(len(self.real_btm_list))
            # 获取附加索引
            row_btm_idx = len(self.real_btm_list)-1
            if time:
                d_t = time.split(" ")[1]  # 取时间
            else:
                d_t = ''
            item_dt = QtWidgets.QTableWidgetItem(d_t)
            item_balise_bum = QtWidgets.QTableWidgetItem(self.real_btm_list[row_btm_idx][0])
            item_adjpos = QtWidgets.QTableWidgetItem(self.real_btm_list[row_btm_idx][2] + 'cm')

            item_dt.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            item_balise_bum.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            item_adjpos.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            # 刷公里标
            if '4294967295' != mile_stone.strip() and mile_stone:
                item_milestone = QtWidgets.QTableWidgetItem('K' + str(int(int(mile_stone) / 1000)) + '+' +
                                                            str(int(mile_stone) % 1000))
            else:
                item_milestone = QtWidgets.QTableWidgetItem('未知')
            # 虽然目前有SP2必有SP7但不能保证，所有还是单独条件
            if self.real_btm_list[row_btm_idx][3].strip() == '13':
                item_milestone.setForeground(QtGui.QBrush(QtGui.QColor(225, 0, 0)))
            # 所有都居中，但只SP7刷红
            item_milestone.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            self.tableATPBTM.setItem(row_btm_idx, 3, item_milestone)
            # JD正常刷颜色
            if self.real_btm_list[row_btm_idx][3].strip() == '13':
                item_dt.setForeground(QtGui.QBrush(QtGui.QColor(225, 0, 0)))
                item_balise_bum.setForeground(QtGui.QBrush(QtGui.QColor(225, 0, 0)))
                item_adjpos.setForeground(QtGui.QBrush(QtGui.QColor(225, 0, 0)))

            self.tableATPBTM.setItem(row_btm_idx, 0, item_dt)
            self.tableATPBTM.setItem(row_btm_idx, 1, item_balise_bum)
            self.tableATPBTM.setItem(row_btm_idx, 2, item_adjpos)

    # 显示IO表格
    def realtime_io_show(self, ret_io=tuple):
        if ret_io:
            cycle_num = ret_io[0]
            time = ret_io[1]
            io_in_real = ret_io[2]
            # 按钮采集信号内容
            if io_in_real:
                self.real_io_in_list.append([QtWidgets.QTableWidgetItem(time.split(" ")[1]), \
                                             QtWidgets.QTableWidgetItem(str(cycle_num)), \
                                             QtWidgets.QTableWidgetItem(io_in_real[0]), \
                                             QtWidgets.QTableWidgetItem(io_in_real[1])])
                # 设置大小
                self.tb_ato_IN.setRowCount(len(self.real_io_in_list))
                self.tb_ato_IN.setColumnCount(4)
                # 填充
                row_in_idx = len(self.real_io_in_list) - 1
                for j in range(len(self.real_io_in_list[row_in_idx])):
                    self.real_io_in_list[row_in_idx][j].setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                    self.tb_ato_IN.setItem(row_in_idx, j, self.real_io_in_list[row_in_idx][j])
            # IO输出信号
            io_out_real = ret_io[3]
            if io_out_real:
                for it in io_in_real:
                    if it != '':
                        self.real_io_out_list.append([QtWidgets.QTableWidgetItem(time.split(" ")[1]),\
                                                      QtWidgets.QTableWidgetItem(str(cycle_num)),\
                                                      QtWidgets.QTableWidgetItem(it)])
                    else:
                        pass
                # 填充
                row_in_idx = len(self.real_io_out_list) - 1
                self.tb_ato_OUT.setRowCount(len(self.real_io_out_list))
                self.tb_ato_OUT.setColumnCount(3)
                # 填充表格
                for m in range(len(self.real_io_out_list[row_in_idx])):
                    self.real_io_out_list[row_in_idx][m].setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                    self.tb_ato_OUT.setItem(row_in_idx, m, self.real_io_out_list[row_in_idx][m])

    # 显示测速测距
    def realtime_sdu_show(self, ret_sdu=tuple):
        if ret_sdu:
            ato_sdu = ret_sdu[0]
            atp_sdu = ret_sdu[1]
            # 检查并计算
            if ato_sdu and atp_sdu:
                # 计算速度和速度误差
                ato_v = abs(int(ato_sdu[0]))
                ato_s = abs(int(ato_sdu[1]))
                self.led_ato_sdu.setText(str(ato_v)+'cm/s')
                ato_v_kilo = int(ato_sdu[0]) * 9 / 250.0
                self.lcd_ato_sdu.display(str(float('%.1f' % ato_v_kilo)))
                # atp速度和公里情况
                atp_v = abs(int(atp_sdu[0]))
                atp_s = abs(int(atp_sdu[1]))
                self.led_atp_sdu.setText(str(atp_v)+'cm/s')
                atp_v_kilo = int(atp_sdu[0]) * 9 / 250.0
                self.lcd_atp_sdu.display(str(float('%.1f' % atp_v_kilo)))
                # 计算测速测距偏差
                self.led_sdu_err.setText(str(abs(ato_v - atp_v))+'cm/s')
                # 判断情况
                if (ato_v - atp_v) < -28: # 若偏低1km/h
                    self.lbl_sdu_judge.setText("ATO速度偏低")
                    self.lbl_sdu_judge.setStyleSheet("background-color: rgb(255, 255, 0);")
                elif(ato_v - atp_v) > 28: # 若偏高1km/h
                    self.lbl_sdu_judge.setText("ATO速度偏高")
                    self.lbl_sdu_judge.setStyleSheet("background-color: rgb(255, 0, 0);")
                else:
                    self.lbl_sdu_judge.setText("速传速度一致")
                    self.lbl_sdu_judge.setStyleSheet("background-color: rgb(170, 170, 255);")
                # 判断位置
                self.led_ato_s_delta.setText(str(ato_s - self.sdu_info_s[0])+'cm')
                self.led_atp_s_delta.setText(str(atp_s - self.sdu_info_s[1])+'cm')
                self.led_sdu_s_err.setText(str((ato_s - self.sdu_info_s[0]) - (atp_s - self.sdu_info_s[1]))+'cm')

                # 判断情况
                if ((ato_s - self.sdu_info_s[0]) - (atp_s - self.sdu_info_s[1])) < -6:  # 若偏低6cm
                    self.lbl_sdu_s_judge.setText("ATO测距偏低")
                    self.lbl_sdu_s_judge.setStyleSheet("background-color: rgb(255, 255, 0);")
                elif((ato_s - self.sdu_info_s[0]) - (atp_s - self.sdu_info_s[1])) > 6: # 若偏高6cm
                    self.lbl_sdu_s_judge.setText("ATO测距偏高")
                    self.lbl_sdu_s_judge.setStyleSheet("background-color: rgb(255, 0, 0);")
                else:
                    self.lbl_sdu_s_judge.setText("测距速度一致")
                    self.lbl_sdu_s_judge.setStyleSheet("background-color: rgb(170, 170, 255);")
                # 记录刷新
                self.sdu_info_s[0] = ato_s
                self.sdu_info_s[1] = atp_s

    # 显示计划信息
    def realtime_plan_show(self, ret_plan=tuple):
        rp1 = ret_plan[0]
        rp2 = ret_plan[1][0]
        rp2_list = ret_plan[1][1]
        rp3 = ret_plan[2]
        rp4 = ret_plan[3]
        # 运行时间和倒计时
        time_remain = ret_plan[4]
        time_count = ret_plan[5]

        # 临时变量
        rp2_temp_list = []
        # 开始计算
        try:
            if rp1 != ():
                self.led_s_track.setText(str(rp1[0]))

                if rp1[3] == '1':
                    self.lbl_stop_flag.setText('停稳状态')
                    self.lbl_stop_flag.setStyleSheet("background-color: rgb(0, 255, 0)；")
                elif rp1[3] == '0':
                    self.lbl_stop_flag.setText('非停稳')
                    self.lbl_stop_flag.setStyleSheet("background-color: rgb(170, 170, 255);")

            if rp2 != ():
                if rp2[0] == '1':
                    self.lbl_plan_legal.setText('计划合法')
                    self.lbl_plan_legal.setStyleSheet("background-color: rgb(0, 255, 0)")
                elif rp2[0] == '0':
                    self.lbl_plan_legal.setText('计划非法')
                    self.lbl_plan_legal.setStyleSheet("background-color: rgb(255, 0, 0)")

                if rp2[1] == '1':
                    self.lbl_plan_final.setText('终到站')
                elif rp2[1] == '0':
                    self.lbl_plan_final.setText('非终到站')
            # 表格显示内容
            if rp2_list != []:
                for item in rp2_list:
                    # 去除打印中计划更新时间信息，无用
                    rp2_temp_list.append(item[0:1] + item[2:])

                len_plan = len(rp2_temp_list)
                self.tableWidgetPlan.setRowCount(len_plan)

                # 计划索引
                for index, item_plan in enumerate(rp2_temp_list):
                    # 内容索引
                    for idx, name in enumerate(item_plan):
                        self.tableWidgetPlan.resizeColumnsToContents()
                        self.tableWidgetPlan.resizeRowsToContents()
                        item = QtWidgets.QTableWidgetItem(item_plan[idx])
                        item.setTextAlignment(QtCore.Qt.AlignHCenter |QtCore.Qt.AlignVCenter)
                        self.tableWidgetPlan.setItem(index, idx, item)

            if rp3 != ():
                if rp3[0] == '1':
                    self.lbl_plan_timeout.setText('已超时')
                    self.lbl_plan_timeout.setStyleSheet("background-color: rgb(255, 0, 0)")
                elif rp3[0] == '0':
                    self.lbl_plan_timeout.setText('未超时')
                    self.lbl_plan_timeout.setStyleSheet("background-color: rgb(0, 255, 0)")

                if rp3[1] == '1':
                    self.lbl_start_flag.setText('发车状态')
                    self.lbl_start_flag.setStyleSheet("background-color: rgb(255, 170, 255);")
                elif rp3[1] == '2':
                    self.lbl_start_flag.setText('接车状态')
                    self.lbl_start_flag.setStyleSheet("background-color: rgb(85, 255, 255);")
                elif rp3[1] == '0':
                    self.lbl_start_flag.setText('未知状态')
                    self.lbl_start_flag.setStyleSheet("background-color: rgb(170, 170, 255);")

            if rp4 != ():
                if rp4[0] == '1':
                    self.lbl_plan_valid.setText('计划有效')
                    self.lbl_plan_valid.setStyleSheet("background-color: rgb(0, 255, 0)")
                elif rp4[0] == '0':
                    self.lbl_plan_valid.setText('计划无效')
                    self.lbl_plan_valid.setStyleSheet("background-color: rgb(255, 0, 0)")

            self.led_plan_coutdown.setText(str(time_count / 1000) + 's')
            self.led_runtime.setText(str(time_remain / 1000) + 's')

        except Exception as err:
            self.Log(err, str(sys._getframe().f_lineno))

    # 设置实时绘图显示
    def realtime_plot_set(self, interval=int, plot_flag=bool):
        lock = threading.Lock()
        lock.acquire()
        self.realtime_plot_interval = interval  # 默认3s绘图
        self.is_realtime_paint = plot_flag  # 实时绘图否
        lock.release()

    # mvb设置端口窗体
    def show_mvb_port_set(self):
        self.mvbdialog.show()

    # 更新MVB识别端口的
    def update_mvb_port_pat(self):
        RealTimeExtension.pat_ato_ctrl = 'MVB[' + str(int(self.mvbdialog.led_ato_ctrl.text(), 16)) + ']'
        RealTimeExtension.pat_ato_stat = 'MVB[' + str(int(self.mvbdialog.led_ato_stat.text(), 16)) + ']'
        RealTimeExtension.pat_tcms_stat = 'MVB[' + str(int(self.mvbdialog.led_tcms_stat.text(), 16)) + ']'

        FileProcess.pat_ato_ctrl = 'MVB[' + str(int(self.mvbdialog.led_ato_ctrl.text(), 16)) + ']'
        FileProcess.pat_ato_stat = 'MVB[' + str(int(self.mvbdialog.led_ato_stat.text(), 16)) + ']'
        FileProcess.pat_tcms_Stat = 'MVB[' + str(int(self.mvbdialog.led_tcms_stat.text(), 16)) + ']'

        MiniWinCollection.pat_ato_ctrl = int(self.mvbdialog.led_ato_ctrl.text(), 16)
        MiniWinCollection.pat_ato_stat = int(self.mvbdialog.led_ato_stat.text(), 16)
        MiniWinCollection.pat_tcms_Stat = int(self.mvbdialog.led_tcms_stat.text(), 16)

    # MVB解析器
    def show_mvb_parser(self):
        MiniWinCollection.pat_ato_ctrl = int(self.mvbdialog.led_ato_ctrl.text(), 16)
        MiniWinCollection.pat_ato_stat = int(self.mvbdialog.led_ato_stat.text(), 16)
        MiniWinCollection.pat_tcms_stat = int(self.mvbdialog.led_tcms_stat.text(), 16)

        self.mvbparaer.show()

    # utc转换器
    def show_utc_transfer(self):
        self.utctransfer.show()

    # 事件处理函数绘制统计区域的 车辆牵引制动统计图
    def show_statistics_mvb_delay(self):
        global load_flag
        if load_flag == 1:
            self.train_com_delay = Train_Com_MeasureDlg(None, self.log)
            self.Log('Plot statistics info!', __name__, sys._getframe().f_lineno)

            self.train_com_delay.measure_plot()
            self.train_com_delay.show()

    # 更新离线绘图事件标示
    def set_log_event(self):
        self.Log('event happen!', __name__, sys._getframe().f_lineno)
        # 获取事件信息，交由绘图模块完成绘图

    # 默认路径的更新，在文件树结构双击时也更新默认路径
    def update_filetab(self):
        temp = '/'
        filepath = temp.join(self.pathlist[:-1])  # 纪录上一次的文件路径
        mdinx = self.model.index(filepath)
        self.treeView.setRootIndex(mdinx)

    # 事件处理函数，获取文件树结构中双击的文件路径和文件名
    def filetab_clicked(self, item_index):
        self.Log("Select from file tab", __name__, sys._getframe().f_lineno)
        if self.model.fileInfo(item_index).isDir():
            pass
        else:
            self.file = self.model.filePath(item_index)  # 带入modelIndex获取model的相关信息
            self.reset_logplot()
            self.Log(self.model.fileName(item_index), __name__, sys._getframe().f_lineno)
            self.Log(self.model.filePath(item_index), __name__, sys._getframe().f_lineno)

    # <待验证> 设置文件目录的格式大小
    def filetab_format(self):
        self.treeView.setColumnWidth(1, 5)
        self.treeView.setColumnWidth(0, 25)

    # 默认路径的更新，用于打开文件时，总打开最近一次的文件路劲
    def update_path_changed(self, path2):
        ret = True
        if len(self.pathlist) == len(path2):
            for idx, value in enumerate(self.pathlist):
                if path2[idx] != value:
                    ret = False
                    break
                else:
                    pass
        else:
            ret = False
        # 是否更新,True相同，False不同
        if ret:
            pass
        else:
            self.pathlist = path2.copy()

    # 事件处理函数，弹窗显示版本信息
    def version_msg(self):
        reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                                                  "版本信息",
                                                  "Software:LogPlot-V" + str(self.ver) + "\n"
                                                                                         "Author   :Baozhengtang\n"
                                                                                         "License  :(C) Copyright 2017-2019, Author Limited.\n"
                                                                                         "Contact :baozhengtang@gmail.com",
                                                  QtWidgets.QMessageBox.Yes)

    # 记录文件处理核心函数，生成周期字典和绘图值列表
    def log_process(self):
        global cursor_in_flag
        cursor_in_flag = 0
        isok = 2  # 0=ato控车，1=没有控车,2=没有周期
        isdone = 0
        self.actionView.trigger()
        # 读取文件
        # 创建文件读取对象
        self.log = FileProcess.FileProcess()  # 类的构造函数，函数中给出属性
        # 绑定信号量
        self.log.bar_show_signal.connect(self.progressBar.setValue)
        self.log.end_result_signal.connect(self.log_process_result)
        # 读取文件
        self.log.readkeyword(self.file)
        self.Log('Preprocess file path!', __name__, sys._getframe().f_lineno)
        self.log.start()  # 启动记录读取线程,run函数不能有返回值
        self.Log('Begin log read thread!', __name__, sys._getframe().f_lineno)
        self.show_message('文件加载中...')

    # 文件处理线程执行完响应方法
    def log_process_result(self):
        self.Log('End log read thread!', __name__, sys._getframe().f_lineno)
        # 处理返回结果
        if self.log.get_time_use():
            [t1, t2, isok] = self.log.get_time_use()
            self.show_message("Info:预处理耗时:" + str(t1) + 's')
            # 记录中模式有AOR或AOS
            if isok == 0:
                self.show_message("Info:文本计算耗时:" + str(t2) + 's')
                max_c = int(max(self.log.cycle))
                min_c = int(min(self.log.cycle))
                self.tag_latest_pos_idx = 0  # 每次加载文件后置为最小
                self.spinBox.setRange(min_c, max_c)
                self.show_message("Info:曲线周期数:" + str(max_c - min_c) + ' ' + 'from' + str(min_c) + 'to' + str(max_c))
                self.spinBox.setValue(min_c)
                self.label_2.setText(self.log.cycle_dic[min_c].time)  # 显示起始周期
            elif isok == 1:
                self.show_message("Info:文本计算耗时:" + str(t2) + 's')
                self.show_message("Info:ATO没有控车！")
                max_c = int(max(self.log.cycle_dic.keys()))
                min_c = int(min(self.log.cycle_dic.keys()))
                self.tag_latest_pos_idx = 0  # 每次加载文件后置为最小
                self.spinBox.setRange(min_c, max_c)
                self.show_message("Info:曲线周期数:" + str(max_c - min_c) + ' ' + 'from' + str(min_c) + 'to' + str(max_c))
                self.spinBox.setValue(min_c)
                self.label_2.setText(self.log.cycle_dic[min_c].time)  # 显示起始周期
            elif isok == 2:
                self.show_message("Info:记录中没有周期！")
            else:
                pass
        else:
            self.Log('Err Can not get time use', __name__, sys._getframe().f_lineno)
        # 后续弹窗提示
        self.after_log_process(isok)
        return isok

    # 文件加载后处理方法
    def after_log_process(self, is_ato_control):
        global load_flag
        self.Log("End all file process", __name__, sys._getframe().f_lineno)
        try:
            if is_ato_control == 0:
                load_flag = 1  # 记录加载且ATO控车
                self.actionView.trigger()  # 目前无效果，待完善，目的 用于加载后重置坐标轴
                self.CBvato.setChecked(True)
                self.show_message('界面准备中...')
                self.win_init_log_processed()  # 记录加载成功且有控车时，初始化显示一些内容
                self.Log('Set View mode and choose Vato', __name__, sys._getframe().f_lineno)
            elif is_ato_control == 1:
                load_flag = 2  # 记录加载但是ATO没有控车
                reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                                                          "无曲线",
                                                          "注意：记录中ATO没有控车！ATO处于非AOM和AOR模式！",
                                                          QtWidgets.QMessageBox.Yes)
            elif is_ato_control == 2:
                load_flag = 0  # 记录加载但是没有检测到周期
            else:
                reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                                                          "待处理",
                                                          "注意：记录中包含ATO重新上下电过程，列车绝对位置重叠"
                                                          "需手动分解记录！\nATO记录启机行号:Line：" + str(is_ato_control),
                                                          QtWidgets.QMessageBox.Yes)

        except Exception as err:
            self.textEdit.setPlainText(' Error Line ' + str(err.start) + ':' + err.reason + '\n')
            self.textEdit.append('Process file failure! \nPlease Predeal the file!')

    # 用于一些界面加载记录初始化后显示的内容,如数据包一次显示
    def win_init_log_processed(self):
        global load_flag
        # 初始化列车数据界面，如果后面更新再有动态光标触发更新，更新后保持
        sp5_tpl = ()
        sp5_snipper = 0
        sp7_cnt = 0
        bar = 95
        cnt = 0
        bar_cnt = int(len(self.log.cycle_dic.keys()) / 5)  # 从90%开始，界面准备占比10%
        try:
            # ATP 右侧标签显示相关
            self.Log("Begin init log show", __name__, sys._getframe().f_lineno)
            # 初始化表格
            self.tableATPBTM.clear()
            self.tableATPBTM.setHorizontalHeaderLabels(['时间', '应答器编号', '位置矫正值', '公里标'])
            self.tableATPBTM.setColumnWidth(0, 60)
            self.tableATPBTM.setColumnWidth(1, 80)
            self.tableATPBTM.setColumnWidth(2, 70)
            self.tableATPBTM.setColumnWidth(3, 70)
            self.tableATPBTM.resizeRowsToContents()
            self.tableATPBTM.resizeColumnsToContents()
            self.tableATPBTM.verticalHeader().setVisible(True)
            self.BTM_cycle = []  # 首先初始化列表
            # BTM TABLE 计数
            sp7_table_row_cnt = 1
            for c in self.log.cycle_dic.keys():
                if 7 in self.log.cycle_dic[c].cycle_sp_dict.keys():
                    sp7_table_row_cnt = sp7_table_row_cnt + 1
                    self.BTM_cycle.append(c)
            self.tableATPBTM.setColumnCount(4)
            self.tableATPBTM.setRowCount(sp7_table_row_cnt)
            self.Log("Begin search log key info", __name__, sys._getframe().f_lineno)
            # 对于信息5,7包，必须搜索所有周期而非AOR.AOM周期
            for c in self.log.cycle_dic.keys():
                # 计算进度条
                cnt = cnt + 1
                if int(cnt % bar_cnt) == 0:
                    bar = bar + 1
                    self.progressBar.setValue(bar)
                else:
                    pass
                if 5 in self.log.cycle_dic[c].cycle_sp_dict.keys():
                    sp5_tpl = self.log.cycle_dic[c].cycle_sp_dict[5]
                    self.set_atp_info_win(sp5_tpl, 5)
                    sp5_snipper = 1
                # 加载应答器信息
                if 7 in self.log.cycle_dic[c].cycle_sp_dict.keys():
                    c_show_sp7 = self.log.cycle_dic[c]
                    d_t = c_show_sp7.time.split(" ")[1]  # 取时间
                    item_dt = QtWidgets.QTableWidgetItem(d_t)
                    item_balise_bum = QtWidgets.QTableWidgetItem(c_show_sp7.cycle_sp_dict[7][0])
                    item_adjpos = QtWidgets.QTableWidgetItem(c_show_sp7.cycle_sp_dict[7][2] + 'cm')

                    item_dt.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                    item_balise_bum.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                    item_adjpos.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

                    # 获取公里标
                    if 2 in self.log.cycle_dic[c].cycle_sp_dict.keys():
                        sp2_tpl = self.log.cycle_dic[c].cycle_sp_dict[2]
                        if '4294967295' != sp2_tpl[23].strip():
                            item_milestone = QtWidgets.QTableWidgetItem('K' + str(int(int(sp2_tpl[23]) / 1000)) + '+' +
                                                                        str(int(sp2_tpl[23]) % 1000))
                        else:
                            item_milestone = QtWidgets.QTableWidgetItem('未知')
                        # 虽然目前有SP2必有SP7但不能保证，所有还是单独条件
                        if c_show_sp7.cycle_sp_dict[7][3].strip() == '13':
                            item_milestone.setForeground(QtGui.QBrush(QtGui.QColor(225, 0, 0)))
                        # 所有都居中，但只SP7刷红
                        item_milestone.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                        self.tableATPBTM.setItem(sp7_cnt, 3, item_milestone)
                    # JD正常刷颜色
                    if c_show_sp7.cycle_sp_dict[7][3].strip() == '13':
                        item_dt.setForeground(QtGui.QBrush(QtGui.QColor(225, 0, 0)))
                        item_balise_bum.setForeground(QtGui.QBrush(QtGui.QColor(225, 0, 0)))
                        item_adjpos.setForeground(QtGui.QBrush(QtGui.QColor(225, 0, 0)))

                    self.tableATPBTM.setItem(sp7_cnt, 0, item_dt)
                    self.tableATPBTM.setItem(sp7_cnt, 1, item_balise_bum)
                    self.tableATPBTM.setItem(sp7_cnt, 2, item_adjpos)
                    sp7_cnt = sp7_cnt + 1
            # 显示IO信息
            self.Log("Begin search IO info", __name__, sys._getframe().f_lineno)
            self.set_io_page_content()
            # 文本显示
            if sp5_snipper == 0:
                self.show_message("Info: N0 SP5 in log,no train data")
            # 事件发生相关
            if load_flag == 1:
                if self.actionJD.isChecked():
                    pass
                else:
                    self.actionJD.trigger()
                # 如果没选中 trigger一下
                if self.actionBTM.isChecked():
                    pass
                else:
                    self.actionBTM.trigger()
                # 更新
                self.update_event_point()

            else:
                pass
        except Exception as err:
            self.Log(err, __name__, sys._getframe().f_lineno)

    # 界面初始化后，加载显示IO信息，参考应答器显示
    def set_io_page_content(self):
        # 搜索IO信息
        self.tb_ato_IN.clear()
        self.tb_ato_IN.setHorizontalHeaderLabels(['时间', '周期', '采集信号', '取值'])
        self.tb_ato_OUT.clear()
        self.tb_ato_OUT.setHorizontalHeaderLabels(['时间', '周期', '输出信号'])
        cnt_in = 0
        cnt_out = 0
        item_in = []
        item_out = []
        try:
            for c in self.log.cycle_dic.keys():
                # io信息
                if self.log.cycle_dic[c].io_in != ():
                    # 填充表格
                    c_show = self.log.cycle_dic[c]
                    # 添加每行内容
                    item_in.append([QtWidgets.QTableWidgetItem(c_show.time.split(" ")[1]), \
                                    QtWidgets.QTableWidgetItem(str(c_show.cycle_num)), \
                                    QtWidgets.QTableWidgetItem(c_show.io_in[0]), \
                                    QtWidgets.QTableWidgetItem(c_show.io_in[1])])
                    # 计算行数
                    cnt_in = cnt_in + 1
                elif self.log.cycle_dic[c].io_out:
                    # 填充表格
                    c_show = self.log.cycle_dic[c]
                    for it in c_show.io_out:
                        if it != '':
                            # 添加每行内容
                            item_out.append([QtWidgets.QTableWidgetItem(c_show.time.split(" ")[1]), \
                                             QtWidgets.QTableWidgetItem(str(c_show.cycle_num)), \
                                             QtWidgets.QTableWidgetItem(it)])
                            cnt_out = cnt_out + 1
                else:
                    pass
        except Exception as err:
            self.Log(err, __name__, sys._getframe().f_lineno)
            print("cnt_in %d  cnt_out %d" % (cnt_in, cnt_out))
        # 设置大小
        self.tb_ato_IN.setRowCount(cnt_in)
        self.tb_ato_IN.setColumnCount(4)
        self.tb_ato_OUT.setRowCount(cnt_out)
        self.tb_ato_OUT.setColumnCount(3)
        # 填充
        for i in range(len(item_in)):
            for j in range(len(item_in[i])):
                item_in[i][j].setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                self.tb_ato_IN.setItem(i, j, item_in[i][j])
        for m in range(len(item_out)):
            for n in range(len(item_out[m])):
                item_out[m][n].setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                self.tb_ato_OUT.setItem(m, n, item_out[m][n])

    # 事件处理函数，计数器数值变化触发事件，绑定光标和内容更新
    def spin_value_changed(self):
        global cursor_in_flag
        global curve_flag
        xy_lim = []
        track_flag = self.sp.get_track_status()  # 获取之前光标的锁定状态

        # 光标离开图像
        if cursor_in_flag == 2:
            cur_cycle = self.spinBox.value()  # 获取当前周期值

            if cur_cycle in self.log.cycle_dic.keys():
                c = self.log.cycle_dic[cur_cycle]  # 查询周期字典
                # 该周期没有控制信息，或打印丢失,不发送光标移动信号
                if c.control != ():
                    info = list(c.control)
                    if curve_flag == 0:
                        # 先更新坐标轴范围
                        xy_lim = self.sp.update_cord_with_cursor((int(info[0]), int(info[1])), self.sp.axes1.get_xlim(),
                                                                 self.sp.axes1.get_ylim())
                        # 如果超出范围再更新
                        is_update = xy_lim[2]
                        if is_update == 1:
                            self.sp.axes1.set_xlim(xy_lim[0][0], xy_lim[0][1])
                            self.sp.axes1.set_ylim(xy_lim[1][0], xy_lim[1][1])
                            self.update_up_cure()

                            if track_flag == 0:  # 如果之前是锁定的，更新后依然锁定在最新位置
                                self.sp.set_track_status()

                        # 再更新光标
                        self.c_vato.sim_mouse_move(int(info[0]), int(info[1]))  # 其中前两者位置和速度为移动目标
                    elif curve_flag == 1:
                        # 先更新坐标轴范围
                        xy_lim = self.sp.update_cord_with_cursor((int(cur_cycle), int(info[1])),
                                                                 self.sp.axes1.get_xlim(),
                                                                 self.sp.axes1.get_ylim())
                        # 如果超出范围再更新
                        is_update = xy_lim[2]
                        if is_update == 1:
                            self.sp.axes1.set_xlim(xy_lim[0][0], xy_lim[0][1])
                            self.sp.axes1.set_ylim(xy_lim[1][0], xy_lim[1][1])
                            self.update_up_cure()
                            if track_flag == 0:
                                self.sp.set_track_status()
                        # 再更新光标
                        self.c_vato.sim_mouse_move(int(cur_cycle), int(info[1]))  # 绘制速度周期曲线时查询为周期，速度
                else:
                    # 因为移动光标意味着重发信号，单纯移动光标有歧义，若发送信号有可能造成大量新防护问题，这里暂不修改。
                    self.show_message('Err:光标不更新，该周期控车信息丢失')
            else:
                self.show_message('Err:记录边界或周期丢失！')
        else:
            pass  # 否则 不处理

    # 事件处理函数，启动后进入测量状态
    def ctrl_measure(self):
        global load_flag
        # 加载文件才能测量
        if load_flag == 1:
            self.ctrl_measure_status = 1  # 一旦单击则进入测量开始状态
            self.sp.setCursor(QtCore.Qt.WhatsThisCursor)
            self.Log('start measure!', __name__, sys._getframe().f_lineno)
        else:
            self.show_message("Info:记录未加载，不测量")

    # 事件处理函数，标记单击事件
    def ctrl_measure_clicked(self, event):
        global curve_flag

        # 如果开始测量则进入，则获取终点
        if self.ctrl_measure_status == 2:
            # 下面是当前鼠标坐标
            x, y = event.xdata, event.ydata
            # 速度位置曲线
            if curve_flag == 0:
                self.indx_measure_end = min(np.searchsorted(self.log.s, [x])[0], len(self.log.s) - 1)
            # 周期速度曲线
            if curve_flag == 1:
                self.indx_measure_end = min(np.searchsorted(self.log.cycle, [x])[0], len(self.log.cycle) - 1)
            self.measure = Ctrl_MeasureDlg(None, self.log)
            self.measure.measure_plot(self.indx_measure_start, self.indx_measure_end, curve_flag)
            self.measure.show()

            # 获取终点索引，测量结束
            self.ctrl_measure_status = 3
            self.Log('end measure!', __name__, sys._getframe().f_lineno)
            # 更改图标
            if self.mode == 1:  # 标记模式
                self.sp.setCursor(QtCore.Qt.PointingHandCursor)  # 如果对象直接self.那么在图像上光标就不变，面向对象操作
            elif self.mode == 0:  # 浏览模式
                self.sp.setCursor(QtCore.Qt.ArrowCursor)

        # 如果是初始状态，则设置为启动
        if self.ctrl_measure_status == 1:
            self.Log('begin measure!', __name__, sys._getframe().f_lineno)
            # 下面是当前鼠标坐标
            x, y = event.xdata, event.ydata
            # 速度位置曲线
            if curve_flag == 0:
                self.indx_measure_start = min(np.searchsorted(self.log.s, [x])[0], len(self.log.s) - 1)
                self.ctrl_measure_status = 2
            # 周期速度曲线
            if curve_flag == 1:
                self.indx_measure_start = min(np.searchsorted(self.log.cycle, [x])[0], len(self.log.cycle) - 1)
                self.ctrl_measure_status = 2

    # 事件处理函数，更新光标进入图像标志，in=1
    def cursor_in_fig(self, event):
        global cursor_in_flag
        cursor_in_flag = 1
        self.c_vato.move_signal.connect(self.set_table_content)  # 进入图后绑定光标触发
        self.Log('connect ' + 'enter figure', __name__, sys._getframe().f_lineno)

    # 事件处理函数，更新光标进入图像标志,out=2
    def cursor_out_fig(self, event):
        global cursor_in_flag
        cursor_in_flag = 2
        try:
            self.c_vato.move_signal.disconnect(self.set_table_content)  # 离开图后解除光标触发
        except Exception as err:
            self.Log(err, __name__, sys._getframe().f_lineno)
        self.Log('disconnect ' + 'leave figure', __name__, sys._getframe().f_lineno)
        # 测量立即终止，恢复初始态:
        if self.ctrl_measure_status > 0:
            self.ctrl_measure_status = 0
            # 更改图标
            if self.mode == 1:  # 标记模式
                self.sp.setCursor(QtCore.Qt.PointingHandCursor)  # 如果对象直接self.那么在图像上光标就不变，面向对象操作
            elif self.mode == 0:  # 浏览模式
                self.sp.setCursor(QtCore.Qt.ArrowCursor)
            self.Log('exit measure', __name__, sys._getframe().f_lineno)

    # 绘制各种速度位置曲线
    def update_up_cure(self):
        global load_flag
        global curve_flag
        # file is load
        if load_flag == 1:
            x_monitor = self.sp.axes1.get_xlim()
            y_monitor = self.sp.axes1.get_ylim()
            if self.CBvato.isChecked() or self.CBcmdv.isChecked() or self.CBatppmtv.isChecked() \
                    or self.CBatpcmdv.isChecked() or self.CBlevel.isChecked():
                self.clear_axis()
                self.Log("Mode Change recreate the paint", __name__, sys._getframe().f_lineno)
                # 清除光标重新创建
                if self.mode == 1:
                    # 重绘文字
                    self.sp.plot_ctrl_text(self.log, self.tag_latest_pos_idx, self.bubble_status, curve_flag)
                    self.Log("Update ctrl text ", __name__, sys._getframe().f_lineno)
                    if Mywindow.is_cursor_created == 1:
                        Mywindow.is_cursor_created = 0
                        del self.c_vato
                    self.tag_cursor_creat()
                self.Log("Update Curve recreate curve and tag cursor ", __name__, sys._getframe().f_lineno)
                # 处理ATO速度
                if self.CBvato.isChecked():
                    self.sp.plotlog_vs(self.log, self.mode, curve_flag)
                else:
                    self.CBvato.setChecked(False)
                # 处理命令速度
                if self.CBcmdv.isChecked():
                    self.sp.plotlog_vcmdv(self.log, self.mode, curve_flag)
                else:
                    self.CBcmdv.setChecked(False)
                # 处理允许速度
                if self.CBatppmtv.isChecked():
                    self.sp.plotlog_v_atp_pmt_s(self.log, self.mode, curve_flag)
                else:
                    self.CBatppmtv.setChecked(False)
                # 处理顶棚速度
                if self.CBatpcmdv.isChecked():
                    self.sp.plotlog_vceil(self.log, curve_flag)
                else:
                    self.CBatpcmdv.setChecked(False)
                # 处理级位
                if self.CBlevel.isChecked():
                    self.sp.plotlog_level(self.log, curve_flag)
                else:
                    self.CBlevel.setChecked(False)
            elif self.CBacc.isChecked() or self.CBramp.isChecked():
                self.update_down_cure()  # 当没有选择下图时更新上图
                self.sp.plot_cord1(self.log, curve_flag, (0.0, 1.0), (0.0, 1.0))
            else:
                self.clear_axis()
                self.sp.plot_cord1(self.log, curve_flag, (0.0, 1.0), (0.0, 1.0))
            self.sp.plot_cord1(self.log, curve_flag, x_monitor, y_monitor)
            self.sp.draw()
        else:
            pass

    # 绘制加速度和坡度曲线
    def update_down_cure(self):
        global load_flag
        global curve_flag
        if load_flag == 1:
            if self.mode == 0:  # 只有浏览模式才可以
                if self.CBacc.isChecked() or self.CBramp.isChecked():
                    self.clear_axis()
                    # 加速度处理
                    if self.CBacc.isChecked():
                        self.sp.plotlog_sa(self.log, curve_flag)
                    else:
                        self.CBacc.setChecked(False)
                    # 坡度处理
                    if self.CBramp.isChecked():
                        self.sp.plotlog_ramp(self.log, curve_flag)
                    else:
                        self.CBramp.setChecked(False)
                elif self.CBvato.isChecked() or self.CBcmdv.isChecked() or self.CBatppmtv.isChecked() \
                        or self.CBatpcmdv.isChecked() or self.CBlevel.isChecked():
                    self.update_up_cure()  # 当没有选择下图时更新上图
                    self.sp.plot_cord1(self.log, curve_flag, (0.0, 1.0), (0.0, 1.0))
                else:
                    self.clear_axis()
                    self.sp.plot_cord1(self.log, curve_flag, (0.0, 1.0), (0.0, 1.0))
                self.sp.plot_cord2(self.log, curve_flag)  # 绘制坐标系II
                self.sp.draw()
            else:
                pass
        else:
            pass

    # 绘制离线模式下事件选择点
    def update_event_point(self):
        event_dict = {}
        global load_flag
        # 记录显示应答器事件
        if self.actionBTM.isChecked():
            event_dict['BTM'] = 1
        else:
            event_dict['BTM'] = 0
        # 记录显示无线呼叫事件
        if self.actionWL.isChecked():
            event_dict['WL'] = 1
        else:
            event_dict['WL'] = 0
        # 显示JD应答器
        if self.actionJD.isChecked():
            event_dict['JD'] = 1
        else:
            event_dict['JD'] = 0
        # 显示计划数据
        if self.actionPLAN.isChecked():
            event_dict['PLAN'] = 1
        else:
            event_dict['PLAN'] = 0

        # 如果文件加载成功，传递数据字典和选择信息
        if load_flag == 1:
            self.sp.set_event_info_plot(event_dict, self.log.cycle_dic, self.log.s, self.log.cycle)
            self.update_up_cure()

    # 清除图像和轴相关内容，画板清屏
    def clear_axis(self):
        try:
            self.sp.axes1.clear()
            self.sp.ax1_twin.clear()
        except Exception as err:
            self.textEdit.append('Clear all figure!\n')

    # 封装用于在文本框显示字符串
    def show_message(self, s):
        self.textEdit.append(s)

    # <待完成> 用于标注模式下按压操作后级处理
    def on_click(self, event):
        pass
        # if self.mode == 1:
        #     # get the x and y coords, flip y from top to bottom
        #     x, y = event.x, event.y
        #     if event.button == 1:
        #         if event.inaxes is not None:
        #             self.Log('data coords %f %f' % (event.xdata, event.ydata))

    # 模式转换函数，修改全局模式变量和光标
    def mode_change(self):
        global load_flag
        sender = self.sender()
        # 查看信号发送者
        if sender.text() == '标注模式' and self.mode == 0:  # 由浏览模式进入标注模式不重绘范围
            self.mode = 1
            if load_flag == 1 and self.CBvato.isChecked():
                self.Log("Mode Change excute!", __name__, sys._getframe().f_lineno)
                self.update_up_cure()
                self.tag_cursor_creat()  # 只针对速度曲线
        elif sender.text() == '浏览模式' and self.mode == 1:  # 进入浏览模式重绘
            self.mode = 0
            if load_flag == 1:
                self.update_up_cure()
                # 重置坐标轴范围
                self.sp.plot_cord1(self.log, curve_flag, (0.0, 1.0), (0.0, 1.0))
            self.tag_cursor_creat()
        else:
            # 重置坐标轴范围
            if load_flag == 1:
                self.sp.plot_cord1(self.log, curve_flag, (0.0, 1.0), (0.0, 1.0))
        self.sp.draw()
        # 更改图标
        if self.mode == 1:  # 标记模式
            self.sp.setCursor(QtCore.Qt.PointingHandCursor)  # 如果对象直接self.那么在图像上光标就不变，面向对象操作
        elif self.mode == 0:  # 浏览模式
            self.sp.setCursor(QtCore.Qt.ArrowCursor)
        self.statusbar.showMessage(self.file + " " + "当前模式：" + sender.text())

    # 曲线类型转换函数，修改全局模式变量
    def cmd_change(self):
        global curve_flag
        global load_flag
        if load_flag == 1:
            sender = self.sender()
            if sender.text() == '位置速度曲线':
                if curve_flag == 1:
                    curve_flag = 0  # 曲线类型改变，如果有光标则删除，并重置标志
                    if Mywindow.is_cursor_created == 1:
                        del self.c_vato
                        Mywindow.is_cursor_created = 0
                    else:
                        pass
                    self.update_up_cure()
                    self.tag_cursor_creat()  # 根据需要重新创建光标
                else:
                    pass
            if sender.text() == "周期速度曲线":
                if curve_flag == 0:
                    curve_flag = 1  # 曲线类型改变
                    if Mywindow.is_cursor_created == 1:
                        del self.c_vato
                        Mywindow.is_cursor_created = 0
                    else:
                        pass
                    self.update_up_cure()
                    self.tag_cursor_creat()
                else:
                    pass
            # 重置坐标轴范围
            self.sp.plot_cord1(self.log, curve_flag, (0.0, 1.0), (0.0, 1.0))
            self.sp.draw()
            self.statusbar.showMessage(self.file + " " + "曲线类型：" + sender.text())
        else:
            pass

    # 用于模式转换后处理，创建光标绑定和解绑槽函数
    def tag_cursor_creat(self):
        global curve_flag
        # 标注模式
        if self.mode == 1 and 0 == Mywindow.is_cursor_created:
            if curve_flag == 0:
                self.c_vato = SnaptoCursor(self.sp, self.sp.axes1, self.log.s, self.log.v_ato)  # 初始化一个光标
            else:
                self.c_vato = SnaptoCursor(self.sp, self.sp.axes1, self.log.cycle, self.log.v_ato)  # 初始化一个光标
            self.c_vato.reset_cursor_plot()
            self.Log("Link Signal to Tag Cursor", __name__, sys._getframe().f_lineno)
            self.cid1 = self.sp.mpl_connect('motion_notify_event', self.c_vato.mouse_move)
            self.cid2 = self.sp.mpl_connect('figure_enter_event', self.cursor_in_fig)
            self.cid3 = self.sp.mpl_connect('figure_leave_event', self.cursor_out_fig)
            self.c_vato.move_signal.connect(self.set_tableall_content)  # 连接图表更新的槽函数
            self.c_vato.sim_move_singal.connect(self.set_table_content)
            self.c_vato.move_signal.connect(self.set_tree_content)  # 连接信号槽函数
            self.c_vato.sim_move_singal.connect(self.set_tree_content)  # 连接信号槽函数
            self.c_vato.move_signal.connect(self.set_ctrl_bubble_content)
            self.c_vato.sim_move_singal.connect(self.set_ctrl_bubble_content)
            self.c_vato.move_signal.connect(self.set_train_page_content)
            self.c_vato.sim_move_singal.connect(self.set_train_page_content)
            self.c_vato.move_signal.connect(self.set_plan_page_content)
            self.c_vato.sim_move_singal.connect(self.set_plan_page_content)
            self.c_vato.sim_move_singal.connect(self.set_ATP_page_content)
            self.c_vato.move_signal.connect(self.set_ATP_page_content)
            self.c_vato.move_signal.connect(self.set_sdu_info_content)
            self.c_vato.sim_move_singal.connect(self.set_sdu_info_content)
            self.c_vato.move_signal.connect(self.set_ato_status_label)  # 标签
            self.c_vato.sim_move_singal.connect(self.set_ato_status_label)
            Mywindow.is_cursor_created = 1
            self.Log("Mode changed Create tag cursor ", __name__, sys._getframe().f_lineno)
        elif self.mode == 0 and 1 == Mywindow.is_cursor_created:
            self.sp.mpl_disconnect(self.cid1)
            self.sp.mpl_disconnect(self.cid2)
            self.sp.mpl_disconnect(self.cid3)
            self.c_vato.move_signal.disconnect(self.set_tableall_content)
            self.c_vato.sim_move_singal.disconnect(self.set_table_content)
            self.c_vato.move_signal.disconnect(self.set_tree_content)  # 连接信号槽函数
            self.c_vato.sim_move_singal.disconnect(self.set_tree_content)  # 连接信号槽函数
            self.c_vato.move_signal.disconnect(self.set_ctrl_bubble_content)
            self.c_vato.sim_move_singal.disconnect(self.set_ctrl_bubble_content)
            self.c_vato.move_signal.disconnect(self.set_train_page_content)
            self.c_vato.sim_move_singal.disconnect(self.set_train_page_content)
            self.c_vato.move_signal.disconnect(self.set_plan_page_content)
            self.c_vato.sim_move_singal.disconnect(self.set_plan_page_content)
            self.c_vato.move_signal.disconnect(self.set_ATP_page_content)
            self.c_vato.sim_move_singal.disconnect(self.set_ATP_page_content)
            self.c_vato.move_signal.disconnect(self.set_ato_status_label)
            self.c_vato.sim_move_singal.disconnect(self.set_ato_status_label)
            self.c_vato.move_signal.disconnect(self.set_sdu_info_content)  # 标签
            self.c_vato.sim_move_singal.disconnect(self.set_sdu_info_content)
            Mywindow.is_cursor_created = 0
            del self.c_vato
            self.Log("Mode changed clear tag cursor ", __name__, sys._getframe().f_lineno)
        else:
            pass

    # 封装工具栏函数，图形缩放
    def zoom(self):
        self.sp.mpl_toolbar.zoom()
        if self.mode == 1:
            self.sp.setCursor(QtCore.Qt.PointingHandCursor)
        else:
            pass

    # 封装工具栏函数，显示画板初始状态，清除曲线
    def home_show(self):
        global load_flag
        global curve_flag
        self.clear_axis()
        self.reset_all_checkbox()
        self.CBvato.setChecked(True)
        self.reset_text_edit()
        if load_flag == 1:
            self.sp.plot_cord1(self.log, curve_flag, (0.0, 1.0), (0.0, 1.0))
            self.update_up_cure()
        else:
            pass

    # 关闭当前绘图
    def close_figure(self, evt):
        global load_flag
        if load_flag == 1:
            self.textEdit.append('Close Log Plot\n')
            self.clear_axis()
            load_flag = 0
            self.sp.draw()
        else:
            pass

    # 事件处理函数，用于弹窗显示当前索引周期
    def cycle_print(self):
        global load_flag
        self.cyclewin.statusBar.showMessage('')  # 清除上一次显示内容
        idx = self.spinBox.value()
        print_flag = 0  # 是否弹窗打印，0=不弹窗，1=弹窗
        c_num = 0
        self.cyclewin.textEdit.clear()
        if 1 == load_flag or 2 == load_flag:  # 文件已经加载
            # 前提是必须有周期，字典能查到
            if idx in self.log.cycle_dic.keys():
                c_num = self.log.cycle_dic[idx].cycle_num
                for line in self.log.cycle_dic[idx].cycle_all_info:
                    self.cyclewin.textEdit.append(line[:-1])
                # 周期完整性
                if self.log.cycle_dic[idx].cycle_property == 1:
                    self.cyclewin.statusBar.showMessage(str(c_num) + '周期序列完整！')
                elif self.log.cycle_dic[idx].cycle_property == 2:
                    self.cyclewin.statusBar.showMessage(str(c_num) + '周期尾部缺失！')
                else:
                    self.cyclewin.statusBar.showMessage('记录异常！')  # 清除上一次显示内容
                print_flag = 1
            else:
                self.show_message("Info：周期不存在，查询无效")
        else:
            self.show_message("Info：文件未加载，查询无效")
        # 有信息才弹窗
        if print_flag == 1:
            self.cyclewin.setWindowTitle('LogPlot-V' + self.ver + " 周期号 : " + str(c_num))
            self.cyclewin.show()
        else:
            pass

    # 设置主界面表格的格式
    def set_table_format(self):
        item_name = ['ATO当前速度', 'ATO命令速度', 'ATP命令速度', 'ATP允许速度', '估计级位', '输出级位', '控车状态机',  # 0~5
                     '当前位置', '目标速度', '目标位置', 'MA终点', 'ATO停车点', '停车误差',  # 6~11
                     '精确停车点', '参考停车点', 'MA停车点',  # 12~14
                     '通过信息', '办客信息']
        item_unit = ['cm/s', 'cm/s', 'cm/s', 'cm/s', '-', '-', '-',
                     'cm', 'cm/s', 'cm', 'cm', 'cm', 'cm', 'cm', 'cm',
                     'cm', '-', '-']
        # table name
        self.tableWidget.setRowCount(18)
        self.tableWidget.setColumnCount(3)
        self.tableWidget.setHorizontalHeaderLabels(['ATO控制信息', '控车数据', '单位'])
        self.tableWidget.resizeRowsToContents()
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setColumnWidth(1, 170)

        for idx, name in enumerate(item_name):
            i_content_name = QtWidgets.QTableWidgetItem(name)
            i_content_name.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            self.tableWidget.setItem(idx, 0, i_content_name)
        for idx2, unit in enumerate(item_unit):
            i_content_unit = QtWidgets.QTableWidgetItem(unit)
            i_content_unit.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            self.tableWidget.setItem(idx2, 2, i_content_unit)

    # 事件处理函数，设置主界面表格内容
    def set_tableall_content(self, indx):
        item_value = []
        stop_list = list(self.log.cycle_dic[self.log.cycle[indx]].stoppoint)
        # 获取和计算
        if 1 == int(self.log.skip[indx]):
            str_skip = '通过'
        elif 2 == int(self.log.skip[indx]):
            str_skip = '到发'
        else:
            str_skip = '未知'
        if 1 == int(self.log.mtask[indx]):
            str_task = '办客'
        elif 2 == int(self.log.mtask[indx]):
            str_task = '不办客'
        else:
            str_task = '未知'
        # 装填
        item_value.append(str(int(self.log.v_ato[indx])))  # 使用int的原因是只有整数精度，不多显示
        item_value.append(str(int(self.log.cmdv[indx])))
        item_value.append(str(int(self.log.ceilv[indx])))
        item_value.append(str(int(self.log.atp_permit_v[indx])))
        item_value.append(str(int(self.log.real_level[indx])))
        item_value.append(str(int(self.log.level[indx])))
        item_value.append(str(int(self.log.statmachine[indx])))
        item_value.append(str(int(self.log.s[indx])))
        item_value.append(str(int(self.log.v_target[indx])))
        item_value.append(str(int(self.log.targetpos[indx])))
        item_value.append(str(int(self.log.ma[indx])))
        item_value.append(str(int(self.log.stoppos[indx])))
        item_value.append(str(int(self.log.stop_error[indx])))
        if stop_list != []:
            item_value.append(str(int(stop_list[0])))
            item_value.append(str(int(stop_list[1])))
            item_value.append(str(int(stop_list[2])))
        else:
            item_value.append('无')
            item_value.append('无')
            item_value.append('无')
        item_value.append(str_skip)
        item_value.append(str_task)
        for idx3, value in enumerate(item_value):
            i_content = QtWidgets.QTableWidgetItem(value)
            i_content.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.label_2.setText(self.log.cycle_dic[self.log.cycle[indx]].time)
        self.spinBox.setValue(int(self.log.cycle_dic[self.log.cycle[indx]].cycle_num))

    # 事件处理函数，设置表格
    def set_table_content(self, indx):
        item_value = []
        stop_list = list(self.log.cycle_dic[self.log.cycle[indx]].stoppoint)
        # 获取和计算
        if 1 == int(self.log.skip[indx]):
            str_skip = '通过'
        elif 2 == int(self.log.skip[indx]):
            str_skip = '到发'
        else:
            str_skip = '未知'
        if 1 == int(self.log.mtask[indx]):
            str_task = '办客'
        elif 2 == int(self.log.mtask[indx]):
            str_task = '不办客'
        else:
            str_task = '未知'
        # 装填
        item_value.append(str(int(self.log.v_ato[indx])))  # 使用int的原因是只有整数精度，不多显示
        item_value.append(str(int(self.log.cmdv[indx])))
        item_value.append(str(int(self.log.ceilv[indx])))
        item_value.append(str(int(self.log.atp_permit_v[indx])))
        item_value.append(str(int(self.log.real_level[indx])))
        item_value.append(str(int(self.log.level[indx])))
        item_value.append(str(int(self.log.statmachine[indx])))
        item_value.append(str(int(self.log.s[indx])))
        item_value.append(str(int(self.log.v_target[indx])))
        item_value.append(str(int(self.log.targetpos[indx])))
        item_value.append(str(int(self.log.ma[indx])))
        item_value.append(str(int(self.log.stoppos[indx])))
        item_value.append(str(int(self.log.stop_error[indx])))
        if stop_list != []:
            item_value.append(str(int(stop_list[0])))
            item_value.append(str(int(stop_list[1])))
            item_value.append(str(int(stop_list[2])))
        else:
            item_value.append('无')
            item_value.append('无')
            item_value.append('无')
        item_value.append(str_skip)
        item_value.append(str_task)
        for idx3, value in enumerate(item_value):
            i_content = QtWidgets.QTableWidgetItem(value)
            i_content.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            self.tableWidget.setItem(idx3, 1, i_content)
        self.label_2.setText(self.log.cycle_dic[self.log.cycle[indx]].time)

    # 事件处理函数，用于设置气泡格式，目前只设置位置
    def set_ctrl_bubble_format(self):
        sender = self.sender()
        # 清除光标重新创建
        if self.mode == 1:
            if sender.text() == '跟随光标':
                self.bubble_status = 1  # 1 跟随模式，立即更新
                self.sp.plot_ctrl_text(self.log, self.tag_latest_pos_idx, self.bubble_status, curve_flag)
            elif sender.text() == '停靠窗口':
                self.bubble_status = 0  # 0 是停靠，默认右上角，立即更新
                self.sp.plot_ctrl_text(self.log, self.tag_latest_pos_idx, self.bubble_status, curve_flag)
            else:
                pass
        self.sp.draw()

    # 事件处理函数，计算控车数据悬浮气泡窗并显示
    def set_ctrl_bubble_content(self, idx):
        global curve_flag
        # 根据输入类型设置气泡
        self.sp.plot_ctrl_text(self.log, idx, self.bubble_status, curve_flag)
        self.tag_latest_pos_idx = idx

    # 设置树形结构
    def set_tree_fromat(self):
        self.treeWidget.setColumnCount(3)  # 协议字段，数据，单位
        self.treeWidget.setHeaderLabels(['协议数据包', '字段', '取值'])
        self.treeWidget.setColumnWidth(0, 100)
        self.treeWidget.setColumnWidth(1, 125)
        # self.treeWidget.setHeaderLabels(['Procotol', 'Field', 'Value', 'Unit']) # 内容解析未来添加

    # 事件处理函数，设置树形结构和内容
    def set_tree_content(self, idx):
        is_p2o_create = 0
        is_o2p_create = 0
        is_t2o_create = 0
        is_o2t_create = 0
        self.treeWidget.clear()
        # 没有ATP-ATO通信包
        if self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict != {}:
            # 所有通信数据包,考虑通过两层循环来实现
            for k in self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict.keys():
                # P->O 数据包
                if k < 10 or k >= 1000:
                    if is_p2o_create == 0:
                        root1 = QtWidgets.QTreeWidgetItem(self.treeWidget)
                        root1.setText(0, 'ATP -> ATO')
                        is_p2o_create = 1
                    else:
                        pass
                    # 针对SP0
                    if k == 0:
                        item_sp0 = QtWidgets.QTreeWidgetItem()
                        item_sp0.setText(0, 'SP' + str(k))
                        # 未来填充
                        root1.addChild(item_sp0)
                    # 针对SP1
                    elif k == 1:
                        item_sp1 = QtWidgets.QTreeWidgetItem()
                        item_sp1.setText(0, 'SP' + str(k))
                        # 未来填充
                        root1.addChild(item_sp1)
                    # 针对 SP2
                    elif k == 2:
                        item_sp2 = QtWidgets.QTreeWidgetItem()
                        item_sp2.setText(0, 'SP' + str(k))
                        txt2 = ['q_atopermit', 'q_ato_hardpermit', 'q_leftdoorpermit',
                                'q_rightdoorpermit', 'q_door_cmd_dir', 'q_tb', 'v_target', 'd_target', 'm_level',
                                'm_mode', 'o_train_pos', 'v_permitted', 'd_ma', 'm_ms_cmd', 'd_neu_sec',
                                'm_low_frequency', 'q_stopstatus', 'm_atp_stop_error', 'd_station_mid_pos',
                                'd_jz_sig_pos', 'd_cz_sig_pos', 'd_tsm', 'm_cab_state', 'm_position', 'm_tco_state',
                                'm_brake_state']
                        for index2, field in enumerate((self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k])):
                            item_field = QtWidgets.QTreeWidgetItem(item_sp2)  # 以该数据包作为父节点
                            item_field.setText(2, str(int(field)))  # 转换去除空格
                            item_field.setText(1, txt2[index2])
                        root1.addChild(item_sp2)
                    # 针对SP5
                    elif k == 5:
                        item_sp5 = QtWidgets.QTreeWidgetItem()
                        item_sp5.setText(0, 'SP' + str(k))
                        txt5 = ['n_units', 'nid_operational', 'nid_driver', 'btm_antenna_position', 'l_door_dis',
                                'l_sdu_wh_size', 'l_sdu_wh_size', 't_cutoff_traction', 'nid_engine', 'v_ato_permitted']
                        for index5, field in enumerate((self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k])):
                            item_field = QtWidgets.QTreeWidgetItem(item_sp5)  # 以该数据包作为父节点
                            item_field.setText(2, field)  # 转换去除空格
                            item_field.setText(1, txt5[index5])
                        root1.addChild(item_sp5)
                    # 针对SP6
                    elif k == 6:
                        item_sp6 = QtWidgets.QTreeWidgetItem()
                        item_sp6.setText(0, 'SP' + str(k))
                        # 未来填充
                        root1.addChild(item_sp6)
                    elif k == 7:
                        item_sp7 = QtWidgets.QTreeWidgetItem()
                        item_sp7.setText(0, 'SP' + str(k))
                        txt7 = ['nid_bg', 't_middle', 'd_pos_adj', 'nid_xuser', 'q_scale', 'q_platform', 'q_door',
                                'n_d', 'd_stop']
                        for index7, field in enumerate((self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k])):
                            item_field = QtWidgets.QTreeWidgetItem(item_sp7)  # 以该数据包作为父节点
                            item_field.setText(2, field)  # 转换去除空格
                            item_field.setText(1, txt7[index7])
                        root1.addChild(item_sp7)
                    # 针对SP8
                    elif k == 8:
                        item_sp8 = QtWidgets.QTreeWidgetItem()
                        item_sp8.setText(0, 'SP' + str(k))
                        txt8 = ['q_tsrs', 'nid_c', 'nid_tsrs', 'nid_radio_h', 'nid_radio_l', 'q_sleepssion', 'm_type']
                        for index8, field in enumerate((self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k])):
                            item_field = QtWidgets.QTreeWidgetItem(item_sp8)  # 以该数据包作为父节点
                            item_field.setText(2, field)  # 转换去除空格
                            item_field.setText(1, txt8[index8])
                        root1.addChild(item_sp8)
                    # 针对SP9
                    elif k == 9:
                        item_sp9 = QtWidgets.QTreeWidgetItem()
                        item_sp9.setText(0, 'SP' + str(k))
                        # 未来填充
                        root1.addChild(item_sp9)
                    elif k == 1001:
                        item_c2ato_p1 = QtWidgets.QTreeWidgetItem()
                        item_c2ato_p1.setText(0, 'P' + str(k-1000))
                        txt1001 = ['q_atopermit', 'q_leftdoorpermit','q_rightdoorpermit', 'v_target', 'd_target', 'o_accmu',
                                'v_normal',  'v_permitted', 'd_ma', 'm_ms_cmd', 'd_neu_sec','m_low_frequency',
                                'atp_stop_error']
                        for index2, field in enumerate((self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k])):
                            item_field = QtWidgets.QTreeWidgetItem(item_c2ato_p1)  # 以该数据包作为父节点
                            item_field.setText(2, str(int(field)))  # 转换去除空格
                            item_field.setText(1, txt1001[index2])
                        root1.addChild(item_c2ato_p1)
                    root1.setExpanded(True)
                # O->P 数据包
                elif 100 < k < 140:
                    # 定义根节点，用来添加数据包
                    if is_o2p_create == 0:
                        root2 = QtWidgets.QTreeWidgetItem(self.treeWidget)
                        root2.setText(0, 'ATO -> ATP')
                        is_o2p_create = 1
                    else:
                        pass
                    if k == 130:
                        item_sp130 = QtWidgets.QTreeWidgetItem()
                        item_sp130.setText(0, 'SP' + str(k))
                        txt130 = ['m_atoerror', 'm_atomode', 'm_ato_stop_error', 'm_doormode', 'm_doorstatus']
                        for index130, field in enumerate((self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k])):
                            item_field = QtWidgets.QTreeWidgetItem(item_sp130)  # 以该数据包作为父节点
                            item_field.setText(2, str(int(field)))  # 转换去除空格
                            item_field.setText(1, txt130[index130])
                        root2.addChild(item_sp130)
                    elif k == 131:
                        item_sp131 = QtWidgets.QTreeWidgetItem()
                        item_sp131.setText(0, 'SP' + str(k))
                        txt131 = ['plan', 'skip', 'tbs', 'count', 'radio', 'session', 'tcms', 'strategy', 'paddings']
                        for index131, field in enumerate((self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k])):
                            item_field = QtWidgets.QTreeWidgetItem(item_sp131)  # 以该数据包作为父节点
                            item_field.setText(2, str(int(field)))  # 转换去除空格
                            item_field.setText(1, txt131[index131])
                        root2.addChild(item_sp131)
                    elif k == 132:
                        item_sp132 = QtWidgets.QTreeWidgetItem()
                        item_sp132.setText(0, 'SP' + str(k))
                        # 未来填充
                        root2.addChild(item_sp132)
                    elif k == 134:
                        item_sp134 = QtWidgets.QTreeWidgetItem()
                        item_sp134.setText(0, 'SP' + str(k))
                        # 未来填充
                        root2.addChild(item_sp134)
                    root2.setExpanded(True)
                # T->A 数据包
                elif 10 < k < 44 or k > 200:
                    # 定义根节点，用来添加数据包
                    if is_t2o_create == 0:
                        root4 = QtWidgets.QTreeWidgetItem(self.treeWidget)
                        root4.setText(0, 'TSRS-> ATO')
                        is_t2o_create = 1
                    else:
                        pass
                    if k == 41:
                        item_c41 = QtWidgets.QTreeWidgetItem()
                        item_c41.setText(0, 'C' + str(k))
                        # 未来填充
                        root4.addChild(item_c41)
                    elif k == 42:
                        item_c42 = QtWidgets.QTreeWidgetItem()
                        item_c42.setText(0, 'C' + str(k))
                        # 未来填充
                        root4.addChild(item_c42)
                    elif k == 43:
                        item_c43 = QtWidgets.QTreeWidgetItem()
                        item_c43.setText(0, 'C' + str(k))
                        # 未来填充
                        root4.addChild(item_c43)
                    elif k == 21:
                        item_p21 = QtWidgets.QTreeWidgetItem()
                        item_p21.setText(0, 'P' + str(k))
                        # 未来填充
                        root4.addChild(item_p21)
                    elif k == 27:
                        item_p27 = QtWidgets.QTreeWidgetItem()
                        item_p27.setText(0, 'P' + str(k))
                        # 未来填充
                        root4.addChild(item_p27)
                    elif k == 202:
                        item_c2 = QtWidgets.QTreeWidgetItem()  # 为防止字典重复特殊添加
                        item_c2.setText(0, 'C' + str(2))
                        # 未来填充
                        root4.addChild(item_c2)
                    root4.setExpanded(True)
                # A->T 数据包
                elif 44 <= k < 50:
                    if is_o2t_create == 0:
                        root3 = QtWidgets.QTreeWidgetItem(self.treeWidget)
                        root3.setText(0, 'ATO -> TSRS')
                        is_o2t_create = 1
                    else:
                        pass
                    if k == 44:  # a->t 的数据包
                        item_c44 = QtWidgets.QTreeWidgetItem()
                        item_c44.setText(0, 'C' + str(k))
                        # 未来填充
                        root3.addChild(item_c44)
                    elif k == 45:
                        item_c45 = QtWidgets.QTreeWidgetItem()
                        item_c45.setText(0, 'C' + str(k))
                        # 未来填充
                        root3.addChild(item_c45)
                    elif k == 46:
                        item_c46 = QtWidgets.QTreeWidgetItem()
                        item_c46.setText(0, 'C' + str(k))
                        # 未来填充
                        root3.addChild(item_c46)
                    root3.setExpanded(True)
                else:
                    pass
        else:
            pass  # 该周期无数据包

    # 事件处理函数，设置车辆接口MVB信息
    def set_train_page_content(self, idx):
        ato2tcms_ctrl = []
        ato2tcms_stat = []
        tcms2ato_stat = []
        # 读取该周期内容
        try:
            for line in self.log.cycle_dic[self.log.cycle[idx]].cycle_all_info:
                pat_ato_ctrl = 'MVB[' + str(int(self.mvbdialog.led_ato_ctrl.text(), 16)) + ']'
                pat_ato_stat = 'MVB[' + str(int(self.mvbdialog.led_ato_stat.text(), 16)) + ']'
                pat_tcms_stat = 'MVB[' + str(int(self.mvbdialog.led_tcms_stat.text(), 16)) + ']'
                real_idx = 0
                tmp = ''
                parse_flag = 0
                if pat_ato_ctrl in line:
                    if '@' in line:
                        pass
                    else:
                        real_idx = line.find('MVB[')
                        tmp = line[real_idx + 10:]  # 还有一个冒号需要截掉
                        ato2tcms_ctrl = self.mvbParserPage.ato_tcms_parse(1025, tmp)
                        if ato2tcms_ctrl != []:
                            parse_flag = 1
                elif pat_ato_stat in line:
                    if '@' in line:
                        pass
                    else:
                        real_idx = line.find('MVB[')
                        tmp = line[real_idx + 10:]  # 还有一个冒号需要截掉
                        ato2tcms_stat = self.mvbParserPage.ato_tcms_parse(1041, tmp)
                        if ato2tcms_stat != []:
                            parse_flag = 1
                elif pat_tcms_stat in line:
                    if '@' in line:
                        pass
                    else:
                        real_idx = line.find('MVB[')
                        tmp = line[real_idx + 10:]  # 还有一个冒号需要截掉
                        tcms2ato_stat = self.mvbParserPage.ato_tcms_parse(1032, tmp)
                        if tcms2ato_stat != []:
                            parse_flag = 1
        except Exception as err:
            self.Log(err, __name__, sys._getframe().f_lineno)
            print(ato2tcms_ctrl)
        # 显示
        # ATO2TCMS 控制信息
        try:
            if ato2tcms_ctrl != []:
                self.led_ctrl_hrt_2.setText(str(int(ato2tcms_ctrl[0], 16)))  # 控制命令心跳
                if ato2tcms_ctrl[1] == 'AA':
                    self.led_ctrl_atovalid_2.setText('有效')  # ATO有效
                elif ato2tcms_ctrl[1] == '00':
                    self.led_ctrl_atovalid_2.setText('无效')
                else:
                    self.led_ctrl_atovalid_2.setText('异常值%s' % ato2tcms_ctrl[1])

                # 牵引制动状态
                if ato2tcms_ctrl[2] == 'AA':
                    self.led_ctrl_tbstat_2.setText('牵引')
                elif ato2tcms_ctrl[2] == '55':
                    self.led_ctrl_tbstat_2.setText('制动')
                elif ato2tcms_ctrl[2] == 'A5':
                    self.led_ctrl_tbstat_2.setText('惰行')
                elif ato2tcms_ctrl[2] == '00':
                    self.led_ctrl_tbstat_2.setText('无命令')
                else:
                    self.led_ctrl_tbstat_2.setText('异常值%s' % ato2tcms_ctrl[2])

                # 牵引控制量
                self.led_ctrl_tract_2.setText(str(int(ato2tcms_ctrl[3], 16)))
                # 制动控制量
                self.led_ctrl_brake_2.setText(str(int(ato2tcms_ctrl[4], 16)))
                # 保持制动施加
                if ato2tcms_ctrl[5] == 'AA':
                    self.led_ctrl_keepbrake_2.setText('施加')
                elif ato2tcms_ctrl[5] == '00':
                    self.led_ctrl_keepbrake_2.setText('无效')
                else:
                    self.led_ctrl_keepbrake_2.setText('异常值%s' % ato2tcms_ctrl[5])
                # 开左门/右门
                if ato2tcms_ctrl[6][0] == 'C':
                    self.led_ctrl_ldoor_2.setText('有效')
                elif ato2tcms_ctrl[6][0] == '0':
                    self.led_ctrl_ldoor_2.setText('无动作')
                else:
                    self.led_ctrl_ldoor_2.setText('异常%s' % ato2tcms_ctrl[6][0])
                if ato2tcms_ctrl[6][1] == 'C':
                    self.led_ctrl_rdoor_2.setText('有效')
                elif ato2tcms_ctrl[6][1] == '0':
                    self.led_ctrl_rdoor_2.setText('无动作')
                else:
                    self.led_ctrl_rdoor_2.setText('异常%s' % ato2tcms_ctrl[6][1])
                # 恒速命令
                if ato2tcms_ctrl[7] == 'AA':
                    self.led_ctrl_costspeed_2.setText('启动')
                elif ato2tcms_ctrl[7] == '00':
                    self.led_ctrl_costspeed_2.setText('取消')
                else:
                    self.led_ctrl_costspeed_2.setText('异常值%s' % ato2tcms_ctrl[7])
                # 恒速目标速度
                self.led_ctrl_aimspeed_2.setText(str(int(ato2tcms_ctrl[8], 16)))
                # ATO启动灯
                if ato2tcms_ctrl[9] == 'AA':
                    self.led_ctrl_starlamp_2.setText('亮')
                elif ato2tcms_ctrl[9] == '00':
                    self.led_ctrl_starlamp_2.setText('灭')
                else:
                    self.led_ctrl_starlamp_2.setText('异常值%s' % ato2tcms_ctrl[9])
        except Exception as err:
            self.Log(err, __name__, sys._getframe().f_lineno)
            print(ato2tcms_ctrl)
        # ATO2TCMS 状态信息
        try:
            if ato2tcms_stat != []:
                self.led_stat_hrt_2.setText(str(int(ato2tcms_stat[0], 16)))  # 状态命令心跳
                if ato2tcms_stat[1] == 'AA':
                    self.led_stat_error_2.setText('无故障')  # ATO故障
                elif ato2tcms_stat[1] == '00':
                    self.led_stat_error_2.setText('故障')
                else:
                    self.led_stat_error_2.setText('异常值%s' % ato2tcms_stat[1])  # ATO故障
                self.led_stat_stonemile_2.setText(str(int(ato2tcms_stat[2], 16)))  # 公里标
                self.led_stat_tunnelin_2.setText(str(int(ato2tcms_stat[3], 16)))  # 隧道入口
                self.led_stat_tunnellen_2.setText(str(int(ato2tcms_stat[4], 16)))  # 隧道长度
                self.led_stat_atospeed_2.setText(str(int(ato2tcms_stat[5], 16)))  # ato速度
        except Exception as err:
            self.Log(err, __name__, sys._getframe().f_lineno)
            print(ato2tcms_stat)
        # TCMS2ATO 状态信息
        try:
            if tcms2ato_stat != []:
                self.led_tcms_hrt_2.setText(str(int(tcms2ato_stat[0], 16)))  # TCMS状态命令心跳
                # 门模式
                if tcms2ato_stat[1][0] == 'C':
                    self.led_tcms_mm_2.setText('有效')
                    self.led_tcms_am_2.setText('无效')
                elif tcms2ato_stat[1][0] == '3':
                    self.led_tcms_am_2.setText('有效')
                    self.led_tcms_mm_2.setText('无效')
                elif tcms2ato_stat[1][0] == '0':
                    self.led_tcms_am_2.setText('无效')
                    self.led_tcms_mm_2.setText('无效')
                else:
                    self.led_tcms_mm_2.setText('异常值%s' % tcms2ato_stat[1][0])
                    self.led_tcms_am_2.setText('异常值%s' % tcms2ato_stat[1][0])
                # ATO启动灯
                if tcms2ato_stat[1][1] == '3':
                    self.led_tcms_startlampfbk_2.setText('有效')
                elif tcms2ato_stat[1][1] == '0':
                    self.led_tcms_startlampfbk_2.setText('无效')
                else:
                    self.led_tcms_startlampfbk_2.setText('异常值%s' % tcms2ato_stat[1][1])

                # ATO有效反馈
                if tcms2ato_stat[2] == 'AA':
                    self.led_tcms_atovalid_fbk_2.setText('有效')
                elif tcms2ato_stat[2] == '00':
                    self.led_tcms_atovalid_fbk_2.setText('无效')
                else:
                    self.led_tcms_atovalid_fbk_2.setText('异常值%s' % tcms2ato_stat[2])

                # 牵引制动反馈
                if tcms2ato_stat[3] == 'AA':
                    self.led_tcms_fbk_2.setText('牵引')
                elif tcms2ato_stat[3] == '55':
                    self.led_tcms_fbk_2.setText('制动')
                elif tcms2ato_stat[3] == 'A5':
                    self.led_tcms_fbk_2.setText('惰行')
                elif tcms2ato_stat[3] == '00':
                    self.led_tcms_fbk_2.setText('无命令')
                else:
                    self.led_tcms_fbk_2.setText('异常值%s' % tcms2ato_stat[3])

                # 牵引反馈
                self.led_tcms_tractfbk_2.setText(str(int(tcms2ato_stat[4], 16)))
                # 制动反馈
                self.led_tcms_bfbk_2.setText(str(int(tcms2ato_stat[5], 16)))
                # 保持制动施加
                if tcms2ato_stat[6] == 'AA':
                    self.led_tcms_keepbfbk_2.setText('有效')
                elif tcms2ato_stat[6] == '00':
                    self.led_tcms_keepbfbk_2.setText('无效')
                else:
                    self.led_tcms_keepbfbk_2.setText('异常值%s' % tcms2ato_stat[6])
                # 左门反馈，右门反馈
                if tcms2ato_stat[7][0] == 'C':
                    self.led_tcms_ldoorfbk_2.setText('有效')
                elif tcms2ato_stat[7][0] == '0':
                    self.led_tcms_ldoorfbk_2.setText('无效')
                else:
                    self.led_tcms_ldoorfbk_2.setText('异常值%s' % tcms2ato_stat[7][0])
                if tcms2ato_stat[7][1] == 'C':
                    self.led_tcms_rdoorfbk_2.setText('有效')
                elif tcms2ato_stat[7][1] == '0':
                    self.led_tcms_rdoorfbk_2.setText('无效')
                else:
                    self.led_tcms_rdoorfbk_2.setText('异常值%s' % tcms2ato_stat[7][0])
                # 恒速反馈
                if tcms2ato_stat[8] == 'AA':
                    self.led_tcms_costspeedfbk_2.setText('有效')
                elif tcms2ato_stat[8] == '00':
                    self.led_tcms_costspeedfbk_2.setText('无效')
                else:
                    self.led_tcms_costspeedfbk_2.setText('异常值%s' % tcms2ato_stat[8])
                # 车门状态
                if tcms2ato_stat[9] == 'AA':
                    self.led_tcms_doorstat_2.setText('关')
                elif tcms2ato_stat[9] == '00':
                    self.led_tcms_doorstat_2.setText('开')
                else:
                    self.led_tcms_doorstat_2.setText('异常值%s' % tcms2ato_stat[9])
                # 空转打滑
                if tcms2ato_stat[10][0] == 'A':
                    self.led_tcms_kz_2.setText('空转')
                    self.led_tcms_kz_2.setStyleSheet("background-color:rgb(255, 0, 0);")
                elif tcms2ato_stat[10][0] == '0':
                    self.led_tcms_kz_2.setText('未发生')
                    self.led_tcms_kz_2.setStyleSheet("background-color:rgb(219, 255, 227);")
                else:
                    self.led_tcms_kz_2.setText('异常值%s' % tcms2ato_stat[10][0])

                if tcms2ato_stat[10][1] == 'A':
                    self.led_tcms_dh_2.setText('打滑')
                    self.led_tcms_dh_2.setStyleSheet("background-color:rgb(255, 0, 0);")
                elif tcms2ato_stat[10][1] == '0':
                    self.led_tcms_dh_2.setText('未发生')
                    self.led_tcms_dh_2.setStyleSheet("background-color:rgb(219, 255, 227);")
                else:
                    self.led_tcms_dh_2.setText('异常值%s' % tcms2ato_stat[10][1])
                # 编组信息
                tmp_units = int(tcms2ato_stat[11], 16)
                if tmp_units == 1:
                    self.led_tcms_nunits_2.setText('8编组')
                elif tmp_units == 2:
                    self.led_tcms_nunits_2.setText('8编重连')
                elif tmp_units == 3:
                    self.led_tcms_nunits_2.setText('16编组')
                elif tmp_units == 4:
                    self.led_tcms_nunits_2.setText('18编组')
                else:
                    self.led_tcms_nunits_2.setText('异常值%s' % tcms2ato_stat[11])
                # 车重
                self.led_tcms_weight_2.setText(str(int(tcms2ato_stat[12], 16)))
                # 动车组允许
                if tcms2ato_stat[13] == 'AA':
                    self.led_tcms_pm_2.setText('允许')
                elif tcms2ato_stat[13] == '00':
                    self.led_tcms_pm_2.setText('不允许')
                else:
                    self.led_tcms_pm_2.setText('异常值%s' % tcms2ato_stat[13])

                # 主断状态
                if tcms2ato_stat[14] == 'AA':
                    self.led_tcms_breakstat_2.setText('闭合')
                    self.lbl_dcmd.setText('主断闭合')
                    self.lbl_dcmd.setStyleSheet("background-color: rgb(0, 255, 127);")
                elif tcms2ato_stat[14] == '00':
                    self.led_tcms_breakstat_2.setText('断开')
                    self.lbl_dcmd.setText('主断断开')
                    self.lbl_dcmd.setStyleSheet("background-color: rgb(255, 0, 0);")
                else:
                    self.led_tcms_breakstat_2.setText('异常值%s' % tcms2ato_stat[14])
                # ATP允许 人工允许
                if tcms2ato_stat[15] == 'C0':
                    self.led_tcms_atpdoorpm_2.setText('有效')
                    self.led_tcms_mandoorpm_2.setText('无效')
                elif tcms2ato_stat[15] == '30':
                    self.led_tcms_atpdoorpm_2.setText('无效')
                    self.led_tcms_mandoorpm_2.setText('有效')
                elif tcms2ato_stat[15] == '00':
                    self.led_tcms_atpdoorpm_2.setText('无效')
                    self.led_tcms_mandoorpm_2.setText('无效')
                else:
                    self.led_tcms_atpdoorpm_2.setText('异常值%s' % tcms2ato_stat[15])
                    self.led_tcms_mandoorpm_2.setText('异常值%s' % tcms2ato_stat[15])
                # 不允许状态字
                str_tcms = ''
                str_raw = ['未定义', '至少有一个车辆空气制动不可用|', 'CCU存在限速保护|', 'CCU自动施加常用制动|',
                           '车辆施加紧急制动EB或紧急制动UB|', '保持制动被隔离|',
                           'CCU判断与ATO通信故障(CCU监测到ATO生命信号32个周期(2s)不变化)|', '预留|']
                if tcms2ato_stat[16] == '00':
                    self.led_tcms_pmt_state_2.setText('正常')
                else:
                    val_field = int(tcms2ato_stat[16], 16)
                    for cnt in range(7, -1, -1):
                        if val_field & (1 << cnt) != 0:
                            str_tcms = str_tcms + str_raw[cnt]
                    self.led_tcms_pmt_state_2.setText('异常原因:%s' % str_tcms)
        except Exception as err:
            self.Log(err, __name__, sys._getframe().f_lineno)
            print(tcms2ato_stat)

    # 事件处理函数，设置计划信息
    def set_plan_page_content(self, idx):
        update_flag = 0
        ret_plan = ()
        temp_utc = ''
        rp1 = ()
        rp2 = ()
        rp2_list = []
        rp3 = ()
        rp4 = ()
        plan_in_cycle = '0'  # 主要用于周期识别比较，清理列表
        newPaintCnt = 0
        time_plan_remain = 0
        time_plan_count = 0
        time_remain = 0
        time_count = 0
        temp_transfer_list = []
        # 当周期系统时间
        cycle_os_time = self.log.cycle_dic[self.log.cycle[idx]].ostime_start
        # 读取该周期内容
        try:
            for line in self.log.cycle_dic[self.log.cycle[idx]].cycle_all_info:
                # 提高解析效率,当均更新时才发送信号
                if '[RP' in line:
                    if self.pat_plan[0].findall(line):
                        rp1 = self.pat_plan[0].findall(line)[0]
                        update_flag = 1

                    elif self.pat_plan[1].findall(line):
                        rp2 = self.pat_plan[1].findall(line)[0]
                        update_flag = 1

                    elif self.pat_plan[2].findall(line):
                        temp_transfer_list = self.comput_plan_content(self.pat_plan[2].findall(line)[0])
                        rp2_list.append(tuple(temp_transfer_list))

                    elif self.pat_plan[3].findall(line):
                        rp3 = self.pat_plan[3].findall(line)[0]
                        update_flag = 1

                    elif self.pat_plan[4].findall(line):
                        rp4 = self.pat_plan[4].findall(line)[0]
                        if int(rp4[1]) != 0:
                            time_plan_remain = int(rp4[1]) - cycle_os_time
                        if int(rp4[2]) != 0:
                            time_plan_count = int(rp4[2]) - cycle_os_time
                        update_flag = 1
                    else:
                        pass
                    ret_plan = (rp1, (rp2, rp2_list), rp3, rp4,
                                time_plan_remain, time_plan_count)
                else:
                    pass
            # 更新搜索完的记录信息,有数才存储
            if ret_plan:
                rp1 = ret_plan[0]
                rp2 = ret_plan[1][0]
                rp2_list = ret_plan[1][1]
                rp3 = ret_plan[2]
                rp4 = ret_plan[3]
                # 运行时间和倒计时
                time_remain = ret_plan[4]
                time_count = ret_plan[5]
        except Exception as err:
            self.Log(err, __name__, sys._getframe().f_lineno)
            print(line)

        # 临时变量
        rp2_temp_list = []
        # 开始计算
        try:
            if rp1 != ():
                self.led_s_track_2.setText(str(rp1[0]))

                if rp1[3] == '1':
                    self.lbl_stop_flag_2.setText('停稳状态')
                    self.lbl_stop_flag_2.setStyleSheet("background-color: rgb(0, 255, 0);")
                elif rp1[3] == '0':
                    self.lbl_stop_flag_2.setText('非停稳')
                    self.lbl_stop_flag_2.setStyleSheet("background-color: rgb(255, 0, 0);")

            if rp2 != ():
                if rp2[0] == '1':
                    self.lbl_plan_legal_2.setText('计划合法')
                    self.lbl_plan_legal_2.setStyleSheet("background-color: rgb(0, 255, 0);")
                elif rp2[0] == '0':
                    self.lbl_plan_legal_2.setText('计划非法')
                    self.lbl_plan_legal_2.setStyleSheet("background-color: rgb(255, 0, 0);")

                if rp2[1] == '1':
                    self.lbl_plan_final_2.setText('终到站')
                elif rp2[1] == '0':
                    self.lbl_plan_final_2.setText('非终到站')
            # 有计划，准备表格显示内容
            if rp2_list != []:
                for item in rp2_list:
                    # 去除打印中计划更新时间信息，无用
                    rp2_temp_list.append(item[0:1] + item[2:])

                len_plan = len(rp2_temp_list)

                # 清空表格内容准备更新
                self.tableWidgetPlan_2.clearContents()

                # 计划索引
                for index, item_plan in enumerate(rp2_temp_list):
                    # 内容索引
                    for idx, name in enumerate(item_plan):
                        self.tableWidgetPlan_2.setItem(idx, index, QtWidgets.QTableWidgetItem(item_plan[idx]))
                        self.tableWidgetPlan_2.item(idx, index).setTextAlignment(QtCore.Qt.AlignCenter)
            else:
                # 没有计划，清空表格内容直接清空
                self.tableWidgetPlan_2.clearContents()

            if rp3 != ():
                if rp3[0] == '1':
                    self.lbl_plan_timeout_2.setText('已超时')
                    self.lbl_plan_timeout_2.setStyleSheet("background-color: rgb(255, 0, 0)")
                elif rp3[0] == '0':
                    self.lbl_plan_timeout_2.setText('未超时')
                    self.lbl_plan_timeout_2.setStyleSheet("background-color: rgb(0, 255, 0)")

                if rp3[1] == '1':
                    self.lbl_start_flag_2.setText('发车状态')
                    self.lbl_start_flag_2.setStyleSheet("background-color: rgb(255, 170, 255);")
                elif rp3[1] == '2':
                    self.lbl_start_flag_2.setText('接车状态')
                    self.lbl_start_flag_2.setStyleSheet("background-color: rgb(85, 255, 255);")
                elif rp3[1] == '0':
                    self.lbl_start_flag_2.setText('未知状态')
                    self.lbl_start_flag_2.setStyleSheet("background-color: rgb(170, 170, 255);")

            if rp4 != ():
                if rp4[0] == '1':
                    self.lbl_plan_valid_2.setText('计划有效')
                    self.lbl_plan_valid_2.setStyleSheet("background-color: rgb(0, 255, 0)")
                elif rp4[0] == '0':
                    self.lbl_plan_valid_2.setText('计划无效')
                    self.lbl_plan_valid_2.setStyleSheet("background-color: rgb(255, 0, 0)")

            self.led_plan_coutdown_2.setText(str(time_count / 1000) + 's')
            self.led_runtime_2.setText(str(time_remain / 1000) + 's')

        except Exception as err:
            self.Log(err, __name__, sys._getframe().f_lineno)
            print(ret_plan)

    # 解析转化计划,参考实时解析实现
    def comput_plan_content(self, t=tuple):
        # 替换其中的UTC时间
        temp_transfer_list = [''] * len(t)
        for idx, item in enumerate(t):
            if idx in [2, 4, 6]:
                if int(t[idx]) == -1:
                    temp_transfer_list[idx] = '无效值'
                else:
                    ltime = time.localtime(int(t[idx]))
                    temp_transfer_list[idx] = time.strftime("%H:%M:%S", ltime)
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

    # 事件处理函数，设置ATP信息
    def set_ATP_page_content(self, idx):
        # 数据包北荣使用tuple类型
        for k in self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict.keys():
            if k == 2:
                sp2_tpl = self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k]
                self.set_atp_info_win(sp2_tpl, 2)
            elif k == 1001:
                c2ato_p1_tpl = self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k]
                self.set_atp_info_win(c2ato_p1_tpl, 1001)
            elif k == 5:
                sp5_tpl = self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k]
                self.set_atp_info_win(sp5_tpl, 5)
            elif k == 7:
                sp7_tpl = self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k]
            elif k == 131:
                sp131_tpl = self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k]
                self.set_atp_info_win(sp131_tpl, 131)

    # 设置数据包显示到界面
    def set_atp_info_win(self, sp_tpl=tuple, clsify=int):
        # SP2包内容
        if clsify == 2:
            if sp_tpl != ():
                # 门允许状态
                if sp_tpl[2].strip() == '1':  # 左门允许
                    self.lbl_door_pmt.setText('左门允许')
                    self.lbl_door_pmt.setStyleSheet("background-color: rgb(0, 255, 127);")
                elif sp_tpl[3].strip() == '1':  # 右门允许
                    self.lbl_door_pmt.setText('右门允许')
                    self.lbl_door_pmt.setStyleSheet("background-color: rgb(0, 255, 127);")
                else:
                    self.lbl_door_pmt.setText('无门允许')
                    self.lbl_door_pmt.setStyleSheet("background-color: rgb(255, 0, 0);")
                # ATP停准停稳状态
                if sp_tpl[16].strip() == '0':
                    self.lbl_atp_stop_ok.setText('未停稳')
                    self.lbl_atp_stop_ok.setStyleSheet("background-color: rgb(255, 0, 0);")
                elif sp_tpl[16].strip() == '1':
                    self.lbl_atp_stop_ok.setText('停稳未停准')
                    self.lbl_atp_stop_ok.setStyleSheet("background-color: rgb(0, 200, 127);")
                elif sp_tpl[16].strip() == '2':
                    self.lbl_atp_stop_ok.setText('停稳停准')
                    self.lbl_atp_stop_ok.setStyleSheet("background-color: rgb(0, 255, 127);")

                # 是否TSM区
                if sp_tpl[21].strip() == '2147483647' or sp_tpl[21].strip() != '4294967295':
                    self.lbl_tsm.setText('恒速区')
                    self.lbl_tsm.setStyleSheet("background-color: rgb(0, 255, 127);")
                else:
                    self.lbl_tsm.setText('减速区')
                    self.lbl_tsm.setStyleSheet("background-color: rgb(255, 255, 0);")

                # 是否立折
                if sp_tpl[5].strip() == '1':
                    self.lbl_tb.setText('立折换端')
                    self.lbl_tb.setStyleSheet("background-color: rgb(0, 255, 127);")
                else:
                    self.lbl_tb.setText('非换端')
                    self.lbl_tb.setStyleSheet("background-color: rgb(170, 170, 255);")

                # 是否切牵引
                if sp_tpl[24].strip() == '1':
                    self.lbl_atp_cut_traction.setText('ATP切除牵引')
                    self.lbl_atp_cut_traction.setStyleSheet("background-color:  rgb(255, 0, 0);")
                else:
                    self.lbl_atp_cut_traction.setText('未切除牵引')
                    self.lbl_atp_cut_traction.setStyleSheet("background-color: rgb(170, 170, 255);")

                # 是否制动
                if sp_tpl[25].strip() == '1':
                    self.lbl_atp_brake.setText('ATP施加制动')
                    self.lbl_atp_brake.setStyleSheet("background-color: rgb(255, 0, 0);")
                else:
                    self.lbl_atp_brake.setText('未施加制动')
                    self.lbl_atp_brake.setStyleSheet("background-color: rgb(170, 170, 255);")

                # ATP等级/模式
                if sp_tpl[8].strip() == '1':
                    self.lbl_atp_level.setText('CTCS2')

                    if sp_tpl[9].strip() == '1':
                        self.lbl_atp_mode.setText('待机模式')
                    elif sp_tpl[9].strip() == '2':
                        self.lbl_atp_mode.setText('完全模式')
                    elif sp_tpl[9].strip() == '3':
                        self.lbl_atp_mode.setText('部分模式')
                    elif sp_tpl[9].strip() == '5':
                        self.lbl_atp_mode.setText('引导模式')
                    elif sp_tpl[9].strip() == '7':
                        self.lbl_atp_mode.setText('目视模式')
                    elif sp_tpl[9].strip() == '8':
                        self.lbl_atp_mode.setText('调车模式')
                    elif sp_tpl[9].strip() == '9':
                        self.lbl_atp_mode.setText('隔离模式')
                    elif sp_tpl[9].strip() == '10':
                        self.lbl_atp_mode.setText('机信模式')
                    elif sp_tpl[9].strip() == '11':
                        self.lbl_atp_mode.setText('休眠模式')
                elif sp_tpl[8].strip() == '3':
                    self.lbl_atp_level.setText('CTCS3')

                    if sp_tpl[9].strip() == '6':
                        self.lbl_atp_mode.setText('待机模式')
                    elif sp_tpl[9].strip() == '0':
                        self.lbl_atp_mode.setText('完全模式')
                    elif sp_tpl[9].strip() == '1':
                        self.lbl_atp_mode.setText('引导模式')
                    elif sp_tpl[9].strip() == '2':
                        self.lbl_atp_mode.setText('目视模式')
                    elif sp_tpl[9].strip() == '3':
                        self.lbl_atp_mode.setText('调车模式')
                    elif sp_tpl[9].strip() == '10':
                        self.lbl_atp_mode.setText('隔离模式')
                    elif sp_tpl[9].strip() == '5':
                        self.lbl_atp_mode.setText('休眠模式')

                # 显示信息
                if '4294967295' != sp_tpl[23].strip():
                    self.led_atp_milestone.setText(
                        'K' + str(int(int(sp_tpl[23]) / 1000)) + '+' + str(int(sp_tpl[23]) % 1000))
                else:
                    self.led_atp_milestone.setText('未知')
                self.led_stn_center_dis.setText(sp_tpl[18].strip() + 'cm')
                self.led_jz_signal_dis.setText(sp_tpl[19].strip() + 'cm')
                self.led_cz_signal_dis.setText(sp_tpl[20].strip() + 'cm')
                self.led_atp_tsm_dis.setText(sp_tpl[21].strip() + 'cm')
                self.led_cz_signal_dis.setText(sp_tpl[20].strip() + 'cm')
                self.led_atp_target_dis.setText(sp_tpl[7].strip() + 'cm')
                self.led_atp_gfx_dis.setText(sp_tpl[14].strip() + 'm')
                self.led_atp_target_v.setText(sp_tpl[6].strip() + 'cm/s')
                self.led_atp_ma.setText(sp_tpl[12].strip() + 'm')
                self.led_atp_stoperr.setText(sp_tpl[17].strip() + 'cm')

        if clsify == 1001:
            # 门允许状态
            if sp_tpl[1].strip() == '1':  # 左门允许
                self.lbl_door_pmt.setText('左门允许')
                self.lbl_door_pmt.setStyleSheet("background-color: rgb(0, 255, 127);")
            elif sp_tpl[2].strip() == '1':  # 右门允许
                self.lbl_door_pmt.setText('右门允许')
                self.lbl_door_pmt.setStyleSheet("background-color: rgb(0, 255, 127);")
            else:
                self.lbl_door_pmt.setText('无门允许')
                self.lbl_door_pmt.setStyleSheet("background-color: rgb(255, 0, 0);")

            self.led_atp_target_v.setText(sp_tpl[3].strip() + 'cm/s')
            self.led_atp_target_dis.setText(sp_tpl[4].strip() + 'cm')
            self.led_atp_gfx_dis.setText(sp_tpl[10].strip() + 'm')
            self.led_atp_ma.setText(sp_tpl[8].strip() + 'm')
            self.led_atp_stoperr.setText(sp_tpl[12].strip() + 'cm')
            # 设置ATP速传sdu
            atp_s = int(sp_tpl[5].strip())
            self.led_atp_sdu.setText(sp_tpl[6].strip() + 'cm/s')  # atp速度
            self.led_atp_s_delta.setText(str(atp_s - self.sdu_info_s[1]) + 'cm')
            self.sdu_info_s[1] = atp_s

        if clsify == 5:
            if sp_tpl != ():
                if sp_tpl[0].strip() == '1':
                    self.led_units.setText('8编组')
                elif sp_tpl[0].strip() == '2':
                    self.led_units.setText('16编组')
                elif sp_tpl[0].strip() == '3':
                    self.led_units.setText('18编组')

                if sp_tpl[9].strip() == '1':
                    self.led_driver_strategy.setText('正常策略')
                elif sp_tpl[9].strip() == '2':
                    self.led_driver_strategy.setText('快行策略')
                elif sp_tpl[9].strip() == '3':
                    self.led_driver_strategy.setText('慢行策略')

                # BTM天线等
                self.led_atp_btm_pos.setText(str(int(sp_tpl[3]) * 10) + 'cm')
                self.led_head_foor_dis.setText(sp_tpl[4].strip() + 'cm')
                self.led_nid_engine.setText(sp_tpl[8].strip())

        if clsify == 131:
            if sp_tpl != ():
                if sp_tpl[6].strip() == '1':
                    self.lbl_mvb_link.setText('MVB正常')
                    self.lbl_mvb_link.setStyleSheet("background-color: rgb(0, 255, 127);")
                elif sp_tpl[6].strip() == '2':
                    self.lbl_mvb_link.setText('MVB中断')
                    self.lbl_mvb_link.setStyleSheet("background-color: rgb(255, 0, 0);")

                if sp_tpl[4].strip() == '1':
                    self.lbl_ato_radio.setText('电台正常')
                    self.lbl_ato_radio.setStyleSheet("background-color: rgb(0, 255, 127);")
                elif sp_tpl[4].strip() == '0':
                    self.lbl_ato_radio.setText('电台异常')
                    self.lbl_ato_radio.setStyleSheet("background-color: rgb(255, 0, 0);")

                if sp_tpl[5].strip() == '1':
                    self.lbl_ato_session.setText('未连接')
                    self.lbl_ato_session.setStyleSheet("background-color: rgb(255, 0, 0);")
                elif sp_tpl[5].strip() == '2':
                    self.lbl_ato_session.setText('正在呼叫')
                    self.lbl_ato_session.setStyleSheet("background-color: rgb(170, 170, 255);")
                elif sp_tpl[5].strip() == '3':
                    self.lbl_ato_session.setText('正常连接')
                    self.lbl_ato_session.setStyleSheet("background-color: rgb(0, 255, 127);")

                if sp_tpl[0].strip() == '1':
                    self.lbl_ato_ctrl_stat.setText('计划有效')
                else:
                    if sp_tpl[7].strip() == '1':
                        self.lbl_ato_ctrl_stat.setText('正常策略')
                    elif sp_tpl[7].strip() == '2':
                        self.lbl_ato_ctrl_stat.setText('快行策略')
                    elif sp_tpl[7].strip() == '3':
                        self.lbl_ato_ctrl_stat.setText('慢行策略')

    # 事件处理函数，应答器表格选中事件,调用光标
    def BTM_selected_info(self, row_item):
        global cur_interface
        if cur_interface == 1:
            c_num = self.BTM_cycle[row_item.row()]
            try:
                self.spinBox.setValue(c_num)
                if 7 in self.log.cycle_dic[c_num].cycle_sp_dict.keys():
                    c_show_sp7 = self.log.cycle_dic[c_num]
                    # JD正常刷颜色
                    if c_show_sp7.cycle_sp_dict[7][3].strip() == '13':
                        self.led_with_c13.setText('有')
                        self.led_with_c13.setStyleSheet("background-color: rgb(225, 0, 0);")
                        # 站台位置
                        platform_pos = int(c_show_sp7.cycle_sp_dict[7][5])
                        if platform_pos == 0:
                            self.led_platform_pos.setText('左侧')
                        elif platform_pos == 1:
                            self.led_platform_pos.setText('右侧')
                        elif platform_pos == 2:
                            self.led_platform_pos.setText('双侧')
                        elif platform_pos == 3:
                            self.led_platform_pos.setText('无站台')
                        # 站台门
                        platform_door = int(c_show_sp7.cycle_sp_dict[7][6])
                        if platform_door == 1:
                            self.led_platform_door.setText('有')
                        elif platform_door == 2:
                            self.led_platform_door.setText('无')
                        # 停车点
                        self.led_track.setText(c_show_sp7.cycle_sp_dict[7][7])
                        scale = int(c_show_sp7.cycle_sp_dict[7][4])
                        d_stop = int(c_show_sp7.cycle_sp_dict[7][8])
                        if scale == 0:
                            scale = 10
                        elif scale == 1:
                            scale = 100
                        elif scale == 2:
                            scale = 1000
                        self.led_stop_d_JD.setText(str(scale * d_stop) + 'cm')
                    else:
                        self.led_with_c13.setText('无')
                        self.led_with_c13.setStyleSheet("background-color: rgb(100, 100, 100);")
                        self.led_platform_door.clear()
                        self.led_platform_pos.clear()
                        self.led_track.clear()
                        self.led_stop_d_JD.clear()
            except Exception as err:
                self.Log(err, __name__, sys._getframe().f_lineno)
        elif cur_interface == 2:
            cur_sp7 = self.real_btm_list[row_item.row()]    # 通过记录的在线btm数据来二次索引
            try:
                # JD正常刷颜色
                if cur_sp7[3].strip() == '13':
                    self.led_with_c13.setText('有')
                    self.led_with_c13.setStyleSheet("background-color: rgb(225, 0, 0);")
                    # 站台位置
                    platform_pos = int(cur_sp7[5])
                    if platform_pos == 0:
                        self.led_platform_pos.setText('左侧')
                    elif platform_pos == 1:
                        self.led_platform_pos.setText('右侧')
                    elif platform_pos == 2:
                        self.led_platform_pos.setText('双侧')
                    elif platform_pos == 3:
                        self.led_platform_pos.setText('无站台')
                    # 站台门
                    platform_door = int(cur_sp7[6])
                    if platform_door == 1:
                        self.led_platform_door.setText('有')
                    elif platform_door == 2:
                        self.led_platform_door.setText('无')
                    # 停车点
                    self.led_track.setText(cur_sp7[7])
                    scale = int(cur_sp7[4])
                    d_stop = int(cur_sp7[8])
                    if scale == 0:
                        scale = 10
                    elif scale == 1:
                        scale = 100
                    elif scale == 2:
                        scale = 1000
                    self.led_stop_d_JD.setText(str(scale * d_stop) + 'cm')
                else:
                    self.led_with_c13.setText('无')
                    self.led_with_c13.setStyleSheet("background-color: rgb(100, 100, 100);")
                    self.led_platform_door.clear()
                    self.led_platform_pos.clear()
                    self.led_track.clear()
                    self.led_stop_d_JD.clear()
            except Exception as err:
                self.Log(err, __name__, sys._getframe().f_lineno)

    # 事件处理函数，显示测速测距信息
    def set_sdu_info_content(self, idx):
        stat_machine = 0
        sdu_ato = []
        sdu_atp = []
        result = ()
        # sdu Info 解析表
        p_ato_sdu = self.pat_list[27]
        p_atp_sdu = self.pat_list[28]

        for line in self.log.cycle_dic[self.log.cycle[idx]].cycle_all_info:
            if 'v&p' in line:
                try:
                    # 查找或清空
                    if p_atp_sdu.findall(line):
                        sdu_atp = p_atp_sdu.findall(line)[0]
                        state_machine = 1
                        # 查找或清空
                    if p_ato_sdu.findall(line):
                        sdu_ato = p_ato_sdu.findall(line)[0]
                        # 如果已经收到了sdu_ato
                        if state_machine == 1:
                            state_machine = 2  # 置状态机为2.收到ATP
                    # 组合数据,前面安装时间和周期
                    result = (sdu_ato, sdu_atp)

                    # 收集到sdu_ato和sdu_atp, 终止状态机，发送信号清空
                    if state_machine == 2:
                        self.realtime_sdu_show(result)
                        state_machine = 0
                        sdu_ato = []
                        sdu_atp = []
                    else:
                        pass
                except Exception as err:
                    self.Log(err, __name__, sys._getframe().f_lineno)

    # 重置主界面所有的选择框
    def reset_all_checkbox(self):
        self.CBacc.setChecked(False)
        self.CBatpcmdv.setChecked(False)
        self.CBlevel.setChecked(False)
        self.CBcmdv.setChecked(False)
        self.CBvato.setChecked(False)
        self.CBramp.setChecked(False)
        self.CBatppmtv.setChecked(False)

    # 重置主界面文本框
    def reset_text_edit(self):
        self.textEdit.setPlainText(time.strftime("%Y-%m-%d %H:%M:%S \n", time.localtime(time.time())))
        self.textEdit.setPlainText('open file : ' + self.file + ' OK! \n')

    # 重绘图形并重置选择框
    def reset_logplot(self):
        global load_flag
        global curve_flag
        # 当文件路径不为空
        if self.file == '':
            pass
        else:
            try:
                self.Log('Init global vars', __name__, sys._getframe().f_lineno)
                load_flag = 0  # 区分是否已经加载文件,1=加载且控车，2=加载但没有控车
                curve_flag = 1  # 区分绘制曲线类型，0=速度位置曲线，1=周期位置曲线
                self.Log('Init UI widgt', __name__, sys._getframe().f_lineno)
                self.update_filetab()
                self.reset_all_checkbox()
                self.reset_text_edit()
                self.mode = 0  # 恢复初始浏览模式
                self.update_mvb_port_pat()  # 更新mvb索引端口信息
                self.Log("Clear axes", __name__, sys._getframe().f_lineno)
                self.sp.axes1.clear()
                self.textEdit.clear()
                self.Log('Init File log', __name__, sys._getframe().f_lineno)
                # 开始处理
                self.log_process()
            except Exception as err:
                self.textEdit.setPlainText(' Error Line ' + str(err.start) + ':' + err.reason + '\n')
                self.textEdit.append('Process file failure! \nPlease Predeal the file!')

    # 设置标签的格式
    def set_label_format(self):
        self.label.setText('ATO时间:')
        self.label_3.setText('周期号:')

    # ATO状态显示标签
    def set_ato_status_label(self, idx):
        temp = ()
        c = self.log.cycle_dic[self.log.cycle[idx]]
        if c.fsm != ():
            temp = self.log.cycle_dic[self.log.cycle[idx]].fsm
            # ATO模式
            if temp[1] == '1':
                self.lbl_mode.setText('AOS模式')
                self.lbl_mode.setStyleSheet("background-color: rgb(180, 180, 180);")
            elif temp[1] == '2':
                self.lbl_mode.setText('AOR模式')
                self.lbl_mode.setStyleSheet("background-color: rgb(255, 255, 0);")
            elif temp[1] == '3':
                self.lbl_mode.setText('AOM模式')
                self.lbl_mode.setStyleSheet("background-color: rgb(255, 255, 255);")
            else:
                self.lbl_mode.setText('ATO模式')
                self.lbl_mode.setStyleSheet("background-color: rgb(170, 170, 255);")

            # 软允许
            if temp[3] == '1':
                self.lbl_pm.setStyleSheet("background-color: rgb(0, 255, 127);")
            else:
                self.lbl_pm.setStyleSheet("background-color: rgb(255, 0, 0);")

            # 硬允许
            if temp[2] == '1':
                self.lbl_hpm.setStyleSheet("background-color: rgb(0, 255, 127);")
            else:
                self.lbl_hpm.setStyleSheet("background-color: rgb(255, 0, 0);")

            # 动车组允许
            if temp[4] == '1':
                self.lbl_carpm.setStyleSheet("background-color: rgb(0, 255, 127);")
            else:
                self.lbl_carpm.setStyleSheet("background-color: rgb(255, 0, 0);")

            # 自检状态
            if temp[5] == '1':
                self.lbl_check.setStyleSheet("background-color: rgb(0, 255, 127);")
            else:
                self.lbl_check.setStyleSheet("background-color: rgb(255, 0, 0);")

            # 发车指示灯
            if temp[6] == '0':
                self.lbl_lamp.setText('发车灯灭')
                self.lbl_lamp.setStyleSheet("background-color: rgb(100, 100, 100);")
            elif temp[6] == '1':
                self.lbl_lamp.setText('发车灯闪')
                self.lbl_lamp.setStyleSheet("background-color: rgb(255, 255, 0);")
            elif temp[6] == '2':
                self.lbl_lamp.setText('发车灯亮')
                self.lbl_lamp.setStyleSheet("background-color: rgb(0, 255, 0);")

            # 车长
            self.lbl_trainlen.setText('车长' + str(int(temp[9]) / 100) + 'm')

            # 门状态
            if temp[10] == '55':
                self.lbl_doorstatus.setText('门开')
            elif temp[10] == 'AA':
                self.lbl_doorstatus.setText('门关')

            # 低频
            if temp[11] == '0':
                self.lbl_freq.setText('H码')
                self.lbl_freq.setStyleSheet("background-color: rgb(255, 0, 0);")
            elif temp[11] == '2':
                self.lbl_freq.setText('HU码')
                self.lbl_freq.setStyleSheet("background-color: rgb(255, 215, 15);")
            elif temp[11] == '10':
                self.lbl_freq.setText('HB码')
                self.lbl_freq.setStyleSheet("background-color: rgb(163, 22, 43);")
            elif temp[11] == '2A':
                self.lbl_freq.setText('L4码')
                self.lbl_freq.setStyleSheet("background-color: rgb(0, 255, 0);")
            elif temp[11] == '2B':
                self.lbl_freq.setText('L5码')
                self.lbl_freq.setStyleSheet("background-color: rgb(0, 255, 0);")
            elif temp[11] == '25':
                self.lbl_freq.setText('U2S码')
                self.lbl_freq.setStyleSheet("background-color: rgb(255, 255, 0);")
            elif temp[11] == '23':
                self.lbl_freq.setText('UUS码')
                self.lbl_freq.setStyleSheet("background-color: rgb(255, 255, 0);")
            elif temp[11] == '22':
                self.lbl_freq.setText('UU码')
                self.lbl_freq.setStyleSheet("background-color: rgb(255, 255, 0);")
            elif temp[11] == '21':
                self.lbl_freq.setText('U码')
                self.lbl_freq.setStyleSheet("background-color: rgb(255, 255, 0);")
            elif temp[11] == '24':
                self.lbl_freq.setText('U2码')
                self.lbl_freq.setStyleSheet("background-color: rgb(255, 255, 0);")
            elif temp[11] == '26':
                self.lbl_freq.setText('LU码')
                self.lbl_freq.setStyleSheet("background-color: rgb(205, 255, 25);")
            elif temp[11] == '28':
                self.lbl_freq.setText('L2码')
                self.lbl_freq.setStyleSheet("background-color: rgb(0, 255, 0);")
            elif temp[11] == '27':
                self.lbl_freq.setText('L码')
                self.lbl_freq.setStyleSheet("background-color: rgb(0, 255, 0);")
            elif temp[11] == '29':
                self.lbl_freq.setText('L3码')
                self.lbl_freq.setStyleSheet("background-color: rgb(0, 255, 0);")
            # 站台
            if temp[13] == '1':
                self.lbl_stn.setText('站内')
            else:
                self.lbl_stn.setText('站外')
        # 主断和分相
        if c.break_status == 1:
            self.lbl_dcmd.setText('主断断开')
            self.lbl_dcmd.setStyleSheet("background-color: rgb(255, 0, 0);")
        else:
            self.lbl_dcmd.setText('主断闭合')
            self.lbl_dcmd.setStyleSheet("background-color: rgb(0, 255, 127);")
        if c.gfx_flag == 1:
            self.lbl_atpdcmd.setText('过分相')
            self.lbl_atpdcmd.setStyleSheet("background-color: rgb(255, 0, 0);")
        else:
            self.lbl_atpdcmd.setText('非过分相')
            self.lbl_atpdcmd.setStyleSheet("background-color: rgb(0, 255, 127);")

    # 导出函数
    def export_ato_ctrl_info(self):
        global load_flag
        # file is load
        if load_flag == 1:
            try:
                filepath = QtWidgets.QFileDialog.getSaveFileName(self, "Save file", "d:/", "excel files(*.xls)")
                if filepath != ('', ''):
                    workbook = xlwt.Workbook()
                    sheet = workbook.add_sheet("ATO控制信息")
                    tb_head = ['系统周期', '位置', '速度', 'ATP允许速度', 'ATP命令速度', 'ATO命令速度', 'ATO输出级位', '等效坡度', '预估等效坡度']
                    tb_content = [self.log.cycle, self.log.s, self.log.v_ato, self.log.atp_permit_v, self.log.ceilv,
                                  self.log.cmdv,
                                  self.log.level, self.log.ramp, self.log.adjramp]
                    for i, item in enumerate(tb_head):
                        sheet.write(0, i, item)
                        for j, content in enumerate(tb_content[i]):
                            sheet.write(j + 1, i, int(content))
                    workbook.save(filepath[0])
                    self.statusbar.showMessage(filepath[0] + "成功导出数据！")
                else:
                    pass
            except Exception as err:
                self.statusbar.showMessage(filepath[0] + "导出失败！")

    # 打印函数
    def Log(self, msg=str, fun=str, lino=int):
        if str == type(msg):
            print(msg + ',File:"' + __file__ + '",Line' + str(lino) +
                  ', in' + fun)
        else:
            print(msg)
            print(',File:"' + __file__ + '",Line' + str(lino) + ', in' + fun)

    # 由于pyinstaller不能打包直接打包图片资源的缺陷，QtDesigner自动生成的图标代码实际无法打包，需在目录下放置图标文件夹
    # 所以通过手动生成的qrc文件（QtDesigner也可以，未试验），通过PyRrc5转为py资源文件
    # 使用该函数重复设置来用资源文件内容替代原来自图片的图标，实现pyinstaller的打包图标
    # 图标更新时需要-修改qrc，且修改该函数才能使生成exe与QtDesigner调试一致
    def icon_from_file(self):
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":IconFiles/file.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.fileOpen.setIcon(icon)

        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":IconFiles/close.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.fileClose.setIcon(icon1)

        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":IconFiles/save.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.fileSave.setIcon(icon2)

        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(":IconFiles/quit.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.Exit.setIcon(icon3)

        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap(":IconFiles/version.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionVersion.setIcon(icon4)

        icon5 = QtGui.QIcon()
        icon5.addPixmap(QtGui.QPixmap(":IconFiles/help.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionHelp.setIcon(icon5)

        icon6 = QtGui.QIcon()
        icon6.addPixmap(QtGui.QPixmap(":IconFiles/tag.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionTag.setIcon(icon6)

        icon7 = QtGui.QIcon()
        icon7.addPixmap(QtGui.QPixmap(":IconFiles/view.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionView.setIcon(icon7)

        icon8 = QtGui.QIcon()
        icon8.addPixmap(QtGui.QPixmap(":IconFiles/pan.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionPan.setIcon(icon8)

        icon9 = QtGui.QIcon()
        icon9.addPixmap(QtGui.QPixmap(":IconFiles/zoom.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionZoom.setIcon(icon9)

        icon10 = QtGui.QIcon()
        icon10.addPixmap(QtGui.QPixmap(":IconFiles/config.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionConfig.setIcon(icon10)

        icon11 = QtGui.QIcon()
        icon11.addPixmap(QtGui.QPixmap(":IconFiles/forward.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionFwd.setIcon(icon11)

        icon12 = QtGui.QIcon()
        icon12.addPixmap(QtGui.QPixmap(":IconFiles/back.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionBck.setIcon(icon12)

        icon13 = QtGui.QIcon()
        icon13.addPixmap(QtGui.QPixmap(":IconFiles/edit.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionEdit.setIcon(icon13)

        icon14 = QtGui.QIcon()
        icon14.addPixmap(QtGui.QPixmap(":IconFiles/reset.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionReset.setIcon(icon14)

        icon15 = QtGui.QIcon()
        icon15.addPixmap(QtGui.QPixmap(":IconFiles/home.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionHome.setIcon(icon15)

        icon16 = QtGui.QIcon()
        icon16.addPixmap(QtGui.QPixmap(":IconFiles/print.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.actionPrint.setIcon(icon16)

        icon17 = QtGui.QIcon()
        icon17.addPixmap(QtGui.QPixmap(":IconFiles/vscurve.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionVS.setIcon(icon17)

        icon18 = QtGui.QIcon()
        icon18.addPixmap(QtGui.QPixmap(":IconFiles/cyclecurve.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionCS.setIcon(icon18)

        icon19 = QtGui.QIcon()
        icon19.addPixmap(QtGui.QPixmap(":IconFiles/serset.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionSerSet.setIcon(icon19)

        icon20 = QtGui.QIcon()
        icon20.addPixmap(QtGui.QPixmap(":IconFiles/offline.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionoffline.setIcon(icon20)

        icon21 = QtGui.QIcon()
        icon21.addPixmap(QtGui.QPixmap(":IconFiles/realtime.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionRealtime.setIcon(icon21)

        icon22 = QtGui.QIcon()
        icon22.addPixmap(QtGui.QPixmap(":IconFiles/port.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionMVB.setIcon(icon22)

        icon23 = QtGui.QIcon()
        icon23.addPixmap(QtGui.QPixmap(":IconFiles/UTCParser.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionUTC.setIcon(icon23)

        icon24 = QtGui.QIcon()
        icon24.addPixmap(QtGui.QPixmap(":IconFiles/MVBParser.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionMVBParser.setIcon(icon24)

        icon25 = QtGui.QIcon()
        icon25.addPixmap(QtGui.QPixmap(":IconFiles/realtimeset.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionRealTimePlot.setIcon(icon25)

        icon26 = QtGui.QIcon()
        icon26.addPixmap(QtGui.QPixmap(":IconFiles/track.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.action_bubble_track.setIcon(icon26)

        icon27 = QtGui.QIcon()
        icon27.addPixmap(QtGui.QPixmap(":IconFiles/dock.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.action_bubble_dock.setIcon(icon27)

        icon28 = QtGui.QIcon()
        icon28.addPixmap(QtGui.QPixmap(":IconFiles/acc.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.action_acc_measure.setIcon(icon28)

        icon29 = QtGui.QIcon()
        icon29.addPixmap(QtGui.QPixmap(":IconFiles/export.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionExport.setIcon(icon29)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Mywindow()
    window.show()
    sys.exit(app.exec_())
