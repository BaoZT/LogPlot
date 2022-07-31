#!/usr/bin/env python
# encoding: utf-8
'''
Author: Zhengtang Bao
Contact: baozhengtang@crscd.com.cn
File: MainWinDisplay
Date: 2022-07-25 20:09:57
Desc: 主界面关键数据处理及显示功能
LastEditors: Zhengtang Bao
LastEditTime: 2022-07-30 21:59:57
'''

from PyQt5 import QtWidgets,QtGui,QtCore
from MsgParse import Atp2atoProto, DisplayMsgield, sp2, sp7


class BtmInfoDisplay(object):
    # 作为类属性全局的
    btmCycleList = []
    btmItemRealList = []
    btmHeaders = ['时间', '应答器编号', '位置矫正值','ATP过中心点时间', '公里标']

    @staticmethod
    def displayInitClear(table=QtWidgets.QTableWidget):
        table.clear()
        table.setColumnCount(len(BtmInfoDisplay.btmHeaders))
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
    def GetBtmItemSelected(cycleDic="dict",item=QtWidgets.QTableWidgetItem, curInf=int, curMode=int,):
        obj = None
        # 离线&标记模式通过周期字典搜索
        if curInf == 1 and curMode == 1:
            if len(BtmInfoDisplay.btmCycleList) > item.row():
                cNum = BtmInfoDisplay.btmCycleList[item.row()]
                obj = cycleDic[cNum].msg_atp2ato.sp7_obj
        # 在线模式下通过保存的列表来进行搜索        
        elif curInf == 2:
            if len(BtmInfoDisplay.btmItemRealList) > item.row():
                obj = BtmInfoDisplay.btmItemRealList[item.row()]    # 通过保存的列表来二次索引
        return obj


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
                      0:"background-color: rgb(255, 0, 0);"}
}


class InerCustomField(object):
    __slots__ = ["name","unit","meaning"]
    def __init__(self,n="field",u=None,m=None) -> None:
        self.name = n
        self.unit = u
        self.meaning = m        

AtoInerDic={
    'ato_start_lamp':InerCustomField('发车指示灯',None,{0:"发车灯灭",1:"发车灯闪",2:"发车灯常亮"}),
    'ato_self_check':InerCustomField('自检状态',None,{1:"自检正常",0:"自检失败"}),
    'station_flag':InerCustomField('站台标志',None,{1:"位于站内",0:"位于区间"})
}

class AtoInfoDisplay(object):
    # 协议字段显示使用MVB和ATP2ATO协议
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
    def labelInterDisplay(keyName=str,value=int,lbl=QtWidgets.QLabel):
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
