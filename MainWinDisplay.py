#!/usr/bin/env python
# encoding: utf-8
'''
Author: Zhengtang Bao
Contact: baozhengtang@crscd.com.cn
File: MainWinDisplay
Date: 2022-07-25 20:09:57
Desc: 主界面关键数据处理及显示功能
LastEditors: Zhengtang Bao
LastEditTime: 2022-08-13 15:07:57
'''

from ast import Pass, Return
import copy
from itertools import cycle
import math
import time
from xml.dom import INDEX_SIZE_ERR
from PyQt5 import QtWidgets,QtGui,QtCore
from ConfigInfo import ConfigFile
from MsgParse import Atp2atoProto, DisplayMsgield, sp2, sp7

# custom field
class InerCustomField(object):
    __slots__ = ["name","unit","meaning"]
    def __init__(self,n="field",u=None,m=None) -> None:
        self.name = n
        self.unit = u
        self.meaning = m  

# format rgb
FieldBGColorDic={
    "m_atomode":{1:"background-color: rgb(180, 180, 180);",
                 2:"background-color: rgb(255, 255, 0);",
                 3:"background-color: rgb(255, 255, 255);",
                 4:"background-color: rgb(30, 30, 30);"},

    "q_ato_hardpermit":{1:"background-color: rgb(0, 255, 127);",
                        2:"background-color: rgb(255, 0, 0);"},

    "q_atopermit":{1:"background-color: rgb(0, 255, 127);",
                   2:"background-color: rgb(255, 0, 0);"},
    
    "m_ms_cmd":{2:"background-color: rgb(0, 255, 127);",
                1:"background-color: rgb(255, 0, 0);"},

    "m_low_frequency": {0x00:"background-color: rgb(255, 0, 0);", # H码
                        0x01:"background-color: rgb(161, 161, 161);", # 无
                        0x02:"background-color: rgb(255, 215, 15);", #H
                        0x10:"background-color: rgb(163, 22, 43);",#HB
                        0x2A:"background-color: rgb(0, 255, 0);",# L4
                        0x2B:"background-color: rgb(0, 255, 0);",# L5
                        0x25:"background-color: rgb(255, 255, 0);",# U2S
                        0x23:"background-color: rgb(255, 255, 0);",# UUS
                        0x22:"background-color: rgb(255, 255, 0);",# UU
                        0x21:"background-color: rgb(255, 255, 0);",# U
                        0x24:"background-color: rgb(255, 255, 0);",# U2
                        0x26:"background-color: rgb(205, 255, 25);",# LU
                        0x28:"background-color: rgb(0, 255, 0);",# L2
                        0x27:"background-color: rgb(0, 255, 0);",# L
                        0x29:"background-color: rgb(0, 255, 0);",# L3
                       },

    "train_permit_ato":{0xAA:"background-color: rgb(0, 255, 127);",
                        0X00:"background-color: rgb(255, 0, 0);"},
                        
    'door_state':{0xAA:"background-color: rgb(0, 255, 127);",
                  0x00:"background-color: rgb(255, 0, 0);"},
                  
    "main_circuit_breaker":{0xAA:"background-color: rgb(0, 255, 127);",
                            0x00:"background-color: rgb(255, 0, 0);"}
    

}

InerFieldBGColorDic={
    # 发车指示灯
    'ato_start_lamp':{0:"background-color: rgb(100, 100, 100);",
                      1:"background-color: rgb(255, 255, 0);",
                      2:"background-color: rgb(0, 255, 0);"},

    "ato_self_check":{1:"background-color: rgb(0, 255, 127);",
                      0:"background-color: rgb(255, 0, 0);"},

    'rpPlanLegalFlg':{1:"background-color: rgb(0, 255, 0);",
                      0:"background-color: rgb(255, 0, 0);"},

    'rpPlanTimeout':{1:"background-color: rgb(255, 0, 0);",
                     0:"background-color: rgb(0, 255, 0);"},

    'rpPlanValid':{1:"background-color: rgb(0, 255, 0);",
                   0:"background-color: rgb(255, 0, 0);"},

    'rpTrainStnState':{1:"background-color: rgb(255, 170, 255);",
                       2:"background-color: rgb(85, 255, 255);",
                       0:"background-color: rgb(170, 170, 255);"}

}

AtoInerDic={
    'ato_start_lamp':InerCustomField('发车指示灯',None,{0:"发车灯灭",1:"发车灯闪",2:"发车灯常亮"}),
    'ato_self_check':InerCustomField('自检状态',None,{1:"自检正常",0:"自检失败"}),
    'station_flag':InerCustomField('站台标志',None,{1:"位于站内",0:"位于区间"}),
    'rpcurTrack':InerCustomField('当前股道',None,None),
    'rpStopStableFlg':InerCustomField('当前股道',None,{1:'列车停稳',0:'未停稳'}),
    'rpPlanLegalFlg':InerCustomField('计划合法性',None,{1:'计划合法',0:'计划非法'}),
    'rpFinalStnFlg':InerCustomField('是否终到站',None,{1:"计划终到",0:"非终到站"}),
    'rpPlanTimeout':InerCustomField('是否超时',None,{1:"计划超时",0:"计划未超时"}),
    'rpTrainStnState':InerCustomField('接发车状态',None,{1:"发车状态",2:"接车状态",0:"未知状态"}),
    'rpPlanValid':InerCustomField('计划有效性',None,{1:"计划有效",0:"计划无效"}),
    'rpStopStn':InerCustomField('到发信息',None,{1:"通过",2:"到发"}),
    'rpTaskStn':InerCustomField('办客信息',None,{1:"办客",2:"不办客"}),
    'remainArrivalTime':InerCustomField('剩余到达时间','s',{0:'无效'}),
    'remainDepartTime':InerCustomField('剩余发车时间','s',{0:'无效'}),
    'rpUpdateSysTime':InerCustomField('计划更新时间','ms',None),

}

class BtmInfoDisplay(object):
    # 作为类属性全局的
    btmCycleList = []
    btmItemRealList = []
    btmHeaders = ['时间', '应答器编号', '位置矫正值','ATP过中心点时间', '公里标']
    
    @staticmethod
    def displayInitClear(table=QtWidgets.QTableWidget):
        table.clear()
        table.setColumnCount(len(BtmInfoDisplay.btmHeaders))
        table.setRowCount(100)
        table.setHorizontalHeaderLabels(BtmInfoDisplay.btmHeaders)
        table.verticalHeader().setVisible(True)
        # 重置数据
        BtmInfoDisplay.btmCycleList = []
        BtmInfoDisplay.btmItemRealList = []

    @staticmethod
    def __btmTableOffLineInit(cycleDic="dict", table=QtWidgets.QTableWidget):
        # 初始化表格
        BtmInfoDisplay.displayInitClear(table)
        # 搜索内容并初始化大小
        for cycle_num in cycleDic.keys():
            if cycleDic[cycle_num].msg_atp2ato.sp7_obj.updateflag:
                BtmInfoDisplay.btmCycleList.append(cycle_num)
        table.setRowCount(len(BtmInfoDisplay.btmCycleList))

    @staticmethod
    def displayRealTimeBtmTable(msg_obj=Atp2atoProto,time=str, table=QtWidgets.QTableWidget):
        '''
        实时显示，每次增加一个单行通过 row_cnt计数
        '''
        sp2_obj = msg_obj.sp2_obj
        sp7_obj = msg_obj.sp7_obj
        row_cnt = 0
        # 检查应答器信息
        if  sp7_obj and sp7_obj.updateflag:
            # 用于后续实时列表缓存使用
            BtmInfoDisplay.btmItemRealList.append(sp7_obj)
            # 扩展表格更新行数
            table.setColumnCount(len(BtmInfoDisplay.btmHeaders))
            row_cnt = len(BtmInfoDisplay.btmItemRealList)
            table.setRowCount(row_cnt)
            if time:
                d_t = time.split(" ")[1]  # 取时间
            else:
                d_t = "未知"
            item_dt = QtWidgets.QTableWidgetItem(d_t)
            item_dt.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            table.setItem(row_cnt, 0, item_dt)
            # 显示这个单行
            BtmInfoDisplay.displayBtmTableRow(sp2_obj,sp7_obj,row_cnt,table)

    @staticmethod
    def displayOffLineBtmTable(cycleDic="dict", table=QtWidgets.QTableWidget):
        '''
        离线显示，通过搜索每次增加一个行
        '''
        BtmInfoDisplay.__btmTableOffLineInit(cycleDic, table)
        row_cnt = 0
        for cycle_num in BtmInfoDisplay.btmCycleList:
            # 进行数据填充 
            cycleItem = cycleDic[cycle_num]
            # 填充表格内容
            sp2_obj = cycleItem.msg_atp2ato.sp2_obj
            sp7_obj = cycleItem.msg_atp2ato.sp7_obj
            # 预判断减少额外处理逻辑
            if sp7_obj.updateflag:
                d_t = cycleItem.time.split(" ")[1]  # 取时间
                item_dt = QtWidgets.QTableWidgetItem(d_t)
                item_dt.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                table.setItem(row_cnt, 0, item_dt)
                # 遍历并尝试填充列表
                row_cnt = BtmInfoDisplay.displayBtmTableRow(sp2_obj,sp7_obj,row_cnt,table)

    @staticmethod
    def displayBtmTableRow(sp2_obj=sp2, sp7_obj=sp7, row_cnt=int, table=QtWidgets.QTableWidget):
        '''
        BTM表单行表格生成显示
        '''
        # 填充表格行
        item_balise_bum = QtWidgets.QTableWidgetItem(str(sp7_obj.nid_bg))
        item_adjpos = QtWidgets.QTableWidgetItem(str(sp7_obj.d_pos_adj) + 'cm')
        item_tmiddle =  QtWidgets.QTableWidgetItem(str(sp7_obj.t_middle) + 'ms')

        item_balise_bum.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        item_adjpos.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        item_tmiddle.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        # 当存在应答器时尝试获取公里标
        if sp7_obj.updateflag:
            if sp2_obj.updateflag:
                value = sp2_obj.m_position
                if 0xFFFFFFFF != value:
                    item_milestone = QtWidgets.QTableWidgetItem('K' + str(int(value/ 1000)) + '+' + str(value % 1000))
                else:
                    item_milestone = QtWidgets.QTableWidgetItem('未知')
            # 当精确定位应答器时标红
            if sp7_obj.nid_xuser == 13:
                item_milestone.setForeground(QtGui.QBrush(QtGui.QColor(225, 0, 0)))
                item_balise_bum.setForeground(QtGui.QBrush(QtGui.QColor(225, 0, 0)))
                item_adjpos.setForeground(QtGui.QBrush(QtGui.QColor(225, 0, 0)))
            # 所有都居中，但只SP7刷红
            item_milestone.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            table.setItem(row_cnt, 1, item_balise_bum)
            table.setItem(row_cnt, 2, item_adjpos)
            table.setItem(row_cnt, 3, item_tmiddle)
            table.setItem(row_cnt, 4, item_milestone)
            row_cnt = row_cnt + 1
            # 当更新内容时才重置
            table.resizeRowsToContents()
            table.resizeColumnsToContents()
        return row_cnt

    @staticmethod
    def displayBtmItemSelInfo(obj=sp7,
        led_with_C13=QtWidgets.QLineEdit, 
        led_platform_pos=QtWidgets.QLineEdit,
        led_platform_door=QtWidgets.QLineEdit,
        led_track=QtWidgets.QLineEdit,
        led_stop_d_JD=QtWidgets.QLineEdit):
        '''
        BTM单行选中后显示辅助信息
        '''
        # 存在应答器包
        if obj and obj.updateflag:
            # JD正常刷颜色
            if obj.nid_xuser == 13:
                DisplayMsgield.disNameOfLineEdit("nid_xuser", obj.nid_xuser, led_with_C13)
                DisplayMsgield.disNameOfLineEdit("q_platform", obj.q_platform, led_platform_pos)
                DisplayMsgield.disNameOfLineEdit("q_door", obj.q_door, led_platform_door)
                DisplayMsgield.disNameOfLineEdit("n_g", obj.n_g, led_track)
                # 停车点手动计算
                if obj.d_stop != 32767:
                    if obj.q_scale == 0:
                        scale = 10
                    elif obj.q_scale == 1:
                        scale = 100
                    elif obj.q_scale == 2:
                        scale = 1000
                    led_stop_d_JD.setText(str(scale * obj.d_stop) + 'cm')
                else:
                    led_stop_d_JD.setText('无效值')
            else:
                led_with_C13.setText('无')
                led_with_C13.setStyleSheet("background-color: rgb(100, 100, 100);")
                led_platform_door.clear()
                led_platform_pos.clear()
                led_track.clear()
                led_stop_d_JD.clear()

    @staticmethod
    def GetBtmDicItemSelected(cycleDic="dict",item=QtWidgets.QTableWidgetItem, curInf=int, curMode=int):
        obj = None
        # 离线&标记模式通过周期字典搜索
        if curInf == 1 and curMode == 1:
            if len(BtmInfoDisplay.btmCycleList) > item.row():
                cNum = BtmInfoDisplay.btmCycleList[item.row()]
                obj = cycleDic[cNum].msg_atp2ato.sp7_obj
        return obj

    @staticmethod
    def GetBtmRealItemSelected(item=QtWidgets.QTableWidgetItem, curInf=int):
        obj = None
        # 在线模式下通过保存的列表来进行搜索        
        if curInf == 2:
            if len(BtmInfoDisplay.btmItemRealList) > item.row():
                obj = BtmInfoDisplay.btmItemRealList[item.row()]    # 通过保存的列表来二次索引
        return obj

class RunningPlanItem(object):
    '''
    提供基础的计划段定义
    '''
    __slots__ = ['rpDepartUtcTime', 'rpDepartTrack', 'rpArrivalUtcTime', 'rpArrivalTrack', 'rpStopStn' , 
    'rpTaskStn','rpWaysideUtcTime','rpWaysideTtrain']
    def __init__(self) -> None:
        self.rpWaysideUtcTime = 0 # 地面UTC东八区时间
        self.rpDepartUtcTime  = 0 # 出发站UTC东八区时间
        self.rpDepartTrack    = 0 # 出发站股道编号
        self.rpArrivalUtcTime = 0 # 到达站UTC东八区时间
        self.rpArrivalTrack   = 0 # 到达站股道编号
        self.rpStopStn        = 0 # 本站到发情况
        self.rpTaskStn        = 0 # 本站办客情况
        self.rpWaysideTtrain  = 0 # 消息对应的车载时间

class InerRunningPlanInfo(object):
    '''
    提供计划信息定义
    '''
    __slots__ = ['rpCurTrack', 'remainArrivalTime', 'remainDepartTime', 'rpUpdateSysTime', 'rpStopStableFlg' ,
    'rpPlanLegalFlg', 'rpFinalStnFlg','rpPlanTimeout','rpTrainStnState','rpPlanValid','rpStartTrain',
    'rpValidNum', 'rpItem0','rpItem1','rpItem2','updateflag'] 
    def __init__(self) -> None:
        self.rpCurTrack      = 0
        self.remainArrivalTime = 0
        self.remainDepartTime  = 0
        self.rpUpdateSysTime   = 0
        # 内部当前计划
        self.rpStopStableFlg = 1
        self.rpPlanLegalFlg  = 1
        self.rpFinalStnFlg   = 1
        # 计划模块状态
        self.rpPlanTimeout   = 1 # 计划超时状态
        self.rpTrainStnState = 2 # 到发状态
        self.rpPlanValid     = 1 # 计划有效状态
        self.rpStartTrain    = 0 # 发车状态-发车按钮按下？

        # 内部合法计划条目
        self.rpValidNum = 0
        self.rpItem0 = RunningPlanItem()
        self.rpItem1 = RunningPlanItem()
        self.rpItem2 = RunningPlanItem()
        # 更新标志
        self.updateflag = False

class InerRunningPlanParse(object):
    '''
    提供文本内部计划解析功能
    '''
    __slots__ = ['rpInfo','cfg']
    def __init__(self) -> None:
        self.rpInfo = InerRunningPlanInfo()
        self.cfg = ConfigFile()
        # 读取配置
        self.cfg.readConfigFile()
    
    def reset(self):
        self.rpInfo.updateflag = False
    
    def rpContentParse(self, content='list'):
        if content and len(content) > 0:
            idx = int(content[0])
            if idx == 0:
                InerRunningPlanParse.rpContentItemParse(self.rpInfo.rpItem0,content[1:])
            elif idx == 1:
                InerRunningPlanParse.rpContentItemParse(self.rpInfo.rpItem1,content[1:])
            elif idx == 2:
                InerRunningPlanParse.rpContentItemParse(self.rpInfo.rpItem2,content[1:])
            else:
                pass
    
    @staticmethod
    def rpContentItemParse(item=RunningPlanItem,content='list'):
        item.rpWaysideTtrain = int(content[0])
        item.rpWaysideUtcTime = int(content[1])
        item.rpDepartTrack = int(content[2])
        item.rpDepartUtcTime = int(content[3])
        item.rpArrivalTrack = int(content[4])
        item.rpArrivalUtcTime = int(content[5])
        item.rpStopStn = int(content[6])
        item.rpTaskStn = int(content[7])

    # 完整计划解析方法
    def rpStringParse(self,line=str,osTime=str):
        # RP1解析
        match = self.cfg.reg_config.pat_rp1.findall(line)
        if match:
            self.rpInfo.rpCurTrack = int(match[0][0]) #计划模块当前股道号
            self.rpInfo.rpStartTrain = int(match[0][1]) #发车标志
            # 索引2为站台标志不显示
            self.rpInfo.rpStopStableFlg = int(match[0][3]) # 停稳标志
        else:
            # RP2解析
            match = self.cfg.reg_config.pat_rp2.findall(line)
            if match:
                self.rpInfo.rpPlanLegalFlg = int(match[0][0])
                self.rpInfo.rpFinalStnFlg  = int(match[0][1])
                self.rpInfo.rpUpdateSysTime = int(match[0][2])
                self.rpInfo.rpValidNum = int(match[0][3]) # 计划合法段数
            else:
                match = self.cfg.reg_config.pat_rp2_cntent.findall(line)
                # 存在RP2尝试进行段数解析
                if match:
                    self.rpContentParse(match[0])
                else:
                    # RP3
                    match = self.cfg.reg_config.pat_rp3.findall(line)
                    if match:
                        self.rpInfo.rpPlanTimeout = int(match[0][0])
                        self.rpInfo.rpTrainStnState = int(match[0][1])
                        # 来自应答器股道 来自计划股道 计划迭代 暂不解析
                    else:
                        match = self.cfg.reg_config.pat_rp4.findall(line)
                        if match:
                            self.rpInfo.rpPlanValid = int(match[0][0])
                            arrivalSysTime = int(match[0][1])
                            if arrivalSysTime == 0:
                                self.rpInfo.remainArrivalTime = 0
                            else:
                                self.rpInfo.remainArrivalTime = int((arrivalSysTime - osTime)/1000)
                            departSysTime = int(match[0][2])
                            if departSysTime == 0:
                                self.rpInfo.remainDepartTime = 0
                            else:
                                self.rpInfo.remainDepartTime = int((departSysTime - osTime)/1000)
                            self.rpInfo.updateflag = True
        return self.rpInfo

class InerIoInfo(object):
    __slots__ = ['doorOpenLeftBtnIn','doorOpenRightBtnIn','doorCloseLeftBtnIn','doorCloseRightBtnIn',
    'doorOpenLeftOut','doorOpenRightOut','doorCloseLeftOut','doorCloseRightOut',
    'updateflagIn','updateflagOut']
    def __init__(self) -> None:
        #----硬线输入信号门按钮
        self.doorOpenLeftBtnIn  = 0
        self.doorOpenRightBtnIn = 0
        self.doorCloseLeftBtnIn = 0
        self.doorCloseRightBtnIn= 0
        self.updateflagIn = False
        #----硬线输出信号门命令
        self.doorOpenLeftOut    = 0
        self.doorOpenRightOut   = 0
        self.doorCloseLeftOut   = 0
        self.doorCloseRightOut  = 0
        self.updateflagOut = False

class InerIoInfoParse(object):
    def __init__(self) -> None:
        self.ioInfo = InerIoInfo()
        self.cfg = ConfigFile()
        # 读取配置
        self.cfg.readConfigFile()
    
    def reset(self):
        self.ioInfo.updateflagIn = False
        self.ioInfo.updateflagOut=False

    @staticmethod
    def resetIoInfo(obj=InerIoInfo):
        obj.doorOpenLeftBtnIn  = 0
        obj.doorOpenRightBtnIn = 0
        obj.doorCloseLeftBtnIn = 0
        obj.doorCloseRightBtnIn= 0
        #----硬线输出信号门命令
        obj.doorOpenLeftOut    = 0
        obj.doorOpenRightOut   = 0
        obj.doorCloseLeftOut   = 0
        obj.doorCloseRightOut  = 0
        # 更新标志
        obj.updateflagIn = False
        obj.updateflagOut = False

    def ioStringParse(self, line=str):
        # 检查输入
        match = self.cfg.reg_config.pat_io_in.findall(line)
        if match:
            if match[0][0] == 'CLOSE_L':
                self.ioInfo.doorCloseLeftBtnIn = int(match[0][1])
            elif match[0][0] == 'OPEN_L':
                self.ioInfo.doorOpenLeftBtnIn  = int(match[0][1])
            elif match[0][0] == 'CLOSE_R':
                self.ioInfo.doorCloseRightBtnIn= int(match[0][1])
            elif match[0][0] == 'OPEN_R':
                self.ioInfo.doorOpenRightBtnIn = int(match[0][1])
            else:
                pass
            self.ioInfo.updateflagIn = True
        # 检查输出
        else: 
            match = self.cfg.reg_config.pat_io_out.findall(line)
            if match:
                if match[0] == 'OPEN L':
                    self.ioInfo.doorOpenLeftOut = 1
                elif match[0] == 'CLOSE_L':
                    self.ioInfo.doorCloseLeftOut = 1
                elif match[0] == 'OPEN_R':
                    self.ioInfo.doorOpenRightOut = 1
                elif match[0] == 'CLOSE_R':
                    self.ioInfo.doorCloseRightOut = 1
                else:
                    pass
                self.ioInfo.updateflagOut = True
        return self.ioInfo

class InerSduInfo(object):
    __slots__ = ['atoSpeed', 'atoDis', 'atpSpeed', 'atpDis','stateMachine', 'cycleTime','updateflag']
    def __init__(self) -> None:
        self.atoSpeed = 0
        self.atoDis   = 0
        self.atpSpeed = 0
        self.atpDis   = 0
        self.stateMachine = 0
        self.cycleTime = 0
        self.updateflag = False         

class InerSduInfoParse(object):
    def __init__(self) -> None:
        self.sduInfo = InerSduInfo()
        self.cfg = ConfigFile()
        # 读取配置
        self.cfg.readConfigFile()
    
    def reset(self):
        self.sduInfo.updateflag = False
        self.sduInfo.stateMachine = 0

    def sduInfoStringParse(self, line=str, cycleTime=int):
        match = self.cfg.reg_config.pat_atp_sdu.findall(line)
        if match:
            self.sduInfo.atpSpeed = int(match[0][0])
            self.sduInfo.atpDis = int(match[0][1])
            self.sduInfo.stateMachine = 1
            self.sduInfo.cycleTime = cycleTime
        else:
            match = self.cfg.reg_config.pat_ato_sdu.findall(line)
            if match:
                self.sduInfo.atoSpeed = int(match[0][0])
                self.sduInfo.atoDis   = int(match[0][1])
                if self.sduInfo.stateMachine == 1 and self.sduInfo.cycleTime == cycleTime:
                    self.sduInfo.stateMachine == 2
                    self.sduInfo.cycleTime = cycleTime
                    # 更新标志
                    self.sduInfo.updateflag = True
                else:
                    self.sduInfo.updateflag = False
        return self.sduInfo

class InerValueStats(object):
    def __init__(self) -> None:
        self.count = 0
        self.lastMeanVal = 0
        self.maxCycle = 0
        self.minCycle = 0
        self.maxVal = 0
        self.meanVal = 0
        self.minVal = 0
        self.updateflag = False
    
class InerValueStatsHandler(object):

    def __init__(self) -> None:
        self.curCycleNum = 0
        self.baseVal = 0

    def statsProcess(value=int, cycleNum=int, obj=InerValueStats):
        obj.count = obj + 1
        obj.meanVal = obj.lastMeanVal + ((value - obj.lastMeanVal)/obj.count)
        obj.lastMeanVal = obj.meanVal
        if value > obj.maxVal:
            obj.maxVal = value
            obj.maxCycle = cycleNum
        if value < obj.minVal:
            obj.minVal = value
    
    def cycleTimeGetValue(self, baseVal=int, curCycleNum=int):
        if curCycleNum == self.curCycleNum:
            delta = baseVal - self.baseVal
            self.baseVal = baseVal
            self.curCycleNum = curCycleNum
            return delta
        else:
            return None

class AtoKeyInfoDisplay(object):
    # 类变量 描述当前IO表格的行号
    curTableInRowNum  = 0 
    curTableOutRowNum = 0
    lastSduAtoDis = 0
    lastSduAtpDis = 0

    # 协议字段显示使用MVB和ATP2ATO协议
    @staticmethod
    def lableFieldDisplay(keyName=str,value=int, FieldDic='dict',lbl=QtWidgets.QLabel):
        # 检查字典和含义
        if keyName in FieldDic.keys() and value in FieldDic[keyName].meaning.keys():
            lbl.setText(FieldDic[keyName].meaning[value])
            if keyName in FieldBGColorDic.keys() and value in FieldBGColorDic[keyName].keys():
                lbl.setStyleSheet(FieldBGColorDic[keyName][value])
            else:
                # 没有颜色定义时重置
                lbl.setStyleSheet("background-color: rgb(170, 170, 255);")
        else:
            lbl.setText(FieldDic[keyName].name)
            lbl.setStyleSheet("background-color: rgb(170, 170, 255);")
            
    # 内部字段显示
    @staticmethod
    def labelInerDisplay(keyName=str,value=int,lbl=QtWidgets.QLabel):
        # 检查字典和含义
        if keyName in AtoInerDic.keys() and value in AtoInerDic[keyName].meaning.keys():
            lbl.setText(AtoInerDic[keyName].meaning[value])
            if keyName in InerFieldBGColorDic.keys() and value in InerFieldBGColorDic[keyName].keys():
                lbl.setStyleSheet(InerFieldBGColorDic[keyName][value])
            else:
                # 没有颜色定义时重置
                lbl.setStyleSheet("background-color: rgb(170, 170, 255);")
        else:
            lbl.setText(AtoInerDic[keyName].name)
            lbl.setStyleSheet("background-color: rgb(170, 170, 255);")
    
    @staticmethod
    def lineditInerDisplay(keyName=str,value=int,led=QtWidgets.QLineEdit):
        if keyName in AtoInerDic.keys():
            if AtoInerDic[keyName].meaning and value in AtoInerDic[keyName].meaning.keys():
                led.setText(AtoInerDic[keyName].meaning[value])
                if keyName in InerFieldBGColorDic.keys() and value in InerFieldBGColorDic[keyName].keys():
                    led.setStyleSheet(InerFieldBGColorDic[keyName][value])
                else:
                    # 没有颜色定义时重置
                    led.setStyleSheet("background-color: rgb(170, 170, 255);")
            elif AtoInerDic[keyName].unit:
                led.setText(str(value)+AtoInerDic[keyName].unit)
            else:
                led.setStyleSheet("background-color: rgb(255, 0, 0);")
                led.setText('异常%d' % value)          
        else:
            led.setText(str(value))
            led.setStyleSheet("background-color: rgb(170, 170, 255);")

    @staticmethod
    def runningPlanTableDisplay(rpInfo=InerRunningPlanInfo ,table=QtWidgets.QTableWidget):
        if rpInfo.rpItem0:
            AtoKeyInfoDisplay.runningPlanItemRowDisplay(rpInfo.rpItem0, 0, table)
        elif rpInfo.rpItem1:
            AtoKeyInfoDisplay.runningPlanItemRowDisplay(rpInfo.rpItem1, 1, table)
        elif rpInfo.rpItem2:
            AtoKeyInfoDisplay.runningPlanItemRowDisplay(rpInfo.rpItem2, 2, table)
        else:
            pass

    @staticmethod
    def runningPlanItemRowDisplay(rpItem=RunningPlanItem, column=int,table=QtWidgets.QTableWidget):
        if rpItem:
            # 消息ttrian
            table.setItem(0, column, QtWidgets.QTableWidgetItem(str(rpItem.rpWaysideTtrain)+'ms'))
            # 地面时刻
            strUtc = AtoKeyInfoDisplay.translateUtc(rpItem.rpWaysideUtcTime)
            table.setItem(1, column, QtWidgets.QTableWidgetItem(strUtc))
            # 发车股道
            table.setItem(2, column, QtWidgets.QTableWidgetItem(str(rpItem.rpDepartTrack)))
            # 发车时刻
            strUtc = AtoKeyInfoDisplay.translateUtc(rpItem.rpDepartUtcTime)
            table.setItem(3, column, QtWidgets.QTableWidgetItem(strUtc))
            # 接车股道
            table.setItem(4, column, QtWidgets.QTableWidgetItem(str(rpItem.rpArrivalTrack)))
            # 接车时刻
            strUtc = AtoKeyInfoDisplay.translateUtc(rpItem.rpArrivalUtcTime)
            table.setItem(5, column, QtWidgets.QTableWidgetItem(strUtc))
            # 到发信息
            if rpItem.rpStopStn == 1 or rpItem.rpStopStn:
                meaning = AtoInerDic["rpStopStn"].meaning[rpItem.rpStopStn]
            else:
                meaning = ('未知:%d'%rpItem.rpStopStn)
            table.setItem(6, column, QtWidgets.QTableWidgetItem(meaning))
            # 办客信息
            if rpItem.rpTaskStn == 1 or rpItem.rpTaskStn:
                meaning = AtoInerDic["rpTaskStn"].meaning[rpItem.rpTaskStn]
            else:
                meaning = ('未知:%d'%rpItem.rpTaskStn)
            table.setItem(7, column, QtWidgets.QTableWidgetItem(meaning))

    # 内部字段显示
    @staticmethod
    def displayRpUdpDuration(osTime=int, value=int,lbl=QtWidgets.QLabel):
        duration = (osTime - value)/1000
        lbl.setText(str('已更新时长:%.1fs'%duration))

    @staticmethod
    def translateUtc(utc=int):
        if utc == -1:
            timeStr = '未知'
        else:
            ltime = time.localtime(utc)
            # %Y-%m-%d 
            timeStr = time.strftime("%H:%M:%S", ltime)
        return timeStr

    def ioInfoDisplay(cycleNumStr=str, timeContentStr=str,ioObj=InerIoInfo, tableIn=QtWidgets.QTableWidget, tableOut=QtWidgets.QTableWidget):
        # 该函数不可重入非静态方法设置为类方法
        if cycleNumStr and timeContentStr and ioObj:
            if ioObj.updateflagIn:
                # 首先计算本次输入表添加的行数
                deltaRowAdd = ioObj.doorCloseLeftBtnIn + ioObj.doorOpenLeftBtnIn + ioObj.doorOpenRightBtnIn + ioObj.doorCloseRightBtnIn
                tableIn.setRowCount(AtoKeyInfoDisplay.curTableInRowNum + deltaRowAdd)

                if ioObj.doorCloseLeftBtnIn == 1:
                    AtoKeyInfoDisplay.addIoInItem(cycleNumStr, timeContentStr,'关左门按钮', ioObj.doorCloseLeftBtnIn,tableIn)
                if ioObj.doorOpenLeftBtnIn == 1:
                    AtoKeyInfoDisplay.addIoInItem(cycleNumStr, timeContentStr,'开左门按钮', ioObj.doorOpenLeftBtnIn,tableIn)
                if ioObj.doorCloseRightBtnIn == 1:
                    AtoKeyInfoDisplay.addIoInItem(cycleNumStr, timeContentStr,'关右门按钮', ioObj.doorCloseRightBtnIn,tableIn)
                if ioObj.doorOpenRightBtnIn == 1:
                    AtoKeyInfoDisplay.addIoInItem(cycleNumStr, timeContentStr,'开右门按钮', ioObj.doorOpenRightBtnIn,tableIn)
            if ioObj.updateflagOut:
                # 首先计算本输出次添加的行数
                deltaRowAdd = ioObj.doorCloseLeftOut + ioObj.doorOpenLeftOut + ioObj.doorOpenRightOut + ioObj.doorCloseRightOut
                tableOut.setRowCount(AtoKeyInfoDisplay.curTableOutRowNum + deltaRowAdd)
                if ioObj.doorCloseLeftOut == 1:
                    AtoKeyInfoDisplay.addIoInItem(cycleNumStr, timeContentStr,'关左门命令', ioObj.doorCloseLeftOut,tableOut)
                if ioObj.doorOpenLeftOut == 1:
                    AtoKeyInfoDisplay.addIoInItem(cycleNumStr, timeContentStr,'开左门命令', ioObj.doorOpenLeftOut,tableOut)
                if ioObj.doorOpenRightOut == 1:
                    AtoKeyInfoDisplay.addIoInItem(cycleNumStr, timeContentStr,'关右门命令', ioObj.doorOpenRightOut,tableOut)
                if ioObj.doorCloseRightOut == 1:
                    AtoKeyInfoDisplay.addIoInItem(cycleNumStr, timeContentStr,'开右门命令', ioObj.doorCloseRightOut,tableOut)
    
    def addIoInItem(cycleNumStr=str, timeContentStr=str, name=str, value=int, table=QtWidgets.QTableWidget):
       
        table.setItem(AtoKeyInfoDisplay.curTableInRowNum, 0, AtoKeyInfoDisplay.createCustomTableItem(timeContentStr.split(" ")[1]))
        table.setItem(AtoKeyInfoDisplay.curTableInRowNum, 1, AtoKeyInfoDisplay.createCustomTableItem(cycleNumStr))
        table.setItem(AtoKeyInfoDisplay.curTableInRowNum, 2, AtoKeyInfoDisplay.createCustomTableItem(name))
        table.setItem(AtoKeyInfoDisplay.curTableInRowNum, 3, AtoKeyInfoDisplay.createCustomTableItem(str(value)))
        AtoKeyInfoDisplay.curTableInRowNum += 1
    
    def addIoOutItem(cycleNumStr=str, timeContentStr=str, name=str, value=int, table=QtWidgets.QTableWidget):
        table.setItem(AtoKeyInfoDisplay.curTableInRowNum, 0, AtoKeyInfoDisplay.createCustomTableItem(timeContentStr.split(" ")[1]))
        table.setItem(AtoKeyInfoDisplay.curTableInRowNum, 1, AtoKeyInfoDisplay.createCustomTableItem(cycleNumStr))
        table.setItem(AtoKeyInfoDisplay.curTableInRowNum, 2, AtoKeyInfoDisplay.createCustomTableItem(name))
        table.setItem(AtoKeyInfoDisplay.curTableInRowNum, 3, AtoKeyInfoDisplay.createCustomTableItem(str(value)))
        AtoKeyInfoDisplay.curTableOutRowNum += 1

    def createCustomTableItem(content=str):
        item = QtWidgets.QTableWidgetItem(content)
        item.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        return item

    def sduVInfoDisplay(value=int, valLed=QtWidgets.QLineEdit, valLcd=QtWidgets.QLCDNumber):
        # 进行测速信息计算时
        v = abs(value)
        ato_v_kilo = (v * 9 / 250.0)
        valLed.setText(str(v)+'cm/s')
        valLcd.display(str(float('%.1f' % ato_v_kilo)))
        return v
    
    def sduVJudgeDisplay(atoV=int, atpV=int, judge=int, errLed=QtWidgets.QLineEdit, resultLbl=QtWidgets.QLabel):
        # 计算测速测距偏差
        delta = atoV - atpV
        errLed.setText(str(abs(delta))+'cm/s')
        # 判断情况
        if delta < -judge: # 若偏低
            resultLbl.setText("ATO速度偏低")
            resultLbl.setStyleSheet("background-color: rgb(255, 255, 0);")
        elif delta > judge: # 若偏高
            resultLbl.setText("ATO速度偏高")
            resultLbl.setStyleSheet("background-color: rgb(255, 0, 0);")
        else:
            resultLbl.setText("测速基本一致")
            resultLbl.setStyleSheet("background-color: rgb(170, 170, 255);")
    
    def sduAtoDeltaSDisplay(vAtoS=int, vAtpS=int, vAtoSLed=QtWidgets.QLineEdit, vAtpSLed=QtWidgets.QLineEdit):
        # 进行测距增量计算时
        deltaAtoS = vAtoS - AtoKeyInfoDisplay.lastSduAtoDis
        AtoKeyInfoDisplay.lastSduAtoDis = vAtoS
        vAtoSLed.setText(str(deltaAtoS)+'cm')

        deltaAtpS = vAtpS - AtoKeyInfoDisplay.lastSduAtpDis
        AtoKeyInfoDisplay.lastSduAtpDis = vAtpS
        vAtpSLed.setText(str(deltaAtpS)+'cm')
        return deltaAtoS - deltaAtpS
    
    def sduSJudgeDisplay(deltaS=int, judge=int, errLed=QtWidgets.QLineEdit, resultLbl=QtWidgets.QLabel):
        errLed.setText(str(deltaS)+'cm')
        # 判断情况
        if deltaS < -judge:  # 若偏低
            resultLbl.setText("ATO测距偏低")
            resultLbl.setStyleSheet("background-color: rgb(255, 255, 0);")
        elif deltaS > judge: # 若偏高
            resultLbl.setText("ATO测距偏高")
            resultLbl.setStyleSheet("background-color: rgb(255, 0, 0);")
        else:
            resultLbl.setText("测距基本一致")
            resultLbl.setStyleSheet("background-color: rgb(170, 170, 255);")