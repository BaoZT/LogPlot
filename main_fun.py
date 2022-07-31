#!/usr/bin/env python
# encoding: utf-8
'''
Author: Zhengtang Bao
Contact: baozhengtang@crscd.com.cn
File: main_fun.py
Desc: 本文件功能集成的主框架
LastEditors: Zhengtang Bao
LastEditTime: 2022-07-31 13:49:33
'''

from itertools import cycle
import os
import sys
import threading
import time
import re
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
from MiniWinCollection import MVBPortDlg, SerialDlg, MVBParserDlg, UTCTransferDlg, RealTimePlotDlg, CtrlMeasureDlg, \
    Cyclewindow, TrainComMeasureDlg, C3ATOTransferDlg
from TcmsParse import MVBParse,Ato2TcmsCtrl,Ato2TcmsState,Tcms2AtoState,DisplayMVBField,MVBFieldDic
from MsgParse import Atp2atoParse, Atp2atoProto, Atp2atpFieldDic, DisplayMsgield
from RealTimeExtension import SerialRead, RealPaintWrite
from ConfigInfo import ConfigFile
from MainWinDisplay import BtmInfoDisplay,AtoInfoDisplay


# 主界面类
class Mywindow(QtWidgets.QMainWindow, Ui_MainWindow):
    # 建立的是Main Window项目，故此处导入的是QMainWindow
    def __init__(self):
        super(Mywindow, self).__init__()
        self.setupUi(self)
        self.initUI()
        self.icon_from_file()
        self.ver = '3.1.0' # 标示软件版本
        # 定义界面变量
        self.file = ''
        self.savePath = os.getcwd()   # 实时存储的文件保存路径（文件夹）,增加斜线直接添加文件名即可
        self.savefilename = ''        # 实时存储的写入文件名(含路径)
        self.pathlist = []
        self.BTM_cycle = []           # 存储含有BTM的周期号，用于操作计数器间接索引
        self.curWinMode = 0                 # 默认0是浏览模式，1是标注模式
        self.curInterface = 0         # 当前界面， 1=离线界面，2=在线界面
        self.seriaLinkBtnStatus = 0   # 实时按钮状态信息0=断开,1=连接
        self.isCursorCreated = 0      # 是否创建光标
        self.curveCordType = 1        # 区分绘制曲线类型，0=速度位置曲线，1=周期位置曲线
        self.isCursorInFram = 0       # 区分光标是否在图像内-仅离线模式,初始化为0,in=1，out=2
        self.islogLoad = 0            # 区分是否已经加载文件,1=加载且控车，2=加载但没有控车
        self.serdialog = SerialDlg()  # 串口设置对话框，串口对象，已经实例
        self.serport = serial.Serial(timeout=None)  # 操作串口对象
        self.mvbdialog = MVBPortDlg()
        self.comboBox.addItems(self.serdialog.Port_List())  # 调用对象方法获取串口对象
        self.setWindowTitle('LogPlot-V' + self.ver)
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/BZT.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        # 离线绘图
        l = QtWidgets.QVBoxLayout(self.widget)
        self.sp = Figure_Canvas(self.widget)  # 这是继承FigureCanvas的子类，使用子窗体widget作为父亲类
        self.sp.mpl_toolbar = NavigationToolbar(self.sp, self.widget)  # 传入FigureCanvas类或子类实例，和父窗体
        self.c_vato = None
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
        # ATP解析面板
        self.Atp2atoParserPage = Atp2atoParse()
        # MVB解析器
        self.mvbparaer = MVBParserDlg()
        # UTC转换器
        self.utctransfer = UTCTransferDlg()
        # C3ATO转义工具
        self.C3ATORecordTransfer = C3ATOTransferDlg()
        # 绘图界面设置器
        self.realtime_plot_dlg = RealTimePlotDlg()  # 实时绘图界面设置
        self.realtime_plot_interval = 0.1  # 默认0.1s绘图
        self.is_realtime_paint = False  # 实时绘图否
        self.realtime_plot_dlg.realtime_plot_set_signal.connect(self.realtime_plot_set)
        # 实时btm和io
        self.real_io_in_list = []
        self.real_io_out_list = []
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
        self.actionHelp.triggered.connect(self.help_msg)
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
        self.actionC3ATOTrans.triggered.connect(self.C3ATORecordTransfer.show)
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
        self.tableATPBTM.itemDoubleClicked.connect(self.BTM_selected_cursor_go)
        self.tb_ato_IN.horizontalHeader().setVisible(True)
     
        self.cfg = ConfigFile()

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
        self.cfg = ConfigFile()
        self.cfg.readConfigFile()

        self.show()

    # 事件处理函数，打开文件读取并初始化界面
    def showDialog(self):
        temp = '/'

        if len(self.pathlist) == 0:
            filepath = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', 'c:/', "txt files(*.txt *.log)")
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
        self.curInterface = 2
        self.stackedWidget.setCurrentWidget(self.page_4)
        self.stackedWidget_RightCol.setCurrentWidget(self.stackedWidgetPage1)
        self.fileOpen.setDisabled(True)  # 设置文件读取不可用
        self.btn_filetab.setDisabled(True)
        # 初始化绘图
        self.CBvato.setChecked(True)
        self.CBacc.setChecked(True)
        self.CBatpcmdv.setChecked(True)
        self.CBlevel.setChecked(True)
        self.CBcmdv.setChecked(True)
        self.CBvato.setChecked(True)
        # 解绑
        self.CBvato.stateChanged.disconnect(self.update_up_cure)
        self.CBatpcmdv.stateChanged.disconnect(self.update_up_cure)
        self.CBlevel.stateChanged.disconnect(self.update_up_cure)
        self.CBcmdv.stateChanged.disconnect(self.update_up_cure)
        self.CBacc.stateChanged.disconnect(self.update_down_cure)
        self.CBramp.stateChanged.disconnect(self.update_down_cure)
        self.CBatppmtv.stateChanged.disconnect(self.update_up_cure)

        # 如有转换重置右边列表
        self.actionView.trigger()
        self.tableWidget.clear()
        self.set_table_format()
        self.treeWidget.clear()
        self.tableWidgetPlan.clear()
        self.set_tree_fromat()
        self.tb_ato_IN.clear()
        self.tb_ato_OUT.clear()
        self.tb_ato_IN.setHorizontalHeaderLabels(['时间', '周期', '采集信号', '取值'])
        self.tb_ato_IN.setColumnCount(4)
        self.tb_ato_OUT.setHorizontalHeaderLabels(['时间', '周期', '输出信号'])
        self.tb_ato_OUT.setColumnCount(3)
        # 初始化表格
        BtmInfoDisplay.displayInitClear(self.tableATPBTM)
        self.real_io_out_list=[]
        self.real_io_in_list=[]

    # 显示离线界面
    def showOffLineUI(self):
        self.curInterface = 1
        self.stackedWidget.setCurrentWidget(self.page_3)
        self.fileOpen.setEnabled(True)  # 设置文件读取可用
        self.stackedWidget_RightCol.setCurrentWidget(self.stackedWidgetPage1)
        self.btn_plan.setEnabled(True)
        self.btn_train.setEnabled(True)
        self.btn_atp.setEnabled(True)
        self.btn_filetab.setEnabled(True)
        self.CBvato.stateChanged.connect(self.update_up_cure)
        self.CBatpcmdv.stateChanged.connect(self.update_up_cure)
        self.CBlevel.stateChanged.connect(self.update_up_cure)
        self.CBcmdv.stateChanged.connect(self.update_up_cure)
        self.CBacc.stateChanged.connect(self.update_down_cure)
        self.CBramp.stateChanged.connect(self.update_down_cure)
        self.CBatppmtv.stateChanged.connect(self.update_up_cure)

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
        if self.seriaLinkBtnStatus == 0:
            RealTimeExtension.exit_flag = 0
            self.seriaLinkBtnStatus = 1
            self.actionoffline.setEnabled(False)
            self.btn_PortLink.setText('断开')
            self.btn_PortLink.setStyleSheet("background: rgb(191, 255, 191);")
            tmpfilename = self.serdialog.filenameLine.text()
            self.update_mvb_port_pat()  # 更新解析用的端口号
            # 按照默认设置，设置并打开串口
            self.serdialog.OpenButton.click()
            self.serport.port = self.comboBox.currentText()
            # 当串口没有打开过
            ser_is_open = 1   # 测试时打开
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
                thPaintWrite.pat_show_signal.connect(self.realtime_content_show)  # 界面显示处理
                thPaintWrite.plan_show_signal.connect(self.realtime_plan_show)  # 局部变量无需考虑后续解绑
                #thPaintWrite.sp7_show_signal.connect(self.realtime_btm_show)  # 应答器更新
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
                self.seriaLinkBtnStatus = 0
                self.actionoffline.setEnabled(True)
                RealTimeExtension.exit_flag = 1
                self.reatimelbl_defaultshow()
                self.btn_PortLink.setText('连接')
                self.btn_PortLink.setStyleSheet(" background: rgb(238, 86, 63);")

        else:
            self.seriaLinkBtnStatus = 0
            self.actionoffline.setEnabled(True)
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
                self.sp_real.show()
                time.sleep(self.realtime_plot_interval)  # 绘图线程非常消耗性能，当小于1s直接影响读取和写入
                self.sp_real.realTimePlot()
            except Exception as err:
                self.Log(err, __name__, sys._getframe().f_lineno)
                self.show_message('Error:绘图线程异常！')
                print('thread paint info!' + str(time.time()))
        self.show_message('Info:绘图线程结束!')

    # 界面更新信号槽函数
    def realtime_content_show(self, result="tuple"):
        cycle_num       = result[0]
        cycle_time      = result[1]
        fsm_list        = result[2]
        sc_ctrl         = result[3]
        stoppoint       = result[4]
        ato2tcms_ctrl   = result[5]
        ato2tcms_stat   = result[6]
        tcms2ato_stat   = result[7]
        atp2ato_msg     = result[8]
        time_statictics = result[9]
        # 显示到侧面
        self.realtime_table_show(cycle_num, cycle_time, sc_ctrl, stoppoint)
        self.atoFsmInfoShow(fsm_list,sc_ctrl,atp2ato_msg,tcms2ato_stat)
        # 显示主界面
        self.mvbShowByData(ato2tcms_ctrl, ato2tcms_stat, tcms2ato_stat)
        self.atpCommonInfoShowByMsg(atp2ato_msg)
        self.atoDmiShowByMsg(atp2ato_msg)
        self.atpTrainDataShowByMsg(atp2ato_msg)
        self.atpBtmShowByMsg(cycle_time, atp2ato_msg)
        self.atoCyleTimeStatistics(time_statictics)

    # 显示时间统计信息
    def atoCyleTimeStatistics(self,time_statictics):
        if time_statictics:
            self.lbl_mean_slot_rtn.setText(str(round(time_statictics[0],1))+'ms')
            self.lbl_max_slot_rtn.setText(str(time_statictics[1])+'ms')
            self.lbl_max_slot_cycle_rtn.setText(str(time_statictics[2]))
            self.lbl_min_slot_rtn.setText(str(time_statictics[3])+'ms')
            self.lbl_slot_count_rtn.setText(str(time_statictics[4]))

    # 显示ATP通用信息SP2
    def atpCommonInfoShowByMsg(self, msg_obj=Atp2atoProto):
        if msg_obj and msg_obj.sp2_obj.updateflag:
            # 门允许左右门合并
            DisplayMsgield.disAtpDoorPmt(msg_obj.sp2_obj.q_leftdoorpermit,msg_obj.sp2_obj.q_rightdoorpermit, self.lbl_door_pmt)
            DisplayMsgield.disNameOfLable("q_stopstatus", msg_obj.sp2_obj.q_stopstatus, self.lbl_atp_stop_ok, 2)
            DisplayMsgield.disTsmStat(msg_obj.sp2_obj.d_tsm, self.lbl_tsm)
            DisplayMsgield.disNameOfLable("m_tco_state", msg_obj.sp2_obj.m_tco_state, self.lbl_atp_cut_traction,2,1)
            DisplayMsgield.disNameOfLable("reserve", msg_obj.sp2_obj.reserve, self.lbl_atp_brake,2,1)
            DisplayMsgield.disNameOfLable("q_tb", msg_obj.sp2_obj.q_tb, self.lbl_tb)
            DisplayMsgield.disNameOfLable("m_level", msg_obj.sp2_obj.m_level, self.lbl_atp_level)
            DisplayMsgield.disAtpMode("m_mode",msg_obj.sp2_obj.m_level,msg_obj.sp2_obj.m_mode,self.lbl_atp_mode)
            DisplayMsgield.disNameOfLineEdit("m_position",msg_obj.sp2_obj.m_position, self.led_atp_milestone)
            DisplayMsgield.disNameOfLineEdit("d_station_mid_pos",msg_obj.sp2_obj.d_station_mid_pos, self.led_stn_center_dis)
            DisplayMsgield.disNameOfLineEdit("d_jz_sig_pos",msg_obj.sp2_obj.d_jz_sig_pos, self.led_jz_signal_dis)
            DisplayMsgield.disNameOfLineEdit("d_cz_sig_pos",msg_obj.sp2_obj.d_cz_sig_pos, self.led_cz_signal_dis)
            DisplayMsgield.disNameOfLineEdit("d_tsm",msg_obj.sp2_obj.d_tsm, self.led_atp_tsm_dis)
            DisplayMsgield.disNameOfLineEdit("d_target",msg_obj.sp2_obj.d_target, self.led_atp_target_dis)
            DisplayMsgield.disNameOfLineEdit("v_target",msg_obj.sp2_obj.v_target, self.led_atp_target_v)
            DisplayMsgield.disNameOfLineEdit("d_neu_sec",msg_obj.sp2_obj.d_neu_sec, self.led_atp_gfx_dis)
            DisplayMsgield.disNameOfLineEdit("d_ma",msg_obj.sp2_obj.d_ma, self.led_atp_ma)
            DisplayMsgield.disNameOfLineEdit("m_atp_stop_error",msg_obj.sp2_obj.m_atp_stop_error, self.led_atp_stoperr)

    # 显示列车数据内容SP5
    def atpTrainDataShowByMsg(self, msg_obj=Atp2atoProto):
        if msg_obj and msg_obj.sp5_obj.updateflag:
            obj = msg_obj.sp5_obj
            DisplayMsgield.disNameOfLineEdit("n_units",obj.n_units,self.led_units)
            DisplayMsgield.disNameOfLineEdit("v_ato_permitted",obj.v_ato_permitted,self.led_driver_strategy)
            DisplayMsgield.disNameOfLineEdit("btm_antenna_position",obj.btm_antenna_position,self.led_atp_btm_pos)
            DisplayMsgield.disNameOfLineEdit("l_door_distance",obj.l_door_distance,self.led_head_foor_dis)
            DisplayMsgield.disNameOfLineEdit("nid_engine",obj.nid_engine,self.led_nid_engine)

    # ATO图标实时显示SP131
    def atoDmiShowByMsg(self, msg_obj=Atp2atoProto):
        if msg_obj and msg_obj.sp131_obj.updateflag:
            obj = msg_obj.sp131_obj
            DisplayMsgield.disNameOfLable("m_tcms_com",obj.m_tcms_com,self.lbl_mvb_link,1,2)
            DisplayMsgield.disNameOfLable("m_gprs_radio",obj.m_gprs_radio,self.lbl_ato_radio,1,0)
            DisplayMsgield.disNameOfLable("m_gprs_session",obj.m_gprs_session,self.lbl_ato_session,3,1)
            # 计划与策略混合显示
            if msg_obj.sp131_obj.m_ato_plan == 1:
                DisplayMsgield.disNameOfLable("m_ato_plan",obj.m_ato_plan,self.lbl_ato_ctrl_stat,1,2)
            else:
                DisplayMsgield.disNameOfLable("m_ato_control_strategy",obj.m_ato_control_strategy,self.lbl_ato_ctrl_stat)
                
    # 显示MVB数据
    def mvbShowByData(self, a2t_ctrl=Ato2TcmsCtrl, a2t_stat=Ato2TcmsState, t2a_stat=Tcms2AtoState):
        if a2t_ctrl and a2t_ctrl.updateflag == True:
            DisplayMVBField.disNameOfLineEdit("ato_heartbeat",a2t_ctrl.ato_heartbeat,self.led_ctrl_hrt)
            DisplayMVBField.disNameOfLineEdit("ato_valid",a2t_ctrl.ato_valid,self.led_ctrl_atovalid)
            DisplayMVBField.disNameOfLineEdit("track_brake_cmd",a2t_ctrl.track_brake_cmd,self.led_ctrl_tbstat)
            DisplayMVBField.disNameOfLineEdit("track_value",a2t_ctrl.track_value,self.led_ctrl_tract)
            DisplayMVBField.disNameOfLineEdit("brake_value",a2t_ctrl.brake_value,self.led_ctrl_brake)
            DisplayMVBField.disNameOfLineEdit("keep_brake_on",a2t_ctrl.keep_brake_on,self.led_ctrl_keepbrake)
            DisplayMVBField.disNameOfLineEdit("open_left_door",a2t_ctrl.open_left_door,self.led_ctrl_ldoor)
            DisplayMVBField.disNameOfLineEdit("open_right_door",a2t_ctrl.open_right_door,self.led_ctrl_rdoor)
            DisplayMVBField.disNameOfLineEdit("const_speed_cmd",a2t_ctrl.const_speed_cmd,self.led_ctrl_costspeed)
            DisplayMVBField.disNameOfLineEdit("const_speed_value",a2t_ctrl.const_speed_value,self.led_ctrl_aimspeed)
            DisplayMVBField.disNameOfLineEdit("ato_start_light",a2t_ctrl.ato_start_light,self.led_ctrl_starlamp)
            a2t_ctrl.updateflag = False
        elif a2t_stat and a2t_stat.updateflag == True:
            DisplayMVBField.disNameOfLineEdit("ato_heartbeat", a2t_stat.ato_heartbeat,self.led_stat_hrt)
            DisplayMVBField.disNameOfLineEdit("ato_error", a2t_stat.ato_error,self.led_stat_error)
            DisplayMVBField.disNameOfLineEdit("killometer_marker", a2t_stat.killometer_marker,self.led_stat_stonemile)
            DisplayMVBField.disNameOfLineEdit("tunnel_entrance", a2t_stat.tunnel_entrance,self.led_stat_tunnelin)
            DisplayMVBField.disNameOfLineEdit("tunnel_length", a2t_stat.tunnel_length,self.led_stat_tunnellen)
            DisplayMVBField.disNameOfLineEdit("ato_speed", a2t_stat.ato_speed,self.led_stat_atospeed)
            a2t_stat.updateflag = False
        elif t2a_stat and t2a_stat.updateflag == True:
            DisplayMVBField.disNameOfLineEdit("tcms_heartbeat", t2a_stat.tcms_heartbeat, self.led_tcms_hrt)
            DisplayMVBField.disNameOfLineEdit("door_mode_mo_mc", t2a_stat.door_mode_mo_mc, self.led_tcms_mm)
            DisplayMVBField.disNameOfLineEdit("door_mode_ao_mc", t2a_stat.door_mode_ao_mc, self.led_tcms_am)
            DisplayMVBField.disNameOfLineEdit("ato_start_btn_valid", t2a_stat.ato_start_btn_valid, self.led_tcms_startlampfbk)
            DisplayMVBField.disNameOfLineEdit("ato_valid_feedback", t2a_stat.ato_valid_feedback, self.led_tcms_atovalid_fbk)
            DisplayMVBField.disNameOfLineEdit("track_brack_cmd_feedback", t2a_stat.track_brack_cmd_feedback, self.led_tcms_fbk)
            DisplayMVBField.disNameOfLineEdit("track_value_feedback", t2a_stat.track_value_feedback, self.led_tcms_tractfbk)
            DisplayMVBField.disNameOfLineEdit("brake_value_feedback", t2a_stat.brake_value_feedback, self.led_tcms_bfbk)
            DisplayMVBField.disNameOfLineEdit("ato_keep_brake_on_feedback", t2a_stat.ato_keep_brake_on_feedback, self.led_tcms_keepbfbk)
            DisplayMVBField.disNameOfLineEdit("open_left_door_feedback", t2a_stat.open_left_door_feedback, self.led_tcms_ldoorfbk)
            DisplayMVBField.disNameOfLineEdit("open_right_door_feedback", t2a_stat.open_right_door_feedback, self.led_tcms_rdoorfbk)
            DisplayMVBField.disNameOfLineEdit("constant_state_feedback", t2a_stat.constant_state_feedback, self.led_tcms_costspeedfbk)
            DisplayMVBField.disNameOfLineEdit("door_state", t2a_stat.door_state, self.led_tcms_doorstat)
            DisplayMVBField.disNameOfLineEdit("spin_state", t2a_stat.spin_state, self.led_tcms_kz)
            DisplayMVBField.disNameOfLineEdit("slip_state", t2a_stat.slip_state, self.led_tcms_dh)
            DisplayMVBField.disNameOfLineEdit("train_unit", t2a_stat.train_unit, self.led_tcms_nunits)
            DisplayMVBField.disNameOfLineEdit("train_weight", t2a_stat.train_weight, self.led_tcms_weight)
            DisplayMVBField.disNameOfLineEdit("train_permit_ato", t2a_stat.train_permit_ato, self.led_tcms_pm)
            DisplayMVBField.disNameOfLineEdit("main_circuit_breaker", t2a_stat.main_circuit_breaker, self.led_tcms_breakstat)
            DisplayMVBField.disNameOfLineEdit("atp_door_permit", t2a_stat.atp_door_permit, self.led_tcms_atpdoorpm)
            DisplayMVBField.disNameOfLineEdit("man_door_permit", t2a_stat.man_door_permit, self.led_tcms_mandoorpm)
            DisplayMVBField.disNameOfLineEdit("no_permit_ato_state", t2a_stat.no_permit_ato_state, self.led_tcms_pmt_state)
            t2a_stat.updateflag = False
        else:
            pass
    
    # 右侧边栏显示
    def realtime_table_show(self, cycle_num=str, cycle_time=str, sc_ctrl="list", stoppoint="list"):
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

    # 更新FSM信息相关
    def atoFsmInfoShow(self, fsm='list', ctrl='tuple', msg_obj=Atp2atoProto,t2a_stat=Tcms2AtoState):
        # 显示ATP2ATO接口协议内容
        if msg_obj:
            if  msg_obj.sp2_obj.updateflag:
                AtoInfoDisplay.lableFieldDisplay("q_ato_hardpermit",msg_obj.sp2_obj.q_ato_hardpermit, Atp2atpFieldDic, self.lbl_hpm)
                AtoInfoDisplay.lableFieldDisplay("q_atopermit",msg_obj.sp2_obj.q_atopermit, Atp2atpFieldDic, self.lbl_pm)
                AtoInfoDisplay.lableFieldDisplay("m_ms_cmd",msg_obj.sp2_obj.m_ms_cmd, Atp2atpFieldDic, self.lbl_atpdcmd)
                AtoInfoDisplay.lableFieldDisplay("m_low_frequency",msg_obj.sp2_obj.m_low_frequency, Atp2atpFieldDic, self.lbl_freq)
            if msg_obj.sp5_obj.updateflag:
                AtoInfoDisplay.lableFieldDisplay("n_units",msg_obj.sp5_obj.n_units, Atp2atpFieldDic, self.lbl_trainlen)
            if msg_obj.sp130_obj.updateflag:
                AtoInfoDisplay.lableFieldDisplay("m_atomode",msg_obj.sp130_obj.m_atomode, Atp2atpFieldDic, self.lbl_mode)
                # 显示MVB接口协议内容
        if t2a_stat and t2a_stat.updateflag:
            AtoInfoDisplay.lableFieldDisplay("train_permit_ato",t2a_stat.train_permit_ato, MVBFieldDic, self.lbl_carpm)
            AtoInfoDisplay.lableFieldDisplay("door_state",t2a_stat.door_state, MVBFieldDic, self.lbl_doorstatus)
            AtoInfoDisplay.lableFieldDisplay("main_circuit_breaker",t2a_stat.main_circuit_breaker, MVBFieldDic, self.lbl_dcmd)
        # 软件内部状态通过打印
        if fsm:
            AtoInfoDisplay.labelInterDisplay("ato_self_check", int(fsm[5]), self.lbl_check)
            AtoInfoDisplay.labelInterDisplay("ato_start_lamp", int(fsm[6]), self.lbl_lamp)
            # 站台标志由于FSM中记录后会经过处理，采用SC才是本周期控车使用的
            if ctrl:  # 按周期索引取控制信息，妨不连续
                AtoInfoDisplay.labelInterDisplay("station_flag", int(list(ctrl)[17]), self.lbl_stn)

    # 实时操作时更新曲线选择
    def realtimeLineChoose(self):

        linelist = [0, 0, 0, 0, 0]
        if self.islogLoad == 0:
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
    def atpBtmShowByMsg(self, time=str, msg_obj=Atp2atoProto):
        BtmInfoDisplay.displayRealTimeBtmTable(msg_obj, time, self.tableATPBTM)

    # 显示IO表格
    def realtime_io_show(self, ret_io="tuple"):
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
    def realtime_sdu_show(self, ret_sdu="tuple"):
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
                if (ato_v - atp_v) < -self.cfg.monitor_config.sdu_spd_fault_th: # 若偏低
                    self.lbl_sdu_judge.setText("ATO速度偏低")
                    self.lbl_sdu_judge.setStyleSheet("background-color: rgb(255, 255, 0);")
                elif(ato_v - atp_v) > self.cfg.monitor_config.sdu_spd_fault_th: # 若偏高
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
                if ((ato_s - self.sdu_info_s[0]) - (atp_s - self.sdu_info_s[1])) < -self.cfg.monitor_config.sdu_dis_fault_th:  # 若偏低
                    self.lbl_sdu_s_judge.setText("ATO测距偏低")
                    self.lbl_sdu_s_judge.setStyleSheet("background-color: rgb(255, 255, 0);")
                elif((ato_s - self.sdu_info_s[0]) - (atp_s - self.sdu_info_s[1])) > self.cfg.monitor_config.sdu_dis_fault_th: # 若偏高
                    self.lbl_sdu_s_judge.setText("ATO测距偏高")
                    self.lbl_sdu_s_judge.setStyleSheet("background-color: rgb(255, 0, 0);")
                else:
                    self.lbl_sdu_s_judge.setText("测距速度一致")
                    self.lbl_sdu_s_judge.setStyleSheet("background-color: rgb(170, 170, 255);")
                # 记录刷新
                self.sdu_info_s[0] = ato_s
                self.sdu_info_s[1] = atp_s

    # 显示计划信息
    def realtime_plan_show(self, ret_plan="tuple"):
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
        self.cfg.readConfigFile()

    # MVB解析器
    def show_mvb_parser(self):
        self.mvbparaer.show()

    # utc转换器
    def show_utc_transfer(self):
        self.utctransfer.show()

    # 事件处理函数绘制统计区域的 车辆牵引制动统计图
    def show_statistics_mvb_delay(self):
        if self.islogLoad == 1:
            self.train_com_delay = TrainComMeasureDlg(None, self.log)
            self.Log('Plot statistics info!', __name__, sys._getframe().f_lineno)
            try:
                self.train_com_delay.measure_plot()
                self.train_com_delay.show()
            except Exception as err:
                self.Log(err, __name__, sys._getframe().f_lineno)

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

    # 默认路径的更新，用于打开文件时，总打开最近一次的文件路径
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
                                                  "License  :(C) Copyright 2017-2020, Author Limited.\n"
                                                   "Contact :baozhengtang@crscd.com",
                                                  QtWidgets.QMessageBox.Yes)

    # 事件处理函数，弹窗显示帮助信息
    def help_msg(self):
        reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                                                "帮助信息-2020/02/02",
                                                "Software:LogPlot-V" + str(self.ver) + " 版本的改进有：\n"
                                                "1.重构文件读取和处理机制，加载速度大幅提升减少内存占用\n"
                                                "2.优化了曲线显示和绘图机制，提高绘图响应速度\n"
                                                "3.显示站台范围和过分相范围，应答器单击显示，双击跳转\n"
                                                "4.优化了曲线范围计算机制，修复了之前跳转出框的缺陷"
                                                "5.C3ATO记录板转义功能已实现，支撑单文件、多文件及路径翻译",
                                                  QtWidgets.QMessageBox.Yes)

    # 记录文件处理核心函数，生成周期字典和绘图值列表
    def log_process(self):
        self.isCursorInFram = 0
        # 创建文件读取对象
        self.log = FileProcess.FileProcess(self.file)  # 类的构造函数，函数中给出属性
        # 绑定信号量
        self.log.bar_show_signal.connect(self.progressBar.setValue)
        self.log.end_result_signal.connect(self.log_process_result)
        # 读取文件
        self.Log('Preprocess file path!', __name__, sys._getframe().f_lineno)
        self.log.start()  # 启动记录读取线程,run函数不能有返回值
        self.Log('Begin log read thread!', __name__, sys._getframe().f_lineno)
        self.show_message('文件加载中...')
        return

    # 文件处理线程执行完响应方法
    def log_process_result(self):
        self.Log('End log read thread!', __name__, sys._getframe().f_lineno)
        isok = -1
        # 处理返回结果
        if self.log.get_time_use():
            [t1, t2, isok] = self.log.get_time_use()     # 0=ato控车，1=没有控车,2=没有周期
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

        self.Log("End all file process", __name__, sys._getframe().f_lineno)
        try:
            if is_ato_control == 0:
                self.islogLoad = 1  # 记录加载且ATO控车
                self.actionRealtime.setEnabled(False)
                # self.actionView.trigger()  # 目前无效果，待完善，目的 用于加载后重置坐标轴
                self.show_message('界面准备中...')
                self.clear_axis()
                self.win_init_log_processed()  # 记录加载成功且有控车时，初始化显示一些内容
                self.CBvato.setChecked(True)
                self.Log('Set View mode and choose Vato', __name__, sys._getframe().f_lineno)
            elif is_ato_control == 1:
                self.islogLoad = 2  # 记录加载但是ATO没有控车
                reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                                                          "无曲线",
                                                          "注意:记录中ATO没有控车！ATO处于非AOM和AOR模式!",
                                                          QtWidgets.QMessageBox.Yes)
            elif is_ato_control == 2:
                self.islogLoad = 0  # 记录加载但是没有检测到周期
                self.actionRealtime.setEnabled(True)
            elif is_ato_control == -1:
                self.islogLoad = 0  # 记录加载但是没有检测到周期
                self.actionRealtime.setEnabled(True)
                reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                                                          "解析错误",
                                                          "注意: 遇到未知解析错误导致中断，请将记录发送开发人员进行诊断定位!",
                                                          QtWidgets.QMessageBox.Yes)
            else:
                reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                                                          "待处理",
                                                          "注意:记录中包含ATO重新上下电过程，列车绝对位置重叠"
                                                          "需手动分解记录！\nATO记录启机行号:Line：" + str(is_ato_control),
                                                          QtWidgets.QMessageBox.Yes)

        except Exception as err:
            self.textEdit.setPlainText(' Error Line ' + str(err.start) + ':' + err.reason + '\n')
            self.textEdit.append('Process file failure! \nPlease Predeal the file!')

    # 用于一些界面加载记录初始化后显示的内容,如数据包一次显示
    def win_init_log_processed(self):
        self.Log("Begin search log key info", __name__, sys._getframe().f_lineno)
        trainDataFind = False
        bar = 95
        cnt = 0
        bar_cnt = int(len(self.log.cycle_dic.keys()) / 5)  # 从95%开始，界面准备占比5%
        for cycle_num in self.log.cycle_dic.keys():
            # 计算进度条
            cnt = cnt + 1
            if int(cnt % bar_cnt) == 0:
                bar = bar + 1
                self.progressBar.setValue(bar)
            else:
                pass
            # 预先设置 设置列车数据
            msg_atp2ato = self.log.cycle_dic[cycle_num].msg_atp2ato
            if (not trainDataFind) and msg_atp2ato.sp5_obj.updateflag:
                self.atpTrainDataShowByMsg(self.log.cycle_dic[cycle_num].msg_atp2ato)
                AtoInfoDisplay.lableFieldDisplay("n_units",msg_atp2ato.sp5_obj.n_units, Atp2atpFieldDic, self.lbl_trainlen)
                trainDataFind = True

        BtmInfoDisplay.displayOffLineBtmTable(self.log.cycle_dic, self.tableATPBTM)
        # 显示IO信息
        self.Log("Begin search IO info", __name__, sys._getframe().f_lineno)
        self.set_io_page_content()
        try:
            # 事件发生相关
            if self.islogLoad == 1:
                self.sp.set_wayside_info_in_cords(self.log.cycle_dic, self.log.s, self.log.cycle)
                if self.actionJD.isChecked():
                    self.update_event_point()    # 若已经选中直接更新
                else:
                    self.actionJD.trigger()
                # 如果没选中 trigger一下
                if self.actionBTM.isChecked():
                    self.update_event_point()    # 若已经选中直接更新
                else:
                    self.actionBTM.trigger()
                self.Log("Comput wayside info and trigger BTM event", __name__, sys._getframe().f_lineno)
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
        xy_lim = []
        track_flag = self.sp.get_track_status()  # 获取之前光标的锁定状态

        # 光标离开图像
        if self.isCursorInFram == 2 and self.curInterface == 1:
            cur_cycle = self.spinBox.value()  # 获取当前周期值

            if cur_cycle in self.log.cycle_dic.keys():
                c = self.log.cycle_dic[cur_cycle]  # 查询周期字典
                # 该周期没有控制信息，或打印丢失,不发送光标移动信号
                if c.control != () and self.isCursorCreated == 1:
                    info = list(c.control)
                    if self.curveCordType == 0:
                        # 先更新坐标轴范围（索引0和1是位置速度）
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
                    elif self.curveCordType == 1:
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
        # 加载文件才能测量
        if self.islogLoad == 1:
            self.ctrl_measure_status = 1  # 一旦单击则进入测量开始状态
            self.sp.setCursor(QtCore.Qt.WhatsThisCursor)
            self.Log('start measure!', __name__, sys._getframe().f_lineno)
        else:
            self.show_message("Info:记录未加载，不测量")

    # 事件处理函数，标记单击事件
    def ctrl_measure_clicked(self, event):
        # 如果开始测量则进入，则获取终点
        if self.ctrl_measure_status == 2:
            # 下面是当前鼠标坐标
            x, y = event.xdata, event.ydata
            # 速度位置曲线
            if self.curveCordType == 0:
                self.indx_measure_end = min(np.searchsorted(self.log.s, [x])[0], len(self.log.s) - 1)
            # 周期速度曲线
            if self.curveCordType == 1:
                self.indx_measure_end = min(np.searchsorted(self.log.cycle, [x])[0], len(self.log.cycle) - 1)
            self.measure = CtrlMeasureDlg(None, self.log)
            self.measure.measure_plot(self.indx_measure_start, self.indx_measure_end, self.curveCordType)
            self.measure.show()

            # 获取终点索引，测量结束
            self.ctrl_measure_status = 3
            self.Log('end measure!', __name__, sys._getframe().f_lineno)
            # 更改图标
            if self.curWinMode == 1:  # 标记模式
                self.sp.setCursor(QtCore.Qt.PointingHandCursor)  # 如果对象直接self.那么在图像上光标就不变，面向对象操作
            elif self.curWinMode == 0:  # 浏览模式
                self.sp.setCursor(QtCore.Qt.ArrowCursor)

        # 如果是初始状态，则设置为启动
        if self.ctrl_measure_status == 1:
            self.Log('begin measure!', __name__, sys._getframe().f_lineno)
            # 下面是当前鼠标坐标
            x, y = event.xdata, event.ydata
            # 速度位置曲线
            if self.curveCordType == 0:
                self.indx_measure_start = min(np.searchsorted(self.log.s, [x])[0], len(self.log.s) - 1)
                self.ctrl_measure_status = 2
            # 周期速度曲线
            if self.curveCordType == 1:
                self.indx_measure_start = min(np.searchsorted(self.log.cycle, [x])[0], len(self.log.cycle) - 1)
                self.ctrl_measure_status = 2

    # 事件处理函数，更新光标进入图像标志，in=1
    def cursor_in_fig(self, event):
        self.isCursorInFram = 1
        self.c_vato.move_signal.connect(self.set_table_content)  # 进入图后绑定光标触发
        self.Log('connect ' + 'enter figure', __name__, sys._getframe().f_lineno)

    # 事件处理函数，更新光标进入图像标志,out=2
    def cursor_out_fig(self, event):
        self.isCursorInFram = 2
        try:
            self.c_vato.move_signal.disconnect(self.set_table_content)  # 离开图后解除光标触发
        except Exception as err:
            self.Log(err, __name__, sys._getframe().f_lineno)
        self.Log('disconnect ' + 'leave figure', __name__, sys._getframe().f_lineno)
        # 测量立即终止，恢复初始态:
        if self.ctrl_measure_status > 0:
            self.ctrl_measure_status = 0
            # 更改图标
            if self.curWinMode == 1:  # 标记模式
                self.sp.setCursor(QtCore.Qt.PointingHandCursor)  # 如果对象直接self.那么在图像上光标就不变，面向对象操作
            elif self.curWinMode == 0:  # 浏览模式
                self.sp.setCursor(QtCore.Qt.ArrowCursor)
            self.Log('exit measure', __name__, sys._getframe().f_lineno)

    # 绘制各种速度位置曲线
    def update_up_cure(self):
        # file is load
        if self.islogLoad == 1:
            x_monitor = self.sp.axes1.get_xlim()
            y_monitor = self.sp.axes1.get_ylim()
            if self.CBvato.isChecked() or self.CBcmdv.isChecked() or self.CBatppmtv.isChecked() \
                    or self.CBatpcmdv.isChecked() or self.CBlevel.isChecked():
                self.clear_axis()
                self.Log("Mode Change recreate the paint", __name__, sys._getframe().f_lineno)
                # 清除光标重新创建
                if self.curWinMode == 1:
                    # 重绘文字
                    self.sp.plot_ctrl_text(self.log, self.tag_latest_pos_idx, self.bubble_status, self.curveCordType)
                    self.Log("Update ctrl text ", __name__, sys._getframe().f_lineno)
                    if self.isCursorCreated == 1:
                        self.isCursorCreated = 0
                        del self.c_vato
                    self.tag_cursor_creat()
                    self.Log("Update Curve recreate curve and tag cursor ", __name__, sys._getframe().f_lineno)
                # 处理ATO速度
                if self.CBvato.isChecked():
                    self.sp.plotlog_vs(self.log, self.curWinMode, self.curveCordType)
                else:
                    self.CBvato.setChecked(False)
                # 处理命令速度
                if self.CBcmdv.isChecked():
                    self.sp.plotlog_vcmdv(self.log, self.curWinMode, self.curveCordType)
                else:
                    self.CBcmdv.setChecked(False)
                # 处理允许速度
                if self.CBatppmtv.isChecked():
                    self.sp.plotlog_v_atp_pmt_s(self.log, self.curWinMode, self.curveCordType)
                else:
                    self.CBatppmtv.setChecked(False)
                # 处理顶棚速度
                if self.CBatpcmdv.isChecked():
                    self.sp.plotlog_vceil(self.log, self.curveCordType)
                else:
                    self.CBatpcmdv.setChecked(False)
                # 处理级位
                if self.CBlevel.isChecked():
                    self.sp.plotlog_level(self.log, self.curveCordType)
                else:
                    self.CBlevel.setChecked(False)
            elif self.CBacc.isChecked() or self.CBramp.isChecked():
                self.update_down_cure()  # 当没有选择下图时更新上图
            else:
                self.clear_axis()
            self.sp.plot_cord1(self.log, self.curveCordType, x_monitor, y_monitor)
            self.sp.draw()
        else:
            pass

    # 绘制加速度和坡度曲线
    def update_down_cure(self):
        if self.islogLoad == 1:
            if self.curWinMode == 0:  # 只有浏览模式才可以
                if self.CBacc.isChecked() or self.CBramp.isChecked():
                    self.clear_axis()
                    # 加速度处理
                    if self.CBacc.isChecked():
                        self.sp.plotlog_sa(self.log, self.curveCordType)
                    else:
                        self.CBacc.setChecked(False)
                    # 坡度处理
                    if self.CBramp.isChecked():
                        self.sp.plotlog_ramp(self.log, self.curveCordType)
                    else:
                        self.CBramp.setChecked(False)
                elif self.CBvato.isChecked() or self.CBcmdv.isChecked() or self.CBatppmtv.isChecked() \
                        or self.CBatpcmdv.isChecked() or self.CBlevel.isChecked():
                    # 图形切换时，先重置轴范围再画图
                    self.sp.plot_cord1(self.log, self.curveCordType, (0.0, 1.0), (0.0, 1.0))
                    self.update_up_cure()  # 当没有选择下图时更新上图
                else:
                    self.clear_axis()
                self.sp.plot_cord2(self.log, self.curveCordType)  # 绘制坐标系II
                self.sp.draw()
            else:
                pass
        else:
            pass

    # 绘制离线模式下事件选择点
    def update_event_point(self):
        event_dict = {}

        # 记录显示应答器事件
        if self.actionBTM.isChecked():
            event_dict['BTM'] = 1
            self.Log('BTM choosed ！', __name__, sys._getframe().f_lineno)
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

        # 如果文件加载成功，传递数据字典和选择信息（必须加载后才能调用）
        if self.islogLoad == 1:
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
        sender = self.sender()
        # 查看信号发送者
        if sender.text() == '标注模式' and self.curWinMode == 0:  # 由浏览模式进入标注模式不重绘范围
            self.curWinMode = 1
            if self.islogLoad == 1 and self.CBvato.isChecked():
                self.Log("Mode Change excute!", __name__, sys._getframe().f_lineno)
                self.update_up_cure()
                self.tag_cursor_creat()  # 只针对速度曲线
        elif sender.text() == '浏览模式' and self.curWinMode == 1:  # 进入浏览模式重绘
            self.curWinMode = 0
            if self.islogLoad == 1:
                self.update_up_cure()
                # 重置坐标轴范围,恢复浏览模式必须重置范围
                self.sp.plot_cord1(self.log, self.curveCordType, (0.0, 1.0), (0.0, 1.0))
            self.tag_cursor_creat()
        else:
            pass
            # 其他情况目前无需重置坐标系
        self.sp.draw()
        # 更改图标
        if self.curWinMode == 1:  # 标记模式
            self.sp.setCursor(QtCore.Qt.PointingHandCursor)  # 如果对象直接self.那么在图像上光标就不变，面向对象操作
        elif self.curWinMode == 0:  # 浏览模式
            self.sp.setCursor(QtCore.Qt.ArrowCursor)
        self.statusbar.showMessage(self.file + " " + "当前模式：" + sender.text())

    # 曲线类型转换函数，修改全局模式变量
    def cmd_change(self):

        if self.islogLoad == 1:
            sender = self.sender()
            if sender.text() == '位置速度曲线':
                if self.curveCordType == 1:
                    self.curveCordType = 0  # 曲线类型改变，如果有光标则删除，并重置标志
                    if self.isCursorCreated == 1:
                        del self.c_vato
                        self.isCursorCreated = 0
                    else:
                        pass
                    self.update_up_cure()
                    self.tag_cursor_creat()  # 根据需要重新创建光标
                else:
                    pass
            if sender.text() == "周期速度曲线":
                if self.curveCordType == 0:
                    self.curveCordType = 1  # 曲线类型改变
                    if self.isCursorCreated == 1:
                        del self.c_vato
                        self.isCursorCreated = 0
                    else:
                        pass
                    self.update_up_cure()
                    self.tag_cursor_creat()
                else:
                    pass
            # 重置坐标轴范围
            self.sp.plot_cord1(self.log, self.curveCordType, (0.0, 1.0), (0.0, 1.0))
            self.sp.draw()
            self.statusbar.showMessage(self.file + " " + "曲线类型：" + sender.text())
        else:
            pass

    # 用于模式转换后处理，创建光标绑定和解绑槽函数
    def tag_cursor_creat(self):
        # 标注模式
        if self.curWinMode == 1 and 0 == self.isCursorCreated:
            if self.curveCordType == 0:
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
            self.isCursorCreated = 1
            self.Log("Mode changed Create tag cursor ", __name__, sys._getframe().f_lineno)
        elif self.curWinMode == 0 and 1 == self.isCursorCreated:
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
            self.isCursorCreated = 0
            del self.c_vato
            self.Log("Mode changed clear tag cursor ", __name__, sys._getframe().f_lineno)
        else:
            pass

    # 封装工具栏函数，图形缩放
    def zoom(self):
        self.sp.mpl_toolbar.zoom()
        if self.curWinMode == 1:
            self.sp.setCursor(QtCore.Qt.PointingHandCursor)
        else:
            pass

    # 封装工具栏函数，显示画板初始状态，清除曲线
    def home_show(self):
        self.clear_axis()
        self.reset_all_checkbox()
        self.CBvato.setChecked(True)
        self.reset_text_edit()
        if self.islogLoad == 1:
            self.sp.plot_cord1(self.log, self.curveCordType, (0.0, 1.0), (0.0, 1.0))
            self.update_up_cure()
        else:
            pass

    # 关闭当前绘图
    def close_figure(self, evt):
        if self.islogLoad == 1:
            self.textEdit.append('Close Log Plot\n')
            self.clear_axis()
            self.islogLoad = 0
            self.actionRealtime.setEnabled(True)
            self.sp.draw()
        else:
            pass

    # 事件处理函数，用于弹窗显示当前索引周期
    def cycle_print(self):
        self.cyclewin.statusBar.showMessage('')  # 清除上一次显示内容
        idx = self.spinBox.value()
        print_flag = 0  # 是否弹窗打印，0=不弹窗，1=弹窗
        c_num = 0
        line_count = 0
        pat_cycle_start = re.compile(r'---CORE_TARK CY_B (\d+),(\d+).')  # 周期终点匹配
        self.cyclewin.textEdit.clear()

        if 1 == self.islogLoad or 2 == self.islogLoad:  # 文件已经加载
            # 前提是必须有周期，字典能查到
            if idx in self.log.cycle_dic.keys():
                c_num = self.log.cycle_dic[idx].cycle_num
                with open(self.file, 'rU', encoding='ansi', errors='ignore') as f:  # notepad++默认是ANSI编码
                    f.seek(self.log.cycle_dic[idx].file_begin_offset, 0)
                    lines = f.readline()   # f.read调用f.readline计算的偏移量，实际多读（每行多一个字节），怀疑为python缺陷
                    line_count = line_count + 1
                    while lines:
                        if self.log.cycle_dic[idx].file_end_offset == f.tell():   # 模拟readline读取过程，逻辑保持一致
                            break
                        elif pat_cycle_start.findall(lines.strip().split('\n')[-1]) and line_count > 1:
                            break                     # 当读出最近一行是否是新的周期，若已经读到另一个周期，防护性退出
                        else:
                            lines = lines + f.readline()
                            line_count = line_count + 1
                    self.cyclewin.textEdit.setText(lines)
                # 周期完整性
                if self.log.cycle_dic[idx].cycle_property == 1:
                    self.cyclewin.statusBar.showMessage(str(c_num) + '周期序列完整！')
                elif self.log.cycle_dic[idx].cycle_property == 2:
                    self.cyclewin.statusBar.showMessage(str(c_num) + '周期尾部缺失！')
                elif self.log.cycle_dic[idx].cycle_property == 3:
                    self.cyclewin.statusBar.showMessage(str(c_num) + '周期头部缺失！')
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
                     '精确停车点', '参考停车点', 'MA停车点']
        item_unit = ['cm/s', 'cm/s', 'cm/s', 'cm/s', '-', '-', '-',
                     'cm', 'cm/s', 'cm', 'cm', 'cm', 'cm', 'cm', 'cm',
                     'cm']
        # table name
        self.tableWidget.setRowCount(16)
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
        if stop_list:
            item_value.append(str(int(stop_list[0])))
            item_value.append(str(int(stop_list[1])))
            item_value.append(str(int(stop_list[2])))
        else:
            item_value.append('无')
            item_value.append('无')
            item_value.append('无')
        for idx3, value in enumerate(item_value):
            i_content = QtWidgets.QTableWidgetItem(value)
            i_content.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.label_2.setText(self.log.cycle_dic[self.log.cycle[indx]].time)
        self.spinBox.setValue(int(self.log.cycle_dic[self.log.cycle[indx]].cycle_num))

    # 事件处理函数，设置表格
    def set_table_content(self, indx):
        item_value = []
        stop_list = list(self.log.cycle_dic[self.log.cycle[indx]].stoppoint)
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
        if stop_list:
            item_value.append(str(int(stop_list[0])))
            item_value.append(str(int(stop_list[1])))
            item_value.append(str(int(stop_list[2])))
        else:
            item_value.append('无')
            item_value.append('无')
            item_value.append('无')
        for idx3, value in enumerate(item_value):
            i_content = QtWidgets.QTableWidgetItem(value)
            i_content.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            self.tableWidget.setItem(idx3, 1, i_content)
        self.label_2.setText(self.log.cycle_dic[self.log.cycle[indx]].time)

    # 事件处理函数，用于设置气泡格式，目前只设置位置
    def set_ctrl_bubble_format(self):
        sender = self.sender()
        # 清除光标重新创建
        if self.curWinMode == 1:
            if sender.text() == '跟随光标':
                self.bubble_status = 1  # 1 跟随模式，立即更新
                self.sp.plot_ctrl_text(self.log, self.tag_latest_pos_idx, self.bubble_status, self.curveCordType)
            elif sender.text() == '停靠窗口':
                self.bubble_status = 0  # 0 是停靠，默认右上角，立即更新
                self.sp.plot_ctrl_text(self.log, self.tag_latest_pos_idx, self.bubble_status, self.curveCordType)
            else:
                pass
        self.sp.draw()

    # 事件处理函数，计算控车数据悬浮气泡窗并显示
    def set_ctrl_bubble_content(self, idx):
        # 根据输入类型设置气泡
        self.sp.plot_ctrl_text(self.log, idx, self.bubble_status, self.curveCordType)
        self.tag_latest_pos_idx = idx

    # 设置树形结构
    def set_tree_fromat(self):
        self.treeWidget.setColumnCount(3)  # 协议字段，数据，单位
        self.treeWidget.setHeaderLabels(['协议数据包', '字段', '取值'])
        self.treeWidget.setColumnWidth(0, 100)
        self.treeWidget.setColumnWidth(1, 125)

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
        cycleObj = self.log.cycle_dic[self.log.cycle[idx]]
        if cycleObj.a2t_ctrl.updateflag or cycleObj.a2t_stat.updateflag or cycleObj.t2a_stat.updateflag:
            self.mvbShowByData(cycleObj.a2t_ctrl, cycleObj.a2t_stat, cycleObj.t2a_stat)
    
    # 事件处理函数，设置ATP信息
    def set_ATP_page_content(self, idx):
        msg_obj = self.log.cycle_dic[self.log.cycle[idx]].msg_atp2ato
        self.atpCommonInfoShowByMsg(msg_obj)
        self.atoDmiShowByMsg(msg_obj)

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
            for line in self.log.cycle_dic[self.log.cycle[idx]].raw_analysis_lines:
                # 提高解析效率,当均更新时才发送信号
                if '[RP' in line:
                    if self.pat_plan[0].findall(line):
                        rp1 = self.pat_plan[0].findall(line)[0]
                        update_flag = 1

                    elif self.pat_plan[1].findall(line):
                        rp2 = self.pat_plan[1].findall(line)[0]
                        update_flag = 1

                    elif self.pat_plan[2].findall(line):
                        temp_transfer_list = self.compute_plan_content(self.pat_plan[2].findall(line)[0])
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
                self.led_s_track.setText(str(rp1[0]))

                if rp1[3] == '1':
                    self.lbl_stop_flag.setText('停稳状态')
                    self.lbl_stop_flag.setStyleSheet("background-color: rgb(0, 255, 0);")
                elif rp1[3] == '0':
                    self.lbl_stop_flag.setText('非停稳')
                    self.lbl_stop_flag.setStyleSheet("background-color: rgb(255, 0, 0);")

            if rp2 != ():
                if rp2[0] == '1':
                    self.lbl_plan_legal.setText('计划合法')
                    self.lbl_plan_legal.setStyleSheet("background-color: rgb(0, 255, 0);")
                elif rp2[0] == '0':
                    self.lbl_plan_legal.setText('计划非法')
                    self.lbl_plan_legal.setStyleSheet("background-color: rgb(255, 0, 0);")

                if rp2[1] == '1':
                    self.lbl_plan_final.setText('终到站')
                elif rp2[1] == '0':
                    self.lbl_plan_final.setText('非终到站')
            # 有计划，准备表格显示内容
            if rp2_list:
                for item in rp2_list:
                    # 去除打印中计划更新时间信息，无用
                    rp2_temp_list.append(item[0:1] + item[2:])

                len_plan = len(rp2_temp_list)

                # 清空表格内容准备更新
                self.tableWidgetPlan.clearContents()

                # 计划索引
                for index, item_plan in enumerate(rp2_temp_list):
                    # 内容索引
                    for idx, name in enumerate(item_plan):
                        self.tableWidgetPlan.setItem(idx, index, QtWidgets.QTableWidgetItem(item_plan[idx]))
                        self.tableWidgetPlan.item(idx, index).setTextAlignment(QtCore.Qt.AlignCenter)
            else:
                # 没有计划，清空表格内容直接清空
                self.tableWidgetPlan.clearContents()

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
            self.Log(err, __name__, sys._getframe().f_lineno)
            print(ret_plan)

    # 解析转化计划,参考实时解析实现
    @staticmethod
    def compute_plan_content(t="tuple"):
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

    # 事件处理函数，双击跳转
    def BTM_selected_cursor_go(self, row_item):
        if self.curInterface == 1 and self.curWinMode == 1:  # 必须标记模式:
            c_num = BtmInfoDisplay.btmCycleList[row_item.row()]
            try:
                self.spinBox.setValue(c_num)
            except Exception as err:
                self.Log(err, __name__, sys._getframe().f_lineno)

    # 事件处理函数，应答器表格选中事件显示
    def BTM_selected_info(self, row_item):
        # 获取SP7应答器包对象
        sp7_obj = BtmInfoDisplay.GetBtmItemSelected(self.log.cycle_dic, row_item, 
        self.curInterface, self.curWinMode)
        if sp7_obj:
            BtmInfoDisplay.displayBtmItemSelInfo(sp7_obj, self.led_with_c13, self.led_platform_pos, 
            self.led_platform_door,self.led_track, self.led_stop_d_JD)

    # 事件处理函数，显示测速测距信息
    def set_sdu_info_content(self, idx):
        stat_machine = 0
        sdu_ato = []
        sdu_atp = []
        result = ()
        # sdu Info 解析表
        p_ato_sdu = self.pat_list[27]
        p_atp_sdu = self.pat_list[28]

        for line in self.log.cycle_dic[self.log.cycle[idx]].raw_analysis_lines:
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
        # 当文件路径不为空
        if self.file == '':
            pass
        else:
            try:
                self.Log('Init global vars', __name__, sys._getframe().f_lineno)
                self.islogLoad = 0  # 区分是否已经加载文件,1=加载且控车，2=加载但没有控车
                self.actionRealtime.setEnabled(True)
                self.curveCordType = 1  # 区分绘制曲线类型，0=速度位置曲线，1=周期位置曲线
                self.Log('Init UI widgt', __name__, sys._getframe().f_lineno)
                self.update_filetab()
                self.reset_all_checkbox()
                self.reset_text_edit()
                self.curWinMode = 0  # 恢复初始浏览模式
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
        cycleItem = self.log.cycle_dic[self.log.cycle[idx]]
        self.atoFsmInfoShow(cycleItem.fsm, cycleItem.control, cycleItem.msg_atp2ato, cycleItem.t2a_stat)
        # 根据分相和主断路器设置光标
        if cycleItem.t2a_stat.main_circuit_breaker == 0x00 or cycleItem.msg_atp2ato.sp2_obj.m_ms_cmd == 1:
            self.c_vato.boldRedEnabled(True)

    # 导出函数
    def export_ato_ctrl_info(self):
        # file is load
        if self.islogLoad == 1:
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
    @staticmethod
    def Log(msg=str, fun=str, lino=int):
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
        self.fileOpen.setIcon(QtGui.QIcon(":IconFiles/file.png"))
        self.fileClose.setIcon(QtGui.QIcon(":IconFiles/close.png"))
        self.fileSave.setIcon(QtGui.QIcon(":IconFiles/save.png"))
        self.Exit.setIcon(QtGui.QIcon(":IconFiles/quit.png"))
        self.actionVersion.setIcon(QtGui.QIcon(":IconFiles/version.png"))
        self.actionHelp.setIcon(QtGui.QIcon(":IconFiles/help.png"))
        self.actionTag.setIcon(QtGui.QIcon(":IconFiles/tag.png"))
        self.actionView.setIcon(QtGui.QIcon(":IconFiles/view.png"))
        self.actionPan.setIcon(QtGui.QIcon(":IconFiles/pan.png"))
        self.actionZoom.setIcon(QtGui.QIcon(":IconFiles/zoom.png"))
        self.actionConfig.setIcon(QtGui.QIcon(":IconFiles/config.png"))
        self.actionFwd.setIcon(QtGui.QIcon(":IconFiles/forward.png"))
        self.actionBck.setIcon(QtGui.QIcon(":IconFiles/back.png"))
        self.actionEdit.setIcon(QtGui.QIcon(":IconFiles/edit.png"))
        self.actionReset.setIcon(QtGui.QIcon(":IconFiles/reset.png"))
        self.actionHome.setIcon(QtGui.QIcon(":IconFiles/home.png"))
        self.actionPrint.setIcon(QtGui.QIcon(":IconFiles/print.png"))
        self.actionVS.setIcon(QtGui.QIcon(":IconFiles/vscurve.png"))
        self.actionCS.setIcon(QtGui.QIcon(":IconFiles/cyclecurve.png"))
        self.actionSerSet.setIcon(QtGui.QIcon(":IconFiles/serset.png"))
        self.actionoffline.setIcon(QtGui.QIcon(":IconFiles/offline.png"))
        self.actionRealtime.setIcon(QtGui.QIcon(":IconFiles/realtime.png"))
        self.actionMVB.setIcon(QtGui.QIcon(":IconFiles/port.png"))
        self.actionUTC.setIcon(QtGui.QIcon(":IconFiles/UTCParser.png"))
        self.actionMVBParser.setIcon(QtGui.QIcon(":IconFiles/MVBParser.png"))
        self.actionRealTimePlot.setIcon(QtGui.QIcon(":IconFiles/realtimeset.png"))
        self.action_bubble_track.setIcon(QtGui.QIcon(":IconFiles/track.png"))
        self.action_bubble_dock.setIcon(QtGui.QIcon(":IconFiles/dock.png"))
        self.action_acc_measure.setIcon(QtGui.QIcon(":IconFiles/acc.png"))
        self.actionExport.setIcon(QtGui.QIcon(":IconFiles/export.png"))
        self.actionC3ATOTrans.setIcon(QtGui.QIcon(":IconFiles/translator.png"))
        self.actionRplay.setIcon(QtGui.QIcon(":IconFiles/replay.png"))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Mywindow()
    window.show()
    sys.exit(app.exec_())
