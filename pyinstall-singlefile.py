'''
Author: Zhengtang Bao
Contact: baozhengtang@crscd.com.cn
File: 
Date: 2020-11-12 14:12:27
Desc: 
LastEditors: Zhengtang Bao
LastEditTime: 2022-08-18 09:22:04
'''
if __name__ == '__main__':
	from PyInstaller.__main__ import run
	opts = ['Main.py', '-w','-D','-F','--icon=./IconFiles/BZT.ico']
	run(opts)