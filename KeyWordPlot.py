#!/usr/bin/env python

# encoding: utf-8


import matplotlib
import matplotlib.figure as matfig
from PyQt5 import QtCore, QtWidgets
from FileProcess import FileProcess
import RealTimeExtension
import numpy as np
matplotlib.use("Qt5Agg")  # 声明使用QT5
matplotlib.rcParams['xtick.direction'] = 'in'
matplotlib.rcParams['ytick.direction'] = 'in'
matplotlib.rcParams['axes.unicode_minus'] = False        # 解决Matplotlib绘图中，负号不正常显示问题
matplotlib.rcParams['font.sans-serif'] = ['SimHei']     # 解决matplotlib绘图，汉字显示不正常的问题
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap, BoundaryNorm

cursor_track_flag = 1   # 1=追踪，0=不追踪


# 光标类定义
class SnaptoCursor(QtCore.QObject):
    """ Like Cursor but the crosshair snaps to the nearest x,y point For simplicity, I'm assuming x is sorted """
    move_signal = QtCore.pyqtSignal(int)        # 带一个参数的信号
    sim_move_singal = QtCore.pyqtSignal(int)    # 模拟手动挪动光标

    def __init__(self, sp, ax, x, y, spAux=None, axAux=None, xAux=None, yAux=None):
        super(SnaptoCursor, self).__init__()
        self.fmpl = sp
        self.ax = ax
        self.ax.set_xlim(x[0], x[len(x)-1])  # 默认与不带光标统一的显示范围
        self.ax.set_ylim(-200, 10000)
        self.lx = self.ax.axhline(color='k', linewidth=0.8, ls='dashdot')  # the horiz line, now only keep vert
        self.ly = self.ax.axvline(color='k', linewidth=0.8, ls='dashdot')  # the vert line
        self.x = x
        self.y = y
        # use for record key words
        self.data_x = 0
        self.data_y = 0
        self.nearest_index = 0
        # 辅助光标 
        if spAux and axAux: 
            self.fmplAux = spAux
            self.axAux = axAux
            self.axAux.set_xlim(xAux[0], xAux[len(x)-1])  # 默认与不带光标统一的显示范围
            self.lxAux = self.axAux.axhline(color='k', linewidth=0.8, ls='dashdot')  # the horiz line, now only keep vert
            self.lyAux = self.axAux.axvline(color='k', linewidth=0.8, ls='dashdot')  # the vert line
            self.xAux = x
            self.yAux = y
            # 辅助光标点
            self.data_xAux = 0
            self.data_yAux = 0
        else:
            self.yAux = np.array([])

    def get_cursor_data(self):
        return self.data_x,self.data_y

    def get_cusor_data_idx(self):
        return self.nearest_index

    def mouse_move(self, event):
        global cursor_track_flag
        if not event.inaxes:
            return
        # 下面是当前鼠标坐标
        x, y = event.xdata, event.ydata
        indx = min(np.searchsorted(self.x, [x])[0], len(self.x) - 1) # 共用X轴索引
        # update record data and index for return
        self.data_x = x
        self.data_y = y
        self.nearest_index = indx
        # nearest data 这是数据
        x = self.x[indx]
        y = self.y[indx]
        # 辅助光标
        if self.yAux.any():
            yAux = self.yAux[indx]
        else:
            yAux = None
        # update the line positions
        if cursor_track_flag == 1:          # 看标志追踪
            y = self.y[indx]
            self.lx.set_ydata(y)
            self.ly.set_xdata(x)
            self.fmpl.draw()
            # 辅助光标
            if yAux:
                self.lxAux.set_ydata(yAux)
                self.lyAux.set_xdata(x)  # 共用X轴索引
                self.fmplAux.draw()
            # 发射信号
            self.move_signal.emit(indx)  # 发射信号索引
        else:
            pass

    # 输入坐标模拟光标移动
    def sim_mouse_move(self, x, y):
        indx = min(np.searchsorted(self.x, [x])[0], len(self.x) - 1)
        # update record data and index for return
        self.data_x = x
        self.data_y = y
        self.nearest_index = indx
        # nearest data 这是数据
        x = self.x[indx]
        y = self.y[indx]
        # 辅助光标
        if self.yAux.any():
            yAux = self.yAux[indx]
        else:
            yAux = None
        # update the line positions
        self.lx.set_ydata(y)
        self.ly.set_xdata(x)
        print('x=%1.2f, y=%1.2f' % (x, y))
        self.fmpl.draw()
        # 辅助光标
        if yAux:
            self.lxAux.set_ydata(yAux)
            self.lyAux.set_xdata(x)  # 共用X轴索引
            self.fmplAux.draw()
        # 发射信号
        self.sim_move_singal.emit(indx)  # 发射信号索引

    def resetCursorPlot(self):
        global cursor_track_flag
        cursor_track_flag = 1

    def boldRedEnabled(self, sw=bool):
        if sw:
            self.ly.set_color('red')
            self.lx.set_color('red')
            self.lx.set_linewidth(1.6)
            self.ly.set_linewidth(1.6)
        else:
            self.ly.set_color('k')
            self.lx.set_color('k')
            self.lx.set_linewidth(0.8)
            self.ly.set_linewidth(0.8)


# 画板类定义
class CurveFigureCanvas(FigureCanvas):   # 通过继承FigureCanvas类，使得该类既是一个PyQt5的Qwidget，又是一个matplotlib
                                     # 的FigureCanvas，这是连接pyqt5与matplotlib的关键
    lock_signal = QtCore.pyqtSignal(int)  # 这个参数用于提醒锁定光标

    def __init__(self, parent=None, width=20, height=10, dpi=100, sharedAxes=None):
        self.fig = matfig.Figure(figsize=(width, height), dpi=100, frameon=False)  # 创建一个Figure，注意：该Figure为
                                                                                # matplotlib下的figure，不是matplotlib
                                                                                # pyplot下面的figure
        self.fig.subplots_adjust(top=0.952, bottom=0.095, left=0.064, right=0.954, hspace=0.17, wspace=0.25)
        if sharedAxes:
            self.mainAxes = self.fig.add_subplot(111, sharex=sharedAxes)
        else:
            self.mainAxes = self.fig.add_subplot(111)
        super().__init__(self.fig)    # 初始化父类函数,这是Python3的风格，且super不带参数
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.twinAxes = self.mainAxes.twinx()
        # 气泡绘制
        self.bubbleCtrl = None
        self.bubbleCrosser = None
        # 事件绘制字典,存储每个需要绘制的列表，列表是tuple类型
        self.event_plot_dic = {}
        self.event_plot_flag = 0                 # 事件绘制标志
        self.event_plot_flag_dic = {}            # 指定绘制
        # 轨旁信息字典
        self.wayside_plot_dic = {}


    # 对于速度绘制区分模式，标注模式下绘点，否则直连线
    # mod : 1=标注模式 0=浏览模式
    # cmd : 1=周期速度曲线 0=位置速度曲线
    def plotLogVS(self, ob=FileProcess, mod=int, cmd=int):
        if mod == 1:
            if cmd == 0:   # 位置速度曲线
                self.mainAxes.plot(ob.s, ob.v_ato, markersize=1.2, marker='.', color='deeppink', label="ATO当前速度", linewidth=1)
            else:           # 周期速度曲线
                self.mainAxes.plot(ob.cycle, ob.v_ato, markersize=1.2, marker='.', color='deeppink', label="ATO当前速度", linewidth=1)
        else:
            if cmd == 0:
                self.mainAxes.plot(ob.s, ob.v_ato, color='deeppink', label="ATO当前速度", linewidth=1)
            else:
                p1 = self.mainAxes.plot(ob.cycle, ob.v_ato, color='deeppink', label="ATO当前速度", linewidth=1)

    # 对命令于速度绘制区分模式，标注模式下绘点，否则直连线
    # mod : 1=标注模式 0=浏览模式
    # cmd : 1=周期速度曲线 0=位置速度曲线
    def plotLogVcmdv(self, ob=FileProcess, mod=int, cmd=int):
        if mod == 1:
            if cmd == 0:    # 位置速度曲线
                self.mainAxes.plot(ob.s, ob.cmdv, marker='.', markersize=1.2, color='green', label="ATO命令速度", linewidth=1)
            else:
                self.mainAxes.plot(ob.cycle, ob.cmdv, marker='.', markersize=1.2, color='green', label="ATO命令速度", linewidth=1)
        else:
            if cmd == 0:
                self.mainAxes.plot(ob.s, ob.cmdv, color='green', label="ATO命令速度", linewidth=1)
            else:
                self.mainAxes.plot(ob.cycle, ob.cmdv, color='green', label="ATO命令速度", linewidth=1)

    # 绘制ATP命令速度曲线（含义改变但名称保留）
    # cmd : 1=周期速度曲线 0=位置速度曲线
    def plotLogVceil(self, ob=FileProcess, cmd=int):
        if cmd == 0:
            self.mainAxes.plot(ob.s, ob.ceilv, color='orange', label="ATP命令速度", linewidth=1)
        else:
            self.mainAxes.plot(ob.cycle, ob.ceilv, color='orange', label="ATP命令速度", linewidth=1)

    # 绘制ATP命令速度曲线（含义改变但名称保留）
    # cmd : 1=周期速度曲线 0=位置速度曲线
    def plotLogRamp(self, ob=FileProcess, cmd=int):
        if cmd == 0:
            self.mainAxes.plot(ob.s, ob.ramp, color='red', label="当前坡度", linewidth=1)
        else:
            self.mainAxes.plot(ob.cycle, ob.ramp, color='red', label="当前坡度", linewidth=1)

    # 对于ATP允许速度绘制区分模式，标注模式下绘点，否则直连线
    # mod : 1=标注模式 0=浏览模式
    # cmd : 1=周期速度曲线 0=位置速度曲线
    def plotLogVatpPmt(self, ob=FileProcess, mod=int, cmd=int):
        if cmd == 0:  # 位置速度曲线
            self.mainAxes.plot(ob.s, ob.atp_permit_v, color='b', label="ATP允许速度", linewidth=1)
        else:  # 周期速度曲线
            self.mainAxes.plot(ob.cycle,ob.atp_permit_v, color='b', label="ATP允许速度", linewidth=1)

    # 绘制级位曲线
    # cmd : 1=周期速度曲线 0=位置速度曲线
    def plotLogLevel(self, ob=FileProcess, cmd=int):
        if cmd == 0:
            self.twinAxes.plot(ob.s, ob.level, color='crimson', label='ATO输出级位', linewidth=0.5)
        else:
            self.twinAxes.plot(ob.cycle, ob.level, color='crimson', label='ATO输出级位', linewidth=0.5)
            self.twinAxes.scatter(ob.cycle, ob.level, color='r', label='ATO输出级位', marker='o', linewidths=0,s=1.1, alpha=0.8)

    # 绘制速度坐标轴相关信息
    def plotMainSpeedCord(self, ob=FileProcess, cmd=int, x_lim="tuple", y_lim="tuple"):
        # paint the speed ruler
        self.mainAxes.axhline(y=1250, xmin=0, xmax=1, color='darkblue', ls='--',        # xmin and xmax Should be between 0 and 1,
                           label = '45km/h,80km/h,350km/h', linewidth=0.4)  # 45km/h   #  0 being the far left of the plot,
        self.mainAxes.axhline(y=9722, xmin=0, xmax=1, color='darkblue', ls='dashed',    # 1 the far right of the plot
                           linewidth=0.4)  # 350km/h
        self.mainAxes.axhline(y=2222, xmin=0, xmax=1, color='darkblue', ls='dashed',
                           linewidth=0.4)  # 80km/h
        # 该条曲线纯粹是为了首次绘图自动范围包括负数
        self.mainAxes.axhline(y=-500, xmin=0, xmax=1, color='darkblue', ls='dashed', linewidth=0)

        # 绘制位置速度坐标系
        if cmd == 0:
            self.plot_wayside_info_in_cords(ob, cmd)
            self.plot_event_in_cords(cmd)
            # 如果绘图范围是默认值，还没有绘图，是默认路径
            if x_lim == (0.0, 1.0) and y_lim == (0.0, 1.0):
                self.mainAxes.set_xlim(ob.s[0], ob.s[len(ob.s) - 1])  # 由于绘制直线会从0开始绘制，这里重置范围
                self.mainAxes.set_ylim(-500, 10000)
            else:
                self.mainAxes.set_xlim(x_lim[0], x_lim[1])
                self.mainAxes.set_ylim(y_lim[0], y_lim[1])
                if self.mainAxes.get_lines():
                    self.mainAxes.legend(loc='upper left')
                if self.twinAxes.get_lines():
                    self.twinAxes.legend(loc='upper right')
            self.mainAxes.set_xlabel('列车位置cm',fontdict={'fontsize': 10})
            self.mainAxes.set_ylabel('列车速度cm/s', fontdict={'fontsize': 10})
            self.mainAxes.set_title(ob.filename+" "+"速度-位置曲线")
        else:
            self.plot_wayside_info_in_cords(ob, cmd)
            self.plot_event_in_cords(cmd)                  # 回去在调试
            if x_lim == (0.0, 1.0) and y_lim == (0.0, 1.0):
                self.mainAxes.set_xlim(ob.cycle[0], ob.cycle[len(ob.cycle) - 1])  # 重置范围
                self.mainAxes.set_ylim(-500, 10000)
            else:
                self.mainAxes.set_xlim(x_lim[0], x_lim[1])
                self.mainAxes.set_ylim(y_lim[0], y_lim[1])
                if self.mainAxes.get_lines():
                    self.mainAxes.legend(loc='upper left')
                if self.twinAxes.get_lines():
                    self.twinAxes.legend(loc='upper right')
            self.mainAxes.set_xlabel('ATO周期', fontdict={'fontsize': 10})
            self.mainAxes.set_ylabel('列车速度cm/s', fontdict={'fontsize': 10})
            self.mainAxes.set_title(ob.filename + " " + "速度-周期曲线")
        # 公共纵坐标部分,暂时屏蔽
        self.fig.subplots_adjust(top=0.96, bottom=0.055, left=0.060, right=0.969, hspace=0.17, wspace=0.25)

    # 绘制坡度坐标轴信息
    def plotMainRampCord(self, ob=FileProcess, cmd=int, x_lim="tuple", y_lim="tuple"):
        self.mainAxes.axhline(y=0, xmin=0, xmax=1, color='black', ls='--', label = '平坡', linewidth=0.4) 

        if self.mainAxes.get_lines():
            self.mainAxes.legend(loc='upper left')
        if self.twinAxes.get_lines():
            self.twinAxes.legend(loc='upper right')
        self.mainAxes.set_ylabel('坡度值‰', fontdict={'fontsize': 10})
        self.fig.subplots_adjust(top=0.96, bottom=0.055, left=0.060, right=0.969, hspace=0.17, wspace=0.25)

    # 绘制级位曲线
    # cmd : 1=周期速度曲线 0=位置速度曲线
    def plotLogState(self, ob=FileProcess, cmd=int):
        # V-A 曲线
        if cmd == 0:
            p3 = self.twinAxes.plot(ob.s, ob.statmachine, markersize='0.8',color='darkkhaki', label='状态机')
        else:
            p3 = self.twinAxes.plot(ob.cycle, ob.statmachine, markersize='0.8', color='darkkhaki', label='状态机')
        self.twinAxes.set_ylabel('状态机')

    # 绘制对称坐标相关信息
    def plotTwinLevelCord(self, ob=FileProcess, cmd=int):
        if cmd == 0:
            self.mainAxes.set_xlim(ob.s[0], ob.s[len(ob.s) - 1])
            self.mainAxes.set_xlabel('列车位置cm',fontdict={'fontsize': 10})
            self.mainAxes.set_title(ob.filename)
            if self.mainAxes.get_lines():
                self.mainAxes.legend(loc='upper left')
        else:
            self.mainAxes.set_xlim(ob.cycle[0], ob.cycle[len(ob.cycle) - 1])
            self.mainAxes.set_xlabel('ATO周期', fontdict={'fontsize': 10})
            self.mainAxes.set_title(ob.filename + " " + "速度-周期曲线")
            if self.mainAxes.get_lines():
                self.mainAxes.legend(loc='upper left')

    # 使光标保持在画面之中，根据给定的数据点更新绘图范围
    def update_cord_with_cursor(self, data='tuple', x_lim='tuple', y_lim='tuple'):
        update_flag = 0
        # 初始化
        x_new_lim = [0, 0]
        y_new_lim = [0, 0]
        # 获取数据点
        data_x = data[0]
        data_y = data[1]
        # 调整X轴
        if data_x < x_lim[0]:
            left_offset = (x_lim[0] - data_x) + 0.5*(x_lim[1] - x_lim[0])  # 移到X轴中间
            x_new_lim[0] = x_lim[0] - left_offset   # x轴整体移动
            x_new_lim[1] = x_lim[1] - left_offset
            update_flag = 1
        elif data_x > x_lim[1]:
            right_offset = (data_x - x_lim[1]) + 0.5*(x_lim[1] - x_lim[0])  # 移到X轴中间
            x_new_lim[0] = x_lim[0] + right_offset  # x轴整体移动
            x_new_lim[1] = x_lim[1] + right_offset
            update_flag = 1
        else:
            x_new_lim[0] = x_lim[0]
            x_new_lim[1] = x_lim[1]
        # 调整y轴,考虑使用习惯采用不同的策略，固定最低显示（为了应答器等），只定量挪动上限，突出水平移动的效果
        if data_y < y_lim[0]:
            y_new_lim[1] = y_lim[1] - ((y_lim[0] - data_y) + 100)  # 固定多偏移100，移到屏幕内
            update_flag = 1
        elif data_y > y_lim[1]:
            y_new_lim[1] = y_lim[1] + ((data_y - y_lim[1]) + 100)
            update_flag = 1
        else:
            y_new_lim[1] = y_lim[1]
        y_new_lim[0] = -500

        return x_new_lim, y_new_lim, update_flag

    # 事件处理函数，响应FigureCanvas鼠标操作，发射光标追踪操作
    def right_press(self, event):
        global cursor_track_flag
        if event.button == 3:
            # 跳转这个值
            if cursor_track_flag == 0:
                cursor_track_flag = 1
                self.lock_signal.emit(cursor_track_flag)    # 右键锁定信号，待使用
            else:
                cursor_track_flag = 0                       # 0 是不追踪
                self.lock_signal.emit(cursor_track_flag)

    # 获取光标跟踪标志
    def get_track_status(self):
        global cursor_track_flag
        return cursor_track_flag

    # 设置光标跟踪标志
    def set_track_status(self):
        global cursor_track_flag
        cursor_track_flag = 0

    # 绘制控车气泡文本绘制
    def plot_ctrl_text(self, ob=FileProcess, pos_idx=int, text_pos_type=int, cmd=int):
        '''
        :param ob: 记录处理结果，含分析所需全部信息，可以直接在本函数计算需要显示的内容和数据
        :param pos_idx: 指示所处理的控车周期索引，内部顺序相对索引
        :param text_pos_type: 文本框摆放类型，1=跟随模式，0=停靠右上角
        :param cmd: 当前曲线类型，1=周期速度曲线 0=位置速度曲线
        :return:None
        '''

        self.mainAxes.texts.clear()    # 删除坐标轴文本信息
        # 越界防护
        if pos_idx < len(ob.s):
            # 根据曲线类型获取文本气泡坐标
            bubble_x = 0
            bubble_y = 0
            # 只在ATO速度曲线坐标上显示， cmd : 1=周期速度曲线 0=位置速度曲线
            if cmd == 0:
                bubble_x = ob.s[pos_idx]
                bubble_y = ob.v_ato[pos_idx]
            elif cmd == 1:
                bubble_x = ob.cycle[pos_idx]
                bubble_y = ob.v_ato[pos_idx]

            # 文本框内容字符串生成
            atppmt_ato_err = ob.atp_permit_v[pos_idx] - ob.v_ato[pos_idx]
            atocmd_ato_err = ob.cmdv[pos_idx] - ob.v_ato[pos_idx]
            atpcmd_ato_err = ob.ceilv[pos_idx] - ob.v_ato[pos_idx]
            stoppos_curpos_err = ob.stoppos[pos_idx] - ob.s[pos_idx]
            targetpos_curpos_err = ob.targetpos[pos_idx] - ob.s[pos_idx]
            ramp = ob.ramp[pos_idx]
            adj_ramp = ob.adjramp[pos_idx]

            if pos_idx > 0:
                delta_v = ob.v_ato[pos_idx] - ob.v_ato[pos_idx - 1]
            else:
                delta_v = ob.v_ato[pos_idx]

            # 设置报警色
            if atpcmd_ato_err > 0:
                paint_color = 'deepskyblue'
            else:
                paint_color = 'red'

            str_atppmt_ato_err = '距ATP允许速度:%d cm/s\n'%atppmt_ato_err
            str_atocmd_ato_err = '距ATO命令速度:%d cm/s\n'%atocmd_ato_err
            str_atpcmd_ato_err = '距ATP命令速度:%d cm/s\n'%atpcmd_ato_err
            str_stoppos_curpos_err = '距停车点:%d cm\n'%stoppos_curpos_err
            str_targetpos_curpos_err = '距目标点:%d cm\n'%targetpos_curpos_err
            str_ramp = '车头实际坡度:%d ‰\n'%ramp
            str_adj_ramp = '等效坡度:%d ‰\n' % adj_ramp
            str_delta_v = '相邻速度差:%d cm/s'%delta_v

            str_show = str_atppmt_ato_err + str_atocmd_ato_err + str_atpcmd_ato_err \
                    + str_stoppos_curpos_err + str_targetpos_curpos_err \
                    + str_ramp + str_adj_ramp \
                    + str_delta_v

            str_spd_sig = ob.cycle_dic[ob.cycle[pos_idx]].time+'\n'\
                        + '列车速度：%dcm/s'%ob.v_ato[pos_idx]+'\n'\
                        + '列车时速：%.2fkm/h'%((ob.v_ato[pos_idx]*9)/250)

            # 获取当前坐标轴范围，用以计算文本框的偏移比例
            cord_lim_x = self.mainAxes.get_xlim()
            cord_lim_y = self.mainAxes.get_ylim()

            x_delta = abs(cord_lim_x[1] - cord_lim_x[0])/100
            y_delta = abs(cord_lim_y[1] - cord_lim_y[0])/90

            #设置气泡显示，右下角
            bubble_x = bubble_x + x_delta  # 固定的右移动
            bubble_y = bubble_y + 6*y_delta  # 固定的上移动
            #右上角设置速度时间tag
            sig_x = bubble_x + x_delta  # 固定的右移动
            sig_y = bubble_y + y_delta  # 固定的下移动

            # 文本悬浮窗绘制位置类型，参考主框架定义 1=跟随模式，0=停靠右上角
            props_bubble = dict(boxstyle='round', facecolor=paint_color, alpha=0.15)
            props_sig = dict(facecolor=paint_color, edgecolor='none', alpha=0.02)

            # 设置显示速度信息
            self.mainAxes.text(sig_x, sig_y, str_spd_sig, fontsize=10, verticalalignment='top', bbox=props_sig)

            if 1 == text_pos_type:
                self.mainAxes.text(bubble_x, bubble_y, str_show,  fontsize=10, verticalalignment='top', bbox=props_bubble)
            elif 0 == text_pos_type:
                self.mainAxes.text(0.78, 0.95, str_show, transform=self.mainAxes.transAxes, fontsize=10, verticalalignment='top',
                                bbox=props_bubble)
            else:
                pass
        else:
            pass

    # 计算并设置事件绘制信息及标志
    def set_event_info_plot(self, event_dic='dict', cycle_dic='dict', pos_list='list', cycle_list='list'):
        """
        该函数主要按照事件字典说明，按照传入的周期列表和位置列表
        计算绘制事件需要的绘图列表，即“事件-周期/位置”列表
        由于周期字典是无序字典，所以索引无法用于周期列表，因此只能通过两个循环，
        单个循环中获得的顺序是字典的不能使用
        :param event_dic: 事件字典，指示绘制哪些事件
        :param cycle_dic: 周期列表，用于查询事件信息对应周期
        :param pos_list: 位置索引列表，用于生成位置图是需要，借助周期索引来查询
        :param cycle_list: 周期索引列表，是AOM控车下周期索引，用于建立其他信息查询的引用
        :return: None
        """
        # btm列表
        temp_pos_list_btm = []
        temp_cycle_list_btm = []
        # 无线列表
        temp_pos_list_wl = []
        temp_cycle_list_wl = []
        # jd列表
        temp_pos_list_jd = []
        temp_cycle_list_jd = []
        # 计划
        temp_pos_list_pl = []
        temp_cycle_list_pl = []

        self.event_plot_flag_dic = event_dic

        for k in event_dic.keys():
            if event_dic[k] == 1:       # 只要有为1的
                self.event_plot_flag = 1
                break
            else:
                self.event_plot_flag = 0
        # 貌似numpy 的array 天然取出时浮点
        map(int, cycle_list)
        # 当需要事件绘制时，该标志标明有需要绘制，无需一个一个查
        if self.event_plot_flag == 1:
            # 周期字典和周期列表中的周期都是int类型
            for idx, item_cycle in enumerate(cycle_list):
                # 应答器事件字典
                if event_dic['BTM'] == 1:
                    if cycle_dic[item_cycle].msg_atp2ato.sp7_obj.updateflag:
                        temp_cycle_list_btm.append(item_cycle)      # 直接添加周期号
                        temp_pos_list_btm.append(pos_list[idx])     # 添加对应位置
                # 无线事件字典
                if event_dic['WL'] == 1:
                    # 为了简化代码，和流程，不对所有周期检测，只检测AOR和AOM周期，即有SC的
                    if cycle_dic[item_cycle].msg_atp2ato.sp8_obj.updateflag:
                        temp_cycle_list_wl.append(item_cycle)  # 直接添加周期号
                        temp_pos_list_wl.append(pos_list[idx])  # 添加对应位置
                # JD应答器
                if event_dic['JD'] == 1:
                    if cycle_dic[item_cycle].msg_atp2ato.sp7_obj.updateflag:
                        if 13 == cycle_dic[item_cycle].msg_atp2ato.sp7_obj.nid_xuser:
                            temp_cycle_list_jd.append(item_cycle)  # 直接添加周期号
                            temp_pos_list_jd.append(pos_list[idx])  # 添加对应位置
                # 计划
                if event_dic['PLAN'] == 1:
                    if 41 in cycle_dic[item_cycle].cycle_sp_dict.keys():
                        temp_cycle_list_pl.append(item_cycle)  # 直接添加周期号
                        temp_pos_list_pl.append(pos_list[idx])  # 添加对应位置
                # 更新所有列表
                self.event_plot_dic['PLAN'] = (temp_pos_list_pl, temp_cycle_list_pl)  # 字典查询结果是两个列表
                self.event_plot_dic['JD'] = (temp_pos_list_jd, temp_cycle_list_jd)  # 字典查询结果是两个列表
                self.event_plot_dic['WL'] = (temp_pos_list_wl, temp_cycle_list_wl)  # 字典查询结果是两个列表
                self.event_plot_dic['BTM'] = (temp_pos_list_btm, temp_cycle_list_btm)  # 字典查询结果是两个列表

    # 绘制事件信息
    def plot_event_in_cords(self, cmd=int):
        # 需要绘图
        if self.event_plot_flag == 1:
            for k in self.event_plot_dic.keys():
                # 前期数据处理保证只要不为空就有位置和周期数据
                if self.event_plot_dic[k]:
                    if k == 'BTM' and self.event_plot_flag_dic['BTM'] == 1:
                        if cmd == 0:
                            self.mainAxes.scatter(self.event_plot_dic[k][0], [0]*len(self.event_plot_dic[k][0]),
                                               marker='^',label='应答器', color='gold')
                        else:
                            self.mainAxes.scatter(self.event_plot_dic[k][1], [0]*len(self.event_plot_dic[k][1]),
                                               marker='^', label='应答器', color='gold')

                    if k == 'JD' and self.event_plot_flag_dic['JD'] == 1:
                        if cmd == 0:
                            self.mainAxes.scatter(self.event_plot_dic[k][0], [0] * len(self.event_plot_dic[k][0]),
                                               marker='^', label='精定应答器', linewidth=3, color='Blue')
                        else:
                            self.mainAxes.scatter(self.event_plot_dic[k][1], [0] * len(self.event_plot_dic[k][1]),
                                               marker='^', label='精定应答器', linewidth=3, color='Blue')

                    if k == 'WL' and self.event_plot_flag_dic['WL'] == 1:
                        if cmd == 0:
                            self.mainAxes.scatter(self.event_plot_dic[k][0], [0] * len(self.event_plot_dic[k][0]),
                                               marker='D', label='无线呼叫命令', color='Peru')
                        else:
                            self.mainAxes.scatter(self.event_plot_dic[k][1], [0] * len(self.event_plot_dic[k][1]),
                                               marker='D', label='无线呼叫命令',  color='Peru')
                    if k == 'PLAN' and self.event_plot_flag_dic['PLAN'] == 1:
                        if cmd == 0:
                            self.mainAxes.scatter(self.event_plot_dic[k][0], [0] * len(self.event_plot_dic[k][0]),
                                               marker='*',label='运行计划数据',  color='Purple')
                        else:
                            self.mainAxes.scatter(self.event_plot_dic[k][1], [0] * len(self.event_plot_dic[k][1]),
                                               marker='*',label='运行计划数据', color='Purple')

    # 计算需要绘制标志的地方
    def set_wayside_info_in_cords(self, cycle_dic='dict', pos_list='list', cycle_list='list'):
        """
        该函数主要搜索绘制站台和分相区
        :param cycle_dic: 周期列表，用于查询事件信息对应周期
        :param pos_list: 位置索引列表，用于生成位置图是需要，借助周期索引来查询
        :param cycle_list: 周期索引列表，是AOM控车下周期索引，用于建立其他信息查询的引用
        :return: None
        """
        # gfx列表
        temp_pos_list_gfx = []
        temp_cycle_list_gfx = []
        # 站台列表
        temp_pos_list_stn = []
        temp_cycle_list_stn = []
        # 轨道电路列表
        temp_pos_list_tcr = []
        temp_cycle_list_tcr = []
        # 貌似numpy 的array 天然取出时浮点
        map(int, cycle_list)
        try:
        # 周期字典和周期列表中的周期都是int类型
            for idx, item_cycle in enumerate(cycle_list):
                # 应答器事件字典
                if 1 == cycle_dic[item_cycle].msg_atp2ato.sp2_obj.m_ms_cmd:
                    temp_cycle_list_gfx.append(item_cycle)  # 直接添加周期号
                    temp_pos_list_gfx.append(pos_list[idx])  # 添加对应位置
                # 改用控车使用的
                if cycle_dic[item_cycle].control:
                    if '1' == list(cycle_dic[item_cycle].control)[17]:
                        temp_cycle_list_stn.append(item_cycle)  # 直接添加周期号
                        temp_pos_list_stn.append(pos_list[idx])  # 添加对应位置
                # 更新所有列表
                self.wayside_plot_dic['GFX'] = (temp_pos_list_gfx, temp_cycle_list_gfx)  # 字典查询结果是两个列表
                self.wayside_plot_dic['STN'] = (temp_pos_list_stn, temp_cycle_list_stn)  # 字典查询结果是两个列表
        except Exception as err:
            print(err)
            print('wayside set err index is %d\n'%idx)

    # 绘制画图轨旁数据内容
    def plot_wayside_info_in_cords(self, ob=FileProcess, cmd=int):
        """
        绘制底部基础数据，初步考虑站台标志，分相的绘制
        :param ob: 文件读取对象
        :param cmd: 绘制周期图还是位置图
        :return:
        """
        try:
            if cmd == 0:
                self.mainAxes.scatter(self.wayside_plot_dic['STN'][0], [-350] * len(self.wayside_plot_dic['STN'][0]),
                                   marker='|', label='车站范围' ,color='k', s=100)

                self.mainAxes.scatter(self.wayside_plot_dic['GFX'][0], [-350] * len(self.wayside_plot_dic['GFX'][0]),
                                   marker='|', label='分相区范围',color='red', s=50)
            else:
                self.mainAxes.scatter(self.wayside_plot_dic['STN'][1], [-350] * len(self.wayside_plot_dic['STN'][1]),
                                   marker='|', label='车站范围', color='k', s=100)
                self.mainAxes.scatter(self.wayside_plot_dic['GFX'][1], [-350] * len(self.wayside_plot_dic['GFX'][1]),
                                   marker='|',label='分相区范围', color='red', s=50)
        except Exception as err:
            print(err)
            print('plot_wayside_info_in_cords error !')


# 实时画板类定义
class Figure_Canvas_R(FigureCanvas):
    def __init__(self, parent=None, width=20, height=10, dpi=100):
        self.fig = matplotlib.figure.Figure(figsize=(width, height), dpi=100, frameon=False)
        FigureCanvas.__init__(self, self.fig)  # 初始化父类函数
        self.fig.subplots_adjust(top=0.977, bottom=0.055, left=0.052, right=0.95, hspace=0.17, wspace=0.25)
        self.axes1 = self.fig.add_subplot(111)  # 画速度曲线
        self.setParent(parent)
        self.line_list = {}                     # 键值对存储曲线
        FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.ax1_twin = self.axes1.twinx()         # 级位
        self.choice = [0, 0, 0, 0, 0]              # 列车速度，ATO命令速度，ATP命令速度， ATP允许速度， 输出级位
        self.l_vato = []
        self.l_atocmdv = []
        self.l_atpcmdv = []
        self.l_atppmtv = []
        self.l_level = []
        self.init_realtime_plot(np.zeros([5, 10000]))
        self.bt = -500
        self.top = 10000

    # 更新绘制需求
    def updatePaintSet(self, ch='list'):
        # 进行处理
        if ch == self.choice:
            pass
        else:
            # 如果变化重置
            self.axes1.clear()
            self.ax1_twin.clear()
            # 更新
            self.choice = ch[:]
            self.init_realtime_plot(np.fliplr(RealTimeExtension.paintList))
        print(self.choice)

    # 重置绘图
    def init_realtime_plot(self, tmp):
        # 初始绘图获得曲线句柄
        if self.choice[0]:
            self.l_vato = self.axes1.plot(tmp[0, :], color='deeppink', linewidth=0.8, label='vato')
        if self.choice[1]:
            self.l_atocmdv = self.axes1.plot(tmp[1, :], color='green', linewidth=0.8, label='atocmdv')
        if self.choice[2]:
            self.l_atpcmdv = self.axes1.plot(tmp[2, :], color='orange', linewidth=0.8, label='atpcmdv')
        if self.choice[3]:
            self.l_atppmtv = self.axes1.plot(tmp[3, :], color='b', linewidth=0.8, label='atppmtv')
        if self.choice[4]:
            self.l_level = self.ax1_twin.plot(tmp[4, :], color='red', linewidth=0.8, label='level')
        #绘制档位辅助线
        self.ax1_twin.axhline(y=-1, xmin=0, xmax=1, color='black', ls='--', linewidth=0.7)  # B1 km/h
        self.ax1_twin.axhline(y=-2, xmin=0, xmax=1, color='black', ls='--', linewidth=0.5)  # B2 km/h
        self.ax1_twin.axhline(y=-3, xmin=0, xmax=1, color='black', ls='--', linewidth=0.5)  # B3 km/h
        self.ax1_twin.axhline(y=-4, xmin=0, xmax=1, color='black', ls='--', linewidth=0.7)  # B4 km/h
        self.ax1_twin.axhline(y=-5, xmin=0, xmax=1, color='black', ls='--', linewidth=0.5)  # B5 km/h
        self.ax1_twin.axhline(y=-6, xmin=0, xmax=1, color='black', ls='--', linewidth=0.5)  # B6 km/h
        self.ax1_twin.axhline(y=-7, xmin=0, xmax=1, color='black', ls='--', linewidth=0.7)  # B7 km/h
        self.ax1_twin.set_ylabel("ATO输出级位")
        # 当有曲线绘制时
        if sum(self.choice) > 0:
            #self.axes1.set_ylim(-100, 10000)
            self.ax1_twin.set_ylim(-8, 21)
            self.ax1_twin.set_yticks([-7, -6, -4, -3, -2, -1], minor=True)
            self.ax1_twin.set_yticklabels(['B7', 'B6', 'B4', 'B3', 'B2', 'B1'], fontdict={'fontsize': 8}, minor=True)
            self.axes1.legend(loc='upper left')
            # 只有选中级位才能更新这个
            if self.choice[4]:
                self.ax1_twin.legend(loc='upper right')

    # 实时绘制曲线
    def realTimePlot(self):
        """
        根据指示绘制图，由外界选择
        :param choice: 1=绘制，0=不绘制 [Vato,Vatocmd,Vatpcmd,Level]
        :return: None
        """
        tmp = np.fliplr(RealTimeExtension.paintList)
        # 重置曲线
        if self.choice[0] == 1:
            self.l_vato[0].set_ydata(tmp[0, :])
        if self.choice[1] == 1:
            self.l_atocmdv[0].set_ydata(tmp[1, :])
        if self.choice[2] == 1:
            self.l_atpcmdv[0].set_ydata(tmp[2, :])
        if self.choice[3] == 1:
            self.l_atppmtv[0].set_ydata(tmp[3, :])
        if self.choice[4] == 1:
            self.l_level[0].set_ydata(tmp[4, :])

        self.axes1.relim()  # 重新计算坐标轴限制
        self.axes1.autoscale_view(scalex=False, scaley=True)   # 重新适应纵轴
        self.draw_idle()


