#!/usr/bin/env python
# encoding: utf-8
'''
Author: Zhengtang Bao
Contact: baozhengtang@crscd.com.cn
File: MsgParse
Date: 2022-07-10 15:13:50
Desc: 本文件用于消息记录中的ATP-ATO,ATO-TSRS功能
LastEditors: Zhengtang Bao
LastEditTime: 2022-07-24 11:26:43
'''

from pickle import OBJ
from ConfigInfo import ConfigFile
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
        'm_mode_c2':ProtoField("ATP模式",0,b_endian,4,None,{1:"待机",2:"完全监控",3:"部分监控",4:"反向完全监控",5:"引导模式",6:"应答器故障",7:"目视行车",8:"调车",9:"隔离",10:"机车信号",11:"休眠"}),
        'm_mode_c3':ProtoField("ATP模式",0,b_endian,4,None,{0:"完全监控",1:"引导",2:"目视行车",3:"调车",5:"休眠",6:"待机",7:"冒进防护",8:"冒进后防护",9:"系统故障",10:"隔离",13:"SN",14:"退行"}),
        'm_level':ProtoField("ATP等级",0,b_endian,3,None,{1:"CTCS-2",3:"CTCS-3",4:"CTCS-4"}),
        'nid_stm':ProtoField("本国系统等级",0,b_endian,8,None,None),
        'btm_antenna_position':ProtoField("BTM 天线位置",0,b_endian,8,"10cm",None),
        'd_cz_sig_pos':ProtoField("前方出站信号机距离",0xFFFFFFFF,b_endian,32,"cm",None),
        'd_jz_sig_pos':ProtoField("前方进站信号机距离",0xFFFFFFFF,b_endian,32,"cm",None),
        'd_ma':ProtoField("ATP的移动授权终点",0xFFFF,b_endian,16,"m",None),
        'd_neu_sec':ProtoField("到最近一个分项区的距离",0xFFFF,b_endian,16,"m",None),
        'd_normal':ProtoField("列车累计走行距离",0xFFFFFFFF,b_endian,32,"cm",None),
        'd_pos_adj':ProtoField("列车位置校正值",0xFFFFFFFF,b_endian,32,"cm",None),
        'd_station_mid_pos':ProtoField("站台/股道中心距离",0xFFFFFFFF,b_endian,32,"cm",None),
        'd_stop':ProtoField("本应答器距离运营停车点距离",0,b_endian,15,"cm",None),
        'd_target':ProtoField("目标距离",0xFFFFFFFF,b_endian,32,"cm",None),
        'd_tsm':ProtoField("前方TSM区的距离",0xFFFFFFFF,b_endian,32,"cm",{0x7FFFFFFF:"无穷远",0xFFFFFFFF:"无TSM区或处于TSM区"}),
        'd_trackcond':ProtoField("到特殊轨道区段长度的距离",0xFFFFFFFF,b_endian,32,"cm",None),
        'l_door_distance':ProtoField("第一对客室门距车头的距离",0,b_endian,16,"cm",None),
        'l_sdu_wheel_size_1':ProtoField("ATP速传1对应轮径值",0,b_endian,16,"mm",None),
        'l_text':ProtoField("文本长度",0,b_endian,8,None,None),
        'l_trackcond':ProtoField("特殊轨道区段的长度",0xFFFFFFFF,b_endian,32,"cm",None),
        'l_train':ProtoField("列车长度",0,b_endian,12,"m",None),
        'm_atoerror':ProtoField("ATO故障码",0,b_endian,16,None,None),
        'm_atomode':ProtoField("ATO模式",0,b_endian,4,None,{0:"ATO故障",1:"AOS",2:"AOR",3:"AOM"}),
        'm_ato_control_strategy':ProtoField("ATO 当前在用控车策略",0,b_endian,4,None,{1:"默认策略",2:"快行策略",3:"慢行策略",4:"按计划控车"}),
        'm_ato_plan':ProtoField("计划状态",0,b_endian,2,None,{0:"不显示",1:"计划有效",2:"计划无效"}),
        'm_ato_skip':ProtoField("计划通过",0,b_endian,2,None,{0:"不显示",1:"前方通过"}),
        'm_ato_stop_error':ProtoField("ATO停准误差",0,b_endian,16,"cm",None),
        'm_ato_tb':ProtoField("折返状态",0,b_endian,2,None,{0:"不显示",1:"折返允许",2:"司机确认后折返"}),
        'm_ato_tbs':ProtoField("ATO 牵引/制动状态",0,b_endian,2,None,{0:"不显示",1:"牵引",2:"制动",3:"惰行"}),
        'm_ato_time':ProtoField("发车倒计时",0,b_endian,16,"s",None),
        'm_atp_stop_error':ProtoField("ATP停车误差",0,b_endian,16,"cm",None),
        'm_cab_state':ProtoField("驾驶台激活状态",0,b_endian,2,None,{0:"异常",1:"打开",2:"关闭"}),
        'm_doormode':ProtoField("门控模式",0,b_endian,2,None,{1:"MM",2:"AM",3:"AA"}),
        'm_doorstatus':ProtoField("车门状态",0,b_endian,2,None,{0:"异常",1:"车门开",2:"车门关"}),
        'm_gprs_radio':ProtoField("电台注册状态",0,b_endian,2,None,{0:"无电台",1:"有电台"}),
        'm_gprs_session':ProtoField("与TSRS连接状态",0,b_endian,2,None,{0:"不显示",1:"未连接",2:"正在连接",3:"已连接"}),
        'm_low_frequency':ProtoField("轨道电路低频信息",0,b_endian,8,None,{0x01:"无码",0x00:"H码",0x02:"HU",0x10:"HB码",0x2A:"L4码",0x2B:"L5码",
        0x25:"U2S码",0x23:"UUS码",0x22:"UU码",0x21:"U码",0x24:"U2码",0x26:"LU码",0x28:"L2码",0x27:"L码",0x29:"L3码"}),
        'm_ms_cmd':ProtoField("ATP断主断命令",0,b_endian,2,None,{1:"断主断",2:"合主断"}),
        'm_position':ProtoField("公里标",0xFFFFFFFF,b_endian,32,"m",None),
        'm_session_type':ProtoField("发起GPRS呼叫/断开的原因",0,b_endian,3,None,{0:"来自应答器发起",1:"来自人工选择数据发起",2:"来自人工选择预选ATO发起"}),
        'm_tcms_com':ProtoField("与车辆通信状态",0,b_endian,2,None,{0:"不显示",1:"MVB正常",2:"MVB中断"}),
        'm_tco_state':ProtoField("ATP切牵引状态",0,b_endian,2,"cm",{0:"切除牵引",2:"未切除牵引"}),
        'm_trackcond':ProtoField("特殊轨道区段类型",0,b_endian,4,"cm",None),
        'n_sequence':ProtoField("消息序号",0,b_endian,32,None,None),
        'nid_bg':ProtoField("应答器组ID",0,b_endian,24,None,None),
        'nid_driver':ProtoField("司机号",0,b_endian,32,None,None),
        'nid_engine':ProtoField("车载设备CTCS标识",0,b_endian,24,None,None),
        'nid_operational':ProtoField("车次好",0,b_endian,32,None,None),
        'nid_radio_h':ProtoField("无线用户地址高32",0,b_endian,32,None,None),
        'nid_radio_l':ProtoField("无线用户地址地32",0,b_endian,32,None,None),
        'nid_text':ProtoField("文本编号",0,b_endian,8,None,{0:"备用",1:"站台门联动失败",2:"动车组不允许控车",3:"停车不办客",4:"ATO起车异常"}),
        'nid_tsrs':ProtoField("TSRS编号",0,b_endian,14,None,None),
        'nid_c':ProtoField("地区编号",0,b_endian,10,None,None),
        'n_g':ProtoField("列车停靠股道编号",0,b_endian,24,None,None),
        'n_iter':ProtoField("迭代字段",0,b_endian,5,None,None),
        'n_units':ProtoField("列车编组类型",0,b_endian,8,None,{1:"8编组",2:"16编组",3:"17编组"}),
        'o_train_pos':ProtoField("经过校正的列车位置",0,b_endian,32,"cm",None),
        'q_atopermit':ProtoField("ATO通信允许",0,b_endian,2,None,{0:"备用",1:"允许",2:"不允许"}),
        'q_ato_hardpermit':ProtoField("ATO硬通信允许",0,b_endian,2,None,{0:"备用",1:"允许",2:"不允许"}),
        'q_dispaly':ProtoField("显示/删除属性",0,b_endian,1,None,{0:"删除",1:"显示"}),
        'q_door':ProtoField("站台是否设置站台门",0,b_endian,2,None,{1:"有站台门",2:"无站台门"}),
        'q_door_cmd_dir':ProtoField("开关门命令验证方向",0,b_endian,2,None,{0:"反向",1:"正向"}),
        'q_leftdoorpermit':ProtoField("左门允许命令",0,b_endian,2,None,{1:"允许",2:"不允许"}),
        'q_platform':ProtoField("站台位置",0,b_endian,2,None,{0:"左侧",1:"右侧",2:"双侧",3:"无站台"}),
        'q_rightdoorpermit':ProtoField("右门允许命令",0,b_endian,2,None,{1:"允许",2:"不允许"}),
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
        'v_permitted':ProtoField("ATP允许速度",0,b_endian,16,"cm/s",None),
        'v_target':ProtoField("目标速度",0,b_endian,16,"cm/s",None),
        'x_text':ProtoField("文本",0,b_endian,8,None,None)
}

class sp0(object):
    __slots__ = ["nid_sub_packet","l_packet","q_scale","nid_lrbg","d_lrbg",
    "q_dirlrbg","q_dlrbg","l_doubtover","l_doubtunder","q_length",
    "q_length","l_traint","v_train","q_dirtrain","m_mode_c2","m_mode_c3",
    "m_level","nid_stm","updateflag"]
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
    __slots__ = ["nid_sub_packet","l_packet","q_scale","nid_lrbg","nid_prvbg","d_lrbg",
    "q_dirlrbg","q_dlrbg","l_doubtover","l_doubtunder","q_length",
    "q_length","l_traint","v_train","q_dirtrain","m_mode_c2","m_mode_c3",
    "m_level","nid_stm","updateflag"]
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
    __slots__ = ["nid_sub_packet","q_atopermit","q_ato_hardpermit","q_leftdoorpermit","q_rightdoorpermit","q_door_cmd_dir",
    "q_tb","v_target","d_target","m_level","m_mode","o_train_pos","v_permitted","d_ma","m_ms_cmd","d_neu_sec",
    "m_low_frequency","q_stopstatus","m_atp_stop_error","d_station_mid_pos","d_jz_sig_pos","d_cz_sig_pos",
    "d_tsm","m_cab_state","m_position","m_tco_state","reserve","updateflag"]
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
        self.m_mode            = 0
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
    __slots__ = ["nid_sub_packet","t_atp","updateflag"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 3
        self.t_atp             = 0


class sp4(object):
    __slots__ = ["nid_sub_packet","v_normal","d_normal","updateflag"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 4
        self.v_normal          = 0
        self.d_normal          = 0

class sp5(object):
    __slots__ = ["nid_sub_packet","n_units","nid_operational","nid_driver","btm_antenna_position",
    "l_door_distance","l_sdu_wheel_size_1","l_sdu_wheel_size_2","t_cutoff_traction","nid_engine",
    "v_ato_permitted","updateflag"]
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
    __slots__ = ["nid_sub_packet","t_year","t_month","t_day","t_hour",
    "t_minutes","t_seconds","updateflag"]
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
    __slots__ = ["nid_sub_packet","nid_bg","t_middle","d_pos_adj","nid_xuser",
    "q_scale","q_platform","q_door","n_g","d_stop","updateflag"]
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
    __slots__ = ["nid_sub_packet","q_tsrs","nid_c","nid_tsrs","nid_radio_h","nid_radio_l",
    "q_sleepsession","m_session_type","updateflag"]
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
    __slots__ = ["nid_sub_packet","n_iter","sp_track_list","updateflag"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 9
        self.n_iter            = 0
        self.sp_track_list     = None

class sp130(object):
    __slots__ = ["nid_sub_packet","m_atomode","m_doormode","m_doorstatus","m_atoerror",
    "m_ato_stop_error","updateflag"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 130
        self.m_atomode         = 0
        self.m_doormode        = 0
        self.m_doorstatus      = 0
        self.m_atoerror        = 0
        self.m_ato_stop_error  = 0

class sp131(object):
    __slots__ = ["nid_sub_packet","m_ato_tbs","m_ato_skip","m_ato_plan","m_ato_time",
    "m_tcms_com","m_gprs_radio","m_gprs_session","m_ato_control_strategy",
    "paddings","updateflag"]
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
    __slots__ = ["nid_sub_packet","updateflag"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 132

class sp133(object):
    __slots__ = ["nid_sub_packet","nid_c","nid_tsrs","nid_radio_h","nid_radio_l","updateflag"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 133
        self.nid_c             = 0
        self.nid_tsrs          = 0
        self.nid_radio_h       = 0
        self.nid_radio_l       = 0

class sp134(object):
    __slots__ = ["nid_sub_packet","nid_text","q_display","l_text","x_text","updateflag"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 134
        self.nid_text          = 0
        self.q_display         = 0
        self.l_text            = 0
        self.x_text            = None

class Atp2atoProto(object):
    __slots__ = ["nid_packet","t_atp","n_sequence","l_msg","sp1_obj","sp2_obj","sp3_obj",
    "sp4_obj","sp5_obj","sp6_obj","sp7_obj","sp8_obj","sp9_obj","sp130_obj","sp131_obj",
    "sp132_obj","sp133_obj","sp134_obj"]
    def __init__(self) -> None:
        self.nid_packet = 0     # packet id
        self.t_atp      = 0     # atp timestamp
        self.n_sequence = 0     # msg seq
        self.l_msg      = 0     # msg length
        self.sp1_obj   = sp1()
        self.sp2_obj   = sp2()
        self.sp3_obj   = sp3()
        self.sp4_obj   = sp4()
        self.sp5_obj   = sp5()
        self.sp6_obj   = sp6()
        self.sp7_obj   = sp7()
        self.sp8_obj   = sp8()
        self.sp9_obj   = sp9()
        self.sp130_obj = sp130()
        self.sp131_obj = sp131()
        self.sp132_obj = sp132()
        self.sp133_obj = sp133()
        self.sp134_obj = sp134()


class Atp2atoParse(object):
    __slots__ = ["msg_obj","pktParseFnDic","update_flag"]
    
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
        130:Atp2atoParse.sp130Parse,
        131:Atp2atoParse.sp131Parse,
        132:Atp2atoParse.sp132Parse,
        133:Atp2atoParse.sp133Parse,
        134:Atp2atoParse.sp134Parse,
        }

    # 消息完整解析
    def msgParse(self, line=str):
        # 去除换行回车
        line = line.strip()
        # 防护性编程外界保证数据仅可能有空格
        if ' ' in line:
            line = ''.join(line.split(' '))
        else:
            pass
        try:
            int(line, 16) # 校验防护
            item = BytesStream(line)
        except Exception as err:
            print("Bytes string err!"+line)
            item = None
        if item:
            nid_msg = item.get_segment_by_index(item.curBitsIndex, 8)
            self.msg_obj.l_msg = item.get_segment_by_index(item.curBitsIndex, 8)
            self.allPktsParse(item,self.msg_obj.l_msg)
        else:
            pass
        return self.msg_obj
        
    @staticmethod
    def sp0Parse(item, obj=sp0):
        """
        except nid_xuser 8bit
        """
        obj.l_packet = item.get_segment_by_index(item.curBitsIndex, 13)
        obj.q_scale = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.nid_lrbg = item.get_segment_by_index(item.curBitsIndex, 24)  # NID_LRBG
        obj.d_lrbg = item.get_segment_by_index(item.curBitsIndex, 15)
        obj.q_dirlrbg = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.q_dlrbg = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.l_doubtover = item.get_segment_by_index(item.curBitsIndex, 15)
        obj.l_doubtunder = item.get_segment_by_index(item.curBitsIndex, 15)
        obj.q_length = item.get_segment_by_index(item.curBitsIndex, 2)
        
        # 列车完整性确认
        if obj.q_length == 1 or obj.q_length == 2:
            obj.l_traint = item.get_segment_by_index(item.curBitsIndex, 15)
            obj.v_train = item.get_segment_by_index(item.curBitsIndex, 7)
            obj.q_dirtrain = item.get_segment_by_index(item.curBitsIndex, 2)
            obj.m_mode = item.get_segment_by_index(item.curBitsIndex, 4)
            obj.m_level =  item.get_segment_by_index(item.curBitsIndex, 3)
            if obj.m_level == 1:
                obj.nid_stm = item.get_segment_by_index(item.curBitsIndex, 8)
        else:
            obj.v_train = item.get_segment_by_index(item.curBitsIndex, 7)
            obj.q_dirtrain = item.get_segment_by_index(item.curBitsIndex, 2)
            obj.m_mode = item.get_segment_by_index(item.curBitsIndex, 4)
            obj.m_level = item.get_segment_by_index(item.curBitsIndex, 3)
            if obj.m_level == 1:
                obj.nid_stm = item.get_segment_by_index(item.curBitsIndex, 8) 
        obj.updateflag = True
    
    @staticmethod
    def sp1Parse(item, obj=sp1):
        """
        except nid_xuser 8bit
        """
        obj.l_packet = item.get_segment_by_index(item.curBitsIndex, 13)
        obj.q_scale = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.nid_lrbg = item.get_segment_by_index(item.curBitsIndex, 24)  # NID_LRBG
        obj.nid_prvbg = item.get_segment_by_index(item.curBitsIndex, 24)  # NID_PRVBG
        obj.d_lrbg = item.get_segment_by_index(item.curBitsIndex, 15)
        obj.q_dirlrbg = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.q_dlrbg = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.l_doubtover = item.get_segment_by_index(item.curBitsIndex, 15)
        obj.l_doubtunder = item.get_segment_by_index(item.curBitsIndex, 15)
        obj.q_length = item.get_segment_by_index(item.curBitsIndex, 2)
        # 列车完整性确认
        if obj.q_length == 1 or obj.q_length == 2:
            obj.l_traint = item.get_segment_by_index(item.curBitsIndex, 15)
            obj.v_train = item.get_segment_by_index(item.curBitsIndex, 7)
            obj.q_dirtrain = item.get_segment_by_index(item.curBitsIndex, 2)
            obj.m_mode = item.get_segment_by_index(item.curBitsIndex, 4)
            obj.m_level = item.get_segment_by_index(item.curBitsIndex, 3)
            if obj.m_level == 1:
                obj.nid_stm = item.get_segment_by_index(item.curBitsIndex, 8)
        else:
            obj.v_train = item.get_segment_by_index(item.curBitsIndex, 7)
            obj.q_dirtrain = item.get_segment_by_index(item.curBitsIndex, 2)
            obj.m_mode = item.get_segment_by_index(item.curBitsIndex, 4)
            obj.m_level = item.get_segment_by_index(item.curBitsIndex, 3)
            if obj.m_level == 1:
                obj.nid_stm = item.get_segment_by_index(item.curBitsIndex, 8)
        obj.updateflag = True

    @staticmethod
    def sp2Parse(item, obj=sp2):
        """
        except nid_xuser 8bit
        """
        obj.q_atopermit = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.q_ato_hardpermit = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.q_leftdoorpermit = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.q_rightdoorpermit =  item.get_segment_by_index(item.curBitsIndex, 2)
        obj.q_door_cmd_dir =  item.get_segment_by_index(item.curBitsIndex, 2)
        obj.q_tb = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.v_target = item.get_segment_by_index(item.curBitsIndex, 16)
        obj.d_target = item.get_segment_by_index(item.curBitsIndex, 32)
        obj.m_level = item.get_segment_by_index(item.curBitsIndex, 3)  # M_LEVEL
        obj.m_mode = item.get_segment_by_index(item.curBitsIndex, 4)  # M_MODE
        obj.o_train_pos = item.get_segment_by_index(item.curBitsIndex, 32)
        obj.v_permitted = item.get_segment_by_index(item.curBitsIndex, 16)
        obj.d_ma = item.get_segment_by_index(item.curBitsIndex, 16)
        obj.m_ms_cmd = item.get_segment_by_index(item.curBitsIndex, 2)  # M_MS_CMD
        obj.d_neu_sec = item.get_segment_by_index(item.curBitsIndex, 16) # D_DEU_SEC
        obj.m_low_frequency = item.get_segment_by_index(item.curBitsIndex, 8)
        obj.q_stopstatus = item.get_segment_by_index(item.curBitsIndex, 4)
        obj.m_atp_stop_err = item.get_segment_by_index(item.curBitsIndex, 16)
        obj.d_station_mid_pos = item.get_segment_by_index(item.curBitsIndex, 32)
        obj.d_jz_sig_pos = item.get_segment_by_index(item.curBitsIndex, 32)
        obj.d_cz_sig_pos = item.get_segment_by_index(item.curBitsIndex, 32)
        obj.d_tsm = item.get_segment_by_index(item.curBitsIndex, 32)
        obj.m_cab_state = item.get_segment_by_index(item.curBitsIndex, 2) # M_CAB_STATE
        obj.m_position = item.get_segment_by_index(item.curBitsIndex, 32)
        obj.m_tco_state = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.reserve = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.updateflag = True

    @staticmethod
    def sp3Parse(item, obj=sp3):
        """
        except nid_xuser 8bit
        """
        obj.t_atp =item.get_segment_by_index(item.curBitsIndex, 32)
        obj.updateflag = True

    @staticmethod
    def sp4Parse(item, obj=sp4):
        """
        except nid_xuser 8bit
        """
        obj.v_normal = item.get_segment_by_index(item.curBitsIndex, 16, sign=1)
        obj.d_normal = item.get_segment_by_index(item.curBitsIndex, 32)
        obj.updateflag = True

    @staticmethod
    def sp5Parse(item, obj=sp5):
        """
        except nid_xuser 8bit
        """
        obj.n_units = item.get_segment_by_index(item.curBitsIndex, 8)
        obj.nid_operational = item.get_segment_by_index(item.curBitsIndex, 32)
        obj.nid_driver = item.get_segment_by_index(item.curBitsIndex, 32)
        obj.btm_antenna_position = item.get_segment_by_index(item.curBitsIndex, 8)
        obj.l_door_dis = item.get_segment_by_index(item.curBitsIndex, 16)
        obj.l_sdu_wheel_size_1 = item.get_segment_by_index(item.curBitsIndex, 16)
        obj.l_sdu_wheel_size_2 = item.get_segment_by_index(item.curBitsIndex, 16)
        obj.t_cutoff_traction = item.get_segment_by_index(item.curBitsIndex, 16)
        obj.nid_engine = item.get_segment_by_index(item.curBitsIndex, 24)
        obj.v_ato_permitted = item.get_segment_by_index(item.curBitsIndex, 4)
        obj.updateflag = True

    @staticmethod
    def sp6Parse(item, obj=sp6):
        """
        except nid_xuser 8bit
        """
        obj.t_year = item.get_segment_by_index(item.curBitsIndex, 8)
        obj.t_month = item.get_segment_by_index(item.curBitsIndex, 8)
        obj.t_day = item.get_segment_by_index(item.curBitsIndex, 8)
        obj.t_hour = item.get_segment_by_index(item.curBitsIndex, 8)
        obj.t_minutes = item.get_segment_by_index(item.curBitsIndex, 8)
        obj.t_seconds = item.get_segment_by_index(item.curBitsIndex, 8)
        obj.updateflag = True

    @staticmethod
    def sp7Parse(item, obj=sp7):
        """
        except nid_xuser 8bit
        """ 
        obj.nid_bg = item.get_segment_by_index(item.curBitsIndex, 24)
        obj.t_middle = item.get_segment_by_index(item.curBitsIndex, 32)
        obj.d_pos_adj = item.get_segment_by_index(item.curBitsIndex, 32, sign=1)
        obj.nid_xuser = item.get_segment_by_index(item.curBitsIndex, 9)
        # 解析到7包
        if  obj.nid_xuser == 13:
            obj.q_scale = item.get_segment_by_index(item.curBitsIndex, 2)
            obj.q_platform = item.get_segment_by_index(item.curBitsIndex, 2)
            obj.q_door = item.get_segment_by_index(item.curBitsIndex, 2)
            obj.n_d = item.get_segment_by_index(item.curBitsIndex, 24)
            obj.d_stop = item.get_segment_by_index(item.curBitsIndex, 15)
        obj.updateflag = True

    @staticmethod
    def sp8Parse(item, obj=sp8):
        """
        except nid_xuser 8bit
        """ 
        obj.q_tsrs = item.get_segment_by_index(item.curBitsIndex, 1)
        obj.nid_c = item.get_segment_by_index(item.curBitsIndex, 10)
        obj.nid_tsrs = item.get_segment_by_index(item.curBitsIndex, 14)
        obj.nid_radio_h = item.get_segment_by_index(item.curBitsIndex, 32)
        obj.nid_radio_l = item.get_segment_by_index(item.curBitsIndex, 32)
        obj.q_sleepssion = item.get_segment_by_index(item.curBitsIndex, 1)
        obj.m_type = item.get_segment_by_index(item.curBitsIndex, 3)  
        obj.updateflag = True

    @staticmethod
    def sp9Parse(item, obj=sp9):
        """
        except nid_xuser 8bit
        """
        obj.n_iter = item.get_segment_by_index(item.curBitsIndex, 5)
        obj.sp_track_list = list()
        for i in range(obj.n_iter):
            tmp = sp9_sp_track()
            tmp.d_trackcond =  item.get_segment_by_index(item.curBitsIndex, 32)
            tmp.l_trackcond = item.get_segment_by_index(item.curBitsIndex, 32)
            tmp.m_trackcond = item.get_segment_by_index(item.curBitsIndex, 4)
            obj.sp_track_list.append(tmp)
        obj.updateflag = True

    @staticmethod
    def sp130Parse(item, obj=sp130):
        """
        except nid_xuser 8bit
        """
        obj.m_atomode = item.get_segment_by_index(item.curBitsIndex, 4)
        obj.m_doormode = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.m_doorstatus = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.m_atoerror = item.get_segment_by_index(item.curBitsIndex, 16)
        obj.m_ato_stop_error = item.get_segment_by_index(item.curBitsIndex, 16)
        obj.updateflag = True
    
    @staticmethod
    def sp131Parse(item, obj=sp131):
        """
        except nid_xuser 8bit
        """
        obj.m_ato_tbs = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.m_ato_skip = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.m_ato_plan = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.m_ato_time = item.get_segment_by_index(item.curBitsIndex, 16)
        obj.m_tcms_com = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.m_gprs_radio = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.m_tsrs_session = item.get_segment_by_index(item.curBitsIndex, 2)
        obj.m_ato_control_strategy = item.get_segment_by_index(item.curBitsIndex, 4)
        obj.paddings = item.get_segment_by_index(item.curBitsIndex, 16)
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
        obj.nid_c = item.get_segment_by_index(item.curBitsIndex, 10)
        obj.nid_tsrs = item.get_segment_by_index(item.curBitsIndex, 14)
        obj.nid_tsrs_h = item.get_segment_by_index(item.curBitsIndex, 32)
        obj.nid_radio_l = item.get_segment_by_index(item.curBitsIndex, 32)
        obj.updateflag = True

    @staticmethod
    def sp134Parse(item, obj=sp134):
        """
        except nid_xuser 8bit
        """
        obj.nid_text = item.get_segment_by_index(item.curBitsIndex, 8)
        obj.q_display =  item.get_segment_by_index(item.curBitsIndex, 1)
        obj.l_text = item.get_segment_by_index(item.curBitsIndex, 8)
        obj.x_text = list()
        for i in range(obj.l_text):
            tmp = 0
            tmp = item.get_segment_by_index(item.curBitsIndex, 8)
            obj.x_text.append(tmp)
        obj.updateflag = True

    # 数据包解析
    def allPktsParse(self, item=BytesStream,l_msg=int):
        # 初始化bit数
        bit_idx = 0
        byte_idx = 0
        # 以下为lpacket描述范围
        nid_packet = item.get_segment_by_index(item.curBitsIndex, 8)
        l_packet = item.get_segment_by_index(item.curBitsIndex, 13)
        # 考虑消息头bit计数防护
        all_len = l_packet + 16 
        # 包内容解析
        while all_len != (item.curBitsIndex - bit_idx):
            nid_sub_packet = item.get_segment_by_index(item.curBitsIndex, 8)
            if nid_sub_packet in self.pktParseFnDic.keys():
                self.pktParseFnDic[nid_sub_packet](item)
            else:
                print('msg parse fatal err！no id！byte:%d,bit:%d'%(item.curBytesIndex,item.curBitsIndex))
            # 消息校验和监测
            if all_len == (item.curBitsIndex - bit_idx):
                if (all_len) % 8 == 0:    # 刚好除整数
                    pass
                else: # 重新校正bit索引
                    padding_bit = int(((all_len + 7) // 8) * 8) - all_len  # 字节下跳的bit数，减去消息头16bit和内容bit后
                    item.get_segment_by_index(item.curBitsIndex, padding_bit)
                # 计算分析消息结尾
                self.msg_obj.n_sequence = item.get_segment_by_index(item.curBitsIndex, 32)
                self.msg_obj.t_atp = item.get_segment_by_index(item.curBitsIndex, 32)
                crc_code = item.get_segment_by_index(item.curBitsIndex, 32)

                if l_msg == item.curBytesIndex - byte_idx + 1:
                    break  # 消息校验正确不打印
                else:
                    print('msg parse fatal err！ l_msg %d, real %d' % (l_msg, item.curBytesIndex - byte_idx + 2))

