import FileProcess
import matplotlib
import RealTimeExtension
import threading
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
matplotlib.use("Qt5Agg")  # 声明使用QT5
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
plt.rcParams['axes.unicode_minus'] = False        # 解决Matplotlib绘图中，负号不正常显示问题
from pylab import *                             # 解决matplotlib绘图，汉字显示不正常的问题
mpl.rcParams['font.sans-serif'] = ['SimHei']


cursor_track_flag = 1   # 1=追踪，0=不追踪
Lock = threading.Lock()

# 光标类定义
class SnaptoCursor(QtCore.QObject):
    """ Like Cursor but the crosshair snaps to the nearest x,y point For simplicity, I'm assuming x is sorted """
    move_signal = QtCore.pyqtSignal(int)        # 带一个参数的信号
    sim_move_singal = QtCore.pyqtSignal(int)    # 模拟手动挪动光标

    def __init__(self, sp, ax, x, y):
        super(SnaptoCursor, self).__init__()
        self.fmpl = sp
        self.ax = ax
        self.ax.set_xlim(x[0], x[len(x)-1])  # 默认与不带光标统一的显示范围
        self.ax.set_ylim(-200, 10000)
        self.lx = sp.axes1.axhline(color='k', linewidth=0.8, ls='dashdot')  # the horiz line, now only keep vert
        self.ly = sp.axes1.axvline(color='k', linewidth=0.8, ls='dashdot')  # the vert line
        self.x = x
        self.y = y
        # use for record key words
        self.data_x = 0
        self.data_y = 0
        self.nearest_index = 0
    # text location in axes coords

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
        indx = min(np.searchsorted(self.x, [x])[0], len(self.x) - 1)
        # update record data and index for return
        self.data_x = x
        self.data_y = y
        self.nearest_index = indx
        # nearest data 这是数据
        x = self.x[indx]
        y = self.y[indx]
        # update the line positions
        if cursor_track_flag == 1:          # 看标志追踪
            y = self.y[indx]
            self.lx.set_ydata(y)
            self.ly.set_xdata(x)
            # print('x=%1.2f, y=%1.2f' % (x, y))
            self.fmpl.draw()
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
        # update the line positions
        self.lx.set_ydata(y)
        self.ly.set_xdata(x)
        print('x=%1.2f, y=%1.2f' % (x, y))
        self.fmpl.draw()
        # 发射信号
        self.sim_move_singal.emit(indx)  # 发射信号索引

    def reset_cursor_plot(self):
        global cursor_track_flag
        cursor_track_flag = 1


# 画板类定义
class Figure_Canvas(FigureCanvas):   # 通过继承FigureCanvas类，使得该类既是一个PyQt5的Qwidget，又是一个matplotlib
                                     # 的FigureCanvas，这是连接pyqt5与matplotlib的关键
    lock_signal = QtCore.pyqtSignal(int)  # 这个参数用于提醒锁定光标

    def __init__(self, parent=None, width=20, height=10, dpi=100):
        self.fig = plt.figure(figsize=(width, height), dpi=100, frameon=False)  # 创建一个Figure，注意：该Figure为
                                                                                # matplotlib下的figure，不是matplotlib
                                                                                # pyplot下面的figure
        self.fig.subplots_adjust(top=0.952, bottom=0.095, left=0.064, right=0.954, hspace=0.17, wspace=0.25)
        self.axes1 = self.fig.add_subplot(111)
        FigureCanvas.__init__(self,self.fig)    # 初始化父类函数
        self.setParent(parent)
        self.line_list = {}                     # 键值对存储曲线
        FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.ax1_twin = self.axes1.twinx()
        # 事件绘制字典,存储每个需要绘制的列表，列表是tuple类型
        self.event_plot_dic = {}
        self.event_plot_flag = 0                 # 事件绘制标志
        self.event_plot_flag_dic = {}            # 指定绘制

    # 对于速度绘制区分模式，标注模式下绘点，否则直连线
    # mod : 1=标注模式 0=浏览模式
    # cmd : 1=周期速度曲线 0=位置速度曲线
    def plotlog_vs(self, ob=FileProcess, mod=int, cmd=int):
        if mod == 1:
            if cmd == 0:   # 位置速度曲线
                self.axes1.plot(ob.s, ob.v_ato, markersize=1.2, marker='.', color='deeppink', label="ATO当前速度", linewidth=1)
            else:           # 周期速度曲线
                self.axes1.plot(ob.cycle, ob.v_ato, markersize=1.2, marker='.', color='deeppink', label="ATO当前速度", linewidth=1)
        else:
            if cmd == 0:
                self.axes1.plot(ob.s, ob.v_ato, color='deeppink', label="ATO当前速度", linewidth=1)
            else:
                p1 = self.axes1.plot(ob.cycle, ob.v_ato, color='deeppink', label="ATO当前速度", linewidth=1)

    # 对命令于速度绘制区分模式，标注模式下绘点，否则直连线
    # mod : 1=标注模式 0=浏览模式
    # cmd : 1=周期速度曲线 0=位置速度曲线
    def plotlog_vcmdv(self, ob=FileProcess, mod=int, cmd=int):
        if mod == 1:
            if cmd == 0:    # 位置速度曲线
                self.axes1.plot(ob.s, ob.cmdv, marker='.', markersize=1.2, color='green', label="ATO命令速度", linewidth=1)
            else:
                self.axes1.plot(ob.cycle, ob.cmdv, marker='.', markersize=1.2, color='green', label="ATO命令速度", linewidth=1)
        else:
            if cmd == 0:
                self.axes1.plot(ob.s, ob.cmdv, color='green', label="ATO命令速度", linewidth=1)
            else:
                self.axes1.plot(ob.cycle, ob.cmdv, color='green', label="ATO命令速度", linewidth=1)

    # 绘制ATP命令速度曲线（含义改变但名称保留）
    # cmd : 1=周期速度曲线 0=位置速度曲线
    def plotlog_vceil(self, ob=FileProcess, cmd=int):
        if cmd == 0:
            self.axes1.plot(ob.s, ob.ceilv, color='orange', label="ATP命令速度", linewidth=1)
        else:
            self.axes1.plot(ob.cycle, ob.ceilv, color='orange', label="ATP命令速度", linewidth=1)

    # 对于ATP允许速度绘制区分模式，标注模式下绘点，否则直连线
    # mod : 1=标注模式 0=浏览模式
    # cmd : 1=周期速度曲线 0=位置速度曲线
    def plotlog_v_atp_pmt_s(self, ob=FileProcess, mod=int, cmd=int):
        if cmd == 0:  # 位置速度曲线
            self.axes1.plot(ob.s, ob.atp_permit_v, color='b', label="ATP允许速度", linewidth=1)
        else:  # 周期速度曲线
            self.axes1.plot(ob.cycle,ob.atp_permit_v, color='b', label="ATP允许速度", linewidth=1)

    # 绘制级位曲线
    # cmd : 1=周期速度曲线 0=位置速度曲线
    def plotlog_level(self, ob=FileProcess, cmd=int):
        if cmd == 0:
            self.ax1_twin.plot(ob.s, ob.level, color='crimson', label='ATO输出级位', linewidth=0.5)
        else:
            self.ax1_twin.plot(ob.cycle, ob.level, color='crimson', label='ATO输出级位', linewidth=0.5)

    # 绘制速度坐标轴相关信息
    def plot_cord1(self, ob=FileProcess, cmd=int, x_lim=tuple, y_lim=tuple):
        # paint the speed ruler
        self.axes1.axhline(y=1250, xmin=0, xmax=1, color='darkblue', ls='--',        # xmin and xmax Should be between 0 and 1,
                           linewidth=1)  # 45km/h                           #  0 being the far left of the plot,
        self.axes1.axhline(y=9722, xmin=0, xmax=1, color='darkblue', ls='dashed',    # 1 the far right of the plot
                           linewidth=1)  # 350km/h
        self.axes1.axhline(y=2222, xmin=0, xmax=1, color='darkblue', ls='dashed',
                           linewidth=1)  # 80km/h
        # 绘制位置速度坐标系
        if cmd == 0:
            self.plot_event_in_cords(cmd)
            # 如果绘图范围是默认值，还没有绘图，是默认路径
            if x_lim == (0.0, 1.0) and y_lim == (0.0, 1.0):
                self.axes1.set_xlim(ob.s[0], ob.s[len(ob.s) - 1])  # 由于绘制直线会从0开始绘制，这里重置范围
                self.axes1.set_ylim(-200, 10000)
            else:
                self.axes1.set_xlim(x_lim[0], x_lim[1])
                self.axes1.set_ylim(y_lim[0], y_lim[1])
            self.axes1.set_xlabel('列车位置cm')
            self.axes1.set_ylabel('列车速度cm/s')
            self.axes1.set_title(ob.filename+" "+"速度-位置曲线")
        else:
            self.plot_event_in_cords(cmd)
            if x_lim == (0.0, 1.0) and y_lim == (0.0, 1.0):
                self.axes1.set_xlim(ob.cycle[0], ob.cycle[len(ob.cycle) - 1])  # 重置范围
                self.axes1.set_ylim(-200, 10000)
            else:
                self.axes1.set_xlim(x_lim[0], x_lim[1])
                self.axes1.set_ylim(y_lim[0], y_lim[1])
            self.axes1.set_xlabel('ATO周期')
            self.axes1.set_ylabel('列车速度cm/s')
            self.axes1.set_title(ob.filename + " " + "速度-周期曲线")
        # 公共绘制部分
        self.axes1.legend(loc='upper left')
        if self.ax1_twin.get_lines():
            self.ax1_twin.legend(loc='upper right')
        self.fig.subplots_adjust(top=0.977, bottom=0.055, left=0.049, right=0.969, hspace=0.17, wspace=0.25)

    # 绘制加速度相关信息
    def plotlog_sa(self, ob=FileProcess, cmd=int):
        # V-A 曲线
        if cmd == 0:
            p3 = self.axes1.plot(ob.s, ob.a, markersize='0.8',color='darkkhaki', label='加速度')
        else:
            p3 = self.axes1.plot(ob.cycle, ob.a, markersize='0.8', color='darkkhaki', label='加速度')
        self.axes1.set_ylabel('列车加速度')

    # 绘制坡度相关信息
    def plotlog_ramp(self, ob=FileProcess, cmd=int):
        #  S-RAMP 曲线
        if cmd == 0:
            self.axes1.plot(ob.s, ob.ramp, 'c-', markersize=0.5 ,label='坡度数据', linewidth=0.5)
        else:
            self.axes1.plot(ob.cycle, ob.ramp, 'c-', label='坡度数据', linewidth=0.5)
        self.axes1.set_ylabel('线路坡度')

    # 绘制对称坐标相关信息
    def plot_cord2(self, ob=FileProcess, cmd=int):
        if cmd == 0:
            self.axes1.set_xlim(ob.s[0], ob.s[len(ob.s) - 1])
            self.axes1.set_xlabel('列车位置cm')
            self.axes1.set_title(ob.filename)
            if self.axes1.get_lines():
                self.axes1.legend(loc='upper left')
        else:
            self.axes1.set_xlim(ob.cycle[0], ob.cycle[len(ob.cycle) - 1])
            self.axes1.set_xlabel('ATO周期')
            self.axes1.set_title(ob.filename + " " + "速度-周期曲线")
            if self.axes1.get_lines():
                self.axes1.legend(loc='upper left')

    # 使光标保持在画面之中，根据给定的数据点更新绘图范围
    def update_cord_with_cursor(self, data=tuple, x_lim=tuple, y_lim=tuple):
        update_flag = 0
        # 初始化
        x_new_lim = [0, 0]
        y_new_lim = [0, 0]
        # 获取数据点
        data_x = data[0]
        data_y = data[1]
        # 调整X轴
        if data_x < x_lim[0]:
            x_new_lim[0] = x_lim[0] - 4*(x_lim[0] - data_x)   # x轴整体移动
            x_new_lim[1] = x_lim[1] - 4*(x_lim[0] - data_x)
            update_flag = 1
        elif data_x > x_lim[1]:
            x_new_lim[0] = x_lim[0] + 4*(data_x - x_lim[1])  # x轴整体移动
            x_new_lim[1] = x_lim[1] + 4*(data_x - x_lim[1])
            update_flag = 1
        else:
            x_new_lim[0] = x_lim[0]
            x_new_lim[1] = x_lim[1]
        # 调整y轴
        if data_y < y_lim[0]:
            y_new_lim[0] = y_lim[0] - 4*(y_lim[0] - data_y)  # y轴整体移动
            y_new_lim[1] = y_lim[1] - 4*(y_lim[0] - data_y)
            update_flag = 1
        elif data_y > y_lim[1]:
            y_new_lim[0] = y_lim[0] + 4*(data_y - y_lim[1])  # y轴整体移动
            y_new_lim[1] = y_lim[1] + 4*(data_y - y_lim[1])
            update_flag = 1
        else:
            y_new_lim[0] = y_lim[0]
            y_new_lim[1] = y_lim[1]
        return x_new_lim, y_new_lim , update_flag

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

        self.axes1.texts.clear()    # 删除坐标轴文本信息

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

        # 获取当前坐标轴范围，用以计算文本框的偏移比例
        cord_lim_x = self.axes1.get_xlim()
        cord_lim_y = self.axes1.get_ylim()

        x_delta = abs(cord_lim_x[1] - cord_lim_x[0])/60
        y_delta = abs(cord_lim_y[1] - cord_lim_y[0])/48

        bubble_x = bubble_x + x_delta  # 右移动
        bubble_y = bubble_y - y_delta  # 下移动

        # 文本悬浮窗绘制位置类型，参考主框架定义 1=跟随模式，0=停靠右上角
        props = dict(boxstyle='round', facecolor=paint_color, alpha=0.15)

        if 1 == text_pos_type:
            self.axes1.text(bubble_x, bubble_y, str_show,  fontsize=10, verticalalignment='top', bbox=props)
        elif 0 == text_pos_type:
            self.axes1.text(0.78, 0.93, str_show, transform=self.axes1.transAxes, fontsize=10, verticalalignment='top',
                            bbox=props)
        else:
            pass


    # 计算并设置事件绘制信息及标志
    def set_event_info_plot(self, event_dic=dict, cycle_dic=dict, pos_list=list, cycle_list=list):
        '''
        该函数主要按照事件字典说明，按照传入的周期列表和位置列表
        计算绘制事件需要的绘图列表，即“事件-周期/位置”列表
        由于周期字典是无序字典，所以索引无法用于周期列表，因此只能通过两个循环，
        单个循环中获得的顺序是字典的不能使用
        :param event_dic: 事件字典，指示绘制哪些事件
        :param cycle_dic: 周期列表，用于查询事件信息对应周期
        :param pos_list: 位置索引列表，用于生成位置图是需要，借助周期索引来查询
        :param cycle_list: 周期索引列表，是AOM控车下周期索引，用于建立其他信息查询的引用
        :return: None
        '''

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
            # 应答器事件字典
            if event_dic['BTM'] == 1:
                temp_pos_list = []
                temp_cycle_list = []
                # 周期字典和周期列表中的周期都是int类型
                for idx, item_cycle in enumerate(cycle_dic.keys()):
                    if 7 in cycle_dic[item_cycle].cycle_sp_dict.keys():
                        temp_cycle_list.append(item_cycle)      # 直接添加周期号
                # 位置信息不一定有，在只使用SC打印时
                for idx, item_cycle in enumerate(cycle_list):
                    if 7 in cycle_dic[item_cycle].cycle_sp_dict.keys():
                        temp_pos_list.append(pos_list[idx])     # 添加对应位置
                self.event_plot_dic['BTM'] = (temp_pos_list, temp_cycle_list)    # 字典查询结果是两个列表

            # 无线事件字典
            if event_dic['WL'] == 1:
                temp_pos_list = []
                temp_cycle_list = []
                # 周期字典和周期列表中的周期都是int类型
                for idx, item_cycle in enumerate(cycle_dic.keys()):
                    if 8 in cycle_dic[item_cycle].cycle_sp_dict.keys():
                        temp_cycle_list.append(item_cycle)  # 直接添加周期号
                for idx, item_cycle in enumerate(cycle_list):
                    if 8 in cycle_dic[item_cycle].cycle_sp_dict.keys():
                        temp_pos_list.append(pos_list[idx])  # 添加对应位置
                self.event_plot_dic['WL'] = (temp_pos_list, temp_cycle_list)  # 字典查询结果是两个列表

            # JD应答器
            if event_dic['JD'] == 1:
                temp_pos_list = []
                temp_cycle_list = []
                # 周期字典和周期列表中的周期都是int类型
                for idx, item_cycle in enumerate(cycle_dic.keys()):
                    if 7 in cycle_dic[item_cycle].cycle_sp_dict.keys():
                        if '13' == cycle_dic[item_cycle].cycle_sp_dict[7][3].strip():
                            temp_cycle_list.append(item_cycle)  # 直接添加周期号
                for idx, item_cycle in enumerate(cycle_list):
                    if 7 in cycle_dic[item_cycle].cycle_sp_dict.keys():
                        if '13' == cycle_dic[item_cycle].cycle_sp_dict[7][3].strip():
                            temp_pos_list.append(pos_list[idx])  # 添加对应位置
                self.event_plot_dic['JD'] = (temp_pos_list, temp_cycle_list)  # 字典查询结果是两个列表


            # 计划
            if event_dic['PLAN'] == 1:
                temp_pos_list = []
                temp_cycle_list = []
                # 周期字典和周期列表中的周期都是int类型
                for idx, item_cycle in enumerate(cycle_dic.keys()):
                    if 41 in cycle_dic[item_cycle].cycle_sp_dict.keys():
                        temp_cycle_list.append(item_cycle)  # 直接添加周期号
                for idx, item_cycle in enumerate(cycle_list):
                    if 41 in cycle_dic[item_cycle].cycle_sp_dict.keys():
                        temp_pos_list.append(pos_list[idx])  # 添加对应位置
                self.event_plot_dic['PLAN'] = (temp_pos_list, temp_cycle_list)  # 字典查询结果是两个列表


    # 绘制事件信息
    def plot_event_in_cords(self, cmd=int):
        # 需要绘图
        if self.event_plot_flag == 1:
            for k in self.event_plot_dic.keys():
                # 前期数据处理保证只要不为空就有位置和周期数据
                if self.event_plot_dic[k] != []:
                    if k == 'BTM' and self.event_plot_flag_dic['BTM'] == 1:
                        if cmd == 0:
                            self.axes1.scatter(self.event_plot_dic[k][0], [0]*len(self.event_plot_dic[k][0]),
                                               marker='^',color='gold')
                        else:
                            self.axes1.scatter(self.event_plot_dic[k][1], [0]*len(self.event_plot_dic[k][1]),
                                               marker='^', color='gold')

                    if k == 'JD' and self.event_plot_flag_dic['JD'] == 1:
                        if cmd == 0:
                            self.axes1.scatter(self.event_plot_dic[k][0], [0] * len(self.event_plot_dic[k][0]),
                                               marker='^', linewidth=3, color='Blue')
                        else:
                            self.axes1.scatter(self.event_plot_dic[k][1], [0] * len(self.event_plot_dic[k][1]),
                                               marker='^',linewidth=3, color='Blue')

                    if k == 'WL' and self.event_plot_flag_dic['WL'] == 1:
                        if cmd == 0:
                            self.axes1.scatter(self.event_plot_dic[k][0], [0] * len(self.event_plot_dic[k][0]),
                                               marker='D', color='Peru')
                        else:
                            self.axes1.scatter(self.event_plot_dic[k][1], [0] * len(self.event_plot_dic[k][1]),
                                               marker='D', color='Peru')
                    if k == 'PLAN' and self.event_plot_flag_dic['PLAN'] == 1:
                        if cmd == 0:
                            self.axes1.scatter(self.event_plot_dic[k][0], [0] * len(self.event_plot_dic[k][0]),
                                               marker='*', color='Purple')
                        else:
                            self.axes1.scatter(self.event_plot_dic[k][1], [0] * len(self.event_plot_dic[k][1]),
                                               marker='*', color='Purple')


# 实时画板类定义
class Figure_Canvas_R(FigureCanvas):
    def __init__(self, parent=None, width=20, height=10, dpi=100):
        self.fig = plt.figure(figsize=(width, height), dpi=100, frameon=False)
        FigureCanvas.__init__(self, self.fig)  # 初始化父类函数
        self.fig.subplots_adjust(top=0.977, bottom=0.055, left=0.040, right=0.96, hspace=0.17, wspace=0.25)
        self.axes1 = self.fig.add_subplot(111)  # 画速度曲线
        self.setParent(parent)
        self.line_list = {}                     # 键值对存储曲线
        FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.ax1_twin = self.axes1.twinx()         # 级位
        self.choice = [0, 0, 0, 0]                 # 全部绘制


    # 更新绘制需求
    def updatePaintSet(self, ch=list):
        self.choice[0] = ch[0]
        self.choice[1] = ch[1]
        self.choice[2] = ch[2]
        self.choice[3] = ch[3]
        print(self.choice)

    # 实时绘制曲线
    def realTimePlot(self):
        '''
        根据指示绘制图，由外界选择
        :param choice: 1=绘制，0=不绘制 [Vato,Vatocmd,Vatpcmd,Level]
        :return: None
        '''
        self.ax1_twin.clear()
        self.axes1.clear()
        Lock.acquire()
        tmp = np.fliplr(RealTimeExtension.paintList)
        if self.choice[0] == 1:
            self.axes1.plot(tmp[0, :], color='deeppink', linewidth=0.8)
        if self.choice[1] == 1:
            self.axes1.plot(tmp[1, :], color='green', linewidth=0.8)
        if self.choice[2] == 1:
            self.axes1.plot(tmp[2, :], color='orange', linewidth=0.8)
        if self.choice[3] == 1:
            self.ax1_twin.plot(tmp[3, :], color='b', linewidth=0.8)
        Lock.release()
        self.axes1.set_ylim(0, 10000)
        self.ax1_twin.set_ylim(-7, 10)
        self.axes1.legend(['ato',' atocmdv', 'atpcmdv', 'level'])