#!/usr/bin/env python
# encoding: utf-8
'''
Author: Zhengtang Bao
Contact: baozhengtang@crscd.com.cn
File: MainWinDisplay
Date: 2022-07-25 20:09:57
Desc: 主界面关键数据处理及显示功能
LastEditors: Zhengtang Bao
LastEditTime: 2022-09-28 13:33:59
'''

import pickle
import time
from PyQt5 import QtWidgets,QtGui,QtCore
from ConfigInfo import ConfigFile
from MsgParse import Ato2tsrsProto, Atp2atoProto, DisplayMsgield, SP2, SP7, Tsrs2atoFieldDic, Tsrs2atoProto

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
    'm_atomode':InerCustomField('ATO模式',None,{0:"未知",1:"AOS模式",2:"AOR模式",3:"AOM模式",4:"AOF模式"}),
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

StateMachineDic={
    1 :'STOPPED 停车',
    2 :'UNUSED 未投入',
    3 :'START 发车',
    4 :'START2 发车2',
    5 :'NORMAL 普通',
    10:'COAST 巡航', 
    15:'UNCONFORM 待确认状态', 
    20:'TARGET_GET 更新目标点', 
    21:'TARGET_GET 目标点制动', 
    22:'TARGET1 目标制动1',
    22:'TARGET2 目标制动2',
    23:'T2B_COAST 转换惰行', 
    25:'TARGET_V_BEFORE 提前将速度控制完毕', 
    26:'TARGET_V_BEYOND 滞后将速度控制完毕', 
    27:'TARGET_KEEP 维持目标', 
    28:'TARGET_END 目标结束', 
    30:'STOP_GET 更新停车点', 
    31:'STOP_IN 停车点减速', 
    32:'STOP_ASTOP 空气制动', 
    33:'STOP_FINAL 一把扎', 
    34:'STOP_END 即将结束', 
    35:'LAST'

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
        sp2_obj = pickle.loads(pickle.dumps(msg_obj.sp2_obj))
        sp7_obj = pickle.loads(pickle.dumps(msg_obj.sp7_obj))
        # 检查应答器信息
        if  sp7_obj and sp7_obj.updateflag:
            # 用于后续实时列表缓存使用
            BtmInfoDisplay.btmItemRealList.append(sp7_obj)
            # 扩展表格更新行数
            #table.setColumnCount(len(BtmInfoDisplay.btmHeaders))
            if len(BtmInfoDisplay.btmItemRealList) > 0:
                rowIdx = len(BtmInfoDisplay.btmItemRealList) - 1
            else:
                rowIdx = 0
            #table.setRowCount(row_cnt)
            if time:
                d_t = time.split(" ")[1]  # 取时间
            else:
                d_t = "未知"
            item_dt = QtWidgets.QTableWidgetItem(d_t)
            item_dt.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            table.setItem(rowIdx, 0, item_dt)
            # 显示这个单行
            BtmInfoDisplay.displayBtmTableRow(sp2_obj,sp7_obj,rowIdx,table)
            # 对于实时显示使用后重置
            msg_obj.sp7_obj.updateflag = False
            msg_obj.sp2_obj.updateflag = False

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
    def displayBtmTableRow(sp2_obj=SP2, sp7_obj=SP7, row_cnt=int, table=QtWidgets.QTableWidget):
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
    def displayBtmItemSelInfo(obj=SP7,
        led_with_C13=QtWidgets.QLineEdit, 
        led_platform_pos=QtWidgets.QLineEdit,
        led_platform_door=QtWidgets.QLineEdit,
        led_track=QtWidgets.QLineEdit,
        led_stop_d_JD=QtWidgets.QLineEdit,
        led_btm_id=QtWidgets.QLineEdit):
        '''
        BTM单行选中后显示辅助信息
        '''
        # 存在应答器包
        if obj and obj.updateflag:
            # 计算应答器编号解析
            majorRegion = (obj.nid_bg & 0xFE0000)>>17
            subRegion   = (obj.nid_bg & 0x01C000)>>14
            station     = (obj.nid_bg & 0x003F00)>>8
            balise      = (obj.nid_bg & 0x0000FF)
            strBalise     = ("(%d-%d-%d-%d)"%(majorRegion,subRegion,station,balise))
            strBaliseInfo = ("大区编号%d-"%majorRegion)+("分区编号%d-"%subRegion)+("车车站编号%d-"%station)+("应答器编号%d"%balise)
            led_btm_id.setText(strBalise + 5*' ' + strBaliseInfo) 
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
        self.rpCurTrack        = 0
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


    @staticmethod
    def labelRouteDisplay(value=int, fieldDic='dict', tcIntroDic='dict' ,lbl=QtWidgets.QLabel):
        keyName = "m_low_frequency"
        # 检查字典和含义
        if value in fieldDic[keyName].meaning.keys():
            # 轨道码值
            tcName = fieldDic[keyName].meaning[value]
            # 轨道码进路说明
            if tcName in tcIntroDic:
                tcRoute = tcIntroDic[tcName]
            else:
                tcRoute = ''
            lbl.setText(tcName+':'+tcRoute)
            if keyName in FieldBGColorDic.keys() and value in FieldBGColorDic[keyName].keys():
                lbl.setStyleSheet(FieldBGColorDic[keyName][value])
            else:
                # 没有颜色定义时重置
                lbl.setStyleSheet("background-color: rgb(170, 170, 255);")
        else:
            lbl.setText(fieldDic[keyName].name)
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
                    pass
            elif AtoInerDic[keyName].unit:
                led.setText(str(value)+AtoInerDic[keyName].unit)
            else:
                led.setStyleSheet("background-color: rgb(255, 0, 0);")
                led.setText('异常%d' % value)          
        else:
            led.setText(str(value))
            led.setStyleSheet("background-color: rgb(170, 170, 255);")
        led.setCursorPosition(0)
        
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

    def btnSerialDisplay(linked=True, btn=QtWidgets.QPushButton):
        if linked:
            btn.setText('断开')
            btn.setStyleSheet("background: rgb(191, 255, 191);")
        else:
            btn.setText('连接')
            btn.setStyleSheet(" background: rgb(238, 86, 63);")

    @staticmethod
    def ctrlStoppointDisplay(stopTuple=tuple, curPos=int, tb=QtWidgets.QTableWidget):
        """
        为了避免过于转换,这里使用原始的字符串位置和停车点
        """
        idx = 0
        if stopTuple and len(stopTuple) > 0:
            valueList = [int(i) for i in stopTuple]
            
            # 设置关键停车点 
            minValue = min(valueList)
            idxKey = valueList.index(minValue) 
            for v in valueList:
                item = QtWidgets.QTableWidgetItem(str(v)+'cm')
                if idx == idxKey:
                    item.setBackground(QtGui.QBrush(QtGui.QColor(255, 107, 107))) # 西瓜红
                else:
                    item.setBackground(QtGui.QBrush(QtGui.QColor(243, 243, 243)))
                tb.setItem(idx, 0, item)
                idx = idx + 1
            if curPos:
                posValue = int(curPos)
                # 设置误距离停车点误差值
                item = QtWidgets.QTableWidgetItem(str(minValue-posValue)+'cm')
                tb.setItem(idx, 0, item)
        else:
            pass

    @staticmethod
    def ctrlStopErrorDisplay(atoError=int, atpError=int, tb=QtWidgets.QTableWidget):
        if atpError == 32768 or atpError == -32768:
            strAtpError = '无效'
        else:
            strAtpError = str(atpError)+'cm'
        
        if atoError == 32768 or atoError == -32768:
            strAtoError = '无效'
        else:
            strAtoError = str(atoError)+'cm'
        item = QtWidgets.QTableWidgetItem(strAtpError)
        tb.setItem(4, 0, item)
        item = QtWidgets.QTableWidgetItem(strAtoError)
        tb.setItem(5, 0, item)

    @staticmethod
    def ctrlSpeedDisplay(vstrList='list', tb=QtWidgets.QTableWidget):
        """
        使用速度列表按照当前速度, ato命令速度, atp命令速度, atp允许速度
        """
        defaultVal = 32767
        idx = 0
        if vstrList and (len(vstrList) == 4):
            curSpeed = vstrList[0]
            atoCmdv  = vstrList[1]
            atpCmdv  = vstrList[2]
            atpPmtv  = vstrList[3]
            # 更新默认值
            intList = [x if x!=-1 else defaultVal for x in [atoCmdv, atpCmdv, atpPmtv]]
            # 最小速度值
            minValue = min(intList)
            idxKey = intList.index(minValue) 
            for v in intList:
                if defaultVal == v:
                    item = QtWidgets.QTableWidgetItem('')
                else:
                    item = QtWidgets.QTableWidgetItem(str(v)+'cm/s')
                if idx == idxKey:
                    item.setBackground(QtGui.QBrush(QtGui.QColor(255, 107, 107))) # 西瓜红
                else:
                    item.setBackground(QtGui.QBrush(QtGui.QColor(243, 243, 243)))
                tb.setItem(idx, 0, item)
                idx = idx + 1
            # 设置误距离停车点误差值
            item = QtWidgets.QTableWidgetItem(str(minValue-curSpeed)+'cm/s')
            tb.setItem(idx, 0, item)
        else:
            pass
    
    @staticmethod
    def ctrlAtoSpeedDisplay(atoSpeed=int, lbl=QtWidgets.QLabel, led=QtWidgets.QLineEdit):
        content = str(atoSpeed)+'cm/s'+' | ' +AtoKeyInfoDisplay.getStrKmh(atoSpeed)+'km/h'
        led.setText(content)
        led.setCursorPosition(0)

    @staticmethod
    def ctrlAtoPosDisplay(atoPos=int, lbl=QtWidgets.QLabel, led=QtWidgets.QLineEdit):
        led.setText(str(atoPos)+'cm')
        led.setCursorPosition(0)

    @staticmethod
    def ctrlStateMachineDisplay(machine=int, lbl=QtWidgets.QLabel, led=QtWidgets.QLineEdit):
        if machine in  StateMachineDic.keys():
            led.setText(str(machine)+' | '+StateMachineDic[machine])
        else:
            led.setText(str(machine))
        led.setCursorPosition(0)

    @staticmethod
    def ctrlEstimateLevelDisplay(esLvl=int,lvlLimit='list', lbl=QtWidgets.QLabel, led=QtWidgets.QLineEdit):
        if lvlLimit:
            [maxTLvl, maxBLvl] = lvlLimit
        else:
            maxTLvl = 10
            maxBLvl = 7
        if esLvl > 0:
            content = str(esLvl) +' | '+'牵引'+('%.1f%%'%(esLvl*100/maxTLvl))
        elif esLvl < 0:
            content = str(esLvl) +' | '+'制动'+('%.1f%%'%(-esLvl*100/maxBLvl))
        else:
            content = str(esLvl) +' | '+'惰行'+('%.1f%%'%(esLvl))
        led.setText(content)
        led.setCursorPosition(0) 

    @staticmethod
    def ctrlLevelDisplay(lvl=int, lvlLimit='list', lbl=QtWidgets.QLabel, led=QtWidgets.QLineEdit):
        if lvlLimit:
            [maxTLvl, maxBLvl] = lvlLimit
        else:
            maxTLvl = 10
            maxBLvl = 7
        if lvl > 0:
            content = str(lvl) +' | '+'牵引'+('%.1f%%'%(lvl*100/maxTLvl))
        elif lvl < 0:
            content = str(lvl) +' | '+'制动'+('%.1f%%'%(-lvl*100/maxBLvl))
        else:
            content = str(lvl) +' | '+'惰行'+('%.1f%%'%(lvl))
        led.setText(content)
        led.setCursorPosition(0)  
    
    @staticmethod
    def ctrlRampDisplay(ramp=int, lbl=QtWidgets.QLabel, led=QtWidgets.QLineEdit):
        if ramp > 0:
            content = str(ramp)+' | '+'上坡'
        elif ramp < 0:
            content = str(ramp)+' | '+'下坡'
        else:
            content = str(ramp)+' | '+'平坡'
        led.setText('千分之'+content) 
        led.setCursorPosition(0)

    @staticmethod
    def ctrlEstimateRampDisplay(esRamp=int, lbl=QtWidgets.QLabel, led=QtWidgets.QLineEdit):
        if esRamp > 0:
            content = str(esRamp)+' | '+'上坡'
        elif esRamp < 0:
            content = str(esRamp)+' | '+'下坡'
        else:
            content = str(esRamp)+' | '+'平坡'
        led.setText('千分之'+content)
        led.setCursorPosition(0)

    @staticmethod
    def ctrlTargetPosDisplay(tPos=int, lbl=QtWidgets.QLabel, led=QtWidgets.QLineEdit):
        if tPos == 0xFFFFFFFF:
            led.setText("无效值")
        else:
            led.setText(str(tPos)+'cm')
        led.setCursorPosition(0) 
    
    @staticmethod
    def ctrlTargetSpeedDisplay(tspeed=int, lbl=QtWidgets.QLabel, led=QtWidgets.QLineEdit):
        content = str(tspeed)+'cm/s'+' | ' +AtoKeyInfoDisplay.getStrKmh(tspeed)+'km/h'
        led.setText(content) 
        led.setCursorPosition(0)
    
    @staticmethod
    def ctrlTargetDisDisplay(tPos=int, curPos=int, lbl=QtWidgets.QLabel, led=QtWidgets.QLineEdit):
        if tPos == 0xFFFFFFFF:
            led.setText("无效值")
        else:
            dis = (tPos - curPos)/100
            led.setText('%.2fm'%dis)
        led.setCursorPosition(0) 

    @staticmethod
    def ctrlSkipDisplay(skip=int, lbl=QtWidgets.QLabel):
        if skip == 1:
            lbl.setText('前方站通过')
        else:
            lbl.setText('前方站到发')
    
    @staticmethod
    def getStrKmh(cms=int):
        return ('%.2f'%(cms*9/250))

    @staticmethod
    def disTurnbackTable(a2tMsg=Ato2tsrsProto, t2aMsg=Tsrs2atoProto, lblTb=QtWidgets.QLabel,tbTable=QtWidgets.QTableWidget):
        if t2aMsg and t2aMsg.c47 and t2aMsg.c47.updateflag:
            tbPlan = t2aMsg.c47
            item = QtWidgets.QTableWidgetItem(Tsrs2atoFieldDic["m_tbplan"].meaning[tbPlan.m_tbplan])
            tbTable.setItem(0, 0, item)
            item = QtWidgets.QTableWidgetItem(str(tbPlan.nid_tbdeparttrack))
            tbTable.setItem(0, 1, item)
            item = QtWidgets.QTableWidgetItem(hex(tbPlan.nid_operational))
            tbTable.setItem(0, 2, item)
            item = QtWidgets.QTableWidgetItem(str(tbPlan.nid_tbarrivaltrack))
            tbTable.setItem(0, 3, item)
            item = QtWidgets.QTableWidgetItem(Tsrs2atoFieldDic["m_task"].meaning[tbPlan.m_task])
            tbTable.setItem(0, 4, item)

        if a2tMsg and a2tMsg.c48 and a2tMsg.c48.updateflag:
            tbAck = a2tMsg.c48
            item = QtWidgets.QTableWidgetItem(Tsrs2atoFieldDic["m_tbplan"].meaning[tbAck.m_tbplan])
            tbTable.setItem(1, 0, item)
            item = QtWidgets.QTableWidgetItem(str(tbAck.nid_tbdeparttrack))
            tbTable.setItem(1, 1, item)
            item = QtWidgets.QTableWidgetItem(hex(tbAck.nid_operational))
            tbTable.setItem(1, 2, item)
            item = QtWidgets.QTableWidgetItem(str(tbAck.nid_tbarrivaltrack))
            tbTable.setItem(1, 3, item)
            item = QtWidgets.QTableWidgetItem(Tsrs2atoFieldDic["m_task"].meaning[tbAck.m_task])
            tbTable.setItem(1, 4, item)
            lblTb.setText(Tsrs2atoFieldDic["m_tbstatus"].meaning[tbAck.m_tbstatus])

class ProgressBarDisplay(object):
    """
    Default total percent is 100 and should execute in one thread at the same time
    """
    def __init__(self, bar=QtWidgets.QProgressBar) -> None:
        self.bar           = bar
        self.percent       = 0
        self.allTicks      = 0  # 期望总数
        self.percentTick   = 0  # 计算百分比的tick
        self.tick          = 0
    
    def barMoving(self):
        """
        本函数应该在循环中调用
        """
        percent = self.barMovingCompute()
        if percent:
            self.bar.setValue(self.percent)
            self.bar.show()
        else:
            pass
    
    def barMovingCompute(self):
        """
        本函数应该在循环中调用
        """
        self.tick  = self.tick + 1
        if self.percentTick == 0:
            return None
        if (self.tick % self.percentTick) == 0:
            self.percent = self.percent + 1
            return self.percent
        else:
            return None

    def setBarStat(self, initPct=int, movePct=int, allTicks=int):
        self.percent       = initPct
        self.allTicks      = allTicks  # 期望总数
        self.percentTick   = int(allTicks/movePct)  # 计算百分比的tick
        self.tick          = 0