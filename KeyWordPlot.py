import os
import FileProcess
import matplotlib
from PyQt5 import QtCore, QtGui, QtWidgets
matplotlib.use("Qt5Agg")  # 声明使用QT5
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
plt.rcParams['axes.unicode_minus'] = False        #解决Matplotlib绘图中，负号不正常显示问题
from pylab import *                             #解决matplotlib绘图，汉字显示不正常的问题
mpl.rcParams['font.sans-serif'] = ['SimHei']


class SnaptoCursor(object):
    """ Like Cursor but the crosshair snaps to the nearest x,y point For simplicity, I'm assuming x is sorted """
def __init__(self, ax, x, y):
    self.ax = ax
    self.lx = ax.axhline(color='k') # the horiz line
    self.ly = ax.axvline(color='k') # the vert line
    self.x = x
    self.y = y
    # text location in axes coords
    # self.txt = self.ax.text(0.7, 0.9, '', transform = self.ax.transAxes)

def mouse_move(self, event):
    if not event.inaxes:
        return
    x, y = event.xdata, event.ydata

    indx = min(np.searchsorted(self.x, [x])[0], len(self.x) - 1)
    x = self.x[indx]
    y = self.y[indx]
    # update the line positions
    self.lx.set_ydata(y)
    self.ly.set_xdata(x)

    self.txt.set_text('x=%1.2f, y=%1.2f' % (x, y))
    print('x=%1.2f, y=%1.2f' % (x, y))
    self.draw()


class Figure_Canvas(FigureCanvas):   # 通过继承FigureCanvas类，使得该类既是一个PyQt5的Qwidget，又是一个matplotlib的FigureCanvas，这是连接pyqt5与matplot                                          lib的关键
    def __init__(self, parent=None, width=20, height=10, dpi=100):
        self.fig = plt.figure(figsize=(width, height), dpi=100, frameon=False) # 创建一个Figure，注意：该Figure为matplotlib下的figure，不是matplotlib.pyplot下面的figure
        self.fig.subplots_adjust(top=0.96,bottom=0.075,left=0.045,right=0.96, hspace=0.185,wspace=0.25)
        self.axes1 = self.fig.add_subplot(111)
        FigureCanvas.__init__(self,self.fig) #初始化父类函数
        self.setParent(parent)
        self.line_list = {}               #键值对存储曲线
        FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.ax1_twin = self.axes1.twinx()

    def plotlog_vs(self, ob=FileProcess):
        p1 = self.axes1.plot(ob.s, ob.v_ato,color='deeppink',label="V_ATO", linewidth=1)
        # c = SnaptoCursor(self.axes1, ob.s, ob.v_ato)
        # self.mpl_connect('motion_notify_event', c.mouse_move)

    def plotlog_vceil(self, ob=FileProcess):
        p2 = self.axes1.plot(ob.s, ob.ceilv,color='orange',label="CEILV", linewidth=1)

    def plotlog_vcmdv(self, ob=FileProcess):
        p2 = self.axes1.plot(ob.s, ob.cmdv, color='green' ,label="CMDV", linewidth=1)

    def plotlog_level(self, ob=FileProcess):
        self.ax1_twin.plot(ob.s, ob.level,color='crimson',label='Level', linewidth=0.5)

    def plot_cord1(self, ob=FileProcess):
        self.axes1.set_xlabel('Train pos cm')
        self.axes1.set_ylabel('Train speed cm/s')
        self.axes1.set_title(ob.filename)
        self.axes1.legend(loc='upper left')
        self.ax1_twin.legend(loc='center level')
        self.axes1.grid(True, color="k")

    def plotlog_sa(self, ob=FileProcess):
        # # V-A 曲线
        p3 = self.axes1.plot(ob.s, ob.a, color='darkkhaki',label='Acc')
        self.axes1.set_xlabel('Train pos cm')
        self.axes1.set_ylabel('Train acc cm/s^2')
        self.axes1.legend(loc='upper right')
        self.axes1.grid(True, color="k")

    def plotlog_ramp(self, ob=FileProcess):
        #  S-RAMP 曲线
        p3 = self.axes1.plot(ob.s, ob.ramp,'c-',label='Ramp', linewidth=0.5)

    def plot_cord2(self, ob=FileProcess):
        self.axes1.set_xlabel('Train pos cm')
        self.axes1.set_ylabel('Train ramp ')
        self.axes1.legend(loc='upper left')
        self.axes1.grid(True, color="k")
