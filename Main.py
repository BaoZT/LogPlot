#!/usr/bin/env python
# encoding: utf-8
'''
Author: Zhengtang Bao
Contact: baozhengtang@crscd.com.cn
File: main_fun.py
Desc: 本文件功能集成的主框架
LastEditors: Zhengtang Bao
LastEditTime: 2022-10-28 14:26:58
'''

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
from KeyWordPlot import CurveFigureCanvas, SnaptoCursor, Figure_Canvas_R
from LogMainWin import Ui_MainWindow
from MiniWinCollection import MVBPortDlg, SerialDlg, MVBParserDlg, ATPParserDlg, TSRSParseDlg, UTCTransferDlg, RealTimePlotDlg, CtrlMeasureDlg, \
    Cyclewindow, TrainComMeasureDlg, C3ATOTransferDlg
from TcmsParse import MVBParse,Ato2TcmsCtrl,Ato2TcmsState,Tcms2AtoState,DisplayMVBField,MVBFieldDic
from MsgParse import Atp2atoParse, Atp2atoProto, Atp2atoFieldDic, DisplayMsgield, TrainCircuitDic
from RealTimeExtension import SerialRead, RealPaintWrite
from ConfigInfo import ConfigFile
from MainWinDisplay import AtoInerDic, BtmInfoDisplay,AtoKeyInfoDisplay, InerIoInfo, InerRunningPlanInfo, InerSduInfo, ProgressBarDisplay
from Version import VersionInfo

# 主界面类
class Mywindow(QtWidgets.QMainWindow, Ui_MainWindow):
    # 建立的是Main Window项目，故此处导入的是QMainWindow
    def __init__(self):
        super(Mywindow, self).__init__()
        self.setupUi(self)
        self.initUI()
        self.icon_from_file()
        self.verObj = VersionInfo()
        # 定义界面变量
        self.file = ''
        self.savePath = os.getcwd()   # 实时存储的文件保存路径（文件夹）,增加斜线直接添加文件名即可
        self.savefilename = ''        # 实时存储的写入文件名(含路径)
        self.pathlist = []
        self.curWinMode = 0           # 默认0是浏览模式，1是标注模式
        self.curInterface = 0         # 当前界面， 1=离线界面，2=在线界面
        self.isCursorCreated = 0      # 是否创建光标
        self.curveCordType = 1        # 区分绘制曲线类型，0=速度位置曲线，1=周期位置曲线
        self.isCursorInFram = 0       # 区分光标是否在图像内-仅离线模式,初始化为0,in=1，out=2
        self.islogLoad = 0            # 区分是否已经加载文件,1=加载且控车，2=加载但没有控车
        self.serialCfgDlg = SerialDlg()  # 串口设置对话框，串口对象，已经实例
        self.serialHandle = serial.Serial(timeout=None)  # 操作串口对象
        self.thPaintWrite = None
        self.thRead = None
        self.thpaint = None
        self.log = None
        self.barDisplay = ProgressBarDisplay(self.progressBar)
        self.mvbdialog = MVBPortDlg()
        self.cbb_serial.addItems(self.serialCfgDlg.Port_List())  # 调用对象方法获取串口对象
        self.setWindowTitle(self.verObj.getVerToken())
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/BZT.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        # 参数配置
        self.cfg = ConfigFile()
        self.cfg.readConfigFile()
        # 离线绘图
        l = QtWidgets.QVBoxLayout(self.mainOfflineWidget)
        self.sp = CurveFigureCanvas(self.mainOfflineWidget)  # 这是继承FigureCanvas的子类，使用子窗体widget作为父亲类
        self.sp.mpl_toolbar = NavigationToolbar(self.sp, self.mainOfflineWidget)  # 传入FigureCanvas类或子类实例，和父窗体
        l.addWidget(self.sp)
        lAux = QtWidgets.QVBoxLayout(self.auxOfflineWidget)
        self.spAux = CurveFigureCanvas(self.auxOfflineWidget, sharedAxes=self.sp.mainAxes)
        lAux.addWidget(self.spAux)
        self.cursorVato = None
        self.bubbleStatus = 0   # 控车悬浮气泡状态，0=停靠，1=跟随
        self.tagLatestPosIdx = 0  # 悬窗最近一次索引，用于状态改变或曲线改变时立即刷新使用，最近一次
        self.ctrlMeasureStatus = 0  # 控车曲线测量状态，0=初始态，1=测量起始态，2=进行中 ,3=测量终止态
        # 在线绘图
        lr = QtWidgets.QVBoxLayout(self.mainOnlineWidget)
        self.spReal = Figure_Canvas_R(self.mainOnlineWidget)
        lr.addWidget(self.spReal)  # 必须创造布局并且加入才行
        # MVB解析面板
        self.mvbParserPage = MVBParse()
        # ATP解析面板
        self.Atp2atoParserPage = Atp2atoParse()
        # MVB解析器
        self.mvbParserDlg = MVBParserDlg()
        # ATP-ATO协议解析器
        self.atpParserDlg = ATPParserDlg()
        # TSRS-ATO协议解析器
        self.tsrsParserDlg = TSRSParseDlg()
        # UTC转换器
        self.utctransfer = UTCTransferDlg()
        # C3ATO转义工具
        self.C3ATORecordTransfer = C3ATOTransferDlg()
        # 绘图界面设置器
        self.realtime_plot_dlg = RealTimePlotDlg()  # 实时绘图界面设置
        self.realtime_plot_interval = 0.1  # 默认0.1s绘图
        self.isRealtimePaint = True  # 实时绘图否
        self.realtime_plot_dlg.realtime_plot_set_signal.connect(self.realtimePlotSet)
        self.mainOfflineWidget.setFocus()
        self.fileOpen.triggered.connect(self.showDialog)
        self.fileClose.triggered.connect(self.closeFigure)
        self.fileSave.triggered.connect(self.sp.mpl_toolbar.save_figure)
        self.actionConfig.triggered.connect(self.sp.mpl_toolbar.configure_subplots)
        self.actionExport.triggered.connect(self.export_ato_ctrl_info)
        self.actionPan.triggered.connect(self.sp.mpl_toolbar.pan)
        self.actionZoom.triggered.connect(self.zoom)
        self.actionEdit.triggered.connect(self.sp.mpl_toolbar.edit_parameters)
        self.actionReset.triggered.connect(self.resetLogPlot)
        self.actionHome.triggered.connect(self.homeShow)  # 这里home,back,和forward都是父类中实现的
        self.actionBck.triggered.connect(self.sp.mpl_toolbar.back)  # NavigationToolbar2方法
        self.actionFwd.triggered.connect(self.sp.mpl_toolbar.forward)
        self.actionTag.triggered.connect(self.modeChange)
        self.actionView.triggered.connect(self.modeChange)
        self.actionVersion.triggered.connect(self.versionMsg)
        self.actionHelp.triggered.connect(self.helpMsg)
        self.sp.mpl_connect('button_press_event', self.sp.right_press)
        self.actionPrint.triggered.connect(self.cyclePrint)  # 打印周期
        self.actionCS.triggered.connect(self.cmdChange)
        self.actionVS.triggered.connect(self.cmdChange)
        self.actionRealtime.triggered.connect(self.showRealTimeUI)
        self.actionoffline.triggered.connect(self.showOffLineUI)
        self.actionReplay.triggered.connect(self.showReplayUI)
        self.actionSerSet.triggered.connect(self.showSerSet)
        self.spinBox.valueChanged.connect(self.spinValueChanged)
        self.serialCfgDlg.serUpdateSingal.connect(self.updateSerSet)
        self.actionMVB.triggered.connect(self.mvbdialog.show)
        self.btn_SavePath.clicked.connect(self.showlogSave)
        self.btn_choose_replay_file.clicked.connect(self.showDialog)
        self.btn_PortLink.clicked.connect(self.btnLinkorBreak)
        self.actionMVBParser.triggered.connect(self.mvbParserDlg.show)
        self.actionATPParser.triggered.connect(self.atpParserDlg.show)
        self.actionTSRSParser.triggered.connect(self.tsrsParserDlg.show)
        self.actionUTC.triggered.connect(self.utctransfer.show)
        self.actionC3ATOTrans.triggered.connect(self.C3ATORecordTransfer.show)
        self.action_bubble_dock.triggered.connect(self.setCtrlBubbleFormat)
        self.action_bubble_track.triggered.connect(self.setCtrlBubbleFormat)
        self.action_acc_measure.triggered.connect(self.ctrlMeasure)
        self.sp.mpl_connect('button_press_event', self.ctrlMeasureClicked)  # 鼠标单击的测量处理事件
        self.btn_mvb_delay_plot.clicked.connect(self.showStatisticsMvbDelay)
        # 事件绑定
        self.actionBTM.triggered.connect(self.updateEventPointType)
        self.actionJD.triggered.connect(self.updateEventPointType)
        self.actionPLAN.triggered.connect(self.updateEventPointType)
        self.actionWL.triggered.connect(self.updateEventPointType)
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
        # 表格显示
        self.tableATPBTM.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tb_ato_IN.horizontalHeader().setVisible(True)
        self.tableWidgetPlan.horizontalHeader().setVisible(True)
        self.tableWidgetTb.horizontalHeader().setVisible(True)
        #self.tab_atp_ato.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        #self.tab_atp_ato.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        #self.tab_tsrs_ato.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        #self.tab_tsrs_ato.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        # 表逻辑
        self.tableATPBTM.itemClicked.connect(self.btmSelectedInfo)
        self.tableATPBTM.itemDoubleClicked.connect(self.btmSelectedCursorGo)
        self.tab_atp_ato.itemClicked.connect(self.msgAtp2atoSelectedInfo)
        self.tab_atp_ato.itemDoubleClicked.connect(self.msgAtp2atoSelectedParserGo)
        self.tab_tsrs_ato.itemClicked.connect(self.msgTsrs2atoSelectedInfo)
        self.tab_tsrs_ato.itemDoubleClicked.connect(self.msgTsrsatoSelectedParserGo)
        # 树逻辑
        self.tree_protocol.itemDoubleClicked.connect(self.msgAtpatoTreeSelectedParserGo)
        self.tree_protocol.itemDoubleClicked.connect(self.msgTsrsatoTreeSelectedParserGo)
        # 窗口设置初始化
        self.showOffLineUI()

    def initUI(self):
        # 初始化
        self.Exit.setStatusTip('Ctrl+Q')
        self.Exit.setStatusTip('Exit app')
        self.fileOpen.setStatusTip('Ctrl+O')
        self.fileOpen.setStatusTip('Open Log')
        self.setCtrlTableFormat()
        self.progressBar.setValue(0)
        self.spinBox.setRange(0, 1000000)
        self.action_bubble_track.setChecked(True)
        self.Exit.triggered.connect(QtWidgets.qApp.quit)
        self.bindOfflineCurve(True)

        self.CBvato.stateChanged.connect(self.realtimeLineChoose)
        self.CBatpcmdv.stateChanged.connect(self.realtimeLineChoose)
        self.CBlevel.stateChanged.connect(self.realtimeLineChoose)
        self.CBcmdv.stateChanged.connect(self.realtimeLineChoose)

        # 如果初始界面实时
        self.fileOpen.setDisabled(True)  # 设置文件读取不可用
        self.cyclewin = Cyclewindow()
        self.cfg = ConfigFile()
        self.cfg.readConfigFile()
        self.led_save_path.setText(self.cfg.base_config.save_path)
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
                self.resetLogPlot()
                self.statusbar.showMessage(self.file)
        else:
            self.Log('Init file path', __name__, sys._getframe().f_lineno)
            filepath = temp.join(self.pathlist[:-1])  # 纪录上一次的文件路径
            filepath = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', filepath)
            path = filepath[0]
            name = filepath[0].split("/")[-1]
            # 求出本次路径序列
            templist = filepath[0].split("/")
            self.updatePathChanged(templist)
            if path:
                self.file = path
                self.resetLogPlot()
            self.statusbar.showMessage(self.file)
        
    # 显示实时界面
    def showRealTimeUI(self):
        self.stackedOnlineWidget.setCurrentWidget(self.pageRealTime)
        self.stackedMainWidget.setCurrentWidget(self.pageOnline)
        self.stackedWidget_RightCol.setCurrentWidget(self.page_ctrl)
        self.fileOpen.setDisabled(True)  # 设置文件读取不可用
        # 初始化绘图
        self.CBvato.setChecked(True)
        self.CBstate.setChecked(True)
        self.CBatpcmdv.setChecked(True)
        self.CBlevel.setChecked(True)
        self.CBcmdv.setChecked(True)
        # 解绑
        if self.curInterface == 1:
            self.bindOfflineCurve(False)

        # 如有转换重置右边列表
        self.actionView.trigger()
        self.setCtrlTableFormat()
        self.tree_protocol.clear()
        # 初始化表格
        BtmInfoDisplay.displayInitClear(self.tableATPBTM)
        self.curInterface = 2

    # 显示离线界面
    def showOffLineUI(self):
        self.stackedMainWidget.setCurrentWidget(self.pageOffline)
        self.fileOpen.setEnabled(True)  # 设置文件读取可用
        self.stackedWidget_RightCol.setCurrentWidget(self.page_ctrl)
        self.btn_plan.setEnabled(True)
        self.btn_train.setEnabled(True)
        self.btn_atp.setEnabled(True)
        self.btn_filetab.setEnabled(True)
        self.bindOfflineCurve(True)
        self.curInterface = 1

    # 绑定离线绘图
    def bindOfflineCurve(self, enabled=bool):
        if enabled:
            self.CBvato.stateChanged.connect(self.updateUpCure)
            self.CBatpcmdv.stateChanged.connect(self.updateUpCure)
            self.CBlevel.stateChanged.connect(self.updateUpCure)
            self.CBcmdv.stateChanged.connect(self.updateUpCure)
            self.CBstate.stateChanged.connect(self.updateUpCure)
            self.CBramp.stateChanged.connect(self.updateUpCure)
            self.CBatppmtv.stateChanged.connect(self.updateUpCure)
        else:
            self.CBvato.stateChanged.disconnect(self.updateUpCure)
            self.CBatpcmdv.stateChanged.disconnect(self.updateUpCure)
            self.CBlevel.stateChanged.disconnect(self.updateUpCure)
            self.CBcmdv.stateChanged.disconnect(self.updateUpCure)
            self.CBstate.stateChanged.disconnect(self.updateUpCure)
            self.CBramp.stateChanged.disconnect(self.updateUpCure)
            self.CBatppmtv.stateChanged.disconnect(self.updateUpCure)

    # 显示回放界面
    def showReplayUI(self):
        self.showRealTimeUI()
        self.stackedOnlineWidget.setCurrentWidget(self.pageReplay)

    # 显示控车情况
    def showOffRight_ATO(self):
        self.stackedWidget_RightCol.setCurrentWidget(self.page_ctrl)

    # 显示MVB数据
    def showOffRight_MVB(self):
        self.stackedWidget_RightCol.setCurrentWidget(self.page_train)

    # 显示计划情况
    def showOffRight_PLAN(self):
        self.stackedWidget_RightCol.setCurrentWidget(self.page_plan)

    # 显示记录情况
    def showOffRight_FILE(self):
        self.stackedWidget_RightCol.setCurrentWidget(self.page_files)

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
        self.serialCfgDlg.show()

    # 如果设置窗口应该更新窗口
    def updateSerSet(self, hd=serial.Serial):
        self.serialHandle = hd

    # 主界面的串口显示,立即更新路径
    def showlogSave(self):
        self.savePath = QtWidgets.QFileDialog.getExistingDirectory(directory=os.getcwd())
        self.led_save_path.setText(self.savePath)
        self.cfg.base_config.save_path=self.savePath
        self.cfg.writeConfigFile()

    # 实时绘设置
    def showRealtimePlotSet(self):
        self.realtime_plot_dlg.show()

    # 串口连接动作
    def serialBtnStateLinked(self, linked=True):
        self.actionoffline.setEnabled(not linked)
        AtoKeyInfoDisplay.btnSerialDisplay(linked, self.btn_PortLink)

    # 实时界面连接或断开按钮
    def btnLinkorBreak(self):
        # 串口关闭状态
        if not self.serialHandle.is_open:
            self.cbb_serial.setEnabled(False)
            # 当串口没有打开过
            try:
                self.serialHandle = self.serialCfgDlg.OpenSerial()
                self.serialHandle.port = self.cbb_serial.currentText()
                self.serialHandle.open()
                self.showMessage('Info:串口%s成功打开!' % self.serialHandle.port)
            except Exception as err:
                reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                        "串口异常",
                        "注意：打开串口失败，关闭其他占用再尝试！",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Close)
                # 按钮显示及串口使能
                self.serialBtnStateLinked(False)
                self.cbb_serial.setEnabled(True)
                # 停止线程执行
                self.isRealtimePaint = False
                # 选择确定继续，否则取消
                if reply == 16384:
                    pass
                elif reply == 2097152:
                    pass
            if self.serialHandle.is_open:
                self.savePath = self.led_save_path.text() + '\\'  # 更新路径选择窗口内容
                self.savePath = self.savePath.replace('//', '/')
                self.savePath = self.savePath.replace('/', '\\')
                tmpfilename = self.serialCfgDlg.filenameLine.text()
                self.thPaintWrite = RealPaintWrite(self.savePath, tmpfilename, self.serialHandle.port)  # 文件写入线程
                self.thpaint = threading.Thread(target=self.runPaint)  # 绘图线程
                self.thRead = SerialRead('COMThread', self.serialHandle)  # 串口数据读取解析线程
                # 链接显示
                self.thPaintWrite.patShowSignal.connect(self.realtimeContentShow)  # 界面显示处理
                self.thPaintWrite.mvbShowSignal.connect(self.mvbShowByData)
                self.thPaintWrite.planShowSignal.connect(self.runningPlanShow)  # 局部变量无需考虑后续解绑
                self.thPaintWrite.ioShowSignal.connect(self.realtimeIoInfoShow)  # io信息更新
                self.thPaintWrite.sduShowSignal.connect(self.sduInfoShow) # sdu 信息更新
                # 设置线程
                self.thpaint.setDaemon(True)
                self.thRead.setDaemon(True)
                self.thPaintWrite.setDaemon(True)
                # 设置按钮状态
                self.serialBtnStateLinked(True)
                # 允许线程执行
                self.isRealtimePaint = True
                self.thRead.setThreadEnabled(True)
                # 开启线程
                self.thPaintWrite.start()
                self.thRead.start()
                self.thpaint.start()
                self.showMessage('Info:读取记录及绘图线程启动成功！')
            else:
                # 打开失败设置回去
                self.showMessage('Info:读取记录及绘图线程启动失败！')
                self.reatimeDefaultShowLabel()
                self.serialBtnStateLinked(False)
        else:
            # 按钮显示
            self.cbb_serial.setEnabled(True)
            self.showMessage('Info:串口关闭!')
            self.serialBtnStateLinked(False)
            # 停止线程执行
            self.isRealtimePaint = False
            self.thRead.setThreadEnabled(False)
            # 断开绑定关系
            self.thPaintWrite.patShowSignal.disconnect(self.realtimeContentShow)  # 界面显示处理
            self.thPaintWrite.mvbShowSignal.disconnect(self.mvbShowByData)
            self.thPaintWrite.planShowSignal.disconnect(self.runningPlanShow)  # 局部变量无需考虑后续解绑
            self.thPaintWrite.ioShowSignal.disconnect(self.realtimeIoInfoShow)  # io信息更新
            self.thPaintWrite.sduShowSignal.disconnect(self.sduInfoShow) # sdu 信息更新
            self.reatimeDefaultShowLabel()       

    # 界面实时绘图函数
    def runPaint(self):
        while self.isRealtimePaint:
            try:
                self.spReal.show()
                time.sleep(self.realtime_plot_interval)  # 绘图线程非常消耗性能，当小于1s直接影响读取和写入
                self.spReal.realTimePlot()
            except Exception as err:
                self.Log(err, __name__, sys._getframe().f_lineno)
                self.showMessage('Error:绘图线程异常！')
                print('thread paint info!' + str(time.time()))
        self.showMessage('Info:绘图线程结束!')

    # 界面更新信号槽函数
    def realtimeContentShow(self, result="tuple"):
        cycleTime       = result[0]
        cycleNum        = result[1]
        dateTime        = result[2]
        fsmList         = result[3]
        scCtrl          = result[4]
        stoppoint       = result[5]
        atp2ato_msg     = result[6]
        tcms2ato_stat   = result[7]
        time_statictics = result[8]
        a2tMsg          = result[9]
        t2aMsg          = result[10]
        # 显示到侧面
        self.realtimeCtrlTableShow(cycleNum, cycleTime, dateTime, scCtrl, stoppoint)
        self.atoFsmInfoShow(fsmList,scCtrl,atp2ato_msg,tcms2ato_stat)
        # 显示主界面
        self.atpCommonInfoShowByMsg(atp2ato_msg, dateTime)
        self.atoDmiShowByMsg(atp2ato_msg)
        self.atpTrainDataShowByMsg(atp2ato_msg)
        self.atpBtmShowByMsg(dateTime, atp2ato_msg)
        self.atoCyleTimeStatistics(time_statictics)
        AtoKeyInfoDisplay.disTurnbackTable(a2tMsg, t2aMsg, self.lbl_ato_tbstatus, self.tableWidgetTb)
        # 停车误差显示
        if scCtrl and atp2ato_msg: 
            ato_error = int(scCtrl[15])
            atp_error = atp2ato_msg.sp2_obj.m_atp_stop_error
            AtoKeyInfoDisplay.ctrlStopErrorDisplay(ato_error, atp_error, self.tb_ctrl_stoppoint)
        else:
            pass
        # 显示表格
        self.msgAtp2atoTabShow((atp2ato_msg, dateTime, int(cycleNum)))
        if t2aMsg.msgHeader.nid_message != 0:
            self.msgTsrsatoTabShow(('T->A', t2aMsg, dateTime, int(cycleNum)))
        if a2tMsg.msgHeader.nid_message != 0:
            self.msgTsrsatoTabShow(('A->T', a2tMsg, dateTime, int(cycleNum)))
        del result

    # 显示时间统计信息
    def atoCyleTimeStatistics(self,time_statictics):
        if time_statictics:
            self.lbl_mean_slot_rtn.setText(str(round(time_statictics[0],1))+'ms')
            self.lbl_max_slot_rtn.setText(str(time_statictics[1])+'ms')
            self.lbl_max_slot_cycle_rtn.setText(str(time_statictics[2]))
            self.lbl_min_slot_rtn.setText(str(time_statictics[3])+'ms')
            self.lbl_slot_count_rtn.setText(str(time_statictics[4]))

    # 显示通用信息SP2/SP13/SP138/SP8
    def atpCommonInfoShowByMsg(self, msg_obj=Atp2atoProto, time=str):
        if msg_obj and msg_obj.sp2_obj.updateflag:
            # 门允许左右门合并
            DisplayMsgield.disAtpDoorPmt(msg_obj.sp2_obj.q_leftdoorpermit,msg_obj.sp2_obj.q_rightdoorpermit, self.lbl_door_pmt)
            DisplayMsgield.disNameOfLable("q_stopstatus", msg_obj.sp2_obj.q_stopstatus, self.lbl_atp_stop_ok, 2)
            DisplayMsgield.disTsmStat(msg_obj.sp2_obj.d_tsm, self.lbl_tsm, False)
            DisplayMsgield.disTsmStat(msg_obj.sp2_obj.d_tsm, self.lbl_csm_or_tsm, True) # 在控制界面复显
            DisplayMsgield.disNameOfLable("m_tco_state", msg_obj.sp2_obj.m_tco_state, self.lbl_atp_cut_traction,2,1)
            DisplayMsgield.disNameOfLable("reserve", msg_obj.sp2_obj.reserve, self.lbl_atp_brake,2,1)
            DisplayMsgield.disNameOfLable("q_tb", msg_obj.sp2_obj.q_tb, self.lbl_tb)
            DisplayMsgield.disNameOfLable("m_level", msg_obj.sp2_obj.m_level, self.lbl_atp_level)
            if msg_obj.sp2_obj.m_level == 1:
                DisplayMsgield.disNameOfLable("m_mode_c2",msg_obj.sp2_obj.m_mode_c2,self.lbl_atp_mode)
            elif msg_obj.sp2_obj.m_level == 3:
                DisplayMsgield.disNameOfLable("m_mode_c3",msg_obj.sp2_obj.m_mode_c3,self.lbl_atp_mode)
            DisplayMsgield.disNameOfLable("m_cab_state", msg_obj.sp2_obj.m_cab_state, self.lbl_cabin,1,2)
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
            # 控制界面显示分相区
            DisplayMsgield.disFxInfo(msg_obj.sp2_obj.d_neu_sec, self.lbl_fx_track)
        if msg_obj and msg_obj.sp13_obj.updateflag:
            DisplayMsgield.disNameOfLable("q_leading", msg_obj.sp13_obj.q_leading, self.lbl_headtail)
            DisplayMsgield.disNameOfLineEdit("m_tb_status", msg_obj.sp13_obj.m_tb_status, self.led_atp_tb_status)
            DisplayMsgield.disNameOfLineEdit("reserved", msg_obj.sp13_obj.reserved, self.led_reserved)
            DisplayMsgield.disNameOfLineEdit("q_tb_relay", msg_obj.sp13_obj.q_tb_relay, self.led_atp_tb_relay)
        if msg_obj and msg_obj.sp138_obj.updateflag:
            DisplayMsgield.disNameOfLable("m_tb_plan" , msg_obj.sp138_obj.m_tb_plan, self.lbl_ato_tb_pmt, 0xA5, 0)
            DisplayMsgield.disNameOfLineEdit("nid_operational", msg_obj.sp138_obj.nid_operational, self.led_tb_nid_operational)
        if msg_obj and msg_obj.sp130_obj.updateflag:
            DisplayMsgield.disNameOfLable("m_atomode", msg_obj.sp130_obj.m_atomode, self.lbl_ato_mode, 3)
        if msg_obj and msg_obj.sp8_obj.updateflag:
            DisplayMsgield.disNameOfLineEdit("q_tsrs", msg_obj.sp8_obj.q_tsrs, self.led_q_tsrs)
            tsrs_id = msg_obj.sp8_obj.nid_tsrs + (msg_obj.sp8_obj.nid_c<<14)
            DisplayMsgield.disNameOfLineEdit("nid_tsrs", tsrs_id, self.led_nid_tsrs)
            DisplayMsgield.disNameOfLineEdit("nid_radio_h", msg_obj.sp8_obj.nid_radio_h, self.led_tsrs_ip)
            DisplayMsgield.disNameOfLineEdit("q_sleepsession", msg_obj.sp8_obj.q_sleepsession, self.led_q_sleep)
            DisplayMsgield.disNameOfLineEdit("m_session_type", msg_obj.sp8_obj.m_session_type, self.led_sess_type)

    # 显示列车数据内容SP5
    def atpTrainDataShowByMsg(self, msg_obj=Atp2atoProto):
        if msg_obj and msg_obj.sp5_obj.updateflag:
            obj = msg_obj.sp5_obj
            DisplayMsgield.disNameOfLineEdit("n_units",obj.n_units,self.led_units)
            DisplayMsgield.disNameOfLineEdit("v_ato_permitted",obj.v_ato_permitted,self.led_driver_strategy)
            DisplayMsgield.disNameOfLineEdit("btm_antenna_position",obj.btm_antenna_position,self.led_atp_btm_pos)
            DisplayMsgield.disNameOfLineEdit("l_door_distance",obj.l_door_distance,self.led_head_foor_dis)
            DisplayMsgield.disNameOfLineEdit("nid_engine",obj.nid_engine,self.led_nid_engine)
            DisplayMsgield.disNameOfLineEdit("l_sdu_wheel_size_1", obj.l_sdu_wheel_size_1, self.led_wheel_size1)
            DisplayMsgield.disNameOfLineEdit("l_sdu_wheel_size_2", obj.l_sdu_wheel_size_2, self.led_wheel_size2)

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
            DisplayMVBField.disNameOfLineEdit("ato_tb_light",a2t_ctrl.ato_start_light,self.led_ctrl_tb_lamp)
        if a2t_stat and a2t_stat.updateflag == True:
            DisplayMVBField.disNameOfLineEdit("ato_heartbeat", a2t_stat.ato_heartbeat,self.led_stat_hrt)
            DisplayMVBField.disNameOfLineEdit("ato_error", a2t_stat.ato_error,self.led_stat_error)
            DisplayMVBField.disNameOfLineEdit("killometer_marker", a2t_stat.killometer_marker,self.led_stat_stonemile)
            DisplayMVBField.disNameOfLineEdit("tunnel_entrance", a2t_stat.tunnel_entrance,self.led_stat_tunnelin)
            DisplayMVBField.disNameOfLineEdit("tunnel_length", a2t_stat.tunnel_length,self.led_stat_tunnellen)
            DisplayMVBField.disNameOfLineEdit("ato_speed", a2t_stat.ato_speed,self.led_stat_atospeed)
            # 设置控制界面隧道信息
            DisplayMVBField.disTunnelInfo(a2t_stat.tunnel_entrance, a2t_stat.tunnel_length, self.lbl_tunnel)
        if t2a_stat and t2a_stat.updateflag == True:
            DisplayMVBField.disNameOfLineEdit("tcms_heartbeat", t2a_stat.tcms_heartbeat, self.led_tcms_hrt)
            DisplayMVBField.disNameOfLineEdit("door_mode_mo_mc", t2a_stat.door_mode_mo_mc, self.led_tcms_mm)
            DisplayMVBField.disNameOfLineEdit("door_mode_ao_mc", t2a_stat.door_mode_ao_mc, self.led_tcms_am)
            DisplayMVBField.disNameOfLineEdit("door_mode_ao_ac", t2a_stat.door_mode_ao_ac, self.led_tcms_aa)
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
            DisplayMVBField.disNameOfLineEdit("ato_tb_btn_valid", t2a_stat.ato_tb_btn_valid, self.led_tcms_tb_btn)
            DisplayMVBField.disNameOfLineEdit("no_permit_ato_state", t2a_stat.no_permit_ato_state, self.led_tcms_pmt_state)
    
    # 右侧边栏显示
    def realtimeCtrlTableShow(self, cycleNum=str, cycleTime=int, dateTime=str, sc_ctrl="list", stTuple="tuple"):
        if sc_ctrl:
            atoPos = int(sc_ctrl[0])
            atoSpeed = int(sc_ctrl[1])
            level = int(sc_ctrl[6])
            esLevel = int(sc_ctrl[5])
            ramp = int(sc_ctrl[9])
            esRamp = int(sc_ctrl[10])
            stateMachine = int(sc_ctrl[17])
            tPos = int(sc_ctrl[12])
            tSpeed = int(sc_ctrl[11])
            atoCmdv = int(sc_ctrl[2])
            atpCmdv = int(sc_ctrl[3])
            atpPmtv = int(sc_ctrl[4])
            skip    = int(sc_ctrl[20])
            keyList = [atoPos,atoSpeed,level,esLevel,ramp,esRamp,stateMachine,tPos,tSpeed,atoCmdv,atpCmdv,atpPmtv,skip]
            self.setCtrlInfoShow(keyList)
        else:
            atoPos = None
        if stTuple:
            # 停车点表格显示
            self.setStoppointShow(atoPos,stTuple)

        self.lbl_date.setText(dateTime)
        self.lbl_sys_time.setText(str(cycleTime)+'ms')
        if cycleNum != '':
            self.spinBox.setValue(int(cycleNum))

    # 更新FSM信息相关
    def atoFsmInfoShow(self, fsm='list', ctrl='tuple', msg_obj=Atp2atoProto,t2a_stat=Tcms2AtoState):
        # 显示ATP2ATO接口协议内容
        if msg_obj:
            if  msg_obj.sp2_obj.updateflag:
                AtoKeyInfoDisplay.lableFieldDisplay("q_ato_hardpermit",msg_obj.sp2_obj.q_ato_hardpermit, Atp2atoFieldDic, self.lbl_hpm)
                AtoKeyInfoDisplay.lableFieldDisplay("q_atopermit",msg_obj.sp2_obj.q_atopermit, Atp2atoFieldDic, self.lbl_pm)
                AtoKeyInfoDisplay.lableFieldDisplay("m_ms_cmd",msg_obj.sp2_obj.m_ms_cmd, Atp2atoFieldDic, self.lbl_atpdcmd)
                AtoKeyInfoDisplay.lableFieldDisplay("m_low_frequency",msg_obj.sp2_obj.m_low_frequency, Atp2atoFieldDic, self.lbl_freq)
                AtoKeyInfoDisplay.labelRouteDisplay(msg_obj.sp2_obj.m_low_frequency, Atp2atoFieldDic, TrainCircuitDic, self.lbl_route_smart)
            if msg_obj.sp5_obj.updateflag:
                AtoKeyInfoDisplay.lableFieldDisplay("n_units",msg_obj.sp5_obj.n_units, Atp2atoFieldDic, self.lbl_trainlen)
        # 显示MVB接口协议内容
        if t2a_stat and t2a_stat.updateflag:
            AtoKeyInfoDisplay.lableFieldDisplay("train_permit_ato",t2a_stat.train_permit_ato, MVBFieldDic, self.lbl_carpm)
            AtoKeyInfoDisplay.lableFieldDisplay("door_state",t2a_stat.door_state, MVBFieldDic, self.lbl_doorstatus)
            AtoKeyInfoDisplay.lableFieldDisplay("main_circuit_breaker",t2a_stat.main_circuit_breaker, MVBFieldDic, self.lbl_dcmd)
        # 软件内部状态通过打印
        if fsm:
            AtoKeyInfoDisplay.labelInerDisplay("ato_self_check", int(fsm[5]), self.lbl_check)
            AtoKeyInfoDisplay.labelInerDisplay("ato_start_lamp", int(fsm[6]), self.lbl_lamp)
            AtoKeyInfoDisplay.lableFieldDisplay("m_atomode",int(fsm[0]), AtoInerDic, self.lbl_mode)
            # 站台标志由于FSM中记录后会经过处理，采用SC才是本周期控车使用的
            if ctrl:  # 按周期索引取控制信息，妨不连续
                AtoKeyInfoDisplay.labelInerDisplay("station_flag", int(list(ctrl)[17]), self.lbl_stn)

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
        self.spReal.updatePaintSet(linelist)

    # 显示重置信息
    def reatimeDefaultShowLabel(self):
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
        self.lbl_doorstatus.setStyleSheet("background-color: rgb(170, 170, 255);")

    # 显示BTM表格
    def atpBtmShowByMsg(self, time=str, msg_obj=Atp2atoProto):
        BtmInfoDisplay.displayRealTimeBtmTable(msg_obj, time, self.tableATPBTM)

    # 显示IO表格
    def realtimeIoInfoShow(self, cycleNumStr=str, timeContentStr=str, ioObj=InerIoInfo):
        AtoKeyInfoDisplay.ioInfoDisplay(cycleNumStr, timeContentStr, ioObj, self.tb_ato_IN,self.tb_ato_OUT)

    # 显示测速测距
    def sduInfoShow(self, obj=InerSduInfo):
        # 测速信息
        atoV = AtoKeyInfoDisplay.sduVInfoDisplay(obj.atoSpeed, self.led_ato_sdu, self.lcd_ato_sdu)
        atpV = AtoKeyInfoDisplay.sduVInfoDisplay(obj.atpSpeed,self.led_atp_sdu, self.lcd_atp_sdu)
        AtoKeyInfoDisplay.sduVJudgeDisplay(atoV, atpV, self.cfg.monitor_config.sdu_spd_fault_th, 
        self.led_sdu_err, self.lbl_sdu_judge)
        # 测距信息
        deltaS = AtoKeyInfoDisplay.sduAtoDeltaSDisplay(obj.atoDis, obj.atpDis, self.led_ato_s_delta,
        self.led_atp_s_delta)
        AtoKeyInfoDisplay.sduSJudgeDisplay(deltaS, self.cfg.monitor_config.sdu_dis_fault_th, 
        self.led_sdu_s_err, self.lbl_sdu_s_judge)

    # 显示计划信息
    def runningPlanShow(self, rp_obj=InerRunningPlanInfo, osTime=int):
        if rp_obj and rp_obj.updateflag:
            # 显示文本lbl
            AtoKeyInfoDisplay.labelInerDisplay("rpPlanValid", rp_obj.rpPlanValid, self.lbl_plan_valid)
            AtoKeyInfoDisplay.labelInerDisplay("rpStopStableFlg", rp_obj.rpStopStableFlg, self.lbl_stop_flag)
            AtoKeyInfoDisplay.labelInerDisplay("rpPlanLegalFlg", rp_obj.rpPlanLegalFlg, self.lbl_plan_legal)
            AtoKeyInfoDisplay.labelInerDisplay("rpFinalStnFlg", rp_obj.rpFinalStnFlg, self.lbl_plan_final)
            AtoKeyInfoDisplay.labelInerDisplay("rpPlanTimeout", rp_obj.rpPlanTimeout, self.lbl_plan_timeout)
            AtoKeyInfoDisplay.labelInerDisplay("rpTrainStnState", rp_obj.rpTrainStnState, self.lbl_start_flag)
            # 显示数值led
            AtoKeyInfoDisplay.lineditInerDisplay("rpCurTrack", rp_obj.rpCurTrack, self.led_s_track)
            AtoKeyInfoDisplay.lineditInerDisplay("remainArrivalTime", rp_obj.remainArrivalTime, self.led_runtime)
            AtoKeyInfoDisplay.lineditInerDisplay("remainDepartTime", rp_obj.remainDepartTime, self.led_plan_coutdown)
            AtoKeyInfoDisplay.lineditInerDisplay("rpUpdateSysTime", rp_obj.rpUpdateSysTime, self.led_plan_updatetime)
            # 增加辅助时间计算显示
            AtoKeyInfoDisplay.displayRpUdpDuration(osTime, rp_obj.rpUpdateSysTime,self.lbl_updateduration)
            # 显示表格
            AtoKeyInfoDisplay.runningPlanTableDisplay(rp_obj, self.tableWidgetPlan)

    # 设置实时绘图显示
    def realtimePlotSet(self, interval=int, plot_flag=bool):
        lock = threading.Lock()
        self.realtime_plot_interval = interval  # 默认3s绘图
        self.isRealtimePaint = plot_flag  # 实时绘图否

    # 事件处理函数绘制统计区域的 车辆牵引制动统计图
    def showStatisticsMvbDelay(self):
        if self.islogLoad == 1:
            self.train_com_delay = TrainComMeasureDlg(None, self.log)
            self.Log('Plot statistics info!', __name__, sys._getframe().f_lineno)
            try:
                self.train_com_delay.measurePlot()
                self.train_com_delay.show()
            except Exception as err:
                self.Log(err, __name__, sys._getframe().f_lineno)

    # 事件处理函数，获取文件树结构中双击的文件路径和文件名
    def filetabClicked(self, item_index):
        self.Log("Select from file tab", __name__, sys._getframe().f_lineno)
        if self.model.fileInfo(item_index).isDir():
            pass
        else:
            self.file = self.model.filePath(item_index)  # 带入modelIndex获取model的相关信息
            self.resetLogPlot()
            self.Log(self.model.fileName(item_index), __name__, sys._getframe().f_lineno)
            self.Log(self.model.filePath(item_index), __name__, sys._getframe().f_lineno)

    # 默认路径的更新，用于打开文件时，总打开最近一次的文件路径
    def updatePathChanged(self, path2):
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
    def versionMsg(self):
        reply = QtWidgets.QMessageBox.information(self,
        "版本信息",
        "Software:"+ self.verObj.getVerToken() + "\n\n"+self.verObj.getLicenseDescription(),
        QtWidgets.QMessageBox.Yes)

    # 事件处理函数，弹窗显示帮助信息
    def helpMsg(self):
        reply = QtWidgets.QMessageBox.information(self, 
        "帮助信息",
        "Software:" + self.verObj.getVerToken() + "\n\n"+self.verObj.getVerDescription(),
        QtWidgets.QMessageBox.Yes)

    # 记录文件处理核心函数，生成周期字典和绘图值列表
    def logProcess(self):
        self.isCursorInFram = 0
        # 创建文件读取对象
        self.log = FileProcess.FileProcess(self.file)  # 类的构造函数，函数中给出属性
        # 绑定信号量
        self.log.bar_show_signal.connect(self.progressBar.setValue)
        self.log.end_result_signal.connect(self.LogProcessResult)
        self.log.msg_atp_ato_signal.connect(self.msgAtp2atoTabShow)
        self.log.msg_tsrs_ato_signal.connect(self.msgTsrsatoTabShow)
        # 读取文件
        self.Log('Preprocess file path!', __name__, sys._getframe().f_lineno)
        self.log.start()  # 启动记录读取线程,run函数不能有返回值
        self.Log('Begin log read thread!', __name__, sys._getframe().f_lineno)
        self.showMessage('文件加载中...')
        return

    # 文件处理线程执行完响应方法
    def LogProcessResult(self):
        self.Log('End log read thread!', __name__, sys._getframe().f_lineno)
        isok = -1
        # 处理返回结果
        if self.log.get_time_use():
            [t1, t2, isok] = self.log.get_time_use()     # 0=ato控车，1=没有控车,2=没有周期
            self.showMessage("Info:预处理耗时:" + str(t1) + 's')
            # 记录中模式有AOR或AOS 或启机行号
            if isok == 0 or isok > 2:
                self.showMessage("Info:文本计算耗时:" + str(t2) + 's')
                max_c = int(max(self.log.cycle))
                min_c = int(min(self.log.cycle))
                self.tagLatestPosIdx = 0  # 每次加载文件后置为最小
                self.spinBox.setRange(min_c, max_c)
                self.showMessage("Info:曲线周期数:" + str(max_c - min_c) + ' ' + 'from' + str(min_c) + 'to' + str(max_c))
                self.spinBox.setValue(min_c)
                self.lbl_date.setText(self.log.cycle_dic[min_c].time)  # 显示起始周期
            elif isok == 1:
                self.showMessage("Info:文本计算耗时:" + str(t2) + 's')
                self.showMessage("Info:ATO没有控车！")
                max_c = int(max(self.log.cycle_dic.keys()))
                min_c = int(min(self.log.cycle_dic.keys()))
                self.tagLatestPosIdx = 0  # 每次加载文件后置为最小
                self.spinBox.setRange(min_c, max_c)
                self.showMessage("Info:曲线周期数:" + str(max_c - min_c) + ' ' + 'from' + str(min_c) + 'to' + str(max_c))
                self.spinBox.setValue(min_c)
                self.lbl_date.setText(self.log.cycle_dic[min_c].time)  # 显示起始周期
            elif isok == 2:
                self.showMessage("Info:记录中没有周期！")
            else:
                pass
        else:
            self.Log('Err Can not get time use', __name__, sys._getframe().f_lineno)
        # 后续弹窗提示
        self.afterLogProcess(isok)
        return isok

    # 文件加载后处理方法
    def afterLogProcess(self, is_ato_control):

        self.Log("End all file process:%d"%is_ato_control, __name__, sys._getframe().f_lineno)
        try:
            if is_ato_control == 0:
                self.islogLoad = 1  # 记录加载且ATO控车
                self.actionRealtime.setEnabled(False)
                # self.actionView.trigger()  # 目前无效果，待完善，目的 用于加载后重置坐标轴
                self.showMessage('界面准备中...')
                self.clearAxis()
                self.winInitAfterLoad()  # 记录加载成功且有控车时，初始化显示一些内容
                self.CBvato.setChecked(True)
                self.CBramp.setChecked(True)
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
            self.textEdit.append('Process file failure! \nPlease Predeal the file!')
        self.showMessage('处理完成!')

    # 用于一些界面加载记录初始化后显示的内容
    def winInitAfterLoad(self):
        trainDataFind = False
        self.barDisplay.setBarStat(90, 10, len(self.log.cycle_dic.keys())) # 从95%开始，界面准备占比5%
    
        self.Log("Begin search log key info", __name__, sys._getframe().f_lineno)
        # 搜索离线数据
        for cycle_num in self.log.cycle_dic.keys():
            # 计算进度条
            self.barDisplay.barMoving()
            # 预先设置 设置列车数据
            msg_atp2ato = self.log.cycle_dic[cycle_num].msg_atp2ato
            dateTime = self.log.cycle_dic[cycle_num].time
            # 添加折返相关按钮信息
            if msg_atp2ato.sp138_obj.updateflag:
                sp138 = msg_atp2ato.sp138_obj
                DisplayMsgield.disTbRelatedBtn(sp138.q_tb_cabbtn, sp138.q_tb_wsdbtn, sp138.q_startbtn, dateTime, self.txt_atp2ato_msg)
            # 添加列车数据
            if (not trainDataFind) and msg_atp2ato.sp5_obj.updateflag:
                self.atpTrainDataShowByMsg(self.log.cycle_dic[cycle_num].msg_atp2ato)
                AtoKeyInfoDisplay.lableFieldDisplay("n_units",msg_atp2ato.sp5_obj.n_units, Atp2atoFieldDic, self.lbl_trainlen)
                trainDataFind = True
            # 添加纯文本信息
            if msg_atp2ato.sp134_obj.updateflag:
                DisplayMsgield.disPlainText(msg_atp2ato.sp134_obj, dateTime, self.txt_atp2ato_msg)
            # 添加折返变化
            if msg_atp2ato.sp13_obj.updateflag:
                DisplayMsgield.disTbStatus(msg_atp2ato.sp13_obj, dateTime, self.txt_atp2ato_msg)

        # 显示BTM信息
        self.Log("Begin search btm info", __name__, sys._getframe().f_lineno)
        BtmInfoDisplay.displayOffLineBtmTable(self.log.cycle_dic, self.tableATPBTM)

        # 显示IO信息
        self.Log("Begin search IO info", __name__, sys._getframe().f_lineno)
        self.setIoContentAfterLoad()
        try:
            # 事件发生相关
            if self.islogLoad == 1:
                self.sp.set_wayside_info_in_cords(self.log.cycle_dic, self.log.s, self.log.cycle)
                if self.actionJD.isChecked():
                    self.updateEventPointType()    # 若已经选中直接更新
                else:
                    self.actionJD.trigger()
                # 如果没选中 trigger一下
                if self.actionBTM.isChecked():
                    self.updateEventPointType()    # 若已经选中直接更新
                else:
                    self.actionBTM.trigger()
                self.Log("Comput wayside info and trigger BTM event", __name__, sys._getframe().f_lineno)
            else:
                pass
        except Exception as err:
            self.Log(err, __name__, sys._getframe().f_lineno)

    # 界面初始化后，加载显示IO信息，参考应答器显示
    def setIoContentAfterLoad(self):
        # 搜索IO信息
        for idx in self.log.cycle_dic.keys():
            cycleObj = self.log.cycle_dic[idx]
            if cycleObj and (cycleObj.ioInfo.updateflagIn or cycleObj.ioInfo.updateflagOut):
                AtoKeyInfoDisplay.ioInfoDisplay(str(cycleObj.cycle_num), cycleObj.time, cycleObj.ioInfo, self.tb_ato_IN, self.tb_ato_OUT)
 
    # 事件处理函数，计数器数值变化触发事件，绑定光标和内容更新
    def spinValueChanged(self):
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
                        xy_lim = self.sp.update_cord_with_cursor((int(info[0]), int(info[1])), self.sp.mainAxes.get_xlim(),
                                                                 self.sp.mainAxes.get_ylim())
                        # 如果超出范围再更新
                        is_update = xy_lim[2]
                        if is_update == 1:
                            self.sp.mainAxes.set_xlim(xy_lim[0][0], xy_lim[0][1])
                            self.sp.mainAxes.set_ylim(xy_lim[1][0], xy_lim[1][1])
                            self.updateUpCure()

                            if track_flag == 0:  # 如果之前是锁定的，更新后依然锁定在最新位置
                                self.sp.set_track_status()

                        # 再更新光标
                        self.cursorVato.sim_mouse_move(int(info[0]), int(info[1]))  # 其中前两者位置和速度为移动目标
                    elif self.curveCordType == 1:
                        # 先更新坐标轴范围
                        xy_lim = self.sp.update_cord_with_cursor((int(cur_cycle), int(info[1])),
                                                                 self.sp.mainAxes.get_xlim(),
                                                                 self.sp.mainAxes.get_ylim())
                        # 如果超出范围再更新
                        is_update = xy_lim[2]
                        if is_update == 1:
                            self.sp.mainAxes.set_xlim(xy_lim[0][0], xy_lim[0][1])
                            self.sp.mainAxes.set_ylim(xy_lim[1][0], xy_lim[1][1])
                            self.updateUpCure()
                            if track_flag == 0:
                                self.sp.set_track_status()
                        # 再更新光标
                        self.cursorVato.sim_mouse_move(int(cur_cycle), int(info[1]))  # 绘制速度周期曲线时查询为周期，速度
                else:
                    # 因为移动光标意味着重发信号，单纯移动光标有歧义，若发送信号有可能造成大量新防护问题，这里暂不修改。
                    self.showMessage('Err:光标不更新，该周期控车信息丢失')
            else:
                self.showMessage('Err:记录边界或周期丢失！')
        else:
            pass  # 否则 不处理

    # 事件处理函数，启动后进入测量状态
    def ctrlMeasure(self):
        # 加载文件才能测量
        if self.islogLoad == 1:
            self.ctrlMeasureStatus = 1  # 一旦单击则进入测量开始状态
            self.sp.setCursor(QtCore.Qt.WhatsThisCursor)
            self.Log('start measure!', __name__, sys._getframe().f_lineno)
        else:
            self.showMessage("Info:记录未加载，不测量")

    # 事件处理函数，标记单击事件
    def ctrlMeasureClicked(self, event):
        # 如果开始测量则进入，则获取终点
        if self.ctrlMeasureStatus == 2:
            # 下面是当前鼠标坐标
            x, y = event.xdata, event.ydata
            # 速度位置曲线
            if self.curveCordType == 0:
                self.indx_measure_end = min(np.searchsorted(self.log.s, [x])[0], len(self.log.s) - 1)
            # 周期速度曲线
            if self.curveCordType == 1:
                self.indx_measure_end = min(np.searchsorted(self.log.cycle, [x])[0], len(self.log.cycle) - 1)
            self.measure = CtrlMeasureDlg(None, self.log)
            self.measure.measurePlot(self.indx_measure_start, self.indx_measure_end, self.curveCordType)
            self.measure.show()

            # 获取终点索引，测量结束
            self.ctrlMeasureStatus = 3
            self.Log('end measure!', __name__, sys._getframe().f_lineno)
            # 更改图标
            if self.curWinMode == 1:  # 标记模式
                self.sp.setCursor(QtCore.Qt.PointingHandCursor)  # 如果对象直接self.那么在图像上光标就不变，面向对象操作
            elif self.curWinMode == 0:  # 浏览模式
                self.sp.setCursor(QtCore.Qt.ArrowCursor)

        # 如果是初始状态，则设置为启动
        if self.ctrlMeasureStatus == 1:
            self.Log('begin measure!', __name__, sys._getframe().f_lineno)
            # 下面是当前鼠标坐标
            x, y = event.xdata, event.ydata
            # 速度位置曲线
            if self.curveCordType == 0:
                self.indx_measure_start = min(np.searchsorted(self.log.s, [x])[0], len(self.log.s) - 1)
                self.ctrlMeasureStatus = 2
            # 周期速度曲线
            if self.curveCordType == 1:
                self.indx_measure_start = min(np.searchsorted(self.log.cycle, [x])[0], len(self.log.cycle) - 1)
                self.ctrlMeasureStatus = 2

    # 事件处理函数，更新光标进入图像标志，in=1
    def cursorInFigEventProcess(self, event):
        self.isCursorInFram = 1
        self.cursorVato.move_signal.connect(self.setCtrlTableAllContentByIndex)  # 进入图后绑定光标触发

    # 事件处理函数，更新光标进入图像标志,out=2
    def cursorOutFigEventProcess(self, event):
        self.isCursorInFram = 2
        try:
            self.cursorVato.move_signal.disconnect(self.setCtrlTableAllContentByIndex)  # 离开图后解除光标触发
        except Exception as err:
            self.Log(err, __name__, sys._getframe().f_lineno)
        # 测量立即终止，恢复初始态:
        if self.ctrlMeasureStatus > 0:
            self.ctrlMeasureStatus = 0
            # 更改图标
            if self.curWinMode == 1:  # 标记模式
                self.sp.setCursor(QtCore.Qt.PointingHandCursor)  # 如果对象直接self.那么在图像上光标就不变，面向对象操作
            elif self.curWinMode == 0:  # 浏览模式
                self.sp.setCursor(QtCore.Qt.ArrowCursor)
            self.Log('exit measure', __name__, sys._getframe().f_lineno)

    # 绘制各种速度位置曲线
    def updateUpCure(self):
        # file is load
        if self.islogLoad == 1:
            x_monitor = self.sp.mainAxes.get_xlim()
            y_monitor = self.sp.mainAxes.get_ylim()
            if self.CBvato.isChecked() or self.CBcmdv.isChecked() or self.CBatppmtv.isChecked() \
                    or self.CBatpcmdv.isChecked() or self.CBlevel.isChecked() or self.CBramp.isChecked() or self.CBstate.isChecked():
                self.clearAxis()
                self.Log("Mode Change recreate the paint", __name__, sys._getframe().f_lineno)
                # 清除光标重新创建
                if self.curWinMode == 1:
                    # 重绘文字
                    self.sp.plot_ctrl_text(self.log, self.tagLatestPosIdx, self.bubbleStatus, self.curveCordType)
                    self.Log("Update ctrl text ", __name__, sys._getframe().f_lineno)
                    if self.isCursorCreated == 1:
                        self.isCursorCreated = 0
                        del self.cursorVato
                    self.tagCursorCreate()
                    self.Log("Update Curve recreate curve and tag cursor ", __name__, sys._getframe().f_lineno)
                # 处理ATO速度
                if self.CBvato.isChecked():
                    self.sp.plotLogVS(self.log, self.curWinMode, self.curveCordType)
                else:
                    self.CBvato.setChecked(False)
                # 处理命令速度
                if self.CBcmdv.isChecked():
                    self.sp.plotLogVcmdv(self.log, self.curWinMode, self.curveCordType)
                else:
                    self.CBcmdv.setChecked(False)
                # 处理允许速度
                if self.CBatppmtv.isChecked():
                    self.sp.plotLogVatpPmt(self.log, self.curWinMode, self.curveCordType)
                else:
                    self.CBatppmtv.setChecked(False)
                # 处理顶棚速度
                if self.CBatpcmdv.isChecked():
                    self.sp.plotLogVceil(self.log, self.curveCordType)
                else:
                    self.CBatpcmdv.setChecked(False)
                # 处理级位
                if self.CBlevel.isChecked():
                    self.sp.plotLogLevel(self.log, self.curveCordType)
                else:
                    self.CBlevel.setChecked(False)
                # 处理级位
                if self.CBramp.isChecked():
                    self.spAux.plotLogRamp(self.log, self.curveCordType)
                else:
                    self.CBramp.setChecked(False)
                # 处理状态机
                if self.CBstate.isChecked():
                    self.spAux.plotLogState(self.log, self.curveCordType)
                else:
                    self.CBstate.setChecked(False)
            else:
                self.clearAxis()
            self.sp.plotMainSpeedCord(self.log, self.curveCordType, x_monitor, y_monitor)
            self.spAux.plotMainRampCord(self.log, self.curveCordType)
        else:
            pass

    # 绘制离线模式下事件选择点
    def updateEventPointType(self):
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
            self.updateUpCure()

    # 清除图像和轴相关内容，画板清屏
    def clearAxis(self):
        try:
            if self.islogLoad == 1:
                self.sp.mainAxes.clear()
                self.sp.twinAxes.clear()
                self.spAux.mainAxes.clear()
                self.spAux.twinAxes.clear()
                self.sp.plotReset()
        except Exception as err:
            print(err)

    # 封装用于在文本框显示字符串
    def showMessage(self, s):
        self.textEdit.append(s)

    # 模式转换函数，修改全局模式变量和光标
    def modeChange(self):
        sender = self.sender()
        # 查看信号发送者
        if sender.text() == '标注模式' and self.curWinMode == 0:  # 由浏览模式进入标注模式不重绘范围
            self.curWinMode = 1
            if self.islogLoad == 1 and self.CBvato.isChecked():
                self.Log("Mode Change excute!", __name__, sys._getframe().f_lineno)
                self.updateUpCure()
                self.tagCursorCreate()  # 只针对速度曲线
        elif sender.text() == '浏览模式' and self.curWinMode == 1:  # 进入浏览模式重绘
            self.curWinMode = 0
            if self.islogLoad == 1:
                self.updateUpCure()
                # 重置坐标轴范围,恢复浏览模式必须重置范围
                self.sp.plotMainSpeedCord(self.log, self.curveCordType, (0.0, 1.0), (0.0, 1.0))
                self.spAux.plotMainRampCord(self.log, self.curveCordType)
            self.tagCursorCreate()
        else:
            pass
            # 其他情况目前无需重置坐标系
        self.sp.draw()
        self.spAux.draw()
        # 更改图标
        if self.curWinMode == 1:  # 标记模式
            self.sp.setCursor(QtCore.Qt.PointingHandCursor)  # 如果对象直接self.那么在图像上光标就不变，面向对象操作
        elif self.curWinMode == 0:  # 浏览模式
            self.sp.setCursor(QtCore.Qt.ArrowCursor)
        self.statusbar.showMessage(self.file + " " + "当前模式：" + sender.text())

    # 曲线类型转换函数，修改全局模式变量
    def cmdChange(self):
        if self.islogLoad == 1:
            sender = self.sender()
            if sender.text() == '位置速度曲线':
                if self.curveCordType == 1:
                    self.curveCordType = 0  # 曲线类型改变，如果有光标则删除，并重置标志
                    if self.isCursorCreated == 1:
                        del self.cursorVato
                        self.isCursorCreated = 0
                    else:
                        pass
                    self.updateUpCure()
                    self.tagCursorCreate()  # 根据需要重新创建光标
                else:
                    pass
            if sender.text() == "周期速度曲线":
                if self.curveCordType == 0:
                    self.curveCordType = 1  # 曲线类型改变
                    if self.isCursorCreated == 1:
                        del self.cursorVato
                        self.isCursorCreated = 0
                    else:
                        pass
                    self.updateUpCure()
                    self.tagCursorCreate()
                else:
                    pass
            # 重置坐标轴范围
            self.sp.plotMainSpeedCord(self.log, self.curveCordType, (0.0, 1.0), (0.0, 1.0))
            self.spAux.plotMainRampCord(self.log, self.curveCordType)
            self.statusbar.showMessage(self.file + " " + "曲线类型：" + sender.text())
        else:
            pass

    # 用于模式转换后处理，创建光标绑定和解绑槽函数
    def tagCursorCreate(self):
        # 标注模式
        if self.curWinMode == 1 and 0 == self.isCursorCreated:
            if self.curveCordType == 0:
                self.cursorVato = SnaptoCursor(self.sp.mainAxes, self.log.s, self.log.v_ato, 
                                               self.spAux.mainAxes, self.log.s, self.log.v_ato)  # 初始化一个光标
            else:
                self.cursorVato = SnaptoCursor(self.sp.mainAxes, self.log.cycle, self.log.v_ato,
                                               self.spAux.mainAxes, self.log.cycle, self.log.v_ato)  # 初始化一个光标
            self.cursorVato.resetCursorPlot()
            self.Log("Link Signal to Tag Cursor", __name__, sys._getframe().f_lineno)
            self.cid1 = self.sp.mpl_connect('motion_notify_event', self.cursorVato.mouse_move)
            self.cid2 = self.sp.mpl_connect('figure_enter_event', self.cursorInFigEventProcess)
            self.cid3 = self.sp.mpl_connect('figure_leave_event', self.cursorOutFigEventProcess)
            self.cursorVato.move_signal.connect(self.setCtrlTableAllContentByIndex)  # 连接图表更新的槽函数
            self.cursorVato.sim_move_singal.connect(self.setCtrlTableAllContentByIndex)
            self.cursorVato.move_signal.connect(self.setProtocolTreeByIndex)  # 连接信号槽函数
            self.cursorVato.sim_move_singal.connect(self.setProtocolTreeByIndex)  # 连接信号槽函数
            self.cursorVato.move_signal.connect(self.setCtrlBubbleByIndex)
            self.cursorVato.sim_move_singal.connect(self.setCtrlBubbleByIndex)
            self.cursorVato.move_signal.connect(self.setTrainContentByIndex)
            self.cursorVato.sim_move_singal.connect(self.setTrainContentByIndex)
            self.cursorVato.move_signal.connect(self.setPlanContentByIndex)
            self.cursorVato.sim_move_singal.connect(self.setPlanContentByIndex)
            self.cursorVato.sim_move_singal.connect(self.setAtpContentByIndex)
            self.cursorVato.move_signal.connect(self.setAtpContentByIndex)
            self.cursorVato.move_signal.connect(self.setSduContentByIndex)
            self.cursorVato.sim_move_singal.connect(self.setSduContentByIndex)
            self.cursorVato.move_signal.connect(self.setAtoStatusLabelByIndex)  # 标签
            self.cursorVato.sim_move_singal.connect(self.setAtoStatusLabelByIndex)
            self.isCursorCreated = 1
        elif self.curWinMode == 0 and 1 == self.isCursorCreated:
            self.sp.mpl_disconnect(self.cid1)
            self.sp.mpl_disconnect(self.cid2)
            self.sp.mpl_disconnect(self.cid3)
            self.cursorVato.move_signal.disconnect(self.setCtrlTableAllContentByIndex)
            self.cursorVato.sim_move_singal.disconnect(self.setCtrlTableAllContentByIndex)
            self.cursorVato.move_signal.disconnect(self.setProtocolTreeByIndex)  # 连接信号槽函数
            self.cursorVato.sim_move_singal.disconnect(self.setProtocolTreeByIndex)  # 连接信号槽函数
            self.cursorVato.move_signal.disconnect(self.setCtrlBubbleByIndex)
            self.cursorVato.sim_move_singal.disconnect(self.setCtrlBubbleByIndex)
            self.cursorVato.move_signal.disconnect(self.setTrainContentByIndex)
            self.cursorVato.sim_move_singal.disconnect(self.setTrainContentByIndex)
            self.cursorVato.move_signal.disconnect(self.setPlanContentByIndex)
            self.cursorVato.sim_move_singal.disconnect(self.setPlanContentByIndex)
            self.cursorVato.move_signal.disconnect(self.setAtpContentByIndex)
            self.cursorVato.sim_move_singal.disconnect(self.setAtpContentByIndex)
            self.cursorVato.move_signal.disconnect(self.setAtoStatusLabelByIndex)
            self.cursorVato.sim_move_singal.disconnect(self.setAtoStatusLabelByIndex)
            self.cursorVato.move_signal.disconnect(self.setSduContentByIndex)  # 标签
            self.cursorVato.sim_move_singal.disconnect(self.setSduContentByIndex)
            self.isCursorCreated = 0
            del self.cursorVato
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
    def homeShow(self):
        self.clearAxis()
        self.resetAllCheckbox()
        self.CBvato.setChecked(True)
        self.CBramp.setChecked(True)
        self.resetTextEdit()
        if self.islogLoad == 1:
            #self.sp.plotMainSpeedCord(self.log, self.curveCordType, (0.0, 1.0), (0.0, 1.0))
            self.updateUpCure()
        else:
            pass

    # 关闭当前绘图
    def closeFigure(self, evt):
        if self.islogLoad == 1:
            self.textEdit.append('Close Log Plot\n')
            self.clearAxis()
            self.islogLoad = 0
            self.actionRealtime.setEnabled(True)
            self.sp.draw()
            self.spAux.draw()
        else:
            pass

    # 事件处理函数，用于弹窗显示当前索引周期
    def cyclePrint(self):
        self.cyclewin.statusBar.showMessage('')  # 清除上一次显示内容
        idx = self.spinBox.value()
        printFlag = 0  # 是否弹窗打印，0=不弹窗，1=弹窗
        cNum = 0
        self.cyclewin.textEdit.clear()

        if 1 == self.islogLoad or 2 == self.islogLoad:  # 文件已经加载
            # 前提是必须有周期，字典能查到
            if idx in self.log.cycle_dic.keys():
                cycleObj = self.log.cycle_dic[idx]
                cNum = cycleObj.cycle_num
                with open(self.file, 'r',encoding='gbk', errors='ignore', newline='') as f:
                    f.seek(cycleObj.file_begin_offset, 0)
                    txtLines = ''
                    txtLines = f.read(cycleObj.file_end_offset - cycleObj.file_begin_offset)  
                    self.cyclewin.textEdit.setText(txtLines)
                # 周期完整性
                if self.log.cycle_dic[idx].cycle_property == 1:
                    self.cyclewin.statusBar.showMessage(str(cNum) + '周期序列完整！')
                elif self.log.cycle_dic[idx].cycle_property == 2:
                    self.cyclewin.statusBar.showMessage(str(cNum) + '周期尾部缺失！')
                elif self.log.cycle_dic[idx].cycle_property == 3:
                    self.cyclewin.statusBar.showMessage(str(cNum) + '周期头部缺失！')
                else:
                    self.cyclewin.statusBar.showMessage('记录异常！')  # 清除上一次显示内容
                printFlag = 1
            else:
                self.showMessage("Info：周期不存在，查询无效")
        else:
            self.showMessage("Info：文件未加载，查询无效")
        # 有信息才弹窗
        if printFlag == 1:
            self.cyclewin.setWindowTitle("周期号:"+str(cNum))
            self.cyclewin.show()
        else:
            pass

    # 设置主界面表格的格式
    def setCtrlTableFormat(self):
      pass

    # 事件处理函数，设置主界面表格内容
    def setCtrlTableAllContentByIndex(self, idx):
        # 不妨使用位置长度进行防护
        if idx < len(self.log.s):
            atoPos = int(self.log.s[idx])
            atoSpeed = int(self.log.v_ato[idx])
            level = int(self.log.level[idx])
            esLevel = int(self.log.real_level[idx])
            ramp = int(self.log.ramp[idx])
            esRamp = int(self.log.adjramp[idx])
            stateMachine = int(self.log.statmachine[idx])
            tPos = int(self.log.targetpos[idx])
            tSpeed = int(self.log.v_target[idx])
            atoCmdv = int(self.log.cmdv[idx])
            atpCmdv = int(self.log.ceilv[idx])
            atpPmtv = int(self.log.atp_permit_v[idx])
            skip    = int(self.log.skip[idx])
            keyList = [atoPos,atoSpeed,level,esLevel,ramp,esRamp,stateMachine,tPos,tSpeed,atoCmdv,atpCmdv,atpPmtv,skip]
            self.setCtrlInfoShow(keyList)
            # 停车点表格显示
            stTuple = self.log.cycle_dic[self.log.cycle[idx]].stoppoint
            self.setStoppointShow(atoPos,stTuple)
            # 停车误差显示
            atoStopErr = int(self.log.stop_error[idx])
            cycleObj = self.log.cycle_dic[self.log.cycle[idx]]
            AtoKeyInfoDisplay.ctrlStopErrorDisplay(atoStopErr, cycleObj.msg_atp2ato.sp2_obj.m_atp_stop_error, self.tb_ctrl_stoppoint)
            # 时间周期
            self.lbl_date.setText(self.log.cycle_dic[self.log.cycle[idx]].time)
            self.lbl_sys_time.setText(str(cycleObj.ostime_start)+'ms')
            self.spinBox.setValue(int(self.log.cycle_dic[self.log.cycle[idx]].cycle_num))
        else:
            pass

    # 辅助显示函数停车点
    def setStoppointShow(self, curPos=int, stTuple='tuple'):
        AtoKeyInfoDisplay.ctrlStoppointDisplay(stTuple, curPos, self.tb_ctrl_stoppoint)

    # 辅助显示函数控车信息
    def setCtrlInfoShow(self, keyList=list):
        [atoPos,atoSpeed,level,esLevel,ramp,esRamp,stateMachine,tPos,tSpeed,atoCmdv,atpCmdv,atpPmtv,skip] = keyList
        AtoKeyInfoDisplay.ctrlAtoPosDisplay(atoPos,self.lbl_ato_pos,self.led_ato_pos)
        AtoKeyInfoDisplay.ctrlAtoSpeedDisplay(atoSpeed, self.lbl_ato_speed, self.led_ato_speed)
        # 获取配置的级位范围
        lvlLimit = [self.cfg.monitor_config.max_tract_level, self.cfg.monitor_config.max_brake_level]
        AtoKeyInfoDisplay.ctrlLevelDisplay(level, lvlLimit, self.lbl_ctrl_level, self.led_ctrl_level)
        AtoKeyInfoDisplay.ctrlEstimateLevelDisplay(esLevel, lvlLimit, self.lbl_ctrl_estimate_level, self.led_ctrl_estimate_level)
        AtoKeyInfoDisplay.ctrlRampDisplay(ramp,self.lbl_ramp, self.led_ramp)
        AtoKeyInfoDisplay.ctrlEstimateRampDisplay(esRamp, self.lbl_estimate_ramp, self.led_estimate_ramp)
        AtoKeyInfoDisplay.ctrlSkipDisplay(skip,self.lbl_is_skip)
        AtoKeyInfoDisplay.ctrlStateMachineDisplay(stateMachine, self.lbl_ctrl_statemachine, self.led_ctrl_statemachine)
        AtoKeyInfoDisplay.ctrlTargetPosDisplay(tPos, self.lbl_target_pos, self.led_target_pos)
        AtoKeyInfoDisplay.ctrlTargetSpeedDisplay(tSpeed, self.lbl_target_speed, self.led_target_speed)
        AtoKeyInfoDisplay.ctrlTargetDisDisplay(tPos, atoPos, self.lbl_target_dis, self.led_target_dis)
        # 速度表格显示
        vStrList = [atoSpeed, atoCmdv, atpCmdv, atpPmtv]
        AtoKeyInfoDisplay.ctrlSpeedDisplay(vStrList, self.tb_ctrl_speed)

    # 事件处理函数，用于设置气泡格式，目前只设置位置
    def setCtrlBubbleFormat(self):
        sender = self.sender()
        # 清除光标重新创建
        if self.curWinMode == 1:
            if sender.text() == '跟随光标':
                self.bubbleStatus = 1  # 1 跟随模式，立即更新
                self.sp.plot_ctrl_text(self.log, self.tagLatestPosIdx, self.bubbleStatus, self.curveCordType)
            elif sender.text() == '停靠窗口':
                self.bubbleStatus = 0  # 0 是停靠，默认右上角，立即更新
                self.sp.plot_ctrl_text(self.log, self.tagLatestPosIdx, self.bubbleStatus, self.curveCordType)
            else:
                pass
        self.sp.draw()

    # 事件处理函数，计算控车数据悬浮气泡窗并显示
    def setCtrlBubbleByIndex(self, idx):
        # 根据输入类型设置气泡
        if idx < len(self.log.s):
            self.sp.plot_ctrl_text(self.log, idx, self.bubbleStatus, self.curveCordType)
            self.tagLatestPosIdx = idx

    # 事件处理函数，设置树形结构和内容
    def setProtocolTreeByIndex(self, idx):
        if idx < len(self.log.s):
            cycle_obj = self.log.cycle_dic[self.log.cycle[idx]]
            AtoKeyInfoDisplay.disMsgOutlineTree(cycle_obj.msg_ato2tsrs, cycle_obj.msg_tsrs2ato, 
            cycle_obj.msg_atp2ato, self.tree_protocol)

    # 事件处理函数，设置车辆接口MVB信息
    def setTrainContentByIndex(self, idx):
        if idx < len(self.log.s):
            cycleObj = self.log.cycle_dic[self.log.cycle[idx]]
            if cycleObj.a2t_ctrl.updateflag or cycleObj.a2t_stat.updateflag or cycleObj.t2a_stat.updateflag:
                self.mvbShowByData(cycleObj.a2t_ctrl, cycleObj.a2t_stat, cycleObj.t2a_stat)
    
    # 事件处理函数，设置ATP信息
    def setAtpContentByIndex(self, idx):
        if idx < len(self.log.s):
            msg_obj = self.log.cycle_dic[self.log.cycle[idx]].msg_atp2ato
            dataTime = self.log.cycle_dic[self.log.cycle[idx]].time
            self.atpCommonInfoShowByMsg(msg_obj, dataTime)
            self.atoDmiShowByMsg(msg_obj)

    # 事件处理函数，设置计划信息
    def setPlanContentByIndex(self, idx):
        if idx < len(self.log.s):
            cycle_obj = self.log.cycle_dic[self.log.cycle[idx]]
            rp_obj = cycle_obj.rpInfo
            self.runningPlanShow(rp_obj, cycle_obj.ostime_start)
            # 显示折返计划
            a2tMsg = cycle_obj.msg_ato2tsrs
            t2aMsg = cycle_obj.msg_tsrs2ato
            AtoKeyInfoDisplay.disTurnbackTable(a2tMsg, t2aMsg, self.lbl_ato_tbstatus, self.tableWidgetTb)
            
    # 事件处理函数，双击跳转
    def btmSelectedCursorGo(self, rowItem):
        if self.curInterface == 1 and self.curWinMode == 1:  # 必须标记模式:
            c_num = BtmInfoDisplay.btmCycleList[rowItem.row()]
            try:
                self.spinBox.setValue(c_num)
            except Exception as err:
                self.Log(err, __name__, sys._getframe().f_lineno)

    # 事件处理函数，应答器表格选中事件显示
    def btmSelectedInfo(self, rowItem):
        sp7_obj = None
        if self.curInterface == 1 and self.curWinMode == 1:  # 必须标记模式:
            # 获取SP7应答器包对象
            sp7_obj = BtmInfoDisplay.GetBtmDicItemSelected(self.log.cycle_dic, rowItem, 
            self.curInterface, self.curWinMode)
        if self.curInterface == 2:
            sp7_obj = BtmInfoDisplay.GetBtmRealItemSelected(rowItem, self.curInterface)

        if sp7_obj:
            BtmInfoDisplay.displayBtmItemSelInfo(sp7_obj, self.led_with_c13, self.led_platform_pos, 
            self.led_platform_door,self.led_track, self.led_stop_d_JD, self.led_btm_id)

    # 事件处理函数，双击解析
    def msgAtp2atoSelectedParserGo(self, rowItem=QtWidgets.QTableWidgetItem):
        # 获取周期
        c_num = int(self.tab_atp_ato.item(rowItem.row(), 1).text())
        if self.log and c_num in self.log.cycle_dic.keys():
            try:
                cycle_obj = self.log.cycle_dic[c_num]
                if 'P->O' == self.tab_atp_ato.item(rowItem.row(), 2).text() and cycle_obj.atp2atoRawBytes:
                    self.atpParserDlg.textEdit.setText(bytes.hex(cycle_obj.atp2atoRawBytes).upper())
                elif 'O->P' == self.tab_atp_ato.item(rowItem.row(), 2).text() and cycle_obj.ato2atpRawBytes:
                    self.atpParserDlg.textEdit.setText(bytes.hex(cycle_obj.ato2atpRawBytes).upper())
                else:
                    pass
                self.atpParserDlg.actionParse.trigger()
                self.atpParserDlg.show()
            except Exception as err:
                self.Log(err, __name__, sys._getframe().f_lineno)

    # 事件处理函数，单击显示
    def msgAtp2atoSelectedInfo(self, rowItem):
        # 获取周期
        c_num = int(self.tab_atp_ato.item(rowItem.row(), 1).text())
        if self.log and c_num in self.log.cycle_dic.keys():
            try:
                cycle_obj = self.log.cycle_dic[c_num]
                if 'P->O' == self.tab_atp_ato.item(rowItem.row(), 2).text() and cycle_obj.atp2atoRawBytes:
                    self.txt_atpato_protocol.setText(bytes.hex(cycle_obj.atp2atoRawBytes).upper())
                elif 'O->P' == self.tab_atp_ato.item(rowItem.row(), 2).text() and cycle_obj.ato2atpRawBytes:
                    self.txt_atpato_protocol.setText(bytes.hex(cycle_obj.ato2atpRawBytes).upper())
                else:
                    pass
            except Exception as err:
                self.Log(err, __name__, sys._getframe().f_lineno)

    # 事件处理函数，显示ATPATO消息表格
    def msgAtp2atoTabShow(self, rst='tuple'):
        msgObj=rst[0]
        dateTime=rst[1]
        cycleNum=rst[2]
        DisplayMsgield.disMsgAtpatoTab(msgObj, dateTime, cycleNum, self.tab_atp_ato)

    # 事件处理函数，单击显示
    def msgTsrs2atoSelectedInfo(self, rowItem):
        # 获取周期
        c_num = int(self.tab_tsrs_ato.item(rowItem.row(), 1).text())
        if self.log and c_num in self.log.cycle_dic.keys():
            try:
                cycle_obj = self.log.cycle_dic[c_num]
                if 'T->A' == self.tab_tsrs_ato.item(rowItem.row(), 2).text() and cycle_obj.tsrs2atoRawBytes:
                    self.txt_tsrsato_protocol.setText(bytes.hex(cycle_obj.tsrs2atoRawBytes).upper())
                elif 'A->T' == self.tab_tsrs_ato.item(rowItem.row(), 2).text() and cycle_obj.ato2tsrsRawBytes:
                    self.txt_tsrsato_protocol.setText(bytes.hex(cycle_obj.ato2tsrsRawBytes).upper())
                else:
                    pass
            except Exception as err:
                self.Log(err, __name__, sys._getframe().f_lineno)

    # 事件处理函数，双击解析
    def msgTsrsatoSelectedParserGo(self, rowItem=QtWidgets.QTableWidgetItem):
         # 获取周期
        c_num = int(self.tab_tsrs_ato.item(rowItem.row(), 1).text())
        if self.log and c_num in self.log.cycle_dic.keys():
            try:
                cycle_obj = self.log.cycle_dic[c_num]
                if 'T->A' == self.tab_tsrs_ato.item(rowItem.row(), 2).text() and cycle_obj.tsrs2atoRawBytes:
                    self.tsrsParserDlg.textEdit.setText(bytes.hex(cycle_obj.tsrs2atoRawBytes).upper())
                    self.tsrsParserDlg.setBytesDir('T->A')
                elif 'A->T' == self.tab_tsrs_ato.item(rowItem.row(), 2).text() and cycle_obj.ato2tsrsRawBytes:
                    self.tsrsParserDlg.textEdit.setText(bytes.hex(cycle_obj.ato2tsrsRawBytes).upper())
                    self.tsrsParserDlg.setBytesDir('A->T')
                else:
                    self.tsrsParserDlg.setBytesDir(None)
                self.tsrsParserDlg.actionParse.trigger()
                self.tsrsParserDlg.show()
            except Exception as err:
                self.Log(err, __name__, sys._getframe().f_lineno)       
        else:
            print('msgTsrsatoSelectedParserGo unknown cycle id:%d'%c_num)
            
    # 事件处理函数，显示TSRSATO消息表格
    def msgTsrsatoTabShow(self, rst='tuple'):
        dirStr = rst[0]
        msgObj=rst[1]
        dateTime=rst[2]
        cycleNum=rst[3]
        if dirStr == 'T->A':
            DisplayMsgield.disMsgTsrsatoTab(msgObj, dateTime, cycleNum, self.tab_tsrs_ato)
        elif dirStr == 'A->T':
            DisplayMsgield.disMsgAtotsrsTab(msgObj, dateTime, cycleNum, self.tab_tsrs_ato)
        else:
            pass

    # 事件处理函数,ATP-ATO协议树快速跳转
    def msgAtpatoTreeSelectedParserGo(self, root=QtWidgets.QTreeWidgetItem):
        dirFlag = None
        if 'Pkt:250' in root.text(0):
            dirFlag = 'P->O'
        elif 'Pkt:251' in root.text(0):
            dirFlag = 'O->P'
        else:
            pass
        # 处理文本
        if dirFlag:
            c_num = self.spinBox.value()
            if c_num in self.log.cycle_dic.keys():
                try:
                    cycle_obj = self.log.cycle_dic[c_num]
                    if 'P->O' == dirFlag and cycle_obj.atp2atoRawBytes:
                        self.atpParserDlg.textEdit.setText(bytes.hex(cycle_obj.atp2atoRawBytes).upper())
                    elif 'O->P' == dirFlag and cycle_obj.ato2atpRawBytes:
                        self.atpParserDlg.textEdit.setText(bytes.hex(cycle_obj.ato2atpRawBytes).upper())
                    else:
                        pass
                    self.atpParserDlg.actionParse.trigger()
                    self.atpParserDlg.show()
                except Exception as err:
                    self.Log(err, __name__, sys._getframe().f_lineno)
            else:
                print('msgAtpatoTreeSelectedParserGo unknown cycle id:%d'%c_num)
        else:
            pass

    # 事件处理函数,TSRS-ATO协议树快速跳转
    def msgTsrsatoTreeSelectedParserGo(self, root=QtWidgets.QTreeWidgetItem):
        dirFlag = None
        rootParent = root.parent()
        if rootParent:
            if 'TSRS->ATO' in rootParent.text(0):
                dirFlag = 'T->A'
            elif 'ATO->TSRS' in rootParent.text(0):
                dirFlag = 'A->T'
            else:
                pass
        # 处理文本
        if dirFlag:
            c_num = self.spinBox.value()
            if c_num in self.log.cycle_dic.keys():
                try:
                    cycle_obj = self.log.cycle_dic[c_num]
                    if 'T->A' == dirFlag and cycle_obj.tsrs2atoRawBytes:
                        self.tsrsParserDlg.textEdit.setText(bytes.hex(cycle_obj.tsrs2atoRawBytes).upper())
                        self.tsrsParserDlg.setBytesDir('T->A')
                    elif 'A->T' == dirFlag and cycle_obj.ato2tsrsRawBytes:
                        self.tsrsParserDlg.textEdit.setText(bytes.hex(cycle_obj.ato2tsrsRawBytes).upper())
                        self.tsrsParserDlg.setBytesDir('A->T')
                    else:
                        self.tsrsParserDlg.setBytesDir(None)
                    self.tsrsParserDlg.actionParse.trigger()
                    self.tsrsParserDlg.show()
                except Exception as err:
                    self.Log(err, __name__, sys._getframe().f_lineno)
            else:
                pass
        else:
            pass

    # 事件处理函数，显示测速测距信息
    def setSduContentByIndex(self, idx):
        if idx < len(self.log.s):
            cycle_obj = self.log.cycle_dic[self.log.cycle[idx]]
            sduObj = cycle_obj.sduInfo
            self.sduInfoShow(sduObj)

    # ATO状态显示标签
    def setAtoStatusLabelByIndex(self, idx):
        if idx < len(self.log.s):
            cycleItem = self.log.cycle_dic[self.log.cycle[idx]]
            self.atoFsmInfoShow(cycleItem.fsm, cycleItem.control, cycleItem.msg_atp2ato, cycleItem.t2a_stat)
            # 根据分相和主断路器设置光标
            if cycleItem.t2a_stat.main_circuit_breaker == 0x00 or cycleItem.msg_atp2ato.sp2_obj.m_ms_cmd == 1:
                self.cursorVato.boldRedEnabled(True)
            else:
                self.cursorVato.boldRedEnabled(False)

    # 重置主界面所有的选择框
    def resetAllCheckbox(self):
        self.CBstate.setChecked(False)
        self.CBatpcmdv.setChecked(False)
        self.CBlevel.setChecked(False)
        self.CBcmdv.setChecked(False)
        self.CBvato.setChecked(False)
        self.CBramp.setChecked(False)
        self.CBatppmtv.setChecked(False)
       
    # 重置主界面文本框
    def resetTextEdit(self):
        self.textEdit.setPlainText(time.strftime("%Y-%m-%d %H:%M:%S \n", time.localtime(time.time())))
        self.textEdit.setPlainText('open file : ' + self.file + ' OK! \n')

    # 重绘图形并重置选择框
    def resetLogPlot(self):
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
                self.resetAllCheckbox()
                self.resetTextEdit()
                self.curWinMode = 0  # 恢复初始浏览模式
                self.cfg.readConfigFile() # 更新mvb索引端口信息
                self.Log("Clear axes", __name__, sys._getframe().f_lineno)
                self.sp.mainAxes.clear()
                self.spAux.mainAxes.clear()
                self.textEdit.clear()
                self.tab_atp_ato.clearContents()
                self.tab_tsrs_ato.clearContents()
                DisplayMsgield.atpatoMsgCnt = 0
                DisplayMsgield.tsrsatoMsgCnt = 0
                self.Log('Init File log', __name__, sys._getframe().f_lineno)
                # 开始处理
                self.logProcess()
            except Exception as err:
                self.textEdit.append('Process file failure! \nPlease Predeal the file!')

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
        self.actionATPParser.setIcon(QtGui.QIcon(":IconFiles/ATPParser.png"))
        self.actionTSRSParser.setIcon(QtGui.QIcon(":IconFiles/TSRSParser.png"))
        self.actionRealTimePlot.setIcon(QtGui.QIcon(":IconFiles/realtimeset.png"))
        self.action_bubble_track.setIcon(QtGui.QIcon(":IconFiles/track.png"))
        self.action_bubble_dock.setIcon(QtGui.QIcon(":IconFiles/dock.png"))
        self.action_acc_measure.setIcon(QtGui.QIcon(":IconFiles/acc.png"))
        self.actionExport.setIcon(QtGui.QIcon(":IconFiles/export.png"))
        self.actionC3ATOTrans.setIcon(QtGui.QIcon(":IconFiles/translator.png"))
        self.actionReplay.setIcon(QtGui.QIcon(":IconFiles/replay.png"))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Mywindow()
    window.show()
    sys.exit(app.exec_())
