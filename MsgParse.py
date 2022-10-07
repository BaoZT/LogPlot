#!/usr/bin/env python
# encoding: utf-8
'''
Author: Zhengtang Bao
Contact: baozhengtang@crscd.com.cn
File: MsgParse
Date: 2022-07-10 15:13:50
Desc: 本文件用于消息记录中的ATP-ATO,ATO-TSRS功能
LastEditors: Zhengtang Bao
LastEditTime: 2022-10-07 20:41:02
'''


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

Atp2atoFieldDic={
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
        'm_atomode':ProtoField("ATO模式",0,b_endian,4,None,{0:"ATO故障",1:"ATO待机",2:"ATO准备",3:"ATO投入",4:"ATO故障"}),
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
        'm_low_frequency':ProtoField("轨道电路低频信息",0,b_endian,8,None,{0x01:"无码",0x00:"H码",0x02:"HU码",0x10:"HB码",0x2A:"L4码",0x2B:"L5码",
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
        'nid_text':ProtoField("文本编号",0,b_endian,8,None,{0:"备用",1:"站台门联动失败",2:"动车组不允许控车",3:"停车不办客",4:"ATO起车异常",255:"纯文本"}),
        'nid_tsrs':ProtoField("TSRS编号",0,b_endian,14,None,None),
        'nid_c':ProtoField("地区编号",0,b_endian,10,None,None),
        'nid_xuser':ProtoField("子包标识",0,b_endian,8,None,{13:"有精确定位包",0:"无精确定位包"}),
        'n_g':ProtoField("列车停靠股道编号",0,b_endian,24,None,None),
        'n_iter':ProtoField("迭代字段",0,b_endian,5,None,None),
        'n_units':ProtoField("列车编组类型",0,b_endian,8,None,{1:"8编组",2:"16编组",3:"17编组", 4:"4编组"}),
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
        'm_tb_plan':ProtoField("折返计划可用状态", 0, b_endian, 8, None, {0x00:"折返无效", 0x5A:"换端计划", 0xA5:"折返计划"}),
        'q_tb_cabbtn':ProtoField('驾驶台换端按钮',0,b_endian,2, None, {0:"未按下", 1:"按下", 15:"状态异常"}),
        'q_tb_wsdbtn':ProtoField('轨旁换端按钮',0,b_endian,2, None, {0:"未按下", 1:"按下", 15:"状态异常"}),
        'q_startbtn':ProtoField('轨旁换端按钮',0,b_endian,2, None, {0:"未按下", 1:"按下", 15:"状态异常"}),
        'q_leading':ProtoField('首尾端状态',0,b_endian,4, None, {0:"非折返换端", 1:"首端", 2:"尾端"}),
        'm_tb_status':ProtoField('换端折返状态',0,b_endian,4, None, {0x00:"非自动折返状态", 0x01:"原地自动折返状态", 
        0x02:"满足原地自动折返条件", 0x03:"站后自动折返准备状态", 0x04:"站后自动折返折入状态", 0x05:"站后自动折返折出状态", 0x06:"无人自折条件具备",
        0x06:"满足站后自动折返条件", 0x07:"站后自动折返成功", 0x08:"原地自动折返成功",0x09:"站后自动折返失败",0x0a:"原地自动折返失败",
        0x0b:"站后自动换端成功", 0x0c:"站后自动换端失败", 0x0d:"原地自动折返准备状态"}),
        'q_tb_relay':ProtoField('折返继电器状态',0,b_endian,4, None, {0:"落下", 1:"吸起", 15:"状态异常"}),
        'reserved':ProtoField('预留字段',0,b_endian, 8, None, None)
}

Tsrs2atoFieldDic={
        'm_tbplan':ProtoField("折返计划",0,b_endian,2,None,{0:"计划无效", 1:"无人折返", 2:"自动换端"}),
        'm_task':ProtoField("是否办客",0,b_endian,8,None,{1:"办客", 2:"不办客"}),
        'm_tbstatus':ProtoField("当前换端折返状态",0,b_endian,8,None,{0x00:"非自动折返状态",0x01:"原地自动折返状态",
        0x03:"站后自动折返准备状态",0x04:"站后自动折返状态", 0x07:"站后自动折返成功", 0x08:"原地自动折返成功",
        0x09:"站后自动折返失败", 0x0A:"原地自动折返失败", 0x0B:"站后自动换端成功", 0x0C:"站后自动换端失败",
        0x0D:"原地自动折返准备状态"})
}

TrainCircuitDic={"L码":"前方有3个及以上闭塞分区空闲",
"LU码":"注意运行,距离目标距离2个闭塞分区",
"U码":"减速运行,距离目标距离1分闭塞分区",
"U2S码":"减速运行,预告UUS码",
"U2码":"减速运行,预告UU码",
"UUS码":"限速运行,道岔开通侧向,默认道岔速度80km/h",
"UU码":"限速运行,道岔开通侧向,默认道岔速度45km/h",
"HB码":"进站或接车进路开放引导信号或收到容许信号",
"HU码":"前方停车目标,及时采取停车措施",
"L5码":"前方有7个及以上闭塞分区空闲",
"L4码":"前方有6个及以上闭塞分区空闲",
"L3码":"前方有5个及以上闭塞分区空闲",
"L2码":"前方有4个及以上闭塞分区空闲",
"LU2码":"要求列车减速到规定的速度等级越过接近的地面信号机,预告U码",
"H码":"要求立即采取紧急制动措施"
}

class P0(object):
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

class P1(object):
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

class SP2(object):
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
        self.m_atp_stop_error  = 32768
        self.d_station_mid_pos = 0
        self.d_jz_sig_pos      = 0
        self.d_cz_sig_pos      = 0
        self.d_tsm             = 0
        self.m_cab_state       = 0
        self.m_position        = 0
        self.m_tco_state       = 0
        self.reserve           = 0

class SP3(object):
    __slots__ = ["updateflag","nid_sub_packet","t_atp"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 3
        self.t_atp             = 0

class SP4(object):
    __slots__ = ["updateflag","nid_sub_packet","v_normal","d_normal"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 4
        self.v_normal          = 0
        self.d_normal          = 0

class SP5(object):
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

class SP6(object):
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

class SP7(object):
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

class SP8(object):
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

class SP9Track(object):
    __slots__ = ["d_trackcond","l_trackcond","m_trackcond"]
    def __init__(self) -> None:
        self.d_trackcond = 0xffffffff
        self.l_trackcond = 0xffffffff
        self.m_trackcond = 0

class SP9(object):
    __slots__ = ["updateflag","nid_sub_packet","n_iter","sp_track_list"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 9
        self.n_iter            = 0
        self.sp_track_list     = None

class SP13(object):
    __slots__ = ["updateflag", "nid_sub_packet","q_leading", "m_tb_status", "q_tb_relay", "reserved"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 13
        self.q_leading         = 0
        self.m_tb_status       = 0
        self.q_tb_relay        = 0
        self.reserved          = 0

class SP130(object):
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

class SP131(object):
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

class SP132(object):
    __slots__ = ["updateflag","nid_sub_packet"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 132

class SP133(object):
    __slots__ = ["updateflag","nid_sub_packet","nid_c","nid_tsrs","nid_radio_h","nid_radio_l"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 133
        self.nid_c             = 0
        self.nid_tsrs          = 0
        self.nid_radio_h       = 0
        self.nid_radio_l       = 0

class SP134(object):
    __slots__ = ["updateflag","nid_sub_packet","nid_text","q_display","l_text","x_text"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 134
        self.nid_text          = 0
        self.q_display         = 0
        self.l_text            = 0
        self.x_text            = None

class SP138(object):
    __slots__ = ["updateflag", "nid_sub_packet","m_tb_plan", "q_tb_cabbtn", "q_tb_wsdbtn",
     "q_startbtn","reserved","nid_operational"]
    def __init__(self) -> None:
        self.updateflag        = False
        self.nid_sub_packet    = 138
        self.m_tb_plan         = 0
        self.q_tb_cabbtn       = 0
        self.q_tb_wsdbtn       = 0
        self.q_startbtn        = 0
        self.reserved          = 0
        self.nid_operational   = 0

class Atp2atoProto(object):
    __slots__ = ["nid_packet","t_msg_atp","crc_code","n_sequence","l_msg","sp0_obj","sp1_obj","sp2_obj","sp3_obj",
    "sp4_obj","sp5_obj","sp6_obj","sp7_obj","sp8_obj","sp9_obj","sp13_obj","sp130_obj","sp131_obj",
    "sp132_obj","sp133_obj","sp134_obj","sp138_obj","l_packet","nid_msg"]

    def __init__(self) -> None:
        self.nid_packet = 0     # packet id
        self.l_packet   = 0
        self.t_msg_atp  = 0     # atp timestamp
        self.crc_code   = 0     # crc
        self.n_sequence = 0     # msg seq
        self.l_msg      = 0     # msg length
        self.nid_msg    = 0
        self.sp0_obj   = P0()
        self.sp1_obj   = P1()
        self.sp2_obj   = SP2()
        self.sp3_obj   = SP3()
        self.sp4_obj   = SP4()
        self.sp5_obj   = SP5()
        self.sp6_obj   = SP6()
        self.sp7_obj   = SP7()
        self.sp8_obj   = SP8()
        self.sp9_obj   = SP9()
        self.sp13_obj  = SP13()
        self.sp130_obj = SP130()
        self.sp131_obj = SP131()
        self.sp132_obj = SP132()
        self.sp133_obj = SP133()
        self.sp134_obj = SP134()
        self.sp138_obj = SP138()

class Atp2atoParse(object):
    __slots__ = ["msg_obj", "rawBytes" ,"pktParseFnDic","objParseDic"]
    
    def __init__(self) -> None:
        self.msg_obj = Atp2atoProto()
        self.rawBytes = bytes()
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
        13:Atp2atoParse.sp13Parse,
        130:Atp2atoParse.sp130Parse,
        131:Atp2atoParse.sp131Parse,
        132:Atp2atoParse.sp132Parse,
        133:Atp2atoParse.sp133Parse,
        134:Atp2atoParse.sp134Parse,
        138:Atp2atoParse.sp138Parse,
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
        13:self.msg_obj.sp13_obj,
        130:self.msg_obj.sp130_obj,
        131:self.msg_obj.sp131_obj,
        132:self.msg_obj.sp132_obj,
        133:self.msg_obj.sp133_obj,
        134:self.msg_obj.sp134_obj,
        138:self.msg_obj.sp138_obj,
        }

    def resetMsg(self):
        self.msg_obj.nid_msg = 0
        self.msg_obj.sp0_obj.updateflag = False
        self.msg_obj.sp1_obj.updateflag = False
        self.msg_obj.sp2_obj.updateflag = False
        self.msg_obj.sp3_obj.updateflag = False
        self.msg_obj.sp4_obj.updateflag = False
        self.msg_obj.sp5_obj.updateflag = False
        self.msg_obj.sp6_obj.updateflag = False
        self.msg_obj.sp7_obj.updateflag = False
        self.msg_obj.sp8_obj.updateflag = False
        self.msg_obj.sp9_obj.updateflag = False
        self.msg_obj.sp13_obj.updateflag = False
        self.msg_obj.sp130_obj.updateflag = False
        self.msg_obj.sp131_obj.updateflag = False
        self.msg_obj.sp132_obj.updateflag = False
        self.msg_obj.sp133_obj.updateflag = False
        self.msg_obj.sp134_obj.updateflag = False
        self.msg_obj.sp138_obj.updateflag = False

    # 消息完整解析
    def msgParse(self, line=str):
        # 去除换行回车
        line = line.strip()
        # 防护性编程外界保证数据仅可能有空格
        line = ''.join(line.split(' '))
        item = None
        self.rawBytes = bytes()
        # 校验字节数
        if (len(line)%2 == 0) and (len(line)/2>=23):
            try:
                int(line, 16) # 校验防护
                item = BytesStream(line)
            except Exception as err:
                print("Bytes string err!"+line)
        else:
            pass
        # 尝试解析消息 
        if item:
            self.rawBytes = item.get_stream_in_bytes()
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
    def sp0Parse(item, obj=P0):
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
    def sp1Parse(item, obj=P1):
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
    def sp2Parse(item, obj=SP2):
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
    def sp3Parse(item, obj=SP3):
        """
        except nid_xuser 8bit
        """
        obj.t_atp =item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.updateflag = True

    @staticmethod
    def sp4Parse(item, obj=SP4):
        """
        except nid_xuser 8bit
        """
        obj.v_normal = item.fast_get_segment_by_index(item.curBitsIndex, 16, sign=1)
        obj.d_normal = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.updateflag = True

    @staticmethod
    def sp5Parse(item, obj=SP5):
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
    def sp6Parse(item, obj=SP6):
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
    def sp7Parse(item, obj=SP7):
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
    def sp8Parse(item, obj=SP8):
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
    def sp9Parse(item, obj=SP9):
        """
        except nid_xuser 8bit
        """
        obj.n_iter = item.fast_get_segment_by_index(item.curBitsIndex, 5)
        obj.sp_track_list = list()
        for i in range(obj.n_iter):
            tmp = SP9Track()
            tmp.d_trackcond =  item.fast_get_segment_by_index(item.curBitsIndex, 32)
            tmp.l_trackcond = item.fast_get_segment_by_index(item.curBitsIndex, 32)
            tmp.m_trackcond = item.fast_get_segment_by_index(item.curBitsIndex, 4)
            obj.sp_track_list.append(tmp)
        obj.updateflag = True

    @staticmethod
    def sp13Parse(item, obj=SP13):
        """
        sy ato specific packet
        """
        obj.q_leading = item.fast_get_segment_by_index(item.curBitsIndex, 4)
        obj.m_tb_status = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.q_tb_relay = item.fast_get_segment_by_index(item.curBitsIndex, 4)
        obj.reserved = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.updateflag = True

    @staticmethod
    def sp130Parse(item, obj=SP130):
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
    def sp131Parse(item, obj=SP131):
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
    def sp132Parse(item, obj=SP132):
        """
        except nid_xuser 8bit, no content
        """
        obj.updateflag = True
    
    @staticmethod
    def sp133Parse(item, obj=SP133):
        """
        except nid_xuser 8bi
        """
        obj.nid_c = item.fast_get_segment_by_index(item.curBitsIndex, 10)
        obj.nid_tsrs = item.fast_get_segment_by_index(item.curBitsIndex, 14)
        obj.nid_radio_h = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.nid_radio_l = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.updateflag = True

    @staticmethod
    def sp134Parse(item, obj=SP134):
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
    def sp138Parse(item, obj=SP138):
        """
        sy ato specific packet
        """
        obj.m_tb_plan = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.q_tb_cabbtn = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.q_tb_wsdbtn = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.q_startbtn  = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.reserved   = item.fast_get_segment_by_index(item.curBitsIndex, 2)
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
                break            
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


class Ato2tsrsProto(object):
    __slots__ = ["msgHeader", "t_train_ack", "p0", "p1", "p4", "p11","c44", "c45", "c46", "c48", "c50"]
    def __init__(self) -> None:
        """
        车到地消息M129/M136/M146/M150/M154/M155/M156/M157/M159
        """
        self.msgHeader = A2tMsgHeader()
        # M146使用确认的时间戳
        self.t_train_ack = None
        # M136/157位置报告
        self.p0  = None
        self.p1  = None
        # M136/M157错误报告
        self.p4  = None
        # M129列车数据
        self.p11 = None
        # M136携带用户数据包
        self.c44 = None
        self.c45 = None
        self.c46 = None
        self.c48 = None
        self.c50 = None

class A2tMsgHeader(object):
    __slots__ = ['nid_message', 'l_message', 't_train', 'nid_engine']
    def __init__(self) -> None:
        self.nid_message    = 0     # msg id
        self.l_message      = 0     # msg length
        self.t_train        = 0     # train stamp
        self.nid_engine     = 0     # ob ctcs id

class P4(object):
    """
    6.5.3	信息包4:错误报告
    """
    __slots__ = ["updateflag","nid_packet","l_packet","m_error"]
    def __init__(self) -> None:
        self.updateflag = False
        self.nid_packet = 4
        self.l_packet   = 0
        self.m_error    = 0

class P11(object):
    """
    6.5.4	信息包11:列车数据
    """
    __slots__ = ["updateflag", "nid_packet", "l_packet","nid_operational","nc_train","l_train","v_maxtrain",
    "m_loadinggauge","m_axleload","m_airtight","n_iter","n_iter_stm","nid_stm0"]
    def __init__(self) -> None:
        self.updateflag = False
        self.nid_packet = 11
        self.l_packet   = 122
        self.nid_operational = 0
        self.nc_train   = 0
        self.l_train    = 0
        self.v_maxtrain = 0
        self.m_loadinggauge = 0
        self.m_axleload = 0
        self.m_airtight = 0
        self.n_iter     = 0
        self.n_iter_stm = 0
        self.nid_stm0   = 0

class P44A2tHeader(object):
    """
    6.5.5	信息包44:用户数据包
    """
    __slots__ = ["updateflag", "nid_packet", "l_packet"]
    def __init__(self) -> None:
        self.nid_packet = 44
        self.l_packet   = 0

class C44(object):
    """
    6.5.6	信息包CTCS-44:开关门命令
    """
    __slots__ = ["updateflag", "p44_header","nid_xuser", "l_packet", "m_sequencenum","m_traintype",
    "nid_track","q_dir","q_tb","m_ldoorcmd","m_rdoorcmd"]
    def __init__(self) -> None:
        self.updateflag = False
        self.p44_header = P44A2tHeader()
        self.nid_xuser  = 44
        self.l_packet   = 0
        self.m_sequencenum = 0
        self.m_traintype= 0
        self.nid_track  = 0
        self.q_dir      = 0
        self.q_tb       = 0
        self.m_ldoorcmd = 0
        self.m_rdoorcmd = 0

class C45(object):
    """
    6.5.7	信息包CTCS-45:ATO运行计划报告
    """
    __slots__ = ["updateflag","p44_header","nid_xuser", "l_packet", "nid_depaturetrack","m_departtime",
    "nid_arrivaltrack","m_arrivaltime","m_task","m_skip"]    
    def __init__(self) -> None:
        self.updateflag = False
        self.p44_header = P44A2tHeader()
        self.nid_xuser  = 45
        self.l_packet   = 0
        self.nid_depaturetrack = 0
        self.m_departtime = 0
        self.nid_arrivaltrack = 0
        self.m_arrivaltime= 0
        self.m_task = 0
        self.m_skip = 0

class C46(object):
    """
    6.5.8	信息包CTCS-46:车载状态
    """
    __slots__ = ["updateflag","p44_header","nid_xuser", "l_packet", "nid_engine","nid_operational",
    "nid_driver", "m_level", "m_mode", "q_stopstatus", "m_ato_mode", "m_ato_control_strategy"]
    def __init__(self) -> None:
        self.updateflag = False
        self.p44_header = P44A2tHeader()
        self.nid_xuser = 46
        self.l_packet  = 0
        self.nid_engine= 0
        self.nid_operational = 0
        self.nid_driver= 0
        self.m_level   = 0
        self.m_mode    = 0
        self.q_stopstatus = 0
        self.m_ato_mode= 0
        self.m_ato_control_strategy = 0

class C48(object):
    """
    6.5.9	信息包CTCS-48:ATO折返状态反馈
    """
    __slots__ = ["updateflag","nid_xuser","p44_header","l_packet", "m_tbplan", "nid_tbdeparttrack",
    "nid_operational","nid_tbarrivaltrack","m_task","m_tbstatus"]
    def __init__(self) -> None:
        self.updateflag = False
        self.p44_header = P44A2tHeader()
        self.nid_xuser = 48
        self.l_packet  = 0
        self.m_tbplan  = 0
        self.nid_tbdeparttrack = 0
        self.nid_operational = 0
        self.nid_tbarrivaltrack = 0
        self.m_task = 0
        self.m_tbstatus= 0

class C50(object):
    """
    6.5.10	信息包CTCS-50:轨旁无人折返按钮指示灯控制命令
    """
    __slots__ = ["updateflag","nid_xuser","p44_header","l_packet", "m_tblamp", "nid_track"]
    def __init__(self) -> None:
        self.updateflag = False
        self.p44_header = P44A2tHeader()
        self.nid_xuser = 0
        self.l_packet  = 0
        self.m_tblamp  = 0
        self.nid_track = 0

class Tsrs2atoProto(object):
    __slots__ = ["msgHeader", "t_train_ack", "version", "p3", "p21", "p27","p58","p72", "c2", "c12", "c41",
    "c43", "c42", "c47","c49"]
    def __init__(self) -> None:
        self.msgHeader = T2aMsgHeader()
        # M8使用确认的时间戳
        self.t_train_ack = None
        # M32使用的系统版本
        self.version     = None
        # M24携带子包P3/P21/P27/P58
        self.p3  = None
        self.p21 = None
        self.p27 = None
        self.p58 = None
        self.p72 = None
        # M24携带的用户数据包
        self.c2  = None
        self.c12 = None
        self.c41 = None
        self.c42 = None
        self.c43 = None
        self.c47 = None
        self.c49 = None

class T2aMsgHeader(object):
    __slots__=["nid_message", "l_message", "t_train", "m_ack", "nid_lrbg"]
    def __init__(self) -> None:
        self.nid_message = 0
        self.l_message   = 0
        self.t_train     = 0
        self.m_ack       = 0
        self.nid_lrbg    = 0

class P3(object):
    """
    6.7.1	信息包3:配置参数
    """
    def __init__(self) -> None:
        self.nid_packet = 0
        self.q_dir      = 0
        self.l_packet   = 0
        self.q_scale    = 0
        self.d_validnv  = 0
        self.n_iter     = 0
        self.nid_c      = list()
        self.v_nvshunt  = 0
        self.v_nvstff   = 0
        self.v_nvonsight= 0
        self.v_nvunfit  = 0
        self.v_nvrel    = 0
        self.d_nvroll   = 0
        self.q_nvsrbktrg= 0
        self.q_nvemrrls = 0
        self.v_nvallowovtrp=0
        self.v_nvsupovtrp=0
        self.d_nvovtrp  = 0
        self.t_nvovtrp  = 0
        self.d_nvpotrp  = 0
        self.m_nvcontact= 0
        self.t_nvcontact= 0
        self.m_nvderun  = 0
        self.d_nvstff   = 0
        self.q_nvdriver_adhes=0

class P21(object):
    """
    6.7.2	信息包21:坡度曲线
    """
    def __init__(self) -> None:
        self.nid_packet = 0
        self.q_dir      = 0
        self.l_packet   = 0
        self.q_scale    = 0
        self.d_gradient = 0
        self.q_gdir     = 0
        self.g_a        = 0
        self.n_iter     = 0
        self.d_gradient_list = list()
        self.q_gdir_list     = list()
        self.g_a_list        = list()

class P27(object):
    """
    6.7.3	信息包27:静态速度曲线
    """
    def __init__(self) -> None:
        self.nid_packet = 0
        self.q_dir      = 0
        self.l_packet   = 0
        self.q_scale    = 0
        self.d_static   = 0
        self.v_static   = 0
        self.q_front    = 0
        self.n_iter_train = 0 # 列车种类
        self.n_iter_static= 0 # 静态限速种类  
        self.d_static_list   = list()
        self.v_static_list   = list()
        self.q_front_list    = list()
        self.n_iter_sub_train = 0 #子列车种类

class P58(object):
    """
    6.7.4	信息包58:位置报告参数
    """
    def __init__(self) -> None:
        self.nid_packet = 0
        self.q_dir      = 0
        self.l_packet   = 0
        self.q_scale    = 0
        self.t_cycloc   = 0
        self.d_cycloc   = 0
        self.m_loc      = 0
        self.n_iter     = 0

class P72(object):
    def __init__(self) -> None:
        self.nid_packet = 0
        self.q_dir      = 0
        self.l_packet   = 0
        self.q_scale    = 0
        self.q_textclass= 0
        self.q_textdisplay = 0
        self.d_textdisplay = 0
        self.m_modetextdisplay_begin = 0
        self.m_leveltextdisplay_begin = 0
        self.nid_stm_begin = 0
        self.l_textdisplay = 0
        self.t_textdisplay = 0
        self.m_modetextdisplay_end = 0
        self.m_leveltextdisplay_end = 0
        self.nid_stm_end = 0
        self.q_textconfirm = 0
        self.l_text = 0
        self.x_text = list()

class P44T2aHeader(object):
    """
    6.5.5	信息包44:用户数据包
    """
    __slots__ = ["updateflag", "nid_packet", "q_dir", "l_packet"]
    def __init__(self) -> None:
        self.nid_packet = 44
        self.q_dir      = 0
        self.l_packet   = 0

class C2(object):
    def __init__(self) -> None:
        self.updateflag = False
        self.p44_header = P44T2aHeader()
        self.nid_xuser  = 0
        self.q_dir      = 0
        self.l_packet   = 0
        self.q_scale    = 0
        self.l_tsrarea  = 0
        self.d_tsr      = 0
        self.l_tsr      = 0
        self.q_front    = 0
        self.v_tsr      = 0
        self.n_iter     = 0
        self.d_tsr_list = list()
        self.l_tsr_list = list()
        self.q_front_list=list()
        self.v_tsr_list  =list()

class C12(object):
    __slots__=["updateflag", "p44_header", "nid_xuser", "q_dir", "l_packet", "q_tsrs", "nid_c",
    "nid_tsrs", "nid_radio_h", "nid_radio_l","q_sleepsession"]
    def __init__(self) -> None:
        self.updateflag = False
        self.p44_header = P44T2aHeader()
        self.nid_xuser  = 0
        self.q_dir      = 0
        self.l_packet   = 0
        self.q_tsrs     = 0
        self.nid_c      = 0
        self.nid_tsrs   = 0
        self.nid_radio_h  = 0
        self.nid_radio_l  = 0
        self.q_sleepsession = 0

class C41(object):
    def __init__(self) -> None:
        self.updateflag = False
        self.p44_header = P44T2aHeader()
        self.nid_xuser  = 0
        self.q_dir      = 0
        self.l_packet   = 0
        self.m_waysidetime = 0
        self.nid_departtrack=0
        self.m_departtime   =0
        self.nid_arrivaltrack=0
        self.m_arrivaltime  =0
        self.m_task     = 0
        self.m_skip     = 0
        self.n_iter     = 0
        self.nid_departtrack_2=0
        self.m_departtime_2   =0
        self.nid_arrivaltrack_2=0
        self.m_arrivaltime_2  =0
        self.m_task_2     = 0
        self.m_skip_2     = 0

class C42(object):
    def __init__(self) -> None:
        self.updateflag = False
        self.p44_header = P44T2aHeader()
        self.nid_xuser  = 0
        self.q_dir      = 0
        self.l_packet   = 0
        self.q_scale    = 0
        self.l_stationdistance = 0

class C43(object):
    def __init__(self) -> None:
        self.updateflag = False
        self.p44_header = P44T2aHeader()
        self.nid_xuser  = 0
        self.q_dir      = 0
        self.l_packet   = 0
        self.m_sequencenum = 0
        self.m_lpsdstatus = 0
        self.m_rpsdstatus = 0

class C47(object):
    __slots__=["updateflag", "p44_header", "nid_xuser", "q_dir", "l_packet", "m_tbplan", "nid_tbdeparttrack",
    "nid_operational", "nid_tbarrivaltrack","m_task"]
    def __init__(self) -> None:
        self.updateflag = False
        self.p44_header = P44T2aHeader()
        self.nid_xuser  = 0
        self.q_dir      = 0
        self.l_packet   = 0
        self.m_tbplan   = 0
        self.nid_tbdeparttrack = 0
        self.nid_operational = 0
        self.nid_tbarrivaltrack = 0
        self.m_task = 0

class C49(object):
    def __init__(self) -> None:
        self.updateflag = False
        self.p44_header = P44T2aHeader()
        self.nid_xuser  = 0
        self.q_dir      = 0
        self.l_packet   = 0
        self.m_tbbtnstatus = 0


class Tsrs2atoParse(object):
    
    def __init__(self) -> None:
        self.msg_obj = Tsrs2atoProto()
        self.rawBytes = bytes()

    def resetMsg(self):
        self.msg_obj = Tsrs2atoProto()
        self.rawBytes = bytes()

    def msgParse(self, line=str):
        # 去除换行回车
        line = line.strip()
        # 防护性编程外界保证数据仅可能有空格
        line = ''.join(line.split(' '))
        item = None
        self.rawBytes = bytes()
        # 校验字节数至少9字节包含空M24
        if (len(line)%2 == 0) and (len(line)/2>=9):
            try:
                int(line, 16) # 校验防护
                item = BytesStream(line)
            except Exception as err:
                print("Bytes string err!"+line)
        else:
            pass
        # 尝试解析消息 
        if item:
            self.rawBytes = item.get_stream_in_bytes()
            self.msg_obj.msgHeader.nid_message = item.fast_get_segment_by_index(item.curBitsIndex, 8)
            self.msg_obj.msgHeader.l_message = item.fast_get_segment_by_index(item.curBitsIndex, 10)
            # 校验消息
            if self.msg_obj.msgHeader.l_message <= (len(line)/2): 
                self.allPktsParse(item, self.msg_obj.msgHeader.nid_message, self.msg_obj.msgHeader.l_message)
            else:
                print("err Tsrs2ato msg:"+line)
        else:
            pass
        return self.msg_obj

    # 数据包解析
    def allPktsParse(self, item=BytesStream,nid_msg=int, l_msg=int):
        # 继续解析消息头
        self.msg_obj.msgHeader.t_train = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        self.msg_obj.msgHeader.m_ack = item.fast_get_segment_by_index(item.curBitsIndex, 1)
        self.msg_obj.msgHeader.nid_lrbg = item.fast_get_segment_by_index(item.curBitsIndex, 24)
        # 解析消息内容
        if nid_msg == 8:
            self.msg_obj.t_train_ack = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        elif nid_msg == 24:
            self.msg24PktsParse(item, self.msg_obj.msgHeader.l_message)
        elif nid_msg == 32:
            self.msg_obj.version = item.fast_get_segment_by_index(item.curBitsIndex, 7)
        elif nid_msg == 39:
            pass
        elif nid_msg == 41:
            pass

    # M24子包解析函数
    def msg24PktsParse(self, item=BytesStream, l_msg=int):
        # 当剩余bit还够一个包头时
        while item.curBitsIndex < (l_msg*8 - 23):
            nid_packet = item.fast_get_segment_by_index(item.curBitsIndex, 8)
            if nid_packet == 3:
                self.msg_obj.p3 = P3()
                Tsrs2atoParse.packetJump(item)
            elif nid_packet == 21:
                self.msg_obj.p21 = P21()
                Tsrs2atoParse.packetJump(item)
            elif nid_packet == 27:
                self.msg_obj.p27 = P27()
                Tsrs2atoParse.packetJump(item)            
            elif nid_packet == 58:
                self.msg_obj.p58 = P58()
                Tsrs2atoParse.packetJump(item) 
            elif nid_packet == 72:
                self.msg_obj.p72 = P72()
                Tsrs2atoParse.packetJump(item) 
            elif nid_packet == 44:
                objP44Header = P44T2aHeader()
                Tsrs2atoParse.p44T2aHeaderParse(item, objP44Header)
                nid_xuser = item.get_segment_by_index(item.curBitsIndex, 9)
                # 根据ID选择子包
                if nid_xuser == 2:
                    Tsrs2atoParse.ctcsPacketJump(item)
                elif nid_xuser == 12:
                    self.msg_obj.c12 = C12()
                    Tsrs2atoParse.c12Parse(item, self.msg_obj.c12,objP44Header)
                elif nid_xuser == 41:
                    self.msg_obj.c41 = C41()
                    Tsrs2atoParse.ctcsPacketJump(item)
                elif nid_xuser == 42:
                    self.msg_obj.c42 = C42()
                    Tsrs2atoParse.ctcsPacketJump(item)
                elif nid_xuser == 43:
                    self.msg_obj.c43 = C43()
                    Tsrs2atoParse.ctcsPacketJump(item)
                elif nid_xuser == 47:
                    self.msg_obj.c47 = C47()
                    Tsrs2atoParse.c47Parse(item, self.msg_obj.c47 ,objP44Header)
                elif nid_xuser == 49:
                    self.msg_obj.c49 = C49()
                    Tsrs2atoParse.ctcsPacketJump(item)                                               
            else:
                pass

    @staticmethod
    def packetJump(item=BytesStream):
        """
        跳包只修改了比特会导致与换算的字节不一致,当不使用字节时无影响
        """
        q_dir = item.get_segment_by_index(item.curBitsIndex, 2)
        l_packet = item.get_segment_by_index(item.curBitsIndex, 13)
        item.curBitsIndex = item.curBitsIndex + l_packet - 8 - 2- 13

    @staticmethod
    def ctcsPacketJump(item=BytesStream):
        """
        跳包只修改了比特会导致与换算的字节不一致,当不使用字节时无影响
        """
        l_packet = item.get_segment_by_index(item.curBitsIndex, 13)
        item.curBitsIndex = item.curBitsIndex + l_packet -9 -13

    @staticmethod
    def p44T2aHeaderParse(item=BytesStream, obj=P44T2aHeader):
        """
        except nid_packet 8bit
        """
        obj.q_dir      = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.l_packet   = item.fast_get_segment_by_index(item.curBitsIndex, 13)
        return obj
    
    @staticmethod
    def c47Parse(item, obj=C47, p44Header=P44T2aHeader):
        """
        except nid_xuser 9bit
        """
        obj.p44_header.l_packet = p44Header.l_packet
        obj.p44_header.q_dir    = p44Header.q_dir
        # 子包 9bit nid_xuser已经解析
        obj.q_dir = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.l_packet = item.fast_get_segment_by_index(item.curBitsIndex, 13)
        obj.m_tbplan = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.nid_tbdeparttrack = item.fast_get_segment_by_index(item.curBitsIndex, 24)
        obj.nid_operational = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.nid_tbarrivaltrack = item.fast_get_segment_by_index(item.curBitsIndex, 24)
        obj.m_task = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.updateflag = True

    @staticmethod
    def c12Parse(item, obj=C12, p44Header=P44T2aHeader):
        """
        except nid_xuser 9bit
        """
        obj.p44_header.l_packet = p44Header.l_packet
        obj.p44_header.q_dir    = p44Header.q_dir
        # 子包 9bit nid_xuser已经解析
        obj.q_dir = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.l_packet = item.fast_get_segment_by_index(item.curBitsIndex, 13)
        obj.q_tsrs = item.fast_get_segment_by_index(item.curBitsIndex, 1)
        obj.nid_c = item.fast_get_segment_by_index(item.curBitsIndex, 10)
        obj.nid_tsrs = item.fast_get_segment_by_index(item.curBitsIndex, 14)
        obj.nid_radio_h = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.nid_radio_l = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.q_sleepsession = item.fast_get_segment_by_index(item.curBitsIndex, 1)
        obj.updateflag = True


class Ato2tsrsParse(object):
    
    def __init__(self) -> None:
        self.msg_obj = Ato2tsrsProto()
        self.rawBytes = bytes()

    def resetMsg(self):
        self.msg_obj = Ato2tsrsProto()
        self.rawBytes = bytes()

    def msgParse(self, line=str):
        # 去除换行回车
        line = line.strip()
        # 防护性编程外界保证数据仅可能有空格
        line = ''.join(line.split(' '))
        item = None
        self.rawBytes = bytes()
        # 校验字节数至少9字节
        if (len(line)%2 == 0) and (len(line)/2>=9):
            try:
                int(line, 16) # 校验防护
                item = BytesStream(line)
            except Exception as err:
                print("Bytes string err!"+line)
        else:
            pass
        # 尝试解析消息 
        if item:
            self.rawBytes = item.get_stream_in_bytes()
            self.msg_obj.msgHeader.nid_message = item.fast_get_segment_by_index(item.curBitsIndex, 8)
            self.msg_obj.msgHeader.l_message = item.fast_get_segment_by_index(item.curBitsIndex, 10)
            # 校验消息
            if self.msg_obj.msgHeader.l_message <= (len(line)/2): 
                self.allPktsParse(item,self.msg_obj.msgHeader.nid_message,self.msg_obj.msgHeader.l_message)
            else:
                print("err Ato2tsrs msg:"+line)
        else:
            pass
        return self.msg_obj

    # 数据包解析
    def allPktsParse(self,item=BytesStream,nid_msg=int, l_msg=int):
        # 继续解析消息头
        self.msg_obj.msgHeader.t_train = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        self.msg_obj.msgHeader.nid_engine = item.fast_get_segment_by_index(item.curBitsIndex, 24)
        # 解析消息内容
        if nid_msg == 129:
            self.msg129PktsParse(item, self.msg_obj.msgHeader.l_message)
        elif nid_msg == 136:
            self.msg136PktsParse(item, self.msg_obj.msgHeader.l_message)
        elif nid_msg == 146:
            self.msg_obj.t_train_ack = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        elif nid_msg == 150:
            self.msg150PktsParse(item, self.msg_obj.msgHeader.l_message)
        elif nid_msg == 154:
            pass
        elif nid_msg == 155:
            pass
        elif nid_msg == 156:
            pass
        elif nid_msg == 157:
            self.msg157PktsParse(item, self.msg_obj.msgHeader.l_message)
        elif nid_msg == 159:
            pass

    # M129消息子包解析函数
    def msg129PktsParse(self, item=BytesStream, l_msg=int):
        # 当剩余bit还够一个包头时
        while item.curBitsIndex < (l_msg*8 - 21):
            nid_packet = item.fast_get_segment_by_index(item.curBitsIndex, 8)
            if nid_packet == 0:
                self.msg_obj.p0 = P0()
                Atp2atoParse.sp0Parse(item,self.msg_obj.p0)
            elif nid_packet == 1:
                self.msg_obj.p1 = P1()
                Atp2atoParse.sp1Parse(item,self.msg_obj.p1)
            elif nid_packet == 11:
                self.msg_obj.p11 = P11()
                Ato2tsrsParse.p11Parse(item, self.msg_obj.p11)
            else:
                pass

    # M150消息子包解析函数
    def msg150PktsParse(self, item=BytesStream, l_msg=int):
        # 当剩余bit还够一个包头时
        while item.curBitsIndex < (l_msg*8 - 21):
            nid_packet = item.fast_get_segment_by_index(item.curBitsIndex, 8)
            if nid_packet == 0:
                self.msg_obj.p0 = P0()
                Atp2atoParse.sp0Parse(item,self.msg_obj.p0)
            elif nid_packet == 1:
                self.msg_obj.p1 = P1()
                Atp2atoParse.sp1Parse(item,self.msg_obj.p1)
            else:
                pass

    # M157消息子包解析函数
    def msg157PktsParse(self, item=BytesStream, l_msg=int):
        # 当剩余bit还够一个包头时
        while item.curBitsIndex < (l_msg*8 - 21):
            nid_packet = item.fast_get_segment_by_index(item.curBitsIndex, 8)
            if nid_packet == 0:
                self.msg_obj.p0 = P0()
                Atp2atoParse.sp0Parse(item,self.msg_obj.p0)
            elif nid_packet == 1:
                self.msg_obj.p1 = P1()
                Atp2atoParse.sp1Parse(item,self.msg_obj.p1)
            elif nid_packet == 4:
                self.msg_obj.p4 = P4()
                Atp2atoParse.p4Parse(item,self.msg_obj.p4)
            else:
                pass

    # M136消息子包解析函数
    def msg136PktsParse(self, item=BytesStream, l_msg=int):
        # 当剩余bit还够一个包头时
        while item.curBitsIndex < (l_msg*8 - 21):
            nid_packet = item.fast_get_segment_by_index(item.curBitsIndex, 8)
            if nid_packet == 0:
                self.msg_obj.p0 = P0()
                Atp2atoParse.sp0Parse(item,self.msg_obj.p0)
            elif nid_packet == 1:
                self.msg_obj.p1 = P1()
                Atp2atoParse.sp1Parse(item,self.msg_obj.p1)
            elif nid_packet == 4:
                self.msg_obj.p4 = P4()
                Ato2tsrsParse.packetJump(item)           
            elif nid_packet == 44:
                objP44Header = P44A2tHeader()
                Ato2tsrsParse.p44A2tHeaderParse(item, objP44Header)
                nid_xuser = item.get_segment_by_index(item.curBitsIndex, 9)
                # 根据ID选择子包
                if nid_xuser == 44:
                    self.msg_obj.c44 = C44()
                    Ato2tsrsParse.ctcsPacketJump(item)
                elif nid_xuser == 45:
                    self.msg_obj.c45 = C45()
                    Ato2tsrsParse.ctcsPacketJump(item)
                elif nid_xuser == 46:
                    self.msg_obj.c46 = C46()
                    Ato2tsrsParse.ctcsPacketJump(item)
                elif nid_xuser == 48:
                    self.msg_obj.c48 = C48()
                    Ato2tsrsParse.c48Parse(item, self.msg_obj.c48, objP44Header)
                elif nid_xuser == 50:
                    Ato2tsrsParse.ctcsPacketJump(item)                                               
            else:
                pass

    @staticmethod
    def packetJump(item=BytesStream):
        """
        跳包只修改了比特会导致与换算的字节不一致,当不使用字节时无影响
        """
        l_packet = item.get_segment_by_index(item.curBitsIndex, 13)
        item.curBitsIndex = item.curBitsIndex + l_packet -8 -13

    @staticmethod
    def ctcsPacketJump(item=BytesStream):
        """
        跳包只修改了比特会导致与换算的字节不一致,当不使用字节时无影响
        """
        l_packet = item.get_segment_by_index(item.curBitsIndex, 13)
        item.curBitsIndex = item.curBitsIndex + l_packet -9 -13

    @staticmethod
    def p44A2tHeaderParse(item=BytesStream, obj=P44A2tHeader):
        """
        except nid_packet 8bit
        """
        obj.l_packet   = item.fast_get_segment_by_index(item.curBitsIndex, 13)
        return obj

    @staticmethod
    def c48Parse(item, obj=C48, p44Header=P44A2tHeader):
        """
        except nid_xuser 9bit
        """
        obj.p44_header.l_packet = p44Header.l_packet
        # 子包 9bit nid_xuser已经解析
        obj.l_packet = item.fast_get_segment_by_index(item.curBitsIndex, 13)
        obj.m_tbplan = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.nid_tbdeparttrack = item.fast_get_segment_by_index(item.curBitsIndex, 24)
        obj.nid_operational = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.nid_tbarrivaltrack = item.fast_get_segment_by_index(item.curBitsIndex, 24)
        obj.m_task = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.m_tbstatus = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.updateflag = True

    @staticmethod
    def p11Parse(item, obj=P11):
        obj.l_packet = item.fast_get_segment_by_index(item.curBitsIndex, 13)
        obj.nid_operational = item.fast_get_segment_by_index(item.curBitsIndex, 32)
        obj.nc_train = item.fast_get_segment_by_index(item.curBitsIndex, 15)
        obj.l_train = item.fast_get_segment_by_index(item.curBitsIndex, 12)
        obj.v_maxtrain = item.fast_get_segment_by_index(item.curBitsIndex, 7)
        obj.m_loadinggauge = item.fast_get_segment_by_index(item.curBitsIndex, 8)
        obj.m_axleload = item.fast_get_segment_by_index(item.curBitsIndex, 7)
        obj.m_airtight = item.fast_get_segment_by_index(item.curBitsIndex, 2)
        obj.n_iter = item.fast_get_segment_by_index(item.curBitsIndex, 5)
        obj.n_iter_stm = item.fast_get_segment_by_index(item.curBitsIndex, 5)
        obj.nid_stm0 = item.fast_get_segment_by_index(item.curBitsIndex, 8)

    @staticmethod
    def p4Parse(item, obj=P4):
        obj.l_packet = item.fast_get_segment_by_index(item.curBitsIndex, 13)
        obj.m_error = item.fast_get_segment_by_index(item.curBitsIndex, 8)

class DisplayMsgield(object):
   
    #类属性
    msg_obj = Atp2atoProto()
    atpatoMsgCnt = 0
    tsrsatoMsgCnt = 0

    @staticmethod
    def disTsmStat(value, lbl=QtWidgets.QLabel, details=False):
        # TSM无穷远 或 TSM区无效时
        if value == 0x7FFFFFFF or value != 0xFFFFFFFF:
            # 当可以计算时显示数值
            if details and value != 0x7FFFFFFF:
                lbl.setText("距减速区:%.2fm"%(value/100))
            else:
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
    def disFxInfo(fxDis=int, lbl=QtWidgets.QLabel):
        expressStr = '分相区信息:'
        if fxDis != 0xFFFF:
            expressStr += ('前方分相区%dm'%fxDis)
            lbl.setStyleSheet('background-color: rgb(255, 107, 107);')
        else:
            expressStr += '前方无分相区'
            lbl.setStyleSheet('background-color: rgb(247, 255, 247);')
        lbl.setText(expressStr)

    @staticmethod
    def disTbRelatedBtn(cabBtn=int, wsdBtn=int, stBtn=int, dateTime=str, txt=QtWidgets.QPlainTextEdit):
        if cabBtn + wsdBtn + stBtn > 0:
            txt.moveCursor(QtGui.QTextCursor.Start)
            txt.insertPlainText(dateTime+':  '+'SP138|')
            if cabBtn == 1:
                txt.insertPlainText(':驾驶台折返按钮按下!\n')
            if wsdBtn == 1:
                txt.insertPlainText(':轨旁折返按钮按下!\n')
            if stBtn == 1:
                txt.insertPlainText(':ATO发车按钮按下!\n')

    @classmethod
    def disTbStatus(cls, obj=SP13, dateTime=str, txt=QtWidgets.QPlainTextEdit):
        if obj.m_tb_status != cls.msg_obj.sp13_obj.m_tb_status:
            txt.moveCursor(QtGui.QTextCursor.Start)
            txt.insertPlainText(dateTime+':  '+'SP13|')
            if obj.m_tb_status in Atp2atoFieldDic["m_tb_status"].meaning.keys():
                txt.insertPlainText(':'+Atp2atoFieldDic["m_tb_status"].meaning[obj.m_tb_status]+'\n')
        cls.msg_obj.sp13_obj.m_tb_status  = obj.m_tb_status

    @staticmethod
    def disPlainText(obj=SP134, dateTime=str, txt=QtWidgets.QPlainTextEdit):
        txt.moveCursor(QtGui.QTextCursor.Start)
        txt.insertPlainText(dateTime+':')
        if obj.nid_text == 255 and obj.x_text:
            for ch in obj.x_text:
                pureText += hex(ch)
        else:
            if obj.nid_text in Atp2atoFieldDic["nid_text"].meaning.keys():
                txt.insertPlainText(':'+Atp2atoFieldDic["nid_text"].meaning[obj.nid_text]+'\n')
            else:
                txt.insertPlainText(':未知文本\n')

    @classmethod
    def disMsgAtpatoTab(cls, msgObj=Atp2atoProto, dateTime=str, cycleNum=int, tab=QtWidgets.QTableWidget):
        # 是否插入新行
        row_count = tab.rowCount()    # 返回当前行数(尾部)
        if row_count == cls.atpatoMsgCnt:
            tab.insertRow(row_count)  # 尾部插入一行  
        # 时间
        item = QtWidgets.QTableWidgetItem(dateTime)
        tab.setItem(cls.atpatoMsgCnt, 0, item)
        # 周期
        item = QtWidgets.QTableWidgetItem(str(cycleNum))
        tab.setItem(cls.atpatoMsgCnt, 1, item)
        # 方向
        if msgObj.nid_packet == 250:
            dir = 'P->O'
        elif msgObj.nid_packet == 251:
            dir = 'O->P'
        else:
            dir = '未知方向'
        item = QtWidgets.QTableWidgetItem(dir)
        tab.setItem(cls.atpatoMsgCnt, 2, item)
        # 序号
        item = QtWidgets.QTableWidgetItem(str(msgObj.n_sequence))
        tab.setItem(cls.atpatoMsgCnt, 3, item)
        # ATP时间戳
        item = QtWidgets.QTableWidgetItem(str(msgObj.t_msg_atp))
        tab.setItem(cls.atpatoMsgCnt, 4, item)
        # 长度        
        item = QtWidgets.QTableWidgetItem(str(msgObj.l_msg))
        tab.setItem(cls.atpatoMsgCnt, 5, item)
        # 详细信息-子包信息
        packAbsStr = DisplayMsgield.getAtpatoMsgPktsDetailsStr(msgObj)
        item = QtWidgets.QTableWidgetItem(packAbsStr)
        tab.setItem(cls.atpatoMsgCnt, 6, item)
        # 设置颜色
        if msgObj.nid_packet == 250:
            colDef = QtGui.QColor(195, 238, 255)
        elif msgObj.nid_packet == 251:
            colDef = QtGui.QColor(234, 213, 255)
        else:
            pass
        for col in range(7):
            tmp = tab.item(cls.atpatoMsgCnt, col)
            if tmp:
                tmp.setBackground(colDef)
        cls.atpatoMsgCnt += 1     
                
    @classmethod
    def disMsgTsrsatoTab(cls, msgObj=Tsrs2atoProto, dateTime=str, cycleNum=int, tab=QtWidgets.QTableWidget):
        # 是否插入新行
        row_count = tab.rowCount()    # 返回当前行数(尾部)
        if row_count == cls.tsrsatoMsgCnt:
            tab.insertRow(row_count)  # 尾部插入一行  
        # 时间
        item = QtWidgets.QTableWidgetItem(dateTime)
        tab.setItem(cls.tsrsatoMsgCnt, 0, item)
        # 周期
        item = QtWidgets.QTableWidgetItem(str(cycleNum))
        tab.setItem(cls.tsrsatoMsgCnt, 1, item)
        # 方向
        item = QtWidgets.QTableWidgetItem('T->A')
        tab.setItem(cls.tsrsatoMsgCnt, 2, item)
        # 消息
        item = QtWidgets.QTableWidgetItem('M'+str(msgObj.msgHeader.nid_message))
        tab.setItem(cls.tsrsatoMsgCnt, 3, item)
        # 时间戳
        item = QtWidgets.QTableWidgetItem(str(msgObj.msgHeader.t_train))
        tab.setItem(cls.tsrsatoMsgCnt, 4, item)
        # 长度        
        item = QtWidgets.QTableWidgetItem(str(msgObj.msgHeader.l_message))
        tab.setItem(cls.tsrsatoMsgCnt, 5, item)
        # 详细信息
        packAbsStr = DisplayMsgield.getT2aMsgPktsDetailsStr(msgObj)
        item = QtWidgets.QTableWidgetItem(packAbsStr)
        tab.setItem(cls.tsrsatoMsgCnt, 6, item)
        # 设置颜色
        colDef = QtGui.QColor(195, 238, 255)
        for col in range(7):
            tmp = tab.item(cls.tsrsatoMsgCnt, col)
            if tmp:
                tmp.setBackground(colDef)
        cls.tsrsatoMsgCnt += 1    

    @classmethod
    def disMsgAtotsrsTab(cls, msgObj=Ato2tsrsProto, dateTime=str, cycleNum=int, tab=QtWidgets.QTableWidget):
        # 是否插入新行
        row_count = tab.rowCount()    # 返回当前行数(尾部)
        if row_count == cls.tsrsatoMsgCnt:
            tab.insertRow(row_count)  # 尾部插入一行  
        # 时间
        item = QtWidgets.QTableWidgetItem(dateTime)
        tab.setItem(cls.tsrsatoMsgCnt, 0, item)
        # 周期
        item = QtWidgets.QTableWidgetItem(str(cycleNum))
        tab.setItem(cls.tsrsatoMsgCnt, 1, item)
        # 方向
        item = QtWidgets.QTableWidgetItem('A->T')
        tab.setItem(cls.tsrsatoMsgCnt, 2, item)
        # 消息
        item = QtWidgets.QTableWidgetItem('M'+str(msgObj.msgHeader.nid_message))
        tab.setItem(cls.tsrsatoMsgCnt, 3, item)
        # 时间戳
        item = QtWidgets.QTableWidgetItem(str(msgObj.msgHeader.t_train))
        tab.setItem(cls.tsrsatoMsgCnt, 4, item)
        # 长度        
        item = QtWidgets.QTableWidgetItem(str(msgObj.msgHeader.l_message))
        tab.setItem(cls.tsrsatoMsgCnt, 5, item)
        # 详细信息
        packAbsStr = DisplayMsgield.getA2tMsgPktsDetailsStr(msgObj)
        item = QtWidgets.QTableWidgetItem(packAbsStr)
        tab.setItem(cls.tsrsatoMsgCnt, 6, item)
        # 设置颜色
        colDef = QtGui.QColor(234, 213, 255)
        for col in range(7):
            tmp = tab.item(cls.tsrsatoMsgCnt, col)
            if tmp:
                tmp.setBackground(colDef)
        cls.tsrsatoMsgCnt += 1    

    @staticmethod
    def getAtpatoMsgPktsDetailsStr(msgObj=Atp2atoProto)->str:
        packAbsStr = ''
        if msgObj.nid_packet == 250:
            if msgObj.sp0_obj.updateflag:
                packAbsStr += 'SP0|'
            if msgObj.sp1_obj.updateflag:
                packAbsStr += 'SP1|'
            if msgObj.sp2_obj.updateflag:
                packAbsStr += 'SP2|'
            if msgObj.sp3_obj.updateflag:
                packAbsStr += 'SP3|'
            if msgObj.sp4_obj.updateflag:
                packAbsStr += 'SP4|'
            if msgObj.sp5_obj.updateflag:
                packAbsStr += 'SP5|'
            if msgObj.sp6_obj.updateflag:
                packAbsStr += 'SP6|'
            if msgObj.sp7_obj.updateflag:
                packAbsStr += 'SP7|'
            if msgObj.sp8_obj.updateflag:
                packAbsStr += 'SP8|'
            if msgObj.sp9_obj.updateflag:
                packAbsStr += 'SP9|'
            if msgObj.sp13_obj.updateflag:
                packAbsStr += 'SP13|'
        if msgObj.nid_packet == 251:
            if msgObj.sp130_obj.updateflag:
                packAbsStr += 'SP130|'
            if msgObj.sp131_obj.updateflag:
                packAbsStr += 'SP131|'
            if msgObj.sp132_obj.updateflag:
                packAbsStr += 'SP132|'
            if msgObj.sp133_obj.updateflag:
                packAbsStr += 'SP133|'
            if msgObj.sp134_obj.updateflag:
                packAbsStr += 'SP134|'
            if msgObj.sp138_obj.updateflag:
                packAbsStr += 'SP138|'
        return packAbsStr

    @staticmethod
    def getA2tMsgPktsDetailsStr(a2tMsg=Ato2tsrsProto)->str:
        packAbsStr = ''
        if a2tMsg.p0:
            packAbsStr += 'P0|'
        if a2tMsg.p1:
            packAbsStr += 'P1|'
        if a2tMsg.p4:
            packAbsStr += 'P4|'
        if a2tMsg.p11:
            packAbsStr += 'P11|'
        if a2tMsg.c44:
            packAbsStr += 'C44|'
        if a2tMsg.c45:
            packAbsStr += 'C45|'
        if a2tMsg.c46:
            packAbsStr += 'C46|'
        if a2tMsg.c48:
            packAbsStr += 'C48|'
        if a2tMsg.t_train_ack:
            packAbsStr += ('ack ttrain %d|'%a2tMsg.t_train_ack)
        return packAbsStr

    @staticmethod
    def getT2aMsgPktsDetailsStr(t2aMsg=Tsrs2atoProto)->str:
        packAbsStr = ''
        if t2aMsg.p3:
            packAbsStr += 'P3|'
        if t2aMsg.p21:
            packAbsStr += 'P27|' 
        if t2aMsg.p58:
            packAbsStr += 'P58|'  
        if t2aMsg.p72:
            packAbsStr += 'P72|' 
        if t2aMsg.c2:
            packAbsStr += 'C2|' 
        if t2aMsg.c12:
            packAbsStr += 'C12|'
        if t2aMsg.c41:
            packAbsStr += 'C41|'
        if t2aMsg.c42:
            packAbsStr += 'C42|'
        if t2aMsg.c43:
            packAbsStr += 'C43|'
        if t2aMsg.c47:
            packAbsStr += 'C47|'                                                                               
        if t2aMsg.c49:
            packAbsStr += 'C49|'
        if t2aMsg.t_train_ack:
            packAbsStr += ('ack ttrain:%d|'%t2aMsg.t_train_ack)
        if t2aMsg.version:
            packAbsStr += ('ver:0x%x|'%t2aMsg.version)
        return packAbsStr

    @staticmethod
    def disNameOfLineEdit(keyName=str, value=int, led=QtWidgets.QLineEdit):
        if keyName in Atp2atoFieldDic.keys():
            # 如果有含义的话
            if Atp2atoFieldDic[keyName].meaning:
                # 检查是否有含义
                if value in Atp2atoFieldDic[keyName].meaning.keys():
                    led.setText(Atp2atoFieldDic[keyName].meaning[value])
                # 检查是否有单位
                elif Atp2atoFieldDic[keyName].unit:
                    led.setText(str(value)+' '+Atp2atoFieldDic[keyName].unit)
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
                elif keyName == "nid_radio_h":
                    ipStr = str((value>>24))+'.'+str((value>>16)&0xff)+'.'+str((value>>8)&0xff)+'.'+str(value&0xff)
                    led.setText(ipStr)
                else:
                    if Atp2atoFieldDic[keyName].unit:
                        led.setText(str(value)+Atp2atoFieldDic[keyName].unit)
                    else:
                        led.setText(str(value))
        else:
            print("[ERR]:DisplayMsgield disNameOfLineEdit error key name!")
        led.setCursorPosition(0)
        
    @staticmethod
    def disNameOfLable(keyName=str, value=int, lbl=QtWidgets.QLabel,keyGoodVal=-1, keyBadval=-1):
        if keyName in Atp2atoFieldDic.keys():
            # 如果有字段定义
            if Atp2atoFieldDic[keyName].meaning:
                # 检查是否有含义
                if value in Atp2atoFieldDic[keyName].meaning.keys():
                    lbl.setText(Atp2atoFieldDic[keyName].meaning[value])
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
                twi.setText(1,keyName)
                twi.setText(2,str(fieldDic[keyName].width)+'bits')
                twi.setText(3,str(value))
                intro = fieldDic[keyName].name+':' # 字段含义说明
                # 上色
                for i in range(1, twi.columnCount()+1):
                    twi.setBackground(i, nomBrush)
                # 如果有字段定义
                if fieldDic[keyName].meaning:
                    # 检查是否有含义
                    if value in fieldDic[keyName].meaning.keys():
                        twi.setText(4,intro+fieldDic[keyName].meaning[value])
                    elif keyName == 'd_tsm': # 含义和特殊值并存
                        if fieldDic[keyName].unit:
                            twi.setText(4, intro+str(value)+'('+fieldDic[keyName].unit+')')
                    else:
                        brush = QtGui.QBrush(QtGui.QColor(255, 0, 0)) #红色
                        for i in range(1,twi.columnCount()+1):
                            twi.setBackground(i, brush)
                        twi.setText(4,intro+'异常值%s' % value)
                else:
                    # 直接处理显示
                    if fieldDic[keyName].unit:
                        twi.setText(4,intro+str(value)+'('+fieldDic[keyName].unit+')')
            elif keyName == 'updateflag':
                pass
            else:
                print("[ERR]:disNameOfTreeWidget error key name!"+keyName)
        root.setExpanded(True)

    @staticmethod
    def disNameOfMsgShell(msg=Atp2atoProto, root=QtWidgets.QTreeWidgetItem):
        if msg and root:
            # 消息头
            if msg.nid_packet == 250:
                root.setText(0, "ATP->ATO通信消息")
            else:
                root.setText(0, "ATO->ATP通信消息")
            msgTree = QtWidgets.QTreeWidgetItem(root)
            msgTree.setText(1,"msg_id")
            msgTree.setText(2, '8bits')
            msgTree.setText(3, str(msg.nid_msg))
            msgTree.setText(4, "消息号:ATP-ATO通信消息固定ID=45")

            msgTree = QtWidgets.QTreeWidgetItem(root)
            msgTree.setText(1,"l_msg")
            msgTree.setText(2, '8bits')
            msgTree.setText(3, str(msg.l_msg))
            msgTree.setText(4, "消息长度:全部长度,单位字节")

            msgTree = QtWidgets.QTreeWidgetItem(root)
            msgTree.setText(1,"nid_packet")
            msgTree.setText(2, '8bits')
            msgTree.setText(3, str(msg.nid_packet))
            msgTree.setText(4, "信息包号:标识ATP-ATO通信方向")
            
            msgTree = QtWidgets.QTreeWidgetItem(root)
            msgTree.setText(1,"l_packet")
            msgTree.setText(2, '13bits')
            msgTree.setText(3, str(msg.l_packet))
            msgTree.setText(4, "信息包长度:包含所有子信息包,单位比特")
            # 消息结尾
            msgTree = QtWidgets.QTreeWidgetItem(root)
            msgTree.setText(1,"n_sequence")
            msgTree.setText(2, '32bits')
            msgTree.setText(3, str(msg.n_sequence))
            msgTree.setText(4, "消息序号:ATP消息序号")

            msgTree = QtWidgets.QTreeWidgetItem(root)
            msgTree.setText(1,"t_atp")
            msgTree.setText(2, '32bits')
            msgTree.setText(3, str(msg.t_msg_atp))
            msgTree.setText(4, "消息时间戳:ATP时间坐标系系统时间,单位ms")

            msgTree = QtWidgets.QTreeWidgetItem(root)
            msgTree.setText(1,"crc_code")
            msgTree.setText(2, '32bits')
            msgTree.setText(3, hex(msg.crc_code))
            msgTree.setText(4, "消息CRC码:循环冗余校验码")
