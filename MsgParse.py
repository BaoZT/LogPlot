#!/usr/bin/env python
# encoding: utf-8
'''
Author: Zhengtang Bao
Contact: baozhengtang@crscd.com.cn
File: MsgParse
Date: 2022-07-10 15:13:50
Desc: 本文件用于消息记录中的ATP-ATO,ATO-TSRS功能
LastEditors: Zhengtang Bao
LastEditTime: 2022-08-31 22:24:16
'''

from statistics import mean
from PyQt5 import  QtWidgets,QtGui
from ProtocolParser.CommonParse import BytesStream

b_endian = 0x4321
l_endian = 0x1234

class ProtoField(object):
    __slots__ = ["name","value","endian","width","unit","meaning"]
    def __init__(self,n="field",v=0,e=b_endian,w=0,u=None,m=None) -> None:
        self.name = n
        self.value = v
        self.endian = e
        self.width = w
        self.unit = u
        self.meaning = m

Atp2atpFieldDic={
        'nid_packet':ProtoField("信息包号",0,b_endian,8,None,None),
        'nid_sub_packet':ProtoField("子包信息包号",0,b_endian,8,None,None),
        'l_packet':ProtoField("信息包位数",0,b_endian,13,None,None),
        'q_scale':ProtoField("距离/长度的分辨率 ",0,b_endian,2,None,{0:"10cm",1:"1m",2:"10m"}),
        'nid_lrbg':ProtoField("最近相关应答器组（LRBG）的标识号",24,b_endian,8,None,None),
        'd_lrbg':ProtoField("最后相关应答器组与列车估计前端(在激活的驾驶室侧)之间的距离",0,b_endian,8,None,None),
        'q_dirlrbg':ProtoField("相对于LRGB方向的列车取向(激活驾驶室的位置取向)",0,b_endian,2,None,None),
        'q_dlrbg':ProtoField("指出列车估计前端位于LRBG哪一侧",0,b_endian,2,None,None),
        'l_doubtover':ProtoField("过读误差",0,b_endian,15,None,None),
        'l_doubtunder':ProtoField("欠读误差",0,b_endian,15,None,None),
        'q_length':ProtoField("列车完整性状态",0,b_endian,2,None,None),
        'l_traint':ProtoField("安全车长",0,b_endian,15,None,None),
        'v_train':ProtoField("实际列车速度5km/h",0,b_endian,7,None,None),
        'q_dirtrain':ProtoField("相对于LRBG方向的列车运行方向",0,b_endian,2,None,None),
        'm_mode_c2':ProtoField("ATP模式C2等级",0,b_endian,4,None,{1:"待机模式",2:"完全监控",3:"部分监控",4:"反向完全监控",5:"引导模式",6:"应答器故障",7:"目视行车",8:"调车模式",9:"隔离模式",10:"机车信号",11:"休眠模式"}),
        'm_mode_c3':ProtoField("ATP模式C3等级",0,b_endian,4,None,{0:"完全监控",1:"引导模式",2:"目视行车",3:"调车模式",5:"休眠模式",6:"待机模式",7:"冒进防护",8:"冒进后防护",9:"系统故障",10:"隔离模式",13:"SN",14:"退行模式"}),
        'm_level':ProtoField("ATP等级",0,b_endian,3,None,{1:"CTCS-2",3:"CTCS-3",4:"CTCS-4"}),
        'nid_stm':ProtoField("本国系统等级",0,b_endian,8,None,None),
        'btm_antenna_position':ProtoField("BTM 天线位置",0,b_endian,8,"10cm",None),
        'd_cz_sig_pos':ProtoField("前方出站信号机距离",0xFFFFFFFF,b_endian,32,"cm",None),
        'd_jz_sig_pos':ProtoField("前方进站信号机距离",0xFFFFFFFF,b_endian,32,"cm",None),
        'd_ma':ProtoField("ATP的移动授权终点",0xFFFF,b_endian,16,"m",None),
        'd_neu_sec':ProtoField("到最近一个分相区的距离",0xFFFF,b_endian,16,"m",None),
        'd_normal':ProtoField("列车累计走行距离",0xFFFFFFFF,b_endian,32,"cm",None),
        'd_pos_adj':ProtoField("列车位置校正值",0xFFFFFFFF,b_endian,32,"cm",None),
        'd_station_mid_pos':ProtoField("站台/股道中心距离",0xFFFFFFFF,b_endian,32,"cm",None),
        'd_stop':ProtoField("本应答器距离运营停车点距离",0,b_endian,15,"cm",None),
        'd_target':ProtoField("目标距离",0xFFFFFFFF,b_endian,32,"cm",None),
        'd_tsm':ProtoField("前方TSM区的距离",0xFFFFFFFF,b_endian,32,"cm",{0x7FFFFFFF:"TSM无穷远",0xFFFFFFFF:"无TSM区或处于TSM区"}),
        'd_trackcond':ProtoField("到特殊轨道区段长度的距离",0xFFFFFFFF,b_endian,32,"cm",None),
        'l_door_distance':ProtoField("第一对客室门距车头的距离",0,b_endian,16,"cm",None),
        'l_sdu_wheel_size_1':ProtoField("ATP速传1对应轮径值",0,b_endian,16,"mm",None),
        'l_sdu_wheel_size_2':ProtoField("ATP速传2对应轮径值",0,b_endian,16,"mm",None),
        'l_text':ProtoField("文本长度",0,b_endian,8,None,None),
        'l_trackcond':ProtoField("特殊轨道区段的长度",0xFFFFFFFF,b_endian,32,"cm",None),
        'l_train':ProtoField("列车长度",0,b_endian,12,"m",None),
        'm_atoerror':ProtoField("ATO故障码",0,b_endian,16,None,None),
        'm_atomode':ProtoField("ATO模式",0,b_endian,4,None,{0:"ATO故障",1:"AOS模式",2:"AOR模式",3:"AOM模式",4:"AOF模式"}),
        'm_ato_control_strategy':ProtoField("ATO 当前在用控车策略",0,b_endian,4,None,{1:"默认策略",2:"快行策略",3:"慢行策略",4:"计划控车"}),
        'm_ato_plan':ProtoField("计划状态",0,b_endian,2,None,{0:"不显示",1:"计划有效",2:"计划无效"}),
        'm_ato_skip':ProtoField("计划通过",0,b_endian,2,None,{0:"不显示",1:"前方通过"}),
        'm_ato_stop_error':ProtoField("ATO停准误差",0,b_endian,16,"cm",None),
        'm_ato_tb':ProtoField("折返状态",0,b_endian,2,None,{0:"不显示",1:"折返允许",2:"司机确认后折返"}),
        'm_ato_tbs':ProtoField("ATO 牵引/制动状态",0,b_endian,2,None,{0:"不显示",1:"牵引",2:"制动",3:"惰行"}),
        'm_ato_time':ProtoField("发车倒计时",0,b_endian,16,"s",None),
        'm_atp_stop_error':ProtoField("ATP停车误差",0,b_endian,16,"cm",None),
        'm_cab_state':ProtoField("驾驶台激活状态",0,b_endian,2,None,{0:"异常",1:"驾驶室打开",2:"驾驶室关闭"}),
        'm_doormode':ProtoField("门控模式",0,b_endian,2,None,{1:"MM",2:"AM",3:"AA"}),
        'm_doorstatus':ProtoField("车门状态",0,b_endian,2,None,{0:"异常",1:"车门开",2:"车门关"}),
        'm_gprs_radio':ProtoField("电台注册状态",0,b_endian,2,None,{0:"无电台",1:"电台正常"}),
        'm_gprs_session':ProtoField("与TSRS连接状态",0,b_endian,2,None,{0:"不显示",1:"TSRS未连接",2:"TSRS连接中",3:"TSRS连接"}),
        'm_low_frequency':ProtoField("轨道电路低频信息",0,b_endian,8,None,{0x01:"无码",0x00:"H码",0x02:"HU",0x10:"HB码",0x2A:"L4码",0x2B:"L5码",
        0x25:"U2S码",0x23:"UUS码",0x22:"UU码",0x21:"U码",0x24:"U2码",0x26:"LU码",0x28:"L2码",0x27:"L码",0x29:"L3码"}),
        'm_ms_cmd':ProtoField("ATP断主断命令",0,b_endian,2,None,{1:"ATP断主断",2:"ATP合主断"}),
        'm_position':ProtoField("公里标",0xFFFFFFFF,b_endian,32,"m",None),
        'm_session_type':ProtoField("发起GPRS呼叫/断开的原因",0,b_endian,3,None,{0:"来自应答器发起",1:"来自人工选择数据发起",2:"来自人工选择预选ATO发起"}),
        'm_tcms_com':ProtoField("与车辆通信状态",0,b_endian,2,None,{0:"不显示",1:"MVB正常",2:"MVB中断"}),
        'm_tco_state':ProtoField("ATP切牵引状态",0,b_endian,2,"cm",{1:"ATP切牵",2:"ATP未切牵"}),
        'reserve':ProtoField("ATP制动状态(预留)",0,b_endian,2,"cm",{1:"ATP制动",2:"ATP未制动",0:"制动未知"}),
        'm_trackcond':ProtoField("特殊轨道区段类型",0,b_endian,4,"cm",None),
        'n_sequence':ProtoField("消息序号",0,b_endian,32,None,None),
        'nid_bg':ProtoField("应答器组ID",0,b_endian,24,None,None),
        'nid_driver':ProtoField("司机号",0,b_endian,32,None,None),
        'nid_engine':ProtoField("车载设备CTCS标识",0,b_endian,24,None,None),
        'nid_operational':ProtoField("车次号",0,b_endian,32,None,None),
        'nid_radio_h':ProtoField("无线用户地址高32",0,b_endian,32,None,None),
        'nid_radio_l':ProtoField("无线用户地址地32",0,b_endian,32,None,None),
        'nid_text':ProtoField("文本编号",0,b_endian,8,None,{0:"备用",1:"站台门联动失败",2:"动车组不允许控车",3:"停车不办客",4:"ATO起车异常"}),
        'nid_tsrs':ProtoField("TSRS编号",0,b_endian,14,None,None),
        'nid_c':ProtoField("地区编号",0,b_endian,10,None,None),
        'nid_xuser':ProtoField("子包标识",0,b_endian,8,None,{13:"有精确定位包",0:"无精确定位包"}),
        'n_g':ProtoField("列车停靠股道编号",0,b_endian,24,None,None),
        'n_iter':ProtoField("迭代字段",0,b_endian,5,None,None),
        'n_units':ProtoField("列车编组类型",0,b_endian,8,None,{1:"8编组",2:"16编组",3:"17编组"}),
        'o_train_pos':ProtoField("经过校正的列车位置",0,b_endian,32,"cm",None),
        'q_atopermit':ProtoField("ATO通信允许",0,b_endian,2,None,{0:"备用",1:"软允许",2:"无软允许"}),
        'q_ato_hardpermit':ProtoField("ATO硬通信允许",0,b_endian,2,None,{0:"备用",1:"硬允许",2:"无硬允许"}),
        'q_dispaly':ProtoField("显示/删除属性",0,b_endian,1,None,{0:"删除",1:"显示"}),
        'q_door':ProtoField("站台是否设置站台门",0,b_endian,2,None,{1:"有站台门",2:"无站台门",0:"无效=0"}),
        'q_door_cmd_dir':ProtoField("开关门命令验证方向",0,b_endian,2,None,{0:"反向",1:"正向",2:"无效=2",3:"无效=3"}),
        'q_leftdoorpermit':ProtoField("左门允许命令",0,b_endian,2,None,{1:"左门允许",2:"不允许"}),
        'q_platform':ProtoField("站台位置",0,b_endian,2,None,{0:"左侧",1:"右侧",2:"双侧",3:"无站台"}),
        'q_rightdoorpermit':ProtoField("右门允许命令",0,b_endian,2,None,{1:"右门允许",2:"不允许"}),
        'q_sleepsession':ProtoField("睡眠设备的通信管理",0,b_endian,1,None,{0:"忽略",1:"考虑"}),
        'q_stopstatus':ProtoField("停稳停准状态",0,b_endian,4,None,{0:"未停稳",1:"停稳未停准",2:"停稳停准"}),
        'q_tb':ProtoField("立折标志",0,b_endian,2,None,{0:"无折返",1:"原地折返"}),
        'q_tsrs':ProtoField("与TSRS的通信命令",0,b_endian,1,None,{0:"断开通信会话",1:"建立通信会话"}),
        't_atp':ProtoField("ATP系统时间",0,b_endian,32,"ms",None),
        't_cutoff_traction':ProtoField("进入分相区前体检输出断主断的时间",0,b_endian,16,"100ms",None),
        't_day':ProtoField("日期时间-日",0,b_endian,8,None,None),
        't_year':ProtoField("日期时间-年",0,b_endian,8,None,None),
        't_month':ProtoField("日期时间-月",0,b_endian,8,None,None),
        't_hour':ProtoField("日期时间-时",0,b_endian,8,None,None),
        't_minites':ProtoField("日期时间-分",0,b_endian,8,None,None),
        't_seconds':ProtoField("日期时间-秒",0,b_endian,8,None,None),
        't_middle':ProtoField("过应答器中心ATP系统时间",0,b_endian,32,"ms",None),
        'v_ato_permitted':ProtoField("控车策略",0,b_endian,4,None,{1:"默认策略",2:"快行策略",3:"慢行策略"}),
        'v_normal':ProtoField("列车速度ATP",0,b_endian,16,"cm/s",None),
        'v_permitted':ProtoField("ATP允许速度",32768,b_endian,16,"cm/s",None),
        'v_target':ProtoField("目标速度",0,b_endian,16,"cm/s",None),
        'x_text':ProtoField("文本",0,b_endian,8,None,None),
        'q_ato_tb_status':ProtoField("ATO允许换端折返状态", 0, b_endian, 8, None, {0x00:"无折返允许", 0x5A:"允许换端", 0xA5:"允许折返"}),
        'q_tb_ob_btn':ProtoField('驾驶台换端按钮',0,b_endian,4, None, {0:"未按下", 1:"按下", 15:"状态异常"}),
        'q_tb_stn_btn':ProtoField('轨旁换端按钮',0,b_endian,4, None, {0:"未按下", 1:"按下", 15:"状态异常"}),
        'q_headtail':ProtoField('首尾端状态',0,b_endian,4, None, {0:"非折返换端", 1:"首端", 2:"尾端"}),
        'q_tb_status':ProtoField('换端折返状态',0,b_endian,4, None, {0x00:"非折返换端", 0x01:"自动换端进行中", 
        0x02:"自动换端条件具备", 0x03:"无人自折准备", 0x04:"无人自折折入", 0x05:"无人自折折出", 0x06:"无人自折条件具备",
        0x07:"无人自折失败", 0x08:"自动换端失败"}),
        'q_tb_relay':ProtoField('折返继电器状态',0,b_endian,4, None, {0:"落下", 1:"吸起", 15:"状态异常"}),
        'm_tb_display':ProtoField('DMI显示换端折返流程',0,b_endian,8, None, {0x00:"非折返换端", 0x01:"无人自折中断", 
        0x02:"无人自折结束", 0x03:"无人自折进行中", 0x04:"无人自折条件具备", 0x05:"自动换端中断", 0x06:"自动换端结束",
        0x07:"自动换端进行中", 0x08:"自动换端条件具备"})

}

class DisplayMsgield(object):
   
    @staticmethod
    def disTsmStat(value, lbl=QtWidgets.QLabel):
        if value == 0x7FFFFFFF or value != 0xFFFFFFFF:
            lbl.setText("恒速区")
            lbl.setStyleSheet("background-color: rgb(0, 255, 127);")
        else:
            lbl.setText("减速区")
            lbl.setStyleSheet("background-color: rgb(255, 255, 0);")
    
    @staticmethod
    def disAtpDoorPmt(ldp=int,rdp=int,lbl=QtWidgets.QLabel):
        if ldp == 1 and rdp == 1:
            lbl.setText("双侧门允许")
            lbl.setStyleSheet("background-color: rgb(0, 255, 127);")
        elif ldp == 1 and rdp == 2:
            lbl.setText("左门允许")
            lbl.setStyleSheet("background-color: rgb(0, 255, 127);")
        elif ldp == 2 and rdp == 1:
            lbl.setText("右门允许")
            lbl.setStyleSheet("background-color: rgb(0, 255, 127);")
        else:
            lbl.setText("无门允许")
            lbl.setStyleSheet("background-color: rgb(170, 170, 255);")

    @staticmethod
    def disNameOfLineEdit(keyName=str, value=int, led=QtWidgets.QLineEdit):
        if keyName in Atp2atpFieldDic.keys():
            # 如果有含义的话
            if Atp2atpFieldDic[keyName].meaning:
                # 检查是否有含义
                if value in Atp2atpFieldDic[keyName].meaning.keys():
                    led.setText(Atp2atpFieldDic[keyName].meaning[value])
                # 检查是否有单位
                elif Atp2atpFieldDic[keyName].unit:
                    led.setText(str(value)+' '+Atp2atpFieldDic[keyName].unit)
                else:
                    led.setStyleSheet("background-color: rgb(255, 0, 0);")
                    led.setText('异常%d' % value)
            else:
                # 直接处理显示
                if keyName == "m_position":
                    if not value == 0xFFFFFFFF:
                        led.setText('K' + str(int(value/ 1000)) + '+' + str(value % 1000))
                    else:
                        led.setText(str(0))
                elif keyName == "nid_operational":
                    led.setText(hex(value))
                else:
                    if Atp2atpFieldDic[keyName].unit:
                        led.setText(str(value)+Atp2atpFieldDic[keyName].unit)
                    else:
                        led.setText(str(value))
        else:
            print("[ERR]:DisplayMsgield disNameOfLineEdit error key name!")

    @staticmethod
    def disNameOfLable(keyName=str, value=int, lbl=QtWidgets.QLabel,keyGoodVal=-1, keyBadval=-1):
        if keyName in Atp2atpFieldDic.keys():
            # 如果有字段定义
            if Atp2atpFieldDic[keyName].meaning:
                # 检查是否有含义
                if value in Atp2atpFieldDic[keyName].meaning.keys():
                    lbl.setText(Atp2atpFieldDic[keyName].meaning[value])
                    # 提供关键显示功能
                    if value == keyGoodVal:
                        lbl.setStyleSheet("background-color: rgb(0, 255, 127);")
                    elif value == keyBadval:
                        lbl.setStyleSheet("background-color: rgb(255, 0, 0);")
                    else:
                        lbl.setStyleSheet("background-color: rgb(170, 170, 255);")
                else:
                    lbl.setStyleSheet("background-color: rgb(255, 0, 0);")
                    lbl.setText('异常%d' % value)
            else:
                # 直接处理显示
                lbl.setText(keyName+str(value))
        else:
            print("[ERR]:DisplayMsgield disNameOfLable error key name!")

    @staticmethod # 解析工具的 名称、数值、解释 3列显示
    def disNameOfTreeWidget(obj, root=QtWidgets.QTreeWidgetItem, fieldDic='dict', nomBrush=QtGui.QBrush):
        for keyName in obj.__slots__:
            if keyName in fieldDic.keys() :
                twi = QtWidgets.QTreeWidgetItem(root)  # 以该数据包作为父节点
                value = obj.__getattribute__(keyName)
                twi.setText(1,fieldDic[keyName].name)
                twi.setText(2,str(fieldDic[keyName].width)+'bits')
                twi.setText(3,str(value))
                # 上色
                for i in range(1, twi.columnCount()+1):
                    twi.setBackground(i, nomBrush)
                # 如果有字段定义
                if fieldDic[keyName].meaning:
                    # 检查是否有含义
                    if value in fieldDic[keyName].meaning.keys():
                        twi.setText(4,fieldDic[keyName].meaning[value])
                    elif keyName == 'd_tsm': # 含义和特殊值并存
                        if fieldDic[keyName].unit:
                            twi.setText(4, str(value)+'('+fieldDic[keyName].unit+')')
                    else:
                        brush = QtGui.QBrush(QtGui.QColor(255, 0, 0)) #红色
                        for i in range(1,twi.columnCount()+1):
                            twi.setBackground(i, brush)
                        twi.setText(4,'异常值%s' % value)
                else:
                    # 直接处理显示
                    if fieldDic[keyName].unit:
                        twi.setText(4, str(value)+'('+fieldDic[keyName].unit+')')
            elif keyName == 'updateflag':
                pass
            else:
                print("[ERR]:disNameOfTreeWidget error key name!"+keyName)
        root.setExpanded(True)


class sp0(object):
    __slots__ = ["updateflag","nid_sub_packet","l_packet","q_scale","nid_lrbg","d_lrbg",
    "q_dirlrbg","q_dlrbg","l_doubtover","l_doubtunder","q_length",
    "q_length","l_traint","v_train","q_dirtrain","m_mode_c2","m_mode_c3","m_level","nid_stm"]
    def __init__(self) -> None:
        self.updateflag    = False
        self.nid_sub_packet= 0
        self.l_packet      = 0
        self.q_scale       = 0
        self.nid_lrbg      = 0
        self.d_lrbg        = 0
        self.q_dirlrbg     = 0
        self.q_dlrbg       = 0
        self.l_doubtover   = 0
        self.l_doubtunder  = 0
        self.q_length      = 0
        self.l_traint      = 0
        self.v_train       = 0
        self.q_dirtrain    = 0
        self.m_mode_c2     = 0
        self.m_mode_c3     = 0
        self.m_level       = 0
        self.nid_stm       = 0

class sp1(object):
    __slots__ = ["updateflag","nid_sub_packet","l_packet","q_scale","nid_lrbg","nid_prvbg","d_lrbg",
    "q_dirlrbg","q_dlrbg","l_doubtover","l_doubtunder","q_length",
    "q_length","l_traint","v_train","q_dirtrain","m_mode_c2","m_mode_c3",
    "m_level","nid_stm"]
    def __init__(self) -> None:
        self.updateflag    = False
        self.nid_sub_packet= 1
        self.l_packet      = 0
        self.q_scale       = 0
        self.nid_lrbg      = 0
        self.nid_prvbg     = 0
        self.d_lrbg        = 0
        self.q_dirlrbg     = 0
        self.q_dlrbg       = 0
        self.l_doubtover   = 0
        self.l_doubtunder  = 0
        self.q_length      = 0
        self.l_traint      = 0
        self.v_train       = 0
        self.q_dirtrain    = 0
        self.m_mode_c2     = 0
        self.m_mode_c3     = 0
        self.m_level       = 0
        self.nid_stm       = 0

class sp2(object):
    __slots__ = ["updateflag","nid_sub_packet","q_atopermit","q_ato_hardpermit","q_leftdoorpermit","q_rightdoorpermit","q_door_cmd_dir",
    "q_tb","v_target","d_target","m_level","m_mode_c2","m_mode_c3","o_train_pos","v_permitted","d_ma","m_ms_cmd","d_neu_sec",
    "m_low_frequency","q_stopstatus","m_atp_stop_error","d_station_mid_pos","d_jz_sig_pos","d_cz_sig_pos",
    "d_tsm","m_cab_state","m_position","m_tco_state","reserve"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 2
        self.q_atopermit       = 0
        self.q_ato_hardpermit  = 0
        self.q_leftdoorpermit  = 0
        self.q_rightdoorpermit = 0
        self.q_door_cmd_dir    = 0
        self.q_tb              = 0
        self.v_target          = 0
        self.d_target          = 0
        self.m_level           = 0
        self.m_mode_c2         = 0
        self.m_mode_c3         = 0
        self.o_train_pos       = 0
        self.v_permitted       = 0
        self.d_ma              = 0
        self.m_ms_cmd          = 0
        self.d_neu_sec         = 0
        self.m_low_frequency   = 0
        self.q_stopstatus      = 0
        self.m_atp_stop_error  = 0
        self.d_station_mid_pos = 0
        self.d_jz_sig_pos      = 0
        self.d_cz_sig_pos      = 0
        self.d_tsm             = 0
        self.m_cab_state       = 0
        self.m_position        = 0
        self.m_tco_state       = 0
        self.reserve           = 0

class sp3(object):
    __slots__ = ["updateflag","nid_sub_packet","t_atp"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 3
        self.t_atp             = 0

class sp4(object):
    __slots__ = ["updateflag","nid_sub_packet","v_normal","d_normal"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 4
        self.v_normal          = 0
        self.d_normal          = 0

class sp5(object):
    __slots__ = ["updateflag","nid_sub_packet","n_units","nid_operational","nid_driver","btm_antenna_position",
    "l_door_distance","l_sdu_wheel_size_1","l_sdu_wheel_size_2","t_cutoff_traction","nid_engine",
    "v_ato_permitted"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 5
        self.n_units           = 0
        self.nid_operational   = 0
        self.nid_driver        = 0
        self.btm_antenna_position = 0
        self.l_door_distance   = 0
        self.l_sdu_wheel_size_1= 0
        self.l_sdu_wheel_size_2= 0
        self.t_cutoff_traction = 0
        self.nid_engine        = 0
        self.v_ato_permitted   = 0

class sp6(object):
    __slots__ = ["updateflag","nid_sub_packet","t_year","t_month","t_day","t_hour",
    "t_minutes","t_seconds"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 6
        self.t_year            = 0
        self.t_month           = 0
        self.t_day             = 0
        self.t_hour            = 0
        self.t_minutes         = 0
        self.t_seconds         = 0

class sp7(object):
    __slots__ = ["updateflag","nid_sub_packet","nid_bg","t_middle","d_pos_adj","nid_xuser",
    "q_scale","q_platform","q_door","n_g","d_stop"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 7
        self.nid_bg            = 0
        self.t_middle          = 0
        self.d_pos_adj         = 0
        self.nid_xuser         = 0
        self.q_scale           = 0
        self.q_platform        = 0
        self.q_door            = 0
        self.n_g               = 0
        self.d_stop            = 0

class sp8(object):
    __slots__ = ["updateflag","nid_sub_packet","q_tsrs","nid_c","nid_tsrs","nid_radio_h","nid_radio_l",
    "q_sleepsession","m_session_type"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 8
        self.q_tsrs            = 0
        self.nid_c             = 0
        self.nid_tsrs          = 0
        self.nid_radio_h       = 0
        self.nid_radio_l       = 0
        self.q_sleepsession    = 0
        self.m_session_type    = 0

class sp9_sp_track(object):
    __slots__ = ["d_trackcond","l_trackcond","m_trackcond"]
    def __init__(self) -> None:
        self.d_trackcond = 0xffffffff
        self.l_trackcond = 0xffffffff
        self.m_trackcond = 0

class sp9(object):
    __slots__ = ["updateflag","nid_sub_packet","n_iter","sp_track_list"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 9
        self.n_iter            = 0
        self.sp_track_list     = None

class sp10(object):
    __slots__ = ["updateflag", "nid_sub_packet","q_headtail", "q_tb_status", "q_tb_relay", "m_tb_display"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 10
        self.q_headtail        = 0
        self.q_tb_status       = 0
        self.q_tb_relay        = 0
        self.m_tb_display      = 0

class sp130(object):
    __slots__ = ["updateflag","nid_sub_packet","m_atomode","m_doormode","m_doorstatus","m_atoerror",
    "m_ato_stop_error"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 130
        self.m_atomode         = 0
        self.m_doormode        = 0
        self.m_doorstatus      = 0
        self.m_atoerror        = 0
        self.m_ato_stop_error  = 0

class sp131(object):
    __slots__ = ["updateflag","nid_sub_packet","m_ato_tbs","m_ato_skip","m_ato_plan","m_ato_time",
    "m_tcms_com","m_gprs_radio","m_gprs_session","m_ato_control_strategy","paddings"]
    def __init__(self) -> None:
        self.updateflag        = False    
        self.nid_sub_packet    = 131
        self.m_ato_tbs         = 0
        self.m_ato_skip        = 0
        self.m_ato_plan        = 0
        self.m_ato_time        = 0
        self.m_tcms_com        = 0
        self.m_gprs_radio      = 0
        self.m_gprs_session    = 0
        self.m_ato_control_strategy  = 0
        self.paddings          = 0

class sp132(object):
    __slots__ = ["updateflag","nid_sub_packet"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 132

class sp133(object):
    __slots__ = ["updateflag","nid_sub_packet","nid_c","nid_tsrs","nid_radio_h","nid_radio_l"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 133
        self.nid_c             = 0
        self.nid_tsrs          = 0
        self.nid_radio_h       = 0
        self.nid_radio_l       = 0

class sp134(object):
    __slots__ = ["updateflag","nid_sub_packet","nid_text","q_display","l_text","x_text"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 134
        self.nid_text          = 0
        self.q_display         = 0
        self.l_text            = 0
        self.x_text            = None

class sp135(object):
    __slots__ = ["updateflag", "nid_sub_packet","q_ato_tb_status", "q_tb_ob_btn", "q_tb_stn_btn","nid_operational"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 135
        self.q_ato_tb_status   = 0
        self.q_tb_ob_btn       = 0
        self.q_tb_stn_btn      = 0
        self.nid_operational   = 0

class Atp2atoProto(object):
    __slots__ = ["nid_packet","t_msg_atp","crc_code","n_sequence","l_msg","sp0_obj","sp1_obj","sp2_obj","sp3_obj",
    "sp4_obj","sp5_obj","sp6_obj","sp7_obj","sp8_obj","sp9_obj","sp10_obj","sp130_obj","sp131_obj",
    "sp132_obj","sp133_obj","sp134_obj","sp135_obj","l_packet","nid_msg"]

    def __init__(self) -> None:
        self.nid_packet = 0     # packet id
        self.l_packet   = 0
        self.t_msg_atp  = 0     # atp timestamp
        self.crc_code   = 0     # crc
        self.n_sequence = 0     # msg seq
        self.l_msg      = 0     # msg length
        self.nid_msg    = 0
        self.sp0_obj   = sp0()
        self.sp1_obj   = sp1()
        self.sp2_obj   = sp2()
        self.sp3_obj   = sp3()
        self.sp4_obj   = sp4()
        self.sp5_obj   = sp5()
        self.sp6_obj   = sp6()
        self.sp7_obj   = sp7()
        self.sp8_obj   = sp8()
        self.sp9_obj   = sp9()
        self.sp10_obj  = sp10()
        self.sp130_obj = sp130()
        self.sp131_obj = sp131()
        self.sp132_obj = sp132()
        self.sp133_obj = sp133()
        self.sp134_obj = sp134()
        self.sp135_obj = sp135()

class Atp2atoParse(object):
    __slots__ = ["msg_obj","pktParseFnDic","objParseDic"]
    
    def __init__(self) -> None:
        self.msg_obj = Atp2atoProto()
        self.pktParseFnDic  ={
        0:Atp2atoParse.sp0Parse,
        1:Atp2atoParse.sp1Parse,
        2:Atp2atoParse.sp2Parse,
        3:Atp2atoParse.sp3Parse,
        4:Atp2atoParse.sp4Parse,
        5:Atp2atoParse.sp5Parse,
        6:Atp2atoParse.sp6Parse,
        7:Atp2atoParse.sp7Parse,
        8:Atp2atoParse.sp8Parse,
        9:Atp2atoParse.sp9Parse,
        10:Atp2atoParse.sp10Parse,
        130:Atp2atoParse.sp130Parse,
        131:Atp2atoParse.sp131Parse,
        132:Atp2atoParse.sp132Parse,
        133:Atp2atoParse.sp133Parse,
        134:Atp2atoParse.sp134Parse,
        135:Atp2atoParse.sp135Parse,
        }

        self.objParseDic  ={
        0:self.msg_obj.sp0_obj,
        1:self.msg_obj.sp1_obj,
        2:self.msg_obj.sp2_obj,
        3:self.msg_obj.sp3_obj,
        4:self.msg_obj.sp4_obj,
        5:self.msg_obj.sp5_obj,
        6:self.msg_obj.sp6_obj,
        7:self.msg_obj.sp7_obj,
        8:self.msg_obj.sp8_obj,
        9:self.msg_obj.sp9_obj,
        10:self.msg_obj.sp10_obj,
        130:self.msg_obj.sp130_obj,
        131:self.msg_obj.sp131_obj,
        132:self.msg_obj.sp132_obj,
        133:self.msg_obj.sp133_obj,
        134:self.msg_obj.sp134_obj,
        135:self.msg_obj.sp135_obj,
        }

    @staticmethod
    def resetMsg(msg_obj=Atp2atoProto):
        msg_obj.sp0_obj.updateflag = False
        msg_obj.sp1_obj.updateflag = False
        msg_obj.sp2_obj.updateflag = False
        msg_obj.sp3_obj.updateflag = False
        msg_obj.sp4_obj.updateflag = False
        msg_obj.sp5_obj.updateflag = False
        msg_obj.sp6_obj.updateflag = False
        msg_obj.sp7_obj.updateflag = False
        msg_obj.sp8_obj.updateflag = False
        msg_obj.sp9_obj.updateflag = False
        msg_obj.sp10_obj.updateflag = False
        msg_obj.sp130_obj.updateflag = False
        msg_obj.sp131_obj.updateflag = False
        msg_obj.sp132_obj.updateflag = False
        msg_obj.sp133_obj.updateflag = False
        msg_obj.sp134_obj.updateflag = False
        msg_obj.sp135_obj.updateflag = False

    # 消息完整解析
    def msgParse(self, line=str):
        # 去除换行回车
        line = line.strip()
        # 防护性编程外界保证数据仅可能有空格
        line = ''.join(line.split(' '))
        item = None
        # 校验字节数至少29字节包含SP3/4
        if (len(line)%2 == 0) and (len(line)/2>=29):
            try:
                int(line, 16) # 校验防护
                item = BytesStream(line)
            except Exception as err:
                print("Bytes string err!"+line)
        else:
            pass
        # 尝试解析消息 
        if item:
            # 首先重置所有包更新标志
            self.msg_obj.nid_msg = item.fast_get_segment_by_index(item.curBitsIndex, 8)
            self.msg_obj.l_msg = item.fast_get_segment_by_index(item.curBitsIndex, 8)
            # 以下为lpacket描述范围
            self.msg_obj.nid_packet = item.fast_get_segment_by_index(item.curBitsIndex, 8)
            self.msg_obj.l_packet = item.fast_get_segment_by_index(item.curBitsIndex, 13)
            # 校验消息
            if self.msg_obj.l_msg <= (len(line)/2): # FIXME: 此处由于打印多一个字符导致
                self.msg_obj.crc_code = self.allPktsParse(item,self.msg_obj.l_msg, self.msg_obj.l_packet)
            else:
                print("err atp2ato msg:"+line)
        else:
            pass
        return self.msg_obj
        
    @staticmethod
    def sp0Parse(item, obj=sp0):
        """
        except nid_xuser 8bit
        """
        obj.l_packet = item.fast_get_segment_by_index(item.curBitsIndex, 13)
        obj.q_scale = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.nid_lrbg = item.fast_get_segment_by_index(item.curBitsIndex, 24)  # NID_LRBG
        obj.d_lrbg = item.fast_get_segment_by_index(item.curBitsIndex, 15)
        obj.q_dirlrbg = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.q_dlrbg = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.l_doubtover = item.fast_get_segment_by_index(item.curBitsIndex, 15)
        obj.l_doubtunder = item.fast_get_segment_by_index(item.curBitsIndex, 15)
        obj.q_length = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        
        # 列车完整性确认
        if obj.q_length == 1 or obj.q_length == 2:
            obj.l_traint = item.fast_get_segment_by_index(item.curBitsIndex, 15)
            obj.v_train = item.fast_get_segment_by_index(item.curBitsIndex, 7)
            obj.q_dirtrain = item.fast_get_segment_by_index(item.curBitsIndex, 2)
            obj.m_mode_c3 = item.fast_get_segment_by_index(item.curBitsIndex, 4)
            obj.m_mode_c2 = obj.m_mode_c3
            obj.m_level =  item.fast_get_segment_by_index(item.curBitsIndex, 3)
            if obj.m_level == 1:
                obj.nid_stm = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        else:
            obj.v_train = item.fast_get_segment_by_index(item.curBitsIndex, 7)
            obj.q_dirtrain = item.fast_get_segment_by_index(item.curBitsIndex, 2)
            obj.m_mode_c3 = item.fast_get_segment_by_index(item.curBitsIndex, 4)
            obj.m_mode_c2 = obj.m_mode_c3
            obj.m_level = item.fast_get_segment_by_index(item.curBitsIndex, 3)
            if obj.m_level == 1:
                obj.nid_stm = item.fast_get_segment_by_index(item.curBitsIndex, 8) 
        obj.updateflag = True
    
    @staticmethod
    def sp1Parse(item, obj=sp1):
        """
        except nid_xuser 8bit
        """
        obj.l_packet = item.fast_get_segment_by_index(item.curBitsIndex, 13)
        obj.q_scale = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.nid_lrbg = item.fast_get_segment_by_index(item.curBitsIndex, 24)  # NID_LRBG
        obj.nid_prvbg = item.fast_get_segment_by_index(item.curBitsIndex, 24)  # NID_PRVBG
        obj.d_lrbg = item.fast_get_segment_by_index(item.curBitsIndex, 15)
        obj.q_dirlrbg = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.q_dlrbg = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.l_doubtover = item.fast_get_segment_by_index(item.curBitsIndex, 15)
        obj.l_doubtunder = item.fast_get_segment_by_index(item.curBitsIndex, 15)
        obj.q_length = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        # 列车完整性确认
        if obj.q_length == 1 or obj.q_length == 2:
            obj.l_traint = item.fast_get_segment_by_index(item.curBitsIndex, 15)
            obj.v_train = item.fast_get_segment_by_index(item.curBitsIndex, 7)
            obj.q_dirtrain = item.fast_get_segment_by_index(item.curBitsIndex, 2)
            obj.m_mode_c3 = item.fast_get_segment_by_index(item.curBitsIndex, 4)
            obj.m_mode_c2 = obj.m_mode_c3
            obj.m_level = item.fast_get_segment_by_index(item.curBitsIndex, 3)
            if obj.m_level == 1:
                obj.nid_stm = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        else:
            obj.v_train = item.fast_get_segment_by_index(item.curBitsIndex, 7)
            obj.q_dirtrain = item.fast_get_segment_by_index(item.curBitsIndex, 2)
            obj.m_mode_c3 = item.fast_get_segment_by_index(item.curBitsIndex, 4)
            obj.m_mode_c2 = obj.m_mode_c3
            obj.m_level = item.fast_get_segment_by_index(item.curBitsIndex, 3)
            if obj.m_level == 1:
                obj.nid_stm = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.updateflag = True

    @staticmethod
    def sp2Parse(item, obj=sp2):
        """
        except nid_xuser 8bit
        """
        obj.q_atopermit = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.q_ato_hardpermit = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.q_leftdoorpermit = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.q_rightdoorpermit =  item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.q_door_cmd_dir =  item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.q_tb = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.v_target = item.fast_get_segment_by_index(item.curBitsIndex, 16)
        obj.d_target = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.m_level = item.fast_get_segment_by_index(item.curBitsIndex, 3)  # M_LEVEL
        if obj.m_level == 1:
            obj.m_mode_c2 = item.fast_get_segment_by_index(item.curBitsIndex, 4)  # M_MODE
        elif obj.m_level == 3:
            obj.m_mode_c3 = item.fast_get_segment_by_index(item.curBitsIndex, 4)  # M_MODE
        else:
            pass
        obj.o_train_pos = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.v_permitted = item.fast_get_segment_by_index(item.curBitsIndex, 16)
        obj.d_ma = item.fast_get_segment_by_index(item.curBitsIndex, 16)
        obj.m_ms_cmd = item.fast_get_segment_by_index(item.curBitsIndex, 2)  # M_MS_CMD
        obj.d_neu_sec = item.fast_get_segment_by_index(item.curBitsIndex, 16) # D_DEU_SEC
        obj.m_low_frequency = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.q_stopstatus = item.fast_get_segment_by_index(item.curBitsIndex, 4)
        obj.m_atp_stop_error = item.fast_get_segment_by_index(item.curBitsIndex, 16)
        obj.d_station_mid_pos = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.d_jz_sig_pos = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.d_cz_sig_pos = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.d_tsm = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.m_cab_state = item.fast_get_segment_by_index(item.curBitsIndex, 2) # M_CAB_STATE
        obj.m_position = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.m_tco_state = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.reserve = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.updateflag = True

    @staticmethod
    def sp3Parse(item, obj=sp3):
        """
        except nid_xuser 8bit
        """
        obj.t_atp =item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.updateflag = True

    @staticmethod
    def sp4Parse(item, obj=sp4):
        """
        except nid_xuser 8bit
        """
        obj.v_normal = item.fast_get_segment_by_index(item.curBitsIndex, 16, sign=1)
        obj.d_normal = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.updateflag = True

    @staticmethod
    def sp5Parse(item, obj=sp5):
        """
        except nid_xuser 8bit
        """
        obj.n_units = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.nid_operational = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.nid_driver = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.btm_antenna_position = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.l_door_distance = item.fast_get_segment_by_index(item.curBitsIndex, 16)
        obj.l_sdu_wheel_size_1 = item.fast_get_segment_by_index(item.curBitsIndex, 16)
        obj.l_sdu_wheel_size_2 = item.fast_get_segment_by_index(item.curBitsIndex, 16)
        obj.t_cutoff_traction = item.fast_get_segment_by_index(item.curBitsIndex, 16)
        obj.nid_engine = item.fast_get_segment_by_index(item.curBitsIndex, 24)
        obj.v_ato_permitted = item.fast_get_segment_by_index(item.curBitsIndex, 4)
        obj.updateflag = True

    @staticmethod
    def sp6Parse(item, obj=sp6):
        """
        except nid_xuser 8bit
        """
        obj.t_year = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.t_month = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.t_day = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.t_hour = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.t_minutes = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.t_seconds = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.updateflag = True

    @staticmethod
    def sp7Parse(item, obj=sp7):
        """
        except nid_xuser 8bit
        """ 
        obj.nid_bg = item.fast_get_segment_by_index(item.curBitsIndex, 24)
        obj.t_middle = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.d_pos_adj = item.fast_get_segment_by_index(item.curBitsIndex, 32, sign=1)
        obj.nid_xuser = item.fast_get_segment_by_index(item.curBitsIndex, 9)
        # 解析到7包
        if  obj.nid_xuser == 13:
            obj.q_scale = item.fast_get_segment_by_index(item.curBitsIndex, 2)
            obj.q_platform = item.fast_get_segment_by_index(item.curBitsIndex, 2)
            obj.q_door = item.fast_get_segment_by_index(item.curBitsIndex, 2)
            obj.n_g = item.fast_get_segment_by_index(item.curBitsIndex, 24)
            obj.d_stop = item.fast_get_segment_by_index(item.curBitsIndex, 15)
        obj.updateflag = True

    @staticmethod
    def sp8Parse(item, obj=sp8):
        """
        except nid_xuser 8bit
        """ 
        obj.q_tsrs = item.fast_get_segment_by_index(item.curBitsIndex, 1)
        obj.nid_c = item.fast_get_segment_by_index(item.curBitsIndex, 10)
        obj.nid_tsrs = item.fast_get_segment_by_index(item.curBitsIndex, 14)
        obj.nid_radio_h = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.nid_radio_l = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.q_sleepsession = item.fast_get_segment_by_index(item.curBitsIndex, 1)
        obj.m_session_type = item.fast_get_segment_by_index(item.curBitsIndex, 3)  
        obj.updateflag = True

    @staticmethod
    def sp9Parse(item, obj=sp9):
        """
        except nid_xuser 8bit
        """
        obj.n_iter = item.fast_get_segment_by_index(item.curBitsIndex, 5)
        obj.sp_track_list = list()
        for i in range(obj.n_iter):
            tmp = sp9_sp_track()
            tmp.d_trackcond =  item.fast_get_segment_by_index(item.curBitsIndex, 32)
            tmp.l_trackcond = item.fast_get_segment_by_index(item.curBitsIndex, 32)
            tmp.m_trackcond = item.fast_get_segment_by_index(item.curBitsIndex, 4)
            obj.sp_track_list.append(tmp)
        obj.updateflag = True

    @staticmethod
    def sp10Parse(item, obj=sp10):
        """
        sy ato specific packet
        """
        obj.q_headtail = item.fast_get_segment_by_index(item.curBitsIndex, 4)
        obj.q_tb_status = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.q_tb_relay = item.fast_get_segment_by_index(item.curBitsIndex, 4)
        obj.m_tb_display = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.updateflag = True

    @staticmethod
    def sp130Parse(item, obj=sp130):
        """
        except nid_xuser 8bit
        """
        obj.m_atomode = item.fast_get_segment_by_index(item.curBitsIndex, 4)
        obj.m_doormode = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.m_doorstatus = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.m_atoerror = item.fast_get_segment_by_index(item.curBitsIndex, 16)
        obj.m_ato_stop_error = item.fast_get_segment_by_index(item.curBitsIndex, 16)
        obj.updateflag = True
    
    @staticmethod
    def sp131Parse(item, obj=sp131):
        """
        except nid_xuser 8bit
        """
        obj.m_ato_tbs = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.m_ato_skip = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.m_ato_plan = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.m_ato_time = item.fast_get_segment_by_index(item.curBitsIndex, 16)
        obj.m_tcms_com = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.m_gprs_radio = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.m_gprs_session = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.m_ato_control_strategy = item.fast_get_segment_by_index(item.curBitsIndex, 4)
        obj.paddings = item.fast_get_segment_by_index(item.curBitsIndex, 16)
        obj.updateflag = True

    @staticmethod
    def sp132Parse(item, obj=sp132):
        """
        except nid_xuser 8bit, no content
        """
        obj.updateflag = True
    
    @staticmethod
    def sp133Parse(item, obj=sp133):
        """
        except nid_xuser 8bi
        """
        obj.nid_c = item.fast_get_segment_by_index(item.curBitsIndex, 10)
        obj.nid_tsrs = item.fast_get_segment_by_index(item.curBitsIndex, 14)
        obj.nid_radio_h = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.nid_radio_l = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.updateflag = True

    @staticmethod
    def sp134Parse(item, obj=sp134):
        """
        except nid_xuser 8bit
        """
        obj.nid_text = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.q_display =  item.fast_get_segment_by_index(item.curBitsIndex, 1)
        obj.l_text = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.x_text = list()
        for i in range(obj.l_text):
            tmp = 0
            tmp = item.fast_get_segment_by_index(item.curBitsIndex, 8)
            obj.x_text.append(tmp)
        obj.updateflag = True
    
    @staticmethod
    def sp135Parse(item, obj=sp135):
        """
        sy ato specific packet
        """
        obj.q_ato_tb_status = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.q_tb_ob_btn = item.fast_get_segment_by_index(item.curBitsIndex, 4)
        obj.q_tb_stn_btn = item.fast_get_segment_by_index(item.curBitsIndex, 4)
        obj.nid_operational = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.updateflag = True

    # 数据包解析
    def allPktsParse(self, item=BytesStream,l_msg=int,l_packet=int):
        crc_code = 0 # 返回非0说明解析成功
        # 初始化bit数
        bit_idx = 0
        byte_idx = 0
        # 考虑消息头bit计数防护
        all_len = l_packet + 16 
        # 包内容解析
        while all_len != (item.curBitsIndex - bit_idx):
            nid_sub_packet = item.fast_get_segment_by_index(item.curBitsIndex, 8)
            if nid_sub_packet in self.pktParseFnDic.keys():
                self.pktParseFnDic[nid_sub_packet](item, self.objParseDic[nid_sub_packet])
            else:
                print('msg parse fatal err！no id:%d！byte:%d,bit:%d'%(nid_sub_packet, item.curBytesIndex,item.curBitsIndex))
            # 消息校验和监测
            if all_len == (item.curBitsIndex - bit_idx):
                if (all_len) % 8 == 0:    # 刚好除整数
                    pass
                else: # 重新校正bit索引
                    padding_bit = int(((all_len + 7) // 8) * 8) - all_len  # 字节下跳的bit数，减去消息头16bit和内容bit后
                    item.fast_get_segment_by_index(item.curBitsIndex, padding_bit)
                # 计算分析消息结尾
                self.msg_obj.n_sequence = item.fast_get_segment_by_index(item.curBitsIndex, 32)
                self.msg_obj.t_msg_atp = item.fast_get_segment_by_index(item.curBitsIndex, 32)
                crc_code = item.fast_get_segment_by_index(item.curBitsIndex, 32)

                if l_msg == item.curBytesIndex - byte_idx + 1:
                    break  # 消息校验正确不打印
                else:
                    print('msg parse fatal err！ l_msg %d, real %d' % (l_msg, item.curBytesIndex - byte_idx + 2))

        return crc_code

class Ctcs45(object):
    
    def __init__(self) -> None:
        pass


class Ato2tsrsProto(object):
    
    def __init__(self) -> None:
        self.nid_msg    = 0     # msg id
        self.l_msg      = 0     # msg length
        self.t_train    = 0     # train stamp
        self.nid_engine = 0     # ob ctcs id

class Tsrs2atoProto(object):

    def __init__(self) -> None:
        self.nid_msg   = 0
        self.l_msg     = 0
        self.t_train   = 0     # train stamp
        self.m_ack     = 0
        self.nid_lrbg  = 0     

class Tsrs2atoParse(object):
    __slots__ = ["msg_obj","pktParseFnDic","objParseDic"]
    
    def __init__(self) -> None:
        pass