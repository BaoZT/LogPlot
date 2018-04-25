#!/usr/bin/env python

# encoding: utf-8

'''

@author:  Baozhengtang

@license: (C) Copyright 2017-2018, Author Limited.

@contact: baozhengtang@gmail.com

@software: LogPlot

@file: ProtocolParse.py

@time: 2018/4/20 14:56

@desc: 本文件用于增加提供记录中相关的协议解析功能，包括
       但不限于MVB，ATP-ATO，ATO-TSRS功能
'''


class MVBParse(object):
    def __init__(self):
        pass

    def raw_str_preprocess(self, stream=str, form=list):
        '''
        :param stream: 字节流的字符串，字节之间可以有空格
        :param form: 字节宽度列表，指示字节流中的切割格式
        :return: 解析结果的列表
        '''




    def ato2tcms(self, port=int, stream=str):
        '''
        :param port: ATO和TCMS通信端口1025和1041
        :return: 解析结果的列表
        '''
        ret = 0
        ret_result = []

        if port == 1025:
            pass
        elif port == 1041:
            pass
        else:
            pass
        return ret_result