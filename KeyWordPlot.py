import FileProcess
import matplotlib
from PyQt5 import QtCore, QtGui, QtWidgets
matplotlib.use("Qt5Agg")  # 声明使用QT5
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
plt.rcParams['axes.unicode_minus'] = False        # 解决Matplotlib绘图中，负号不正常显示问题
from pylab import *                             # 解决matplotlib绘图，汉字显示不正常的问题
mpl.rcParams['font.sans-serif'] = ['SimHei']


cursor_track_flag = 1   # 1=追踪，0=不追踪


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
        # print('x=%1.2f, y=%1.2f' % (x, y))
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

    # 对于速度绘制区分模式，标注模式下绘点，否则直连线
    # mod : 1=标注模式 0=浏览模式
    # cmd : 1=周期速度曲线 0=位置速度曲线
    def plotlog_vs(self, ob=FileProcess, mod=int, cmd=int):
        if mod == 1:
            if cmd == 0:   # 位置速度曲线
                self.axes1.plot(ob.s, ob.v_ato, markersize=1.2, marker='.', color='deeppink', label="V_ATO", linewidth=1)
            else:           # 周期速度曲线
                self.axes1.plot(ob.cycle, ob.v_ato, markersize=1.2, marker='.', color='deeppink', label="V_ATO", linewidth=1)
        else:
            if cmd == 0:
                self.axes1.plot(ob.s, ob.v_ato, color='deeppink', label="V_ATO", linewidth=1)
            else:
                p1 = self.axes1.plot(ob.cycle, ob.v_ato, color='deeppink', label="V_ATO", linewidth=1)

    # 对命令于速度绘制区分模式，标注模式下绘点，否则直连线
    # mod : 1=标注模式 0=浏览模式
    # cmd : 1=周期速度曲线 0=位置速度曲线
    def plotlog_vcmdv(self, ob=FileProcess, mod=int, cmd=int):
        if mod == 1:
            if cmd == 0:    # 位置速度曲线
                self.axes1.plot(ob.s, ob.cmdv, marker='.', markersize=1.2, color='green', label="CMDV", linewidth=1)
            else:
                self.axes1.plot(ob.cycle, ob.cmdv, marker='.', markersize=1.2, color='green', label="CMDV", linewidth=1)
        else:
            if cmd == 0:
                self.axes1.plot(ob.s, ob.cmdv, color='green', label="ATOCMDV", linewidth=1)
            else:
                self.axes1.plot(ob.cycle, ob.cmdv, color='green', label="ATOCMDV", linewidth=1)

    # 绘制ATP命令速度曲线（含义改变但名称保留）
    # cmd : 1=周期速度曲线 0=位置速度曲线
    def plotlog_vceil(self, ob=FileProcess, cmd=int):
        if cmd == 0:
            self.axes1.plot(ob.s, ob.ceilv, color='orange', label="ATPCMDV", linewidth=1)
        else:
            self.axes1.plot(ob.cycle, ob.ceilv, color='orange', label="ATPCMDV", linewidth=1)

    # 绘制级位曲线
    # cmd : 1=周期速度曲线 0=位置速度曲线
    def plotlog_level(self, ob=FileProcess, cmd=int):
        if cmd == 0:
            self.ax1_twin.plot(ob.s, ob.level, color='crimson', label='Level', linewidth=0.5)
        else:
            self.ax1_twin.plot(ob.cycle, ob.level, color='crimson', label='Level', linewidth=0.5)

    # paint the pos-speed axes
    def plot_cord1(self, ob=FileProcess, cmd=int, x_lim=tuple, y_lim=tuple):
        # paint the speed ruler
        self.axes1.axhline(y=1250, xmin=0, xmax=1, color='k', ls='--',        # xmin and xmax Should be between 0 and 1,
                           linewidth=0.8)  # 45km/h                           #  0 being the far left of the plot,
        self.axes1.axhline(y=9722, xmin=0, xmax=1, color='k', ls='dashed',    # 1 the far right of the plot
                           linewidth=0.8)  # 350km/h
        self.axes1.axhline(y=2222, xmin=0, xmax=1, color='k', ls='dashed',
                           linewidth=0.8)  # 80km/h
        # 绘制位置速度坐标系
        if cmd == 0:
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

    def plotlog_sa(self, ob=FileProcess, cmd=int):
        # V-A 曲线
        if cmd == 0:
            p3 = self.axes1.plot(ob.s, ob.a, markersize='0.8',color='darkkhaki', label='Acc')
        else:
            p3 = self.axes1.plot(ob.cycle, ob.a, markersize='0.8', color='darkkhaki', label='Acc')
        self.axes1.set_ylabel('列车加速度')

    def plotlog_ramp(self, ob=FileProcess, cmd=int):
        #  S-RAMP 曲线
        if cmd == 0:
            self.axes1.plot(ob.s, ob.ramp, 'c-', markersize=0.5 ,label='Ramp', linewidth=0.5)
        else:
            self.axes1.plot(ob.cycle, ob.ramp, 'c-', label='Ramp', linewidth=0.5)
        self.axes1.set_ylabel('线路坡度')

    # paint the pos-acc axes
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

    def get_track_status(self):
        global cursor_track_flag
        return cursor_track_flag

    def set_track_status(self):
        global cursor_track_flag
        cursor_track_flag = 0