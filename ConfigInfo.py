'''
@Author: Zhengtang Bao
@Contact: baozhengtang@crscd.com.cn
@File: simpModule.py
@Date: 2020-06-29 20:45:25
@Desc: Provide base simp agent Defination
LastEditors: Zhengtang Bao
LastEditTime: 2022-07-09 22:25:32
'''
#!/usr/bin/env python
# encoding: utf-8

import os
import configparser
from re import compile

logname = 'LogPlotCfg.ini'

class BaseConfig(object):
    __slots__ = ['section_name','project',"save_path"]
    def __init__(self) -> None:
        self.project = "C3ATO"
        self.save_path = os.path.split(os.path.realpath(__file__))[0]
        self.section_name = "BaseInfo"

class MVBConfig(object):
    __slots__ = ['section_name','ato2tcms_ctrl_port','ato2tcms_state_port','tcms2ato_state_port', 'mvb_addr']
    def __init__(self) -> None:
        self.ato2tcms_ctrl_port = 1025
        self.ato2tcms_state_port = 1041
        self.tcms2ato_state_port = 1032
        self.mvb_addr = 64
        self.section_name = "MVBInfo"

class RegConfig(object):
    __slots__ = ['section_name', 'reg_cycle_end', 'reg_cycle_start', 'reg_time', 'reg_fsm','reg_ctrl',
    'reg_stoppoint','reg_p2o','reg_o2p','reg_t2a','reg_a2t','reg_mvb','reg_io_in','reg_io_out','reg_ato_sdu',
    'reg_atp_sdu','reg_rp1','reg_rp2','reg_rp2_cntent','reg_rp3','reg_rp4',
    'pat_cycle_end', 'pat_cycle_start', 'pat_time', 'pat_fsm','pat_ctrl',
    'pat_stoppoint','pat_p2o','pat_o2p','pat_t2a','pat_a2t','pat_mvb','pat_io_in','pat_io_out','pat_ato_sdu',
    'pat_atp_sdu','pat_rp1','pat_rp2','pat_rp2_cntent','pat_rp3','pat_rp4']
    def __init__(self) -> None:
        self.section_name = "RegexInfo"
        # 周期
        self.reg_cycle_end = '---CORE_TARK CY_E (\d+),(\d+).'  # 周期起点匹配，括号匹配取出ostime和周期号，最后可以任意匹配
        self.reg_cycle_start = '---CORE_TARK CY_B (\d+),(\d+).' # 周期终点匹配
        # 北京时间
        self.reg_time = 'time:(\d+-\d+-\d+ \d+:\d+:\d+)'
        # ATO模式转换条件
        self.reg_fsm = 'FSM{(\d) (\d) (\d) (\d) (\d) (\d)}sg{(\d) (\d) (\d+) (\d+) (\w+) (\w+)}ss{(\d+) (\d)}'
        # 控车信息
        self.reg_ctrl =  'SC{(\d+) (\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (\d+) (\d+) (-?\d+) (-?\d+)}t (\d+) (\d+) (\d+) (\d+),(\d+)} f (-?\d+) (\d+) (\d+) (-?\w+)} p(\d+) (\d+)}CC'
        # 停车点信息
        self.reg_stoppoint = 'stoppoint:jd=(\d+) ref=(\d+) ma=(\d+)'
        # 原始数据
        self.reg_p2o = '\[P->O\]\[\d+\]:([\w?\s]*)'
        self.reg_o2p = '\[O->P\]\[\d+\]:([\w?\s]*)'
        self.reg_t2a = '\[T->A\]\[\d+\]:([\w?\s]*)'
        self.reg_a2t = '\[A->T\]\[\d+\]:([\w?\s]*)'
        # MVB原始数据
        self.reg_mvb = 'MVB\[\d+]:([\w?\s]*)'

        # IO IN的信息
        self.reg_io_in = '\[DOOR\]IO_IN_(\w+)=(\d)'
        # 匹配多个表达式时，或符号|两边不能有空格！
        self.reg_io_out = "\[MSG\](OPEN\s[LR])|\[MSG\](CLOSE\s[LR])|\[MSG\](OPEN\sPSD[LR])|\[MSG\](CLOSE\sPSD[LR])"
        # 测速测距信息
        self.reg_ato_sdu = 'v&p_ato:(\d+),(\d+)'
        self.reg_atp_sdu = 'v&p_atp:(-?\d+),(-?\d+)'
        # 计划信息 计划解析RP1-RP4
        self.reg_rp1 = '\[RP1\](-?\d+),(\d+),(\d+),(\d+)'
        self.reg_rp2 = '\[RP2\](\d),(\d),(-?\d+),(\d)'
        self.reg_rp2_cntent = '\[RP2-(\d+)\](\d+),(\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(\d),(\d)'
        self.reg_rp3 = '\[RP3\](\d),(\d),(-?\d+),(-?\d+),(\d)'
        self.reg_rp4 = '\[RP4\](\d),(-?\d+),(-?\d+),(\d),(\d)'
        self.updatePattern()

    def updatePattern(self):
        # 周期
        self.pat_cycle_end = compile(self.reg_cycle_end)
        self.pat_cycle_start =  compile(self.reg_cycle_start)
        # 北京时间
        self.pat_time =  compile(self.reg_time)
        # ATO模式转换条件
        self.pat_fsm =  compile(self.reg_fsm)
        # 控车信息
        self.pat_ctrl =   compile(self.reg_ctrl)
        # 停车点信息
        self.pat_stoppoint =  compile(self.reg_stoppoint)
        # 原始数据
        self.pat_p2o =  compile(self.reg_p2o)
        self.pat_o2p =  compile(self.reg_o2p)
        self.pat_t2a =  compile(self.reg_t2a)
        self.pat_a2t =  compile(self.reg_a2t)
        # MVB原始数据
        self.pat_mvb =  compile(self.reg_mvb)
        # IO IN的信息
        self.pat_io_in =  compile(self.reg_io_in)
        # 匹配多个表达式时，或符号|两边不能有空格！
        self.pat_io_out =  compile(self.reg_io_out)
        # 测速测距信息
        self.pat_ato_sdu =  compile(self.reg_ato_sdu)
        self.pat_atp_sdu =  compile(self.reg_atp_sdu)
        # 计划信息 计划解析RP1-RP4
        self.pat_rp1 =  compile(self.reg_rp1)
        self.pat_rp2 =  compile(self.reg_rp2)
        self.pat_rp2_cntent =  compile(self.reg_rp2_cntent)
        self.pat_rp3 =  compile(self.reg_rp3)
        self.pat_rp4 =  compile(self.reg_rp4)


class MonitorConfig(object):
    __slots__ = ['section_name','sdu_spd_fault_th',"sdu_dis_fault_th"]
    def __init__(self) -> None:
        self.section_name = "MonitorInfo"
        # 测速测距判断信息
        self.sdu_spd_fault_th = 50   # 测速故障误差阈值 50cm/s
        self.sdu_dis_fault_th = 500  # 测距故障误差阈值 500cm

class ConfigFile(object):
    __slots__ = ["hd","base_config", "mvb_config", "reg_config","monitor_config"]
    
    def __init__(self, comment_prefixes='#') -> None:
        self.hd = configparser.ConfigParser()
        self.base_config = BaseConfig()
        self.mvb_config = MVBConfig()
        self.reg_config = RegConfig()
        self.monitor_config = MonitorConfig()

    def __writeMonitorSection(self):
        if self.hd.has_section(self.monitor_config.section_name):
            pass
        else:
            self.hd.add_section(self.monitor_config.section_name)
        self.hd.set(self.monitor_config.section_name,"sdu_spd_fault_th", str(self.monitor_config.sdu_spd_fault_th))
        self.hd.set(self.monitor_config.section_name,"sdu_dis_fault_th",str(self.monitor_config.sdu_dis_fault_th))

    def __writeBaseSection(self):
        if self.hd.has_section(self.base_config.section_name):
            pass
        else:
            self.hd.add_section(self.base_config.section_name)
        # base info config
        self.hd.set(self.base_config.section_name, 'project', self.base_config.project)
        self.hd.set(self.base_config.section_name,"save_path",self.base_config.save_path)
    
    def __writeMVBSection(self):
        if self.hd.has_section(self.mvb_config.section_name):
            pass
        else:
            self.hd.add_section(self.mvb_config.section_name)
        # mvb info config
        self.hd.set(self.mvb_config.section_name,"ato2tcms_ctrl_port",str(self.mvb_config.ato2tcms_ctrl_port))
        self.hd.set(self.mvb_config.section_name,"ato2tcms_state_port",str(self.mvb_config.ato2tcms_state_port))
        self.hd.set(self.mvb_config.section_name,"tcms2ato_state_port",str(self.mvb_config.tcms2ato_state_port))

    def __writeRegSection(self):
        if self.hd.has_section(self.reg_config.section_name):
            pass
        else:
            self.hd.add_section(self.reg_config.section_name)
        # regex pattern
        self.hd.set(self.reg_config.section_name,"pat_cycle_end",self.reg_config.reg_cycle_end)
        self.hd.set(self.reg_config.section_name,"pat_cycle_start",self.reg_config.reg_cycle_start)
        self.hd.set(self.reg_config.section_name,"pat_time",self.reg_config.reg_time)
        self.hd.set(self.reg_config.section_name,"pat_fsm",self.reg_config.reg_fsm)
        self.hd.set(self.reg_config.section_name,"pat_ctrl",self.reg_config.reg_ctrl)
        self.hd.set(self.reg_config.section_name,"pat_stoppoint",self.reg_config.reg_stoppoint)
        self.hd.set(self.reg_config.section_name,"pat_p2o",self.reg_config.reg_p2o)
        self.hd.set(self.reg_config.section_name,"pat_o2p",self.reg_config.reg_o2p)
        self.hd.set(self.reg_config.section_name,"pat_t2a",self.reg_config.reg_t2a)
        self.hd.set(self.reg_config.section_name,"pat_a2t",self.reg_config.reg_a2t)
        self.hd.set(self.reg_config.section_name,"pat_mvb",self.reg_config.reg_mvb)
        self.hd.set(self.reg_config.section_name,"pat_io_in",self.reg_config.reg_io_in)
        self.hd.set(self.reg_config.section_name,"pat_io_out",self.reg_config.reg_io_out)
        self.hd.set(self.reg_config.section_name,"pat_ato_sdu",self.reg_config.reg_ato_sdu)
        self.hd.set(self.reg_config.section_name,"pat_atp_sdu",self.reg_config.reg_atp_sdu)
        self.hd.set(self.reg_config.section_name,"pat_rp1",self.reg_config.reg_rp1)
        self.hd.set(self.reg_config.section_name,"pat_rp2",self.reg_config.reg_rp2)
        self.hd.set(self.reg_config.section_name,"pat_rp2_cntent",self.reg_config.reg_rp2_cntent)
        self.hd.set(self.reg_config.section_name,"pat_rp3",self.reg_config.reg_rp3)
        self.hd.set(self.reg_config.section_name,"pat_rp4",self.reg_config.reg_rp4)
            

    def __readBaseSection(self):
        if self.hd.has_section(self.base_config.section_name):
            self.base_config.project = self.hd.get(self.base_config.section_name,"project")
            self.base_config.save_path = self.hd.get(self.base_config.section_name, "save_path")
        else:
            self.__writeBaseSection()

    def __readMVBSection(self):
        if self.hd.has_section(self.mvb_config.section_name):
            self.mvb_config.ato2tcms_ctrl_port = self.hd.getint(self.mvb_config.section_name,"ato2tcms_ctrl_port")
            self.mvb_config.ato2tcms_state_port = self.hd.getint(self.mvb_config.section_name,"ato2tcms_state_port")
            self.mvb_config.tcms2ato_state_port = self.hd.getint(self.mvb_config.section_name, "tcms2ato_state_port")
        else:
            self.__writeMVBSection()

    def __readRegSection(self):
        if self.hd.has_section(self.reg_config.section_name):
            self.reg_config.reg_cycle_end = self.hd.get(self.reg_config.section_name, "pat_cycle_end")
            self.reg_config.reg_cycle_start = self.hd.get(self.reg_config.section_name, "pat_cycle_start")
            self.reg_config.reg_time = self.hd.get(self.reg_config.section_name, "pat_time")
            self.reg_config.reg_fsm = self.hd.get(self.reg_config.section_name, "pat_fsm")
            self.reg_config.reg_ctrl = self.hd.get(self.reg_config.section_name, "pat_ctrl")
            self.reg_config.reg_stoppoint = self.hd.get(self.reg_config.section_name, "pat_stoppoint")
            self.reg_config.reg_p2o = self.hd.get(self.reg_config.section_name, "pat_p2o")
            self.reg_config.reg_o2p = self.hd.get(self.reg_config.section_name, "pat_o2p")
            self.reg_config.reg_t2a = self.hd.get(self.reg_config.section_name, "pat_t2a")
            self.reg_config.reg_a2t = self.hd.get(self.reg_config.section_name, "pat_a2t")
            self.reg_config.reg_mvb = self.hd.get(self.reg_config.section_name, "pat_mvb")
            self.reg_config.reg_io_in = self.hd.get(self.reg_config.section_name, "pat_io_in")
            self.reg_config.reg_io_out = self.hd.get(self.reg_config.section_name, "pat_io_out")
            self.reg_config.reg_ato_sdu = self.hd.get(self.reg_config.section_name, "pat_ato_sdu")
            self.reg_config.reg_atp_sdu = self.hd.get(self.reg_config.section_name, "pat_atp_sdu")
            self.reg_config.reg_rp1 = self.hd.get(self.reg_config.section_name,"pat_rp1")
            self.reg_config.reg_rp2 = self.hd.get(self.reg_config.section_name,"pat_rp2")
            self.reg_config.reg_rp2_cntent = self.hd.get(self.reg_config.section_name,"pat_rp2_cntent")
            self.reg_config.reg_rp3 = self.hd.get(self.reg_config.section_name,"pat_rp3")
            self.reg_config.reg_rp4 = self.hd.get(self.reg_config.section_name,"pat_rp4")
            self.reg_config.updatePattern()
        else:
            self.__writeRegSection()

    def __readMonitorSection(self):
            if self.hd.has_section(self.monitor_config.section_name):
                self.monitor_config.sdu_dis_fault_th = self.hd.getint(self.monitor_config.section_name, "sdu_dis_fault_th")
                self.monitor_config.sdu_spd_fault_th = self.hd.getint(self.monitor_config.section_name,"sdu_spd_fault_th")
            else:
                self.__writeMonitorSection()

    def __writeAllSections(self):
        with open(logname, 'w') as f:
            self.__writeBaseSection()
            self.__writeMVBSection()
            self.__writeRegSection()
            self.__writeMonitorSection()
            self.hd.write(f,space_around_delimiters=False)

    def __readAllSections(self):
        with open(logname, 'r+') as f:
            self.hd.read_file(f)
            self.__readBaseSection()
            self.__readMVBSection()
            self.__readRegSection()
            self.__readMonitorSection()

    def readConfigFile(self):
        if os.path.exists(logname):
            self.__readAllSections()
        else:
            self.__writeAllSections()

    def writeConfigFile(self):
        self.__writeAllSections()