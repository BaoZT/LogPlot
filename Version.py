'''
Author: Zhengtang Bao
Contact: baozhengtang@crscd.com.cn
File: 
Date: 2022-08-20 10:37:01
Desc: 
LastEditors: Zhengtang Bao
LastEditTime: 2023-01-10 11:44:48
'''
#!/usr/bin/env python
# encoding: utf-8




class VersionInfo(object):

    def __init__(self) -> None:
        self.major  = 4  # 主版本-软件进行了大量重写,这些重写使得无法实现向后兼容性。
        self.junior = 1  # 子版本-新功能新版本照顾到了兼容性
        self.build  = 0  # 编译版本-区分平台
        self.revision = 230110  # 修补版本-内部程序集可以互换
        self.name = 'LogPlot'
        self.note = 'Alpha'
    
    def __getVerStr(self):
        return str(self.major)+'.'+str(self.junior)+'.'+str(self.build)+'.'+str(self.revision)+'-'+self.note
    
    def getVerToken(self):
        return self.name + '-Ver ' + self.__getVerStr()

    def getVerDescription(self):
        desc = \
        "1.重写了数据处理,使用数据解析实现ATP/MVB/TSRS信息\n"+\
        "2.重写了显示处理逻辑统一了离线和在线数据控件\n"+\
        "3.提供了软件配置、协议解析、统计功能\n"
        return desc
    
    def getLicenseDescription(self):
        desc = \
        "Author  :Baozhengtang\n"+\
        "License :(C) Copyright 2017-2022, Author Limited.\n"+\
        "Contact :baozhengtang@crscd.com"
        return desc
    