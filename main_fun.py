import FileProcess
import KeyWordPlot
import numpy as np
import time
from PyQt5 import QtWidgets, QtCore, QtGui
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
import matplotlib.cbook as cbook
from matplotlib.widgets import MultiCursor, Cursor
from LogMainWin import Ui_MainWindow
import sys
from  KeyWordPlot import Figure_Canvas
import matplotlib.pyplot as plt
from numpy import arange, sin, pi


class Mywindow(QtWidgets.QMainWindow, Ui_MainWindow):
    #全局静态变量
    load_flag = 0
    # 建立的是Main Window项目，故此处导入的是QMainWindow
    def __init__(self):
        super(Mywindow, self).__init__()
        self.setupUi(self)
        self.initUI()
        self.file = ''
        self.pathlist = []
        self.mode = 0          # 默认0是浏览模式，1是标注模式
        self.resize(900, 600)
        self.setWindowTitle('LogPlot-V0.4')
        self.setWindowIcon(QtGui.QIcon('./IconFiles/h4.ico'))
        l = QtWidgets.QVBoxLayout(self.widget)
        self.sp = Figure_Canvas(self.widget)        #这是继承FigureCanvas的子类，使用子窗体widget作为父亲类
        self.sp.mpl_toolbar = NavigationToolbar(self.sp, self.widget)  # 传入FigureCanvas类或子类实例，和父窗体
        l.addWidget(self.sp)
        l.addWidget(self.sp.mpl_toolbar)
        self.widget.setFocus()
        self.fileOpen.triggered.connect(self.showDialog)
        self.fileClose.triggered.connect(self.close_figure)
        self.fileSave.triggered.connect(self.sp.mpl_toolbar.save_figure)
        self.actionTag.triggered.connect(self.mode_change)
        self.actionView.triggered.connect(self.mode_change)
        self.sp.mpl_connect('button_press_event', self.on_click)

    def initUI(self):
        self.Exit.setStatusTip('Ctrl+Q')
        self.Exit.setStatusTip('Exit app')
        self.Exit.triggered.connect(QtWidgets.qApp.quit)
        self.show()
        self.fileOpen.setStatusTip('Ctrl+O')
        self.fileOpen.setStatusTip('Open Log')
        self.set_table_format()
        self.progressBar.setValue(0)
        self.CBvato.stateChanged.connect(self.update_up_cure)
        self.CBceilv.stateChanged.connect(self.update_up_cure)
        self.CBlevel.stateChanged.connect(self.update_up_cure)
        self.CBcmdv.stateChanged.connect(self.update_up_cure)
        self.CBacc.stateChanged.connect(self.update_down_cure)
        self.CBramp.stateChanged.connect(self.update_down_cure)

    def showDialog(self):
        temp = '/'
        global load_flag
        if self.pathlist == []:
            filepath = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', 'd:/')
            path = filepath[0]
            name = filepath[0].split("/")[-1]
            self.pathlist = filepath[0].split("/")
            self.file = path
            self.statusbar.showMessage(path)
        else:
            filepath = temp.join(self.pathlist[:-1])                # 纪录上一次的文件路径
            filepath = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', filepath)
            path = filepath[0]
            name = filepath[0].split("/")[-1]
            self.file = path
            self.statusbar.showMessage(path)
        self.sp.axes1.clear()
        self.textEdit.clear()
        self.reset_all_checkbox()
        self.reset_text_edit()
        try:
            self.log_process()
            self.CBvato.setChecked(True)
            self.set_table_content()
            load_flag = 1
        except Exception as err:
            self.textEdit.setPlainText('Error Line ' + str(err.start) + ':' + err.reason + '\n')
            self.textEdit.append('Process file failure! \nPlease Predeal the file!')

    def log_process(self):
        self.log = FileProcess.FileProcess(self.progressBar)  # construct class
        self.log.readkeyword(self.file)       # D:\A.txt

    def update_up_cure(self):
        if self.CBvato.isChecked() or self.CBcmdv.isChecked() \
                or self.CBceilv.isChecked() or self.CBlevel.isChecked():
            try:
                self.sp.axes1.clear()
                self.sp.ax1_twin.clear()
            except Exception as err:
                self.textEdit.append('Clear all figure!\n')
            # 处理ATO速度
            if self.CBvato.isChecked():
                self.sp.plotlog_vs(self.log)
            else:
                self.CBvato.setChecked(False)
            # 处理命令速度
            if self.CBcmdv.isChecked():
                self.sp.plotlog_vcmdv(self.log)
            else:
                self.CBcmdv.setChecked(False)
            # 处理顶棚速度
            if self.CBceilv.isChecked():
                self.sp.plotlog_vceil(self.log)
            else:
                self.CBceilv.setChecked(False)
            # 处理级位
            if self.CBlevel.isChecked():
                self.sp.plotlog_level(self.log)
            else:
                self.CBlevel.setChecked(False)
        elif self.CBacc.isChecked() or self.CBramp.isChecked():
            self.update_down_cure()             #当没有选择下图时更新上图
        else:
            self.clear_axis()
        self.sp.plot_cord1(self.log)
        self.sp.draw()

    def update_down_cure(self):
        if self.CBacc.isChecked() or self.CBramp.isChecked():
            self.clear_axis()
            # 加速度处理
            if self.CBacc.isChecked():
                self.sp.plotlog_sa(self.log)
            else:
                self.CBacc.setChecked(False)
            # 坡度处理
            if self.CBramp.isChecked():
                self.sp.plotlog_ramp(self.log)
            else:
                self.CBramp.setChecked(False)
        elif self.CBvato.isChecked() or self.CBcmdv.isChecked() \
                or self.CBceilv.isChecked() or self.CBlevel.isChecked():
            self.update_up_cure()               #当没有选择上图时更新下图
        else:
            self.clear_axis()
        self.sp.plot_cord2()
        self.sp.draw()

    def clear_axis(self):
        global load_flag
        if load_flag == 1:
            try:
                self.sp.axes1.clear()
                self.sp.ax1_twin.clear()
            except Exception as err:
                self.textEdit.append('Clear all figure!\n')
            load_flag = 0
        else:
            pass

    def show_message(self, s):
        self.textEdit.append(s)

    def on_click(self, event):
        pass
        # if self.mode == 1:
        #     # get the x and y coords, flip y from top to bottom
        #     x, y = event.x, event.y
        #     if event.button == 1:
        #         if event.inaxes is not None:
        #             print('data coords %f %f' % (event.xdata, event.ydata))

    def plot_tag(self,x_tag):
        # cursor = Cursor(self.sp.axes1.axes, horizOn=True, color='r', lw=1)
        # self.sp.axes1.axvline()
        self.sp.draw()

    def mode_change(self):
        sender = self.sender()
        if sender.text() == '标注模式':
            self.mode = 1
        if sender.text() == '浏览模式':
            self.mode = 0
        # 更改图标
        if self.mode == 1:      #标记模式
            self.sp.setCursor(QtCore.Qt.CrossCursor) #如果对象直接self.那么在图像上光标就不变，面向对象操作
        elif self.mode == 0:    #浏览模式
            self.sp.setCursor(QtCore.Qt.ArrowCursor)

    def close_figure(self, evt):
        self.textEdit.append('Close Log Plot\n')
        try:
            self.sp.axes1.clear()
            self.sp.ax1_twin.clear()
        except Exception as err:
            self.textEdit.append('Clear all figure!\n')
        self.sp.draw()

    def set_table_format(self):
        # table name
        self.tableWidget.setRowCount(5)
        self.tableWidget.setColumnCount(3)
        self.tableWidget.setHorizontalHeaderLabels(['ItemName', 'Value', 'Uint'])
        unitss_cm_item = QtWidgets.QTableWidgetItem("cm")
        unitts_cm_item = QtWidgets.QTableWidgetItem("cm")
        unitse_cm_item = QtWidgets.QTableWidgetItem("cm")
        stop_pos_item = QtWidgets.QTableWidgetItem("Stop_Pos")
        target_item = QtWidgets.QTableWidgetItem("Target_Pos")
        stop_err_item = QtWidgets.QTableWidgetItem("Stop_Err")
        skip_item = QtWidgets.QTableWidgetItem("Skip_Status")
        task_item = QtWidgets.QTableWidgetItem("Task_Status")
        self.tableWidget.setItem(0, 0, target_item)
        self.tableWidget.setItem(0, 2, unitts_cm_item)
        self.tableWidget.setItem(1, 0, stop_pos_item)
        self.tableWidget.setItem(1, 2, unitss_cm_item)
        self.tableWidget.setItem(2, 0, stop_err_item)
        self.tableWidget.setItem(2, 2, unitse_cm_item)
        self.tableWidget.setItem(3, 0, skip_item)
        self.tableWidget.setItem(4, 0, task_item)

    def set_table_content(self):
        valuese_item = QtWidgets.QTableWidgetItem(str(self.log.stoperr))
        valuets_item = QtWidgets.QTableWidgetItem(str(self.log.targetstop))
        valuesp_item = QtWidgets.QTableWidgetItem(str(self.log.stoppos))
        if 1== self.log.skip:
            str_skip ='Skip'
        elif 0 == self.log.skip:
            str_skip = 'No Skip'
        else:
            str_skip = 'None'
        if 1 == self.log.mtask:
            str_task = 'Task'
        elif 2 == self.log.mtask:
            str_task = 'No Task'
        else:
            str_task = 'None'
        skip_item = QtWidgets.QTableWidgetItem(str_skip)
        task_item = QtWidgets.QTableWidgetItem(str_task)
        value_skip_item = QtWidgets.QTableWidgetItem(str(self.log.skip))
        value_task_item = QtWidgets.QTableWidgetItem(str(self.log.mtask))
        self.tableWidget.setItem(0, 1, valuets_item)
        self.tableWidget.setItem(1, 1, valuesp_item)
        self.tableWidget.setItem(2, 1, valuese_item)
        self.tableWidget.setItem(3, 1, value_skip_item)
        self.tableWidget.setItem(4, 1, value_task_item)
        self.tableWidget.setItem(3, 2, skip_item)
        self.tableWidget.setItem(4, 2, task_item)

    def reset_all_checkbox(self):
        self.CBacc.setChecked(False)
        self.CBceilv.setChecked(False)
        self.CBlevel.setChecked(False)
        self.CBcmdv.setChecked(False)
        self.CBvato.setChecked(False)
        self.CBramp.setChecked(False)

    def reset_text_edit(self):
        self.textEdit.setPlainText(time.strftime("%Y-%m-%d %H:%M:%S \n", time.localtime(time.time())))
        self.textEdit.setPlainText('open file : ' + self.file + ' OK! \n')

if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    window = Mywindow()
    window.show()
    sys.exit(app.exec_())