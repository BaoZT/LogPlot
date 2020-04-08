#!/usr/bin/env python

# encoding: utf-8

'''

@author:  Baozhengtang

@license: (C) Copyright 2017-2018, Author Limited.

@contact: baozhengtang@gmail.com

@software: LogPlot

@file: TCMSParse.py

@time: 2018/4/20 14:56

@desc: 本文件用于增加提供记录中相关的协议解析功能，包括
       但不限于MVB，ATP-ATO，ATO-TSRS功能
'''

import sys


class MVBParse(object):

    def __init__(self):
        # mvb格式解析表
        self.mvb_tcms2ato_status = [4, 1, 1, 1, 1, 2, 2, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1]
        self.mvb_ato2tcms_ctrl = [4, 1, 1, 1, 2, 2, 1, 1, 1, 2, 1]
        self.mvb_ato2tcms_status = [4, 1, 1, 4, 2, 2, 2]

    @staticmethod
    def raw_str_preprocess(identifier=str, stream=str, form=list):
        """
        :param stream: 字节流的字符串，字节之间可以有空格
        :param form: 字节宽度列表，指示字节流中的切割格式
        :return: 解析结果的列表（第一个元素是数据头）
        """
        err_flag = 0
        tmp = 0
        result = []
        stream_list = []
        content_str_list = []
        adder = 0
        # 开始计算
        stream = stream.strip()  # 去掉两侧的空格
        stream_list = stream.split(identifier)  # 分隔字节流
        stream = ''.join(stream_list)  # 生成连续的字节流，一个占位是4位
        # 根据格式列表切片按字节8位
        if (len(stream) / 2) >= sum(form):
            for item in form:
                content_str_list.append(stream[adder:adder + 2 * item])
                adder += 2 * item
                try:
                    tmp = int(stream[adder:adder + 2 * item], 16)
                except Exception as err:
                    err_flag = 1
                    print(err)
                    print('lineno:' + sys._getframe().f_lineno)
        else:
            content_str_list = []
        # 如果有错误重置
        if err_flag == 1:
            content_str_list = []
        # result = list(map(int, content_str_list, [16]*len(content_str_list)))
        return content_str_list

    def ato_tcms_parse(self, port=int, stream=str):
        """
        :param port: ATO和TCMS通信端口1025和1041
        :param stream: 原始字节流
        :return: 解析结果的列表
        """
        ret = 0
        ret_result = []
        # 这里按照仅配置数据长度的解析表，加上数据头4个字节（len+8）
        if port == 1025:
            if len(stream) >= 34:
                try:
                    ret_result = self.raw_str_preprocess(' ', stream, self.mvb_ato2tcms_ctrl)[1:]
                except Exception as err:
                    self.Log(err, __name__, sys._getframe().f_lineno)
            else:
                print('1025 mvb stream error! len=%d' % len(stream))
                print(stream)
        elif port == 1041:
            if len(stream) >= 30:
                try:
                    ret_result = self.raw_str_preprocess(' ', stream, self.mvb_ato2tcms_status)[1:]
                except Exception as err:
                    self.Log(err, __name__, sys._getframe().f_lineno)
            else:
                print('1041 mvb stream error! len=%d' % len(stream))
                print(stream)
        elif port == 1032:
            if len(stream) >= 48:
                try:
                    ret_result = self.raw_str_preprocess(' ', stream, self.mvb_tcms2ato_status)[1:]
                except Exception as err:
                    self.Log(err, __name__, sys._getframe().f_lineno)
            else:
                print('1032 mvb stream error! len=%d' % len(stream))
                print(stream)
        else:
            ret = -1
        return ret_result

    @staticmethod
    def Log(msg=str, fun=str, lino=int):
        if str == type(msg):
            print(msg + ',File:"' + __file__ + '",Line' + str(lino) +
                  ', in' + fun)
        else:
            print(msg)
            print(',File:"' + __file__ + '",Line' + str(lino) + ', in' + fun)
