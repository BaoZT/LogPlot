#!/usr/bin/env python
# encoding: utf-8
'''
@author:  Baozhengtang
@license: (C) Copyright 2017-2018, Author Limited.
@contact: baozhengtang@gmail.com
@software: LogPlot
@file: TCMSParse.py
@time: 2018/4/20 14:56
@desc: 本文件用于MVB解析功能
LastEditors: Zhengtang Bao
LastEditTime: 2022-09-15 11:37:49
'''

from PyQt5 import  QtWidgets,QtGui
from ConfigInfo import ConfigFile
from ProtocolParser.CommonParse import BytesStream
from MsgParse import ProtoField

b_endian = 0x4321
l_endian = 0x1234

MVBFieldDic = {
    'frame_header_recv':ProtoField("帧头",0,b_endian,8,None,{3:"接收数据帧"}),
    'frame_header_send':ProtoField("帧头",0,b_endian,8,None,{1:"发送数据帧"}),
    'frame_seq':ProtoField("包序号",0,b_endian,8,None,None),
    'frame_port':ProtoField("MVB端口号",0,l_endian,16,None,None),
    'ato_heartbeat':ProtoField("ATO心跳",0,b_endian,8,None,None),
    # ATO 控制
    'ato_valid':ProtoField("ATO有效",0,b_endian,8,None,{0xAA:"ATO有效",0x00:"ATO无效"}),
    'track_brake_cmd':ProtoField("牵引/制动命令状态标志",0,b_endian,8,None,{0xAA:"牵引",0x55:"制动",0xA5:"惰行",0x00:"无命令"}),
    'track_value':ProtoField("牵引控制量",0,b_endian,16,None,None),
    'brake_value':ProtoField("制动控制量",0,b_endian,16,None,None),
    'keep_brake_on':ProtoField("保持制动施加命令",0,b_endian,8,None,{0xAA:"施加有效,",0x00:"施加无效"}),
    'open_left_door':ProtoField("开左门命令",0,b_endian,2,None,{3:"有效命令",0:"无动作"}),
    'open_right_door':ProtoField("开右门命令",0,b_endian,2,None,{3:"有效命令",0:"无动作"}),
    'const_speed_cmd':ProtoField("恒速命令(预留)",0,b_endian,8,None,{0xAA:"启动恒速",0x00:"取消恒速"}),
    'const_speed_value':ProtoField("恒速目标速度(预留)",0,b_endian,16,"km/h",{0xFFFF:"按当前速度执行恒速",0:"取消恒速时"}),
    'ato_start_light':ProtoField("ATO启动灯",0,b_endian,8,None,{0xAA:"亮",0x00:"灭"}),
    'ato_tb_light':ProtoField("折返指示灯",0,b_endian,8,None,{0xAA:"亮",0x00:"灭"}),
    # ATO状态
    'ato_error':ProtoField("ATO故障信息",0,b_endian,8,None,{0xAA:"无故障",0x00:"故障"}),
    'killometer_marker':ProtoField("公里标",0,b_endian,32,"m",None),
    'tunnel_entrance':ProtoField("隧道入口",0,b_endian,16,"m",None),
    'tunnel_length':ProtoField("隧道长度",0,b_endian,16,"m",None),
    'ato_speed':ProtoField("ATO速度",0,b_endian,16,"0.1km/h",None),
    # TCMS状态
    'tcms_heartbeat':ProtoField("TCMS心跳",0,b_endian,8,None,None),
    'door_mode_mo_mc':ProtoField("MO/MC",0,b_endian,2,None,{3:"有效",0:"无效"}),
    'door_mode_ao_mc':ProtoField("AO/MC",0,b_endian,2,None,{3:"有效",0:"无效"}),
    'door_mode_ao_ac':ProtoField("AO/AC",0,b_endian,2,None,{3:"有效",0:"无效"}),
    'ato_start_btn_valid':ProtoField("ATO启动按钮有效信号",0,b_endian,2,None,{3:"按钮有效",0:"按钮无效"}),
    'ato_tb_btn_valid':ProtoField("驾驶台折返按钮有效信号",0,b_endian,2,None,{3:"按钮有效",0:"按钮无效"}),
    'ato_valid_feedback':ProtoField("ATO有效命令反馈",0,b_endian,8,None,{0xAA:"ATO有效",0x00:"ATO无效"}),
    'track_brack_cmd_feedback':ProtoField("牵引/制动命令状态标志反馈",0,b_endian,8,None,{0xAA:"牵引",0x55:"制动",0xA5:"惰行",0x00:"无命令"}),
    'track_value_feedback':ProtoField("牵引控制量反馈",0,b_endian,16,None,None),
    'brake_value_feedback':ProtoField("制动控制量反馈",0,b_endian,16,None,None),
    'ato_keep_brake_on_feedback':ProtoField("ATO保持制动施加命令反馈",0,b_endian,8,None,{0xAA:"保持制动有效",0x00:"保持制动无效"}),
    'open_left_door_feedback':ProtoField("开左门命令反馈",0,b_endian,2,None,{3:"有效命令",0:"无动作"}),
    'open_right_door_feedback':ProtoField("开右门命令反馈",0,b_endian,2,None,{3:"有效命令",0:"无动作"}),
    'constant_state_feedback':ProtoField("恒速反馈(预留)",0,b_endian,8,None,{0xAA:"处于恒速状态",0x00:"退出恒速状态"}),
    'door_state':ProtoField("车门状态",0,b_endian,8,None,{0xAA:"车门关锁闭",0x00:"车门未关或锁闭"}),
    'spin_state':ProtoField("空转",0,b_endian,4,None,{10:"发生",0:"未发生"}),
    'slip_state':ProtoField("打滑",0,b_endian,4,None,{10:"发生",0:"不发生"}),
    'train_unit':ProtoField("编组信息",0,b_endian,8,None,{1:"8编组",2:"8编组重连",3:"16编组",4:"17编组"}),
    'train_weight':ProtoField("车重",0,b_endian,16,"0.1t",None),
    'train_permit_ato':ProtoField("动车组允许ATO控车信号",0,b_endian,8,None,{0xAA:"车辆允许",0x00:"车辆不允许"}),
    'main_circuit_breaker':ProtoField("主断路器状态",0,b_endian,8,None,{0xAA:"主断闭合",0x00:"主断断开"}),
    'atp_door_permit':ProtoField("ATP开门允许",0,b_endian,2,None,{3:"有效",0:"无效"}),
    'man_door_permit':ProtoField("人工开门允许",0,b_endian,2,None,{3:"有效",0:"无效"}),
    'no_permit_ato_state':ProtoField("不允许ATO控车信号状态字",0,b_endian,8,None,None)
}



class DisplayMVBField(object):
    @staticmethod
    def disTcmsNoPmState(value=int):
        str_tcms = ''
        str_raw = ['未定义', '至少有一个车辆空气制动不可用|', 'CCU存在限速保护|', 'CCU自动施加常用制动|',
                    '车辆施加紧急制动EB或紧急制动UB|', '保持制动被隔离|',
                    'CCU判断与ATO通信故障(CCU监测到ATO生命信号32个周期(2s)不变化)|', '预留|']
        if 0 == value:
            return ('正常')
        else:
            for cnt in range(7, -1, -1):
                if value & (1 << cnt) != 0:
                    str_tcms = str_tcms + str_raw[cnt]
            return ('异常原因:%s' % str_tcms)

    @staticmethod
    def disTunnelInfo(tunnelDis=int,tunnelLen=int, lbl=QtWidgets.QLabel):
        expressStr = '隧道信息:'
        if (tunnelDis != 0xFFFF) and (tunnelDis != 0):
            expressStr += ('前方%dm有隧道,长度为%dm'%(tunnelDis,tunnelLen))
        elif tunnelDis == 0:
            expressStr += ('已经驶入隧道,长度为%dm'%(tunnelLen))
            lbl.setStyleSheet('background-color: rgb(255, 107, 107);')
        else:
            expressStr += '前方无隧道'
            lbl.setStyleSheet('background-color: rgb(247, 255, 247);')
        lbl.setText(expressStr)

    @staticmethod
    def disNameOfLineEdit(keyName=str, value=int, led=QtWidgets.QLineEdit):
        if keyName in MVBFieldDic.keys():
            # 如果有字段定义
            if MVBFieldDic[keyName].meaning:
                # 检查是否有含义
                if value in MVBFieldDic[keyName].meaning.keys():
                    led.setText(MVBFieldDic[keyName].meaning[value])
                # 检查是否有单位
                elif MVBFieldDic[keyName].unit:
                    led.setText(str(value)+'  '+MVBFieldDic[keyName].unit)
                else:
                    led.setStyleSheet("background-color: rgb(255, 0, 0);")
                    led.setText('异常值0x%X' % value)
            else:
                # 针对组合含义特殊解析
                if keyName == "no_permit_ato_state":
                    led.setText(DisplayMVBField.disTcmsNoPmState(value))
                else:
                    if MVBFieldDic[keyName].unit:
                        led.setText(str(value)+'  '+MVBFieldDic[keyName].unit)
                    else:
                        # 直接处理显示
                        led.setText(str(value))
        else:
            print("[ERR]:disNameOfLineEdit error key name!")
    
    @staticmethod # 解析工具的 名称、数值、解释 3列显示
    def disNameOfTreeWidget(obj, root=QtWidgets.QTreeWidgetItem, fieldDic='dict'):
        for keyName in obj.__slots__:
            if keyName in fieldDic.keys() :
                twi = QtWidgets.QTreeWidgetItem(root)  # 以该数据包作为父节点
                value = obj.__getattribute__(keyName)
                twi.setText(1,fieldDic[keyName].name)
                twi.setText(2,str(fieldDic[keyName].width))
                twi.setText(3,"0x"+("%02x"%value).upper())
                # 如果有字段定义
                if fieldDic[keyName].meaning:
                    # 检查是否有含义
                    if value in fieldDic[keyName].meaning.keys():
                        twi.setText(4,fieldDic[keyName].meaning[value])
                    elif keyName == 'd_tsm': # 含义和特殊值并存
                        if fieldDic[keyName].unit:
                            twi.setText(4, str(value)+fieldDic[keyName].unit)
                    else:
                        brush = QtGui.QBrush(QtGui.QColor(255, 0, 0)) #红色
                        twi.setBackground(1, brush)
                        twi.setBackground(2, brush)
                        twi.setBackground(3, brush)
                        twi.setBackground(4, brush)
                        twi.setText(4,'异常值%s' % value)
                else:
                    # 针对组合含义特殊解析
                    if keyName == "no_permit_ato_state":
                        twi.setText(4,DisplayMVBField.disTcmsNoPmState(value))
                    else:
                        # 直接处理显示
                        if fieldDic[keyName].unit:
                            twi.setText(4, str(value)+fieldDic[keyName].unit)
            elif keyName == 'updateflag':
                pass
            elif keyName == 'm_mode':
                pass
            else:
                print("[ERR]:disNameOfTreeWidget error key name!"+keyName)
        root.setExpanded(True)

class Ato2TcmsCtrl(object):
    __slots__ = ["frame_header_send","frame_seq","frame_port","ato_heartbeat","ato_valid",
    "track_brake_cmd","track_value","brake_value","keep_brake_on","open_left_door",'ato_tb_light',
    "open_right_door","const_speed_cmd","const_speed_value","ato_start_light","updateflag"]
    def __init__(self) -> None:
        self.updateflag = False
        # 定义ATO2TCMS控制字段
        self.frame_header_send = 0
        self.frame_seq    = 0
        self.frame_port   = 0
        self.ato_heartbeat = 0
        self.ato_valid = 0
        self.track_brake_cmd = 0
        self.track_value = 0
        self.brake_value = 0
        self.keep_brake_on = 0
        self.open_left_door = 0
        self.ato_tb_light = 0
        self.open_right_door = 0
        self.const_speed_cmd = 0
        self.const_speed_value = 0
        self.ato_start_light = 0

class Ato2TcmsState(object):
    __slots__ = ["frame_header_send","frame_seq","frame_port","ato_heartbeat","ato_error",
    "killometer_marker","tunnel_entrance","tunnel_length","ato_speed","updateflag"]
    def __init__(self) -> None:
        self.updateflag = False
        # 定义ATO2TCMS状态字段
        self.frame_header_send = 0
        self.frame_seq    = 0
        self.frame_port   = 0
        self.ato_heartbeat = 0
        self.ato_error = 0
        self.killometer_marker = 0
        self.tunnel_entrance = 0xFFFF
        self.tunnel_length = 0xFFFF
        self.ato_speed = 0

class Tcms2AtoState(object):
    __slots__ = ["frame_header_recv","frame_seq","frame_port","tcms_heartbeat","door_mode_mo_mc",
    "door_mode_ao_mc","door_mode_ao_ac","ato_start_btn_valid","ato_valid_feedback","track_brack_cmd_feedback",
    "track_value_feedback","brake_value_feedback","ato_keep_brake_on_feedback","open_left_door_feedback",
    "open_right_door_feedback","constant_state_feedback","door_state","spin_state","slip_state","train_unit",
    "train_weight","train_permit_ato","main_circuit_breaker","atp_door_permit","man_door_permit",
    "no_permit_ato_state","ato_tb_btn_valid","updateflag"]
    def __init__(self) -> None:
        self.updateflag = False
        # 定义ATO2TCMS状态字段
        self.frame_header_recv = 0
        self.frame_seq    = 0
        self.frame_port   = 0
        self.tcms_heartbeat = 0
        self.door_mode_mo_mc = 0
        self.door_mode_ao_mc = 0
        self.door_mode_ao_ac = 0
        self.ato_start_btn_valid = 0
        self.ato_tb_btn_valid = 0
        self.ato_valid_feedback = 0
        self.track_brack_cmd_feedback = 0
        self.track_value_feedback = 0
        self.brake_value_feedback = 0
        self.ato_keep_brake_on_feedback = 0
        self.open_left_door_feedback = 0
        self.open_right_door_feedback = 0
        self.constant_state_feedback = 0
        self.door_state = 0
        self.spin_state = 0
        self.slip_state = 0
        self.train_unit = 0
        self.train_weight = 0
        self.train_permit_ato = 0
        self.main_circuit_breaker = 0xAA
        self.atp_door_permit = 0
        self.man_door_permit = 0
        self.no_permit_ato_state = 0

class MVBParse(object):

    def __init__(self):
        self.cfg = ConfigFile()
        self.cfg.readConfigFile()
        self.ato2tcms_ctrl_obj = Ato2TcmsCtrl()
        self.ato2tcms_state_obj = Ato2TcmsState()
        self.tcms2ato_state_obj = Tcms2AtoState()
    
    def resetPacket(self):
        self.ato2tcms_ctrl_obj.updateflag = False
        self.ato2tcms_state_obj.updateflag = False
        self.ato2tcms_state_obj.updateflag = False

    '''
    @breif 从周期检查中获取的原始line进行解析获取解析结构结构体
    @mvb_line 原始的line也即只要"MVB["就进行尝试
    '''
    def parseProtocol(self, mvb_line=str):
        port = 0
        # 去除回车
        mvb_line = mvb_line.strip()
        # 抽取十六进制字符串
        mvb_line = ''.join(mvb_line.strip().split(' '))
        # 验证
        
        strByteLen = len(mvb_line)/2
        # 获取MVB端口,至少16字节数据
        if (len(mvb_line)%2 == 0) and strByteLen > 4:
            port = int(mvb_line[6:8] + mvb_line[4:6], 16)
            try:
                mvbData = BytesStream(mvb_line)
                # 查询端口解析并核对包长
                if strByteLen >= 20 and port == self.cfg.mvb_config.ato2tcms_ctrl_port:
                    self.parseAto2TcmsCtrl(mvbData,self.ato2tcms_ctrl_obj)
                elif strByteLen >= 20 and port == self.cfg.mvb_config.ato2tcms_state_port:
                    self.parseAto2TcmsState(mvbData,self.ato2tcms_state_obj)
                elif strByteLen >= 36 and port == self.cfg.mvb_config.tcms2ato_state_port:
                    pass
                    self.parseTcms2AtoState(mvbData, self.tcms2ato_state_obj)
                else:
                    print("[MVB]err mvb line:"+mvb_line)
            except Exception as err:
                print("err mvb line"+mvb_line)
        else:
            pass
            
        return (self.ato2tcms_ctrl_obj, self.ato2tcms_state_obj, self.tcms2ato_state_obj)

    def parseAto2TcmsCtrl(self,item=BytesStream,obj=Ato2TcmsCtrl):
        obj.frame_header_send= item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.frame_seq        = item.fast_get_segment_by_index(item.curBitsIndex,8)
        # 端口小端
        lsb = item.fast_get_segment_by_index(item.curBitsIndex,8)
        hsb = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.frame_port       = (hsb<<8)+lsb
        obj.ato_heartbeat    = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.ato_valid        = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.track_brake_cmd  = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.track_value      = item.fast_get_segment_by_index(item.curBitsIndex,16) 
        obj.brake_value      = item.fast_get_segment_by_index(item.curBitsIndex,16)
        obj.keep_brake_on    = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.open_left_door   = item.fast_get_segment_by_index(item.curBitsIndex,2)
        item.fast_get_segment_by_index(item.curBitsIndex,2) #reserved bit
        obj.open_right_door  = item.fast_get_segment_by_index(item.curBitsIndex,2)
        item.fast_get_segment_by_index(item.curBitsIndex,2) #reserved bit
        obj.const_speed_cmd  = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.const_speed_value= item.fast_get_segment_by_index(item.curBitsIndex,16)
        obj.ato_start_light  = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.ato_tb_light     = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.updateflag = True
    
    def parseAto2TcmsState(self,item=BytesStream,obj=Ato2TcmsState):
        obj.frame_header_send= item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.frame_seq        = item.fast_get_segment_by_index(item.curBitsIndex,8)
        # 端口小端
        lsb = item.fast_get_segment_by_index(item.curBitsIndex,8)
        hsb = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.frame_port       = (hsb<<8)+lsb
        obj.ato_heartbeat    = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.ato_error        = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.killometer_marker= item.fast_get_segment_by_index(item.curBitsIndex,32)
        obj.tunnel_entrance  = item.fast_get_segment_by_index(item.curBitsIndex,16) 
        obj.tunnel_length    = item.fast_get_segment_by_index(item.curBitsIndex,16)
        obj.ato_speed        = item.fast_get_segment_by_index(item.curBitsIndex,16)
        obj.updateflag = True

    def parseTcms2AtoState(self,item=BytesStream,obj=Tcms2AtoState):
        obj.frame_header_recv     = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.frame_seq        = item.fast_get_segment_by_index(item.curBitsIndex,8)
        # 端口小端
        lsb = item.fast_get_segment_by_index(item.curBitsIndex,8)
        hsb = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.frame_port       = (hsb<<8)+lsb
        obj.tcms_heartbeat   = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.door_mode_mo_mc = item.fast_get_segment_by_index(item.curBitsIndex,2)
        obj.door_mode_ao_mc = item.fast_get_segment_by_index(item.curBitsIndex,2)
        obj.door_mode_ao_ac = item.fast_get_segment_by_index(item.curBitsIndex,2)
        obj.ato_start_btn_valid = item.fast_get_segment_by_index(item.curBitsIndex,2)
        obj.ato_valid_feedback = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.track_brack_cmd_feedback = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.track_value_feedback = item.fast_get_segment_by_index(item.curBitsIndex,16)
        obj.brake_value_feedback = item.fast_get_segment_by_index(item.curBitsIndex,16)
        obj.ato_keep_brake_on_feedback = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.open_left_door_feedback = item.fast_get_segment_by_index(item.curBitsIndex,2)
        item.fast_get_segment_by_index(item.curBitsIndex,2) #reserved bit
        obj.open_right_door_feedback = item.fast_get_segment_by_index(item.curBitsIndex,2)
        item.fast_get_segment_by_index(item.curBitsIndex,2) #reserved bit
        obj.constant_state_feedback = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.door_state = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.spin_state = item.fast_get_segment_by_index(item.curBitsIndex,4)
        obj.slip_state = item.fast_get_segment_by_index(item.curBitsIndex,4)
        obj.train_unit = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.train_weight = item.fast_get_segment_by_index(item.curBitsIndex,16)
        obj.train_permit_ato = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.main_circuit_breaker = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.atp_door_permit = item.fast_get_segment_by_index(item.curBitsIndex,2)
        obj.man_door_permit = item.fast_get_segment_by_index(item.curBitsIndex,2)
        obj.ato_tb_btn_valid = item.fast_get_segment_by_index(item.curBitsIndex,2)
        item.fast_get_segment_by_index(item.curBitsIndex,2) #reserved bit
        obj.no_permit_ato_state = item.fast_get_segment_by_index(item.curBitsIndex,8)
        obj.updateflag = True

    @staticmethod
    def Log(msg=str, fun=str, lino=int):
        if str == type(msg):
            print(msg + ',File:"' + __file__ + '",Line' + str(lino) +
                  ', in' + fun)
        else:
            print(msg)
            print(',File:"' + __file__ + '",Line' + str(lino) + ', in' + fun)
