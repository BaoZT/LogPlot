'''
@Author: Zhengtang Bao
@Contact: baozhengtang@crscd.com.cn
@File: simpModule.py
@Date: 2020-06-29 20:45:25
@Desc: Provide base simp agent Defination
LastEditors: Zhengtang Bao
LastEditTime: 2022-07-02 21:33:26
'''
#!/usr/bin/env python
# encoding: utf-8
from distutils.command.config import config
import os
import configparser
from enum import IntEnum, Enum

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
    def __init__(self) -> None:
        self.section_name = "RegexInfo"
        # 周期
        self.pat_cycle_end = '---CORE_TARK CY_E (\d+),(\d+).'  # 周期起点匹配，括号匹配取出ostime和周期号，最后可以任意匹配
        self.pat_cycle_start = '---CORE_TARK CY_B (\d+),(\d+).' # 周期终点匹配
        # 北京时间
        self.pat_time = 'time:(\d+-\d+-\d+ \d+:\d+:\d+)'
        # ATO模式转换条件
        self.pat_fsm = 'FSM{(\d) (\d) (\d) (\d) (\d) (\d)}sg{(\d) (\d) (\d+) (\d+) (\w+) (\w+)}ss{(\d+) (\d)}'
        # 控车信息
        self.pat_ctrl =  'SC{(\d+) (\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (\d+) (\d+) (-?\d+) (-?\d+)}t (\d+) (\d+) (\d+) (\d+),(\d+)} f (-?\d+) (\d+) (\d+) (-?\w+)} p(\d+) (\d+)}CC'
        # 停车点信息
        self.pat_stoppoint = 'stoppoint:jd=(\d+) ref=(\d+) ma=(\d+)'
        # 原始数据
        self.pat_p2o = '\[P->O\]\[\d+\]:([\w?\s]*)'
        self.pat_o2p = '\[O->P\]\[\d+\]:([\w?\s]*)'
        self.pat_t2a = '\[T->A\]\[\d+\]:([\w?\s]*)'
        self.pat_a2t = '\[A->T\]\[\d+\]:([\w?\s]*)'

        # IO IN的信息
        self.pat_io_in = '\[DOOR\]IO_IN_(\w+)=(\d)'
        # 匹配多个表达式时，或符号|两边不能有空格！
        self.pat_io_out = "\[MSG\](OPEN\s[LR])|\[MSG\](CLOSE\s[LR])|\[MSG\](OPEN\sPSD[LR])|\[MSG\](CLOSE\sPSD[LR])"
        # sdu 信息
        self.pat_ato_sdu = 'v&p_ato:(\d+),(\d+)'
        self.pat_atp_sdu = 'v&p_atp:(-?\d+),(-?\d+)'



class ConfigFile(object):
    __slots__ = ["hd","base_config", "mvb_config", "reg_config"]
    
    def __init__(self) -> None:
        self.hd = configparser.ConfigParser()
        self.base_config = BaseConfig()
        self.mvb_config = MVBConfig()
        self.reg_config = RegConfig()
    
    def __writeBaseSection(self):
        with open(logname, 'w') as f:
            if self.hd.has_section(self.base_config.section_name):
                pass
            else:
                self.hd.add_section(self.base_config.section_name)
            # base info config
            self.hd.set(self.base_config.section_name, 'project', self.base_config.project)
            self.hd.set(self.base_config.section_name,"save_path",self.base_config.save_path)
            self.hd.write(f,space_around_delimiters=False)
    
    def __writeMVBSection(self):
        with open(logname, 'w') as f:
            if self.hd.has_section(self.mvb_config.section_name):
                pass
            else:
                self.hd.add_section(self.mvb_config.section_name)
            # mvb info config
            self.hd.set(self.mvb_config.section_name,"ato2tcms_ctrl_port",str(self.mvb_config.ato2tcms_ctrl_port))
            self.hd.set(self.mvb_config.section_name,"ato2tcms_state_port",str(self.mvb_config.ato2tcms_state_port))
            self.hd.set(self.mvb_config.section_name,"tcms2ato_state_port",str(self.mvb_config.tcms2ato_state_port))
            self.hd.write(f,space_around_delimiters=False)

    def __writeRegSection(self):
        with open(logname, 'w') as f:
            if self.hd.has_section(self.reg_config.section_name):
                pass
            else:
                self.hd.add_section(self.reg_config.section_name)
            # regex pattern
            self.hd.set(self.reg_config.section_name,"pat_cycle_end",self.reg_config.pat_cycle_end)
            self.hd.set(self.reg_config.section_name,"pat_cycle_start",self.reg_config.pat_cycle_start)
            self.hd.set(self.reg_config.section_name,"pat_time",self.reg_config.pat_time)
            self.hd.set(self.reg_config.section_name,"pat_fsm",self.reg_config.pat_fsm)
            self.hd.set(self.reg_config.section_name,"pat_ctrl",self.reg_config.pat_ctrl)
            self.hd.set(self.reg_config.section_name,"pat_stoppoint",self.reg_config.pat_stoppoint)
            self.hd.set(self.reg_config.section_name,"pat_p2o",self.reg_config.pat_p2o)
            self.hd.set(self.reg_config.section_name,"pat_o2p",self.reg_config.pat_o2p)
            self.hd.set(self.reg_config.section_name,"pat_t2a",self.reg_config.pat_t2a)
            self.hd.set(self.reg_config.section_name,"pat_a2t",self.reg_config.pat_a2t)
            self.hd.set(self.reg_config.section_name,"pat_io_in",self.reg_config.pat_io_in)
            self.hd.set(self.reg_config.section_name,"pat_io_out",self.reg_config.pat_io_out)
            self.hd.set(self.reg_config.section_name,"pat_ato_sdu",self.reg_config.pat_ato_sdu)
            self.hd.set(self.reg_config.section_name,"pat_atp_sdu",self.reg_config.pat_atp_sdu)
            self.hd.write(f,space_around_delimiters=False)

    def __readBaseSection(self):
        with open(logname, 'r+') as f:
            self.hd.read_file(f)
            if self.hd.has_section(self.base_config.section_name):
                self.base_config.project = self.hd.get(self.base_config.section_name,"project")
                self.base_config.save_path = self.hd.get(self.base_config.section_name, "save_path")
            else:
                self.__writeBaseSection()

    def __readMVBSection(self):
        with open(logname, 'r+') as f:
            self.hd.read_file(f)
            if self.hd.has_section(self.mvb_config.section_name):
                self.mvb_config.ato2tcms_ctrl_port = self.hd.getint(self.mvb_config.section_name,"ato2tcms_ctrl_port")
                self.mvb_config.ato2tcms_state_port = self.hd.getint(self.mvb_config.section_name,"ato2tcms_state_port")
                self.mvb_config.tcms2ato_state_port = self.hd.getint(self.mvb_config.section_name, "tcms2ato_state_port")
            else:
                self.__writeMVBSection()

    def __readRegSection(self):
        with open(logname, 'r+') as f:
            self.hd.read_file(f)
            if self.hd.has_section(self.reg_config.section_name):
                self.reg_config.pat_cycle_end = self.hd.get(self.reg_config.section_name, "pat_cycle_end")
                self.reg_config.pat_cycle_start = self.hd.get(self.reg_config.section_name, "pat_cycle_start")
                self.reg_config.pat_time = self.hd.get(self.reg_config.section_name, "pat_time")
                self.reg_config.pat_fsm = self.hd.get(self.reg_config.section_name, "pat_fsm")
                self.reg_config.pat_ctrl = self.hd.get(self.reg_config.section_name, "pat_ctrl")
                self.reg_config.pat_stoppoint = self.hd.get(self.reg_config.section_name, "pat_stoppoint")
                self.reg_config.pat_p2o = self.hd.get(self.reg_config.section_name, "pat_p2o")
                self.reg_config.pat_o2p = self.hd.get(self.reg_config.section_name, "pat_o2p")
                self.reg_config.pat_t2a = self.hd.get(self.reg_config.section_name, "pat_t2a")
                self.reg_config.pat_a2t = self.hd.get(self.reg_config.section_name, "pat_a2t")
                self.reg_config.pat_io_in = self.hd.get(self.reg_config.section_name, "pat_io_in")
                self.reg_config.pat_io_out = self.hd.get(self.reg_config.section_name, "pat_io_out")
                self.reg_config.pat_ato_sdu = self.hd.get(self.reg_config.section_name, "pat_ato_sdu")
                self.reg_config.pat_atp_sdu = self.hd.get(self.reg_config.section_name, "pat_atp_sdu")
            else:
                self.__writeRegSection()

    def __writeAllSections(self):
        self.__writeBaseSection()
        self.__writeMVBSection()
        self.__writeRegSection()

    def __readAllSections(self):
        self.__readBaseSection()
        self.__readMVBSection()
        self.__readRegSection()

    def readConfigFile(self):
        if os.path.exists(logname):
            self.__readAllSections()
        else:
            self.__writeAllSections()

    def writeConfigFile(self):
        with open('LogPlotCfg.ini', 'w') as f:
            self.hd.write(f, space_around_delimiters=False)