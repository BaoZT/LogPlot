import FileProcess
import KeyWordPlot
import time
from PyQt5 import QtWidgets, QtCore, QtGui
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from LogMainWin import Ui_MainWindow
from CycleInfo import Ui_MainWindow as CycleWin
import sys
from KeyWordPlot import Figure_Canvas, SnaptoCursor
import time

# 全局静态变量
load_flag = 0         # 区分是否已经加载文件
cursor_in_flag = 0    # 区分光标是否在图像内,初始化为0,in=1，out=2
curve_flag = 0        # 区分绘制曲线类型，0=速度位置曲线，1=周期位置曲线


# 主界面类
class Mywindow(QtWidgets.QMainWindow, Ui_MainWindow):
    is_cursor_created = 0

    # 建立的是Main Window项目，故此处导入的是QMainWindow
    def __init__(self):
        super(Mywindow, self).__init__()
        self.setupUi(self)
        self.initUI()
        self.icon_from_file()
        self.file = ''
        self.pathlist = []
        self.mode = 0          # 默认0是浏览模式，1是标注模式
        self.ver = '1.9.8'     # 标示软件版本
        self.resize(1000, 600)
        self.setWindowTitle('LogPlot-V' + self.ver)
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/BZT.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        l = QtWidgets.QVBoxLayout(self.widget)
        self.sp = Figure_Canvas(self.widget)        # 这是继承FigureCanvas的子类，使用子窗体widget作为父亲类
        self.sp.mpl_toolbar = NavigationToolbar(self.sp, self.widget)  # 传入FigureCanvas类或子类实例，和父窗体
        l.addWidget(self.sp)

        # l.addWidget(self.sp.mpl_toolbar)
        self.widget.setFocus()
        self.fileOpen.triggered.connect(self.showDialog)
        self.fileClose.triggered.connect(self.close_figure)
        self.fileSave.triggered.connect(self.sp.mpl_toolbar.save_figure)
        self.actionConfig.triggered.connect(self.sp.mpl_toolbar.configure_subplots)
        self.actionPan.triggered.connect(self.sp.mpl_toolbar.pan)
        self.actionZoom.triggered.connect(self.zoom)
        self.actionEdit.triggered.connect(self.sp.mpl_toolbar.edit_parameters)
        self.actionReset.triggered.connect(self.reset_logplot)
        self.actionHome.triggered.connect(self.home_show)            # 这里home,back,和forward都是父类中实现的
        self.actionBck.triggered.connect(self.sp.mpl_toolbar.back)   # NavigationToolbar2方法
        self.actionFwd.triggered.connect(self.sp.mpl_toolbar.forward)
        self.actionTag.triggered.connect(self.mode_change)
        self.actionView.triggered.connect(self.mode_change)
        self.actionVersion.triggered.connect(self.version_msg)
        self.sp.mpl_connect('button_press_event', self.sp.right_press)
        self.actionPrint.triggered.connect(self.cycle_print)         # 打印周期
        self.actionCS.triggered.connect(self.cmd_change)
        self.actionVS.triggered.connect(self.cmd_change)
        self.spinBox.valueChanged.connect(self.spin_value_changed)

        self.filetab_format()
        self.set_label_format()
        self.set_tree_fromat()
        self.model = QtWidgets.QDirModel()
        self.treeView.setModel(self.model)
        self.treeView.doubleClicked.connect(self.filetab_clicked)

    def initUI(self):
        self.splitter.setStretchFactor(0, 35)
        self.splitter.setStretchFactor(1, 12)
        self.splitter_2.setStretchFactor(0, 7)
        self.splitter_2.setStretchFactor(1, 3)
        self.Exit.setStatusTip('Ctrl+Q')
        self.Exit.setStatusTip('Exit app')
        self.fileOpen.setStatusTip('Ctrl+O')
        self.fileOpen.setStatusTip('Open Log')
        self.set_table_format()
        self.progressBar.setValue(0)
        self.label_2.setText('')
        self.Exit.triggered.connect(QtWidgets.qApp.quit)
        self.CBvato.stateChanged.connect(self.update_up_cure)
        self.CBatpcmdv.stateChanged.connect(self.update_up_cure)
        self.CBlevel.stateChanged.connect(self.update_up_cure)
        self.CBcmdv.stateChanged.connect(self.update_up_cure)
        self.CBacc.stateChanged.connect(self.update_down_cure)
        self.CBramp.stateChanged.connect(self.update_down_cure)
        self.cyclewin = Cyclewindow()
        self.show()

    # 事件处理函数，打开文件读取并初始化界面
    def showDialog(self):
        temp = '/'
        global curve_flag
        is_ato_control = 1
        global load_flag
        if len(self.pathlist) == 0:
            filepath = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', 'd:/', "txt files(*.txt *.log)")
            path = filepath[0]      # 取出文件地址
            if path == '':          # 没有选择文件
                self.statusbar.showMessage('Choose Nothing ！')
            else:
                name = filepath[0].split("/")[-1]
                self.pathlist = filepath[0].split("/")
                self.file = path
                self.statusbar.showMessage(path)
        else:
            filepath = temp.join(self.pathlist[:-1])                # 纪录上一次的文件路径
            filepath = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', filepath)
            path = filepath[0]
            name = filepath[0].split("/")[-1]
            # 求出本次路径序列
            templist = filepath[0].split("/")
            self.update_path_changed(templist)
            self.file = path
            self.statusbar.showMessage(path)
        # 当文件路径不为空
        if path == '':
            pass
        else:
            self.update_filetab()
            self.sp.axes1.clear()
            self.textEdit.clear()
            self.reset_all_checkbox()
            self.reset_text_edit()
            self.mode = 0              # 恢复初始浏览模式
            try:
                is_ato_control = self.log_process()
                if is_ato_control == 0:
                    load_flag = 1      # 记录加载且ATO控车
                    self.CBvato.setChecked(True)
                elif is_ato_control == 1:
                    load_flag = 2      # 记录加载但是ATO没有控车
                    reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                                                              "无曲线",
                                                              "注意：记录中ATO没有控车！ATO处于非AOM和AOR模式！",
                                                              QtWidgets.QMessageBox.Yes)
                elif is_ato_control == 2:
                    load_flag = 0      # 记录加载但是没有检测到周期
                else:
                    reply = QtWidgets.QMessageBox.information(self,     # 使用infomation信息框
                                                              "待处理",
                                                              "注意：记录中包含ATO重新上下电过程，列车绝对位置重叠"
                                                              "需手动分解记录！\nATO记录启机行号:Line：" + str(is_ato_control),
                                                              QtWidgets.QMessageBox.Yes)
            except Exception as err:
                self.textEdit.setPlainText(' Error Line ' + str(err.start) + ':' + err.reason + '\n')
                self.textEdit.append('Process file failure! \nPlease Predeal the file!')

    # 当打开文件解码失败时尝试转码
    def log_codec_transfer(self):
        pass

    # 默认路径的更新，在文件树结构双击时也更新默认路径
    def update_filetab(self):
        temp = '/'
        filepath = temp.join(self.pathlist[:-1])  # 纪录上一次的文件路径
        mdinx = self.model.index(filepath)
        self.treeView.setRootIndex(mdinx)

    # 事件处理函数，获取文件树结构中双击的文件路径和文件名
    def filetab_clicked(self, item_index):
        print(item_index.row(), item_index.column())
        if self.model.fileInfo(item_index).isDir():
            pass
        else:
            self.file = self.model.filePath(item_index)  # 带入modelIndex获取model的相关信息
            self.reset_logplot()
            print(self.model.fileName(item_index))
            print(self.model.filePath(item_index))

    # <待验证> 设置文件目录的格式大小
    def filetab_format(self):
        self.treeView.setColumnWidth(1, 5)
        self.treeView.setColumnWidth(0, 25)

    # 默认路径的更新，用于打开文件时，总打开最近一次的文件路劲
    def update_path_changed(self, path2):
        ret = True
        if len(self.pathlist) == len(path2):
            for idx, value in enumerate(self.pathlist):
                if path2[idx] != value:
                    ret = False
                    break
                else:
                    pass
        else:
            ret = False
        # 是否更新,True相同，False不同
        if ret:
            pass
        else:
            self.pathlist = path2.copy()

    # 事件处理函数，弹窗显示版本信息
    def version_msg(self):
        reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                                        "版本信息",
                                        "Software:LogPlot-V"+str(self.ver)+"\n"
                                        "Author   :Baozhengtang\n"
                                        "License  :(C) Copyright 2017-2018, Author Limited.\n"
                                        "Contact :baozhengtang@gmail.com",
                                        QtWidgets.QMessageBox.Yes)

    # 记录文件处理核心函数，生成周期字典和绘图值列表
    def log_process(self):
        isok = 2                                                # 0=ato控车，1=没有控车,2=没有周期
        isdone = 0
        self.log = FileProcess.FileProcess(self.progressBar)    # 类的构造函数，函数中给出属性
        self.log.readkeyword(self.file)
        self.log.start()                                        # 启动记录读取线程,run函数不能有返回值
        while self.log.is_alive():                              # 由于文件读取线程和后面是依赖关系，不能立即继续执行
            time.sleep(1)
            continue
        [t1, t2, isok] = self.log.get_time_use()
        self.show_message("Info:预处理耗时:" + str(t1) + 's')
        # 记录中模式有AOR或AOS
        if isok == 0:
            self.show_message("Info:文本计算耗时:" + str(t2) + 's')
            max_c = int(max(self.log.cycle))
            min_c = int(min(self.log.cycle))
            self.spinBox.setRange(min_c, max_c)
            self.show_message("Info:曲线周期数:"+str(max_c - min_c)+' '+'from'+str(min_c)+'to'+str(max_c))
            self.spinBox.setValue(min_c)
            self.label_2.setText(self.log.cycle_dic[min_c].time)    # 显示起始周期
        elif isok == 1:
            self.show_message("Info:文本计算耗时:" + str(t2)+'s')
            self.show_message("Info:ATO没有控车！")
            max_c = int(max(self.log.cycle_dic.keys()))
            min_c = int(min(self.log.cycle_dic.keys()))
            self.spinBox.setRange(min_c, max_c)
            self.show_message("Info:曲线周期数:"+str(max_c - min_c)+' '+'from'+str(min_c)+'to'+str(max_c))
            self.spinBox.setValue(min_c)
            self.label_2.setText(self.log.cycle_dic[min_c].time)  # 显示起始周期
        elif isok == 2:
            self.show_message("Info:记录中没有周期！")
        else:
            pass
        return isok

    # 事件处理函数，计数器数值变化触发事件，绑定光标和内容更新
    def spin_value_changed(self):
        global cursor_in_flag
        global curve_flag
        xy_lim = []
        track_flag = self.sp.get_track_status()               # 获取之前光标的锁定状态
        print(self.sp.get_track_status())
        # 光标离开图像
        if cursor_in_flag == 2:
            cur_cycle = self.spinBox.value()                  # 获取当前周期值

            if cur_cycle in self.log.cycle_dic.keys():
                c = self.log.cycle_dic[cur_cycle]             # 查询周期字典
                # 该周期没有控制信息，或打印丢失,不发送光标移动信号
                if c.control != ():
                    info = list(c.control)
                    if curve_flag == 0:
                        # 先更新坐标轴范围
                        xy_lim = self.sp.update_cord_with_cursor((int(info[0]), int(info[1])),self.sp.axes1.get_xlim(),
                                                                 self.sp.axes1.get_ylim())
                        # 如果超出范围再更新
                        is_update = xy_lim[2]
                        if is_update == 1:
                            self.sp.axes1.set_xlim(xy_lim[0][0], xy_lim[0][1])
                            self.sp.axes1.set_ylim(xy_lim[1][0], xy_lim[1][1])
                            self.update_up_cure()
                            if track_flag == 0:     # 如果之前是锁定的，更新后依然锁定在最新位置
                                self.sp.set_track_status()
                        # 再更新光标
                        self.c_vato.sim_mouse_move(int(info[0]), int(info[1]))  # 其中前两者位置和速度为移动目标
                    elif curve_flag == 1:
                        # 先更新坐标轴范围
                        xy_lim = self.sp.update_cord_with_cursor((int(cur_cycle), int(info[1])),self.sp.axes1.get_xlim(),
                                                                 self.sp.axes1.get_ylim())
                        # 如果超出范围再更新
                        is_update = xy_lim[2]
                        if is_update == 1:
                            self.sp.axes1.set_xlim(xy_lim[0][0], xy_lim[0][1])
                            self.sp.axes1.set_ylim(xy_lim[1][0], xy_lim[1][1])
                            self.update_up_cure()
                            if track_flag == 0:
                                self.sp.set_track_status()
                        # 再更新光标
                        self.c_vato.sim_mouse_move(int(cur_cycle), int(info[1]))     # 绘制速度周期曲线时查询为周期，速度
                else:
                    pass
            else:
                self.show_message('Err:记录边界或周期丢失！')
        else:
            pass        # 否则 不处理

    # 事件处理函数，更新光标进入图像标志，in=1
    def cursor_in_fig(self, event):
        global cursor_in_flag
        cursor_in_flag = 1
        self.c_vato.move_signal.connect(self.set_table_content)        # 进入图后绑定光标触发
        print('connect '+'enter figure'+str(cursor_in_flag))

    # 事件处理函数，更新光标进入图像标志,out=2
    def cursor_out_fig(self, event):
        global cursor_in_flag
        cursor_in_flag = 2
        self.c_vato.move_signal.disconnect(self.set_table_content)      # 离开图后解除光标触发
        print('disconnect '+'leave figure'+str(cursor_in_flag))

    # 绘制各种速度位置曲线
    def update_up_cure(self):
        global load_flag
        global curve_flag
        # file is load
        if load_flag == 1:
            x_monitor = self.sp.axes1.get_xlim()
            y_monitor = self.sp.axes1.get_ylim()
            if self.CBvato.isChecked() or self.CBcmdv.isChecked() \
                    or self.CBatpcmdv.isChecked() or self.CBlevel.isChecked():
                self.clear_axis()
                # 清除光标重新创建
                if self.mode == 1:
                    if Mywindow.is_cursor_created == 1:
                        Mywindow.is_cursor_created = 0
                        del self.c_vato
                    self.tag_cursor_creat()
                # 处理ATO速度
                if self.CBvato.isChecked():
                    self.sp.plotlog_vs(self.log, self.mode, curve_flag)
                else:
                    self.CBvato.setChecked(False)
                # 处理命令速度
                if self.CBcmdv.isChecked():
                    self.sp.plotlog_vcmdv(self.log, self.mode, curve_flag)
                else:
                    self.CBcmdv.setChecked(False)
                # 处理顶棚速度
                if self.CBatpcmdv.isChecked():
                    self.sp.plotlog_vceil(self.log, curve_flag)
                else:
                    self.CBatpcmdv.setChecked(False)
                # 处理级位
                if self.CBlevel.isChecked():
                    self.sp.plotlog_level(self.log, curve_flag)
                else:
                    self.CBlevel.setChecked(False)
            elif self.CBacc.isChecked() or self.CBramp.isChecked():
                self.update_down_cure()             # 当没有选择下图时更新上图
                self.sp.plot_cord1(self.log, curve_flag, (0.0, 1.0), (0.0, 1.0))
            else:
                self.clear_axis()
                self.sp.plot_cord1(self.log, curve_flag, (0.0, 1.0), (0.0, 1.0))
            self.sp.plot_cord1(self.log, curve_flag, x_monitor, y_monitor)
            self.sp.draw()
        else:
            pass

    # 绘制加速度和坡度曲线
    def update_down_cure(self):
        global load_flag
        global curve_flag
        if load_flag == 1:
            if self.mode == 0:  # 只有浏览模式才可以
                if self.CBacc.isChecked() or self.CBramp.isChecked():
                    self.clear_axis()
                    # 加速度处理
                    if self.CBacc.isChecked():
                        self.sp.plotlog_sa(self.log, curve_flag)
                    else:
                        self.CBacc.setChecked(False)
                    # 坡度处理
                    if self.CBramp.isChecked():
                        self.sp.plotlog_ramp(self.log, curve_flag)
                    else:
                        self.CBramp.setChecked(False)
                elif self.CBvato.isChecked() or self.CBcmdv.isChecked() \
                        or self.CBatpcmdv.isChecked() or self.CBlevel.isChecked():
                    self.update_up_cure()               # 当没有选择下图时更新上图
                    self.sp.plot_cord1(self.log, curve_flag, (0.0, 1.0), (0.0, 1.0))
                else:
                    self.clear_axis()
                    self.sp.plot_cord1(self.log, curve_flag, (0.0, 1.0), (0.0, 1.0))
                self.sp.plot_cord2(self.log, curve_flag)            # 绘制坐标系II
                self.sp.draw()
            else:
                pass
        else:
            pass

    # 清除图像和轴相关内容，画板清屏
    def clear_axis(self):
        try:
            self.sp.axes1.clear()
            self.sp.ax1_twin.clear()
        except Exception as err:
            self.textEdit.append('Clear all figure!\n')

    # 封装用于在文本框显示字符串
    def show_message(self, s):
        self.textEdit.append(s)

    # <待完成> 用于标注模式下按压操作后级处理
    def on_click(self, event):
        pass
        # if self.mode == 1:
        #     # get the x and y coords, flip y from top to bottom
        #     x, y = event.x, event.y
        #     if event.button == 1:
        #         if event.inaxes is not None:
        #             print('data coords %f %f' % (event.xdata, event.ydata))

    # 模式转换函数，修改全局模式变量和光标
    def mode_change(self):
        global load_flag
        sender = self.sender()
        # 查看信号发送者
        if sender.text() == '标注模式' and self.mode == 0:      # 由浏览模式进入标注模式不重绘范围
            self.mode = 1
            if load_flag == 1 and self.CBvato.isChecked():
                self.update_up_cure()
                self.tag_cursor_creat()      # 只针对速度曲线
        elif sender.text() == '浏览模式' and self.mode == 1:    # 进入浏览模式重绘
            self.mode = 0
            if load_flag == 1:
                self.update_up_cure()
                # 重置坐标轴范围
                self.sp.plot_cord1(self.log, curve_flag, (0.0, 1.0), (0.0, 1.0))
            self.tag_cursor_creat()
        else:
            # 重置坐标轴范围
            if load_flag == 1:
                self.sp.plot_cord1(self.log, curve_flag, (0.0, 1.0), (0.0, 1.0))
        self.sp.draw()
        # 更改图标
        if self.mode == 1:      # 标记模式
            self.sp.setCursor(QtCore.Qt.PointingHandCursor)  # 如果对象直接self.那么在图像上光标就不变，面向对象操作
        elif self.mode == 0:    # 浏览模式
            self.sp.setCursor(QtCore.Qt.ArrowCursor)
        self.statusbar.showMessage(self.file + " " + "当前模式："+sender.text())

    # 曲线类型转换函数，修改全局模式变量
    def cmd_change(self):
        global curve_flag
        sender = self.sender()
        if sender.text() == '位置速度曲线':
            if curve_flag == 1:
                curve_flag = 0      # 曲线类型改变，如果有光标则删除，并重置标志
                if Mywindow.is_cursor_created == 1:
                    del self.c_vato
                    Mywindow.is_cursor_created = 0
                else:
                    pass
                self.update_up_cure()
                self.tag_cursor_creat()  # 根据需要重新创建光标
            else:
                pass
        if sender.text() == "周期速度曲线":
            if curve_flag == 0:
                curve_flag = 1      # 曲线类型改变
                if Mywindow.is_cursor_created == 1:
                    del self.c_vato
                    Mywindow.is_cursor_created = 0
                else:
                    pass
                self.update_up_cure()
                self.tag_cursor_creat()
            else:
                pass
        # 重置坐标轴范围
        self.sp.plot_cord1(self.log, curve_flag, (0.0, 1.0), (0.0, 1.0))
        self.sp.draw()
        self.statusbar.showMessage(self.file + " " + "曲线类型：" + sender.text())

    # 用于模式转换后处理，创建光标绑定和解绑槽函数
    def tag_cursor_creat(self):
        global curve_flag
        # 标注模式
        if self.mode == 1 and 0 == Mywindow.is_cursor_created:
            if curve_flag == 0:
                self.c_vato = SnaptoCursor(self.sp, self.sp.axes1, self.log.s, self.log.v_ato)  # 初始化一个光标
            else:
                self.c_vato = SnaptoCursor(self.sp, self.sp.axes1, self.log.cycle, self.log.v_ato)  # 初始化一个光标
            self.c_vato.reset_cursor_plot()
            self.cid1 = self.sp.mpl_connect('motion_notify_event', self.c_vato.mouse_move)
            self.cid2 = self.sp.mpl_connect('figure_enter_event', self.cursor_in_fig)
            self.cid3 = self.sp.mpl_connect('figure_leave_event', self.cursor_out_fig)
            self.c_vato.move_signal.connect(self.set_tableall_content)  # 连接图表更新的槽函数
            self.c_vato.sim_move_singal.connect(self.set_table_content)
            self.c_vato.move_signal.connect(self.set_tree_content)      # 连接信号槽函数
            self.c_vato.sim_move_singal.connect(self.set_tree_content)  # 连接信号槽函数
            Mywindow.is_cursor_created = 1
        elif self.mode == 0 and 1 == Mywindow.is_cursor_created:
            self.sp.mpl_disconnect(self.cid1)
            self.sp.mpl_disconnect(self.cid2)
            self.sp.mpl_disconnect(self.cid3)
            self.c_vato.move_signal.disconnect(self.set_tableall_content)
            self.c_vato.sim_move_singal.disconnect(self.set_table_content)
            self.c_vato.move_signal.disconnect(self.set_tree_content)  # 连接信号槽函数
            self.c_vato.sim_move_singal.disconnect(self.set_tree_content)  # 连接信号槽函数
            Mywindow.is_cursor_created = 0
            del self.c_vato
        else:
            pass

    # 封装工具栏函数，图形缩放
    def zoom(self):
        self.sp.mpl_toolbar.zoom()
        if self.mode == 1:
            self.sp.setCursor(QtCore.Qt.PointingHandCursor)
        else:
            pass

    # 封装工具栏函数，显示画板初始状态，清除曲线
    def home_show(self):
        global load_flag
        global curve_flag
        self.clear_axis()
        self.reset_all_checkbox()
        self.CBvato.setChecked(True)
        self.reset_text_edit()
        if load_flag == 1:
            self.sp.plot_cord1(self.log, curve_flag, (0.0, 1.0), (0.0, 1.0))
            self.update_up_cure()
        else:
            pass

    # 关闭当前绘图
    def close_figure(self, evt):
        global load_flag
        if load_flag == 1:
            self.textEdit.append('Close Log Plot\n')
            self.clear_axis()
            load_flag = 0
            self.sp.draw()
        else:
            pass

    # 事件处理函数，用于弹窗显示当前索引周期
    def cycle_print(self):
        global load_flag
        self.cyclewin.statusBar.showMessage('')  # 清除上一次显示内容
        idx = self.spinBox.value()
        print_flag = 0                           # 是否弹窗打印，0=不弹窗，1=弹窗
        c_num = 0
        self.cyclewin.textEdit.clear()
        if 1 == load_flag or 2 == load_flag:            # 文件已经加载
            # 前提是必须有周期，字典能查到
            if idx in self.log.cycle_dic.keys():
                c_num = self.log.cycle_dic[idx].cycle_num
                for line in self.log.cycle_dic[idx].cycle_all_info:
                    self.cyclewin.textEdit.append(line[:-1])
                # 周期完整性
                if self.log.cycle_dic[idx].cycle_property == 1:
                    self.cyclewin.statusBar.showMessage(str(c_num) + '周期序列完整！')
                elif self.log.cycle_dic[idx].cycle_property == 2:
                    self.cyclewin.statusBar.showMessage(str(c_num) + '周期尾部缺失！')
                else:
                    self.cyclewin.statusBar.showMessage('记录异常！')  # 清除上一次显示内容
                print_flag = 1
            else:
                self.show_message("Info：周期不存在，查询无效")
        else:
            self.show_message("Info：文件未加载，查询无效")
        # 有信息才弹窗
        if print_flag == 1:
            self.cyclewin.setWindowTitle('LogPlot-V'+ self.ver + " 周期号 : " +str(c_num))
            self.cyclewin.show()
        else:
            pass

    # 设置主界面表格的格式
    def set_table_format(self):
        item_name = ['V_ato', 'V_cmd', 'V_atpcmdv', 'Real_level', 'Level', 'StateMachine',   # 0~5
                     'Current_Pos', 'V_target', 'Target_Pos', 'MA', 'Stop_Pos', 'Stop_Err',  # 6~11
                     'JD_Stop', 'Ref_Stop', 'Ma_Stop',                                       # 12~14
                     'Skip_Status', 'Task_Status']
        item_unit = ['cm/s', 'cm/s', 'cm/s', '-','-','-',
                     'cm', 'cm/s', 'cm', 'cm', 'cm', 'cm', 'None',  'None',
                     'cm', 'cm', 'cm']
        # table name
        self.tableWidget.setRowCount(17)
        self.tableWidget.setColumnCount(3)
        self.tableWidget.setHorizontalHeaderLabels(['CtrlInfo', 'Values', 'Uint'])
        self.tableWidget.resizeRowsToContents()
        self.tableWidget.verticalHeader().setVisible(False)

        for idx, name in enumerate(item_name):
            self.tableWidget.setItem(idx, 0, QtWidgets.QTableWidgetItem(name))
        for idx2, unit in enumerate(item_unit):
            self.tableWidget.setItem(idx2, 2, QtWidgets.QTableWidgetItem(unit))

    # 事件处理函数，设置主界面表格内容
    def set_tableall_content(self, indx):
        item_value = []
        stop_list = list(self.log.cycle_dic[self.log.cycle[indx]].stoppoint)
        # 获取和计算
        if 1 == self.log.skip[indx]:
            str_skip = 'Skip'
        elif 2 == self.log.skip[indx]:
            str_skip = 'No'
        else:
            str_skip = 'None'
        if 1 == self.log.mtask[indx]:
            str_task = 'Task'
        elif 2 == self.log.mtask[indx]:
            str_task = 'No'
        else:
            str_task = 'None'
        # 装填
        item_value.append(str(int(self.log.v_ato[indx])))   # 使用int的原因是只有整数精度，不多显示
        item_value.append(str(int(self.log.cmdv[indx])))
        item_value.append(str(int(self.log.ceilv[indx])))
        item_value.append(str(int(self.log.real_level[indx])))
        item_value.append(str(int(self.log.level[indx])))
        item_value.append(str(int(self.log.statmachine[indx])))
        item_value.append(str(int(self.log.s[indx])))
        item_value.append(str(int(self.log.v_target[indx])))
        item_value.append(str(int(self.log.targetpos[indx])))
        item_value.append(str(int(self.log.ma[indx])))
        item_value.append(str(int(self.log.stoppos[indx])))
        item_value.append(str(int(self.log.stop_error[indx])))
        item_value.append(str(int(stop_list[0])))
        item_value.append(str(int(stop_list[1])))
        item_value.append(str(int(stop_list[2])))
        item_value.append(str_skip)
        item_value.append(str_task)
        for idx3, value in enumerate(item_value):
            self.tableWidget.setItem(idx3, 1, QtWidgets.QTableWidgetItem(value))
        self.label_2.setText(self.log.cycle_dic[self.log.cycle[indx]].time)
        self.spinBox.setValue(int(self.log.cycle_dic[self.log.cycle[indx]].cycle_num))

    # 事件处理函数，设置表格
    def set_table_content(self, indx):
        item_value = []
        stop_list = list(self.log.cycle_dic[self.log.cycle[indx]].stoppoint)
        # 获取和计算
        if 1 == self.log.skip[indx]:
            str_skip = 'Skip'
        elif 2 == self.log.skip[indx]:
            str_skip = 'No'
        else:
            str_skip = 'None'
        if 1 == self.log.mtask[indx]:
            str_task = 'Task'
        elif 2 == self.log.mtask[indx]:
            str_task = 'No'
        else:
            str_task = 'None'
        # 装填
        item_value.append(str(int(self.log.v_ato[indx])))  # 使用int的原因是只有整数精度，不多显示
        item_value.append(str(int(self.log.cmdv[indx])))
        item_value.append(str(int(self.log.ceilv[indx])))
        item_value.append(str(int(self.log.real_level[indx])))
        item_value.append(str(int(self.log.level[indx])))
        item_value.append(str(int(self.log.statmachine[indx])))
        item_value.append(str(int(self.log.s[indx])))
        item_value.append(str(int(self.log.v_target[indx])))
        item_value.append(str(int(self.log.targetpos[indx])))
        item_value.append(str(int(self.log.ma[indx])))
        item_value.append(str(int(self.log.stoppos[indx])))
        item_value.append(str(int(self.log.stop_error[indx])))
        item_value.append(str(int(stop_list[0])))
        item_value.append(str(int(stop_list[1])))
        item_value.append(str(int(stop_list[2])))
        item_value.append(str_skip)
        item_value.append(str_task)
        for idx3, value in enumerate(item_value):
            self.tableWidget.setItem(idx3, 1, QtWidgets.QTableWidgetItem(value))
        self.label_2.setText(self.log.cycle_dic[self.log.cycle[indx]].time)

    # 设置树形结构
    def set_tree_fromat(self):
        self.treeWidget.setColumnCount(3)       # 协议字段，数据，单位
        self.treeWidget.setHeaderLabels(['Procotol', 'Field', 'Value'])
        self.treeWidget.setColumnWidth(0, 100)
        self.treeWidget.setColumnWidth(1, 125)
        # self.treeWidget.setHeaderLabels(['Procotol', 'Field', 'Value', 'Unit']) # 内容解析未来添加

    # 事件处理函数，设置树形结构和内容
    def set_tree_content(self, idx):
        is_p2o_create = 0
        is_o2p_create = 0
        is_t2o_create = 0
        is_o2t_create = 0
        self.treeWidget.clear()
        # 没有ATP-ATO通信包
        if self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict != {}:
            # 所有通信数据包,考虑通过两层循环来实现
            for k in self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict.keys():
                # P->O 数据包
                if k < 10:
                    if is_p2o_create == 0:
                        root1 = QtWidgets.QTreeWidgetItem(self.treeWidget)
                        root1.setText(0, 'ATP -> ATO')
                        is_p2o_create = 1
                    else:
                        pass
                    # 针对SP0
                    if k == 0:
                        item_sp0 = QtWidgets.QTreeWidgetItem()
                        item_sp0.setText(0, 'SP' + str(k))
                        # 未来填充
                        root1.addChild(item_sp0)
                    # 针对SP1
                    elif k == 1:
                        item_sp1 = QtWidgets.QTreeWidgetItem()
                        item_sp1.setText(0, 'SP' + str(k))
                        # 未来填充
                        root1.addChild(item_sp1)
                    # 针对 SP2
                    elif k == 2:
                        item_sp2 = QtWidgets.QTreeWidgetItem()
                        item_sp2.setText(0, 'SP' + str(k))
                        txt2 = ['q_atopermit', 'q_ato_hardpermit', 'q_leftdoorpermit',
                                'q_rightdoorpermit', 'q_door_cmd_dir', 'q_tb', 'v_target', 'd_target', 'm_level',
                                'm_mode', 'o_train_pos', 'v_permitted', 'd_ma', 'm_ms_cmd', 'd_neu_sec',
                                'm_low_frequency', 'q_stopstatus', 'm_atp_stop_error', 'd_station_mid_pos',
                                'd_jz_sig_pos', 'd_cz_sig_pos',  'd_tsm', 'm_cab_state', 'm_position', 'm_tco_state',
                                'm_brake_state']
                        for index2, field in enumerate((self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k])):
                            item_field = QtWidgets.QTreeWidgetItem(item_sp2)     # 以该数据包作为父节点
                            item_field.setText(2, str(int(field)))                 # 转换去除空格
                            item_field.setText(1, txt2[index2])
                        root1.addChild(item_sp2)
                    # 针对SP5
                    elif k == 5:
                        item_sp5 = QtWidgets.QTreeWidgetItem()
                        item_sp5.setText(0, 'SP' + str(k))
                        txt5 = ['n_units', 'nid_operational', 'nid_driver', 'btm_antenna_position', 'l_door_dis',
                                'l_sdu_wh_size' ,'l_sdu_wh_size', 't_cutoff_traction', 'nid_engine', 'v_ato_permitted']
                        for index5, field in enumerate((self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k])):
                            item_field = QtWidgets.QTreeWidgetItem(item_sp5)  # 以该数据包作为父节点
                            item_field.setText(2, field)  # 转换去除空格
                            item_field.setText(1, txt5[index5])
                        root1.addChild(item_sp5)
                    # 针对SP6
                    elif k == 6:
                        item_sp6 = QtWidgets.QTreeWidgetItem()
                        item_sp6.setText(0, 'SP' + str(k))
                        # 未来填充
                        root1.addChild(item_sp6)
                    elif k == 7:
                        item_sp7 = QtWidgets.QTreeWidgetItem()
                        item_sp7.setText(0, 'SP' + str(k))
                        txt7 = ['nid_bg', 't_middle', 'd_pos_adj', 'nid_xuser', 'q_scale', 'q_platform', 'q_door',
                                'n_d', 'd_stop']
                        for index7, field in enumerate((self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k])):
                            item_field = QtWidgets.QTreeWidgetItem(item_sp7)  # 以该数据包作为父节点
                            item_field.setText(2, field)  # 转换去除空格
                            item_field.setText(1, txt7[index7])
                        root1.addChild(item_sp7)
                    # 针对SP8
                    elif k == 8:
                        item_sp8 = QtWidgets.QTreeWidgetItem()
                        item_sp8.setText(0, 'SP' + str(k))
                        txt8 = ['q_tsrs', 'nid_c', 'nid_tsrs', 'nid_radio_h', 'nid_radio_l', 'q_sleepssion', 'm_type']
                        for index8, field in enumerate((self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k])):
                            item_field = QtWidgets.QTreeWidgetItem(item_sp8)  # 以该数据包作为父节点
                            item_field.setText(2, field)  # 转换去除空格
                            item_field.setText(1, txt8[index8])
                        root1.addChild(item_sp8)
                    # 针对SP9
                    elif k == 9:
                        item_sp9 = QtWidgets.QTreeWidgetItem()
                        item_sp9.setText(0, 'SP' + str(k))
                        # 未来填充
                        root1.addChild(item_sp9)
                    root1.setExpanded(True)
                # O->P 数据包
                elif 100 < k < 140:
                    # 定义根节点，用来添加数据包
                    if is_o2p_create == 0:
                        root2 = QtWidgets.QTreeWidgetItem(self.treeWidget)
                        root2.setText(0, 'ATO -> ATP')
                        is_o2p_create = 1
                    else:
                        pass
                    if k == 130:
                        item_sp130 = QtWidgets.QTreeWidgetItem()
                        item_sp130.setText(0, 'SP' + str(k))
                        txt130 = ['m_atoerror', 'm_atomode', 'm_ato_stop_error', 'm_doormode', 'm_doorstatus']
                        for index130, field in enumerate((self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k])):
                            item_field = QtWidgets.QTreeWidgetItem(item_sp130)  # 以该数据包作为父节点
                            item_field.setText(2, str(int(field)))  # 转换去除空格
                            item_field.setText(1, txt130[index130])
                        root2.addChild(item_sp130)
                    elif k == 131:
                        item_sp131 = QtWidgets.QTreeWidgetItem()
                        item_sp131.setText(0, 'SP' + str(k))
                        txt131 = ['plan', 'skip', 'tbs', 'count', 'radio', 'session', 'tcms', 'strategy', 'paddings']
                        for index131, field in enumerate((self.log.cycle_dic[self.log.cycle[idx]].cycle_sp_dict[k])):
                            item_field = QtWidgets.QTreeWidgetItem(item_sp131)  # 以该数据包作为父节点
                            item_field.setText(2, str(int(field)))  # 转换去除空格
                            item_field.setText(1, txt131[index131])
                        root2.addChild(item_sp131)
                    elif k == 132:
                        item_sp132 = QtWidgets.QTreeWidgetItem()
                        item_sp132.setText(0, 'SP' + str(k))
                        # 未来填充
                        root2.addChild(item_sp132)
                    elif k == 134:
                        item_sp134 = QtWidgets.QTreeWidgetItem()
                        item_sp134.setText(0, 'SP' + str(k))
                        # 未来填充
                        root2.addChild(item_sp134)
                    root2.setExpanded(True)
                # T->A 数据包
                elif 10 < k < 44 or k > 200:
                    # 定义根节点，用来添加数据包
                    if is_t2o_create == 0:
                        root4 = QtWidgets.QTreeWidgetItem(self.treeWidget)
                        root4.setText(0, 'TSRS-> ATO')
                        is_t2o_create = 1
                    else:
                        pass
                    if k == 41:
                        item_c41 = QtWidgets.QTreeWidgetItem()
                        item_c41.setText(0, 'C' + str(k))
                        # 未来填充
                        root4.addChild(item_c41)
                    elif k == 42:
                        item_c42 = QtWidgets.QTreeWidgetItem()
                        item_c42.setText(0, 'C' + str(k))
                        # 未来填充
                        root4.addChild(item_c42)
                    elif k == 43:
                        item_c43 = QtWidgets.QTreeWidgetItem()
                        item_c43.setText(0, 'C' + str(k))
                        # 未来填充
                        root4.addChild(item_c43)
                    elif k == 21:
                        item_p21 = QtWidgets.QTreeWidgetItem()
                        item_p21.setText(0, 'P' + str(k))
                        # 未来填充
                        root4.addChild(item_p21)
                    elif k == 27:
                        item_p27 = QtWidgets.QTreeWidgetItem()
                        item_p27.setText(0, 'P' + str(k))
                        # 未来填充
                        root4.addChild(item_p27)
                    elif k == 202:
                        item_c2 = QtWidgets.QTreeWidgetItem()   # 为防止字典重复特殊添加
                        item_c2.setText(0, 'C' + str(2))
                        # 未来填充
                        root4.addChild(item_c2)
                    root4.setExpanded(True)
                # A->T 数据包
                elif 44 <= k < 50:
                    if is_o2t_create == 0:
                        root3 = QtWidgets.QTreeWidgetItem(self.treeWidget)
                        root3.setText(0, 'ATO -> TSRS')
                        is_o2t_create = 1
                    else:
                        pass
                    if k == 44:                               # a->t 的数据包
                        item_c44 = QtWidgets.QTreeWidgetItem()
                        item_c44.setText(0, 'C' + str(k))
                        # 未来填充
                        root3.addChild(item_c44)
                    elif k == 45:
                        item_c45 = QtWidgets.QTreeWidgetItem()
                        item_c45.setText(0, 'C' + str(k))
                        # 未来填充
                        root3.addChild(item_c45)
                    elif k == 46:
                        item_c46 = QtWidgets.QTreeWidgetItem()
                        item_c46.setText(0, 'C' + str(k))
                        # 未来填充
                        root3.addChild(item_c46)
                    root3.setExpanded(True)
                else:
                    pass
        else:
            pass    # 该周期无数据包

    # 重置主界面所有的选择框
    def reset_all_checkbox(self):
        self.CBacc.setChecked(False)
        self.CBatpcmdv.setChecked(False)
        self.CBlevel.setChecked(False)
        self.CBcmdv.setChecked(False)
        self.CBvato.setChecked(False)
        self.CBramp.setChecked(False)

    # 重置主界面文本框
    def reset_text_edit(self):
        self.textEdit.setPlainText(time.strftime("%Y-%m-%d %H:%M:%S \n", time.localtime(time.time())))
        self.textEdit.setPlainText('open file : ' + self.file + ' OK! \n')

    # 重绘图形并重置选择框
    def reset_logplot(self):
        ret_process = 2
        global load_flag
        if load_flag == 0:
            pass
        else:
            self.mode = 0
            self.sp.axes1.clear()
            self.textEdit.clear()
            self.reset_all_checkbox()
            self.reset_text_edit()
            self.sp.setCursor(QtCore.Qt.ArrowCursor)
            load_flag = 1
            try:
                is_ato_control = self.log_process()
                if is_ato_control == 0:
                    load_flag = 1      # 记录加载且ATO控车
                    self.CBvato.setChecked(True)
                    self.tag_cursor_creat()
                elif is_ato_control == 1:
                    load_flag = 2      # 记录加载但是ATO没有控车
                    reply = QtWidgets.QMessageBox.information(self,  # 使用infomation信息框
                                                              "无曲线",
                                                              "注意：记录中ATO没有控车！ATO处于非AOM和AOR模式！",
                                                              QtWidgets.QMessageBox.Yes)
                elif is_ato_control == 2:
                    load_flag = 0      # 记录加载但是没有检测到周期
                else:
                    reply = QtWidgets.QMessageBox.information(self,     # 使用infomation信息框
                                                              "待处理",
                                                              "注意：记录中包含ATO重新上下电过程，列车绝对位置重叠"
                                                              "需手动分解记录！\nATO记录启机行号:Line：" + str(is_ato_control),
                                                              QtWidgets.QMessageBox.Yes)
            except Exception as err:
                self.textEdit.setPlainText(' Error Line ' + str(err.start) + ':' + err.reason + '\n')
                self.textEdit.append('Process file failure! \nPlease Predeal the file!')

    # 设置标签的格式
    def set_label_format(self):
        self.label.setText('ATO时间:')
        self.label_3.setText('周期号:')

    # 由于pyinstaller不能打包直接打包图片资源的缺陷，QtDesigner自动生成的图标代码实际无法打包，需在目录下放置图标文件夹
    # 所以通过手动生成的qrc文件（QtDesigner也可以，未试验），通过PyRrc5转为py资源文件
    # 使用该函数重复设置来用资源文件内容替代原来自图片的图标，实现pyinstaller的打包图标
    # 图标更新时需要-修改qrc，且修改该函数才能使生成exe与QtDesigner调试一致
    def icon_from_file(self):
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":IconFiles/file.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.fileOpen.setIcon(icon)

        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":IconFiles/close.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.fileClose.setIcon(icon1)

        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":IconFiles/save.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.fileSave.setIcon(icon2)

        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(":IconFiles/quit.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.Exit.setIcon(icon3)

        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap(":IconFiles/version.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionVersion.setIcon(icon4)

        icon5 = QtGui.QIcon()
        icon5.addPixmap(QtGui.QPixmap(":IconFiles/help.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionHelp.setIcon(icon5)

        icon6 = QtGui.QIcon()
        icon6.addPixmap(QtGui.QPixmap(":IconFiles/tag.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionTag.setIcon(icon6)

        icon7 = QtGui.QIcon()
        icon7.addPixmap(QtGui.QPixmap(":IconFiles/view.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionView.setIcon(icon7)

        icon8 = QtGui.QIcon()
        icon8.addPixmap(QtGui.QPixmap(":IconFiles/pan.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionPan.setIcon(icon8)

        icon9 = QtGui.QIcon()
        icon9.addPixmap(QtGui.QPixmap(":IconFiles/zoom.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionZoom.setIcon(icon9)

        icon10 = QtGui.QIcon()
        icon10.addPixmap(QtGui.QPixmap(":IconFiles/config.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionConfig.setIcon(icon10)

        icon11 = QtGui.QIcon()
        icon11.addPixmap(QtGui.QPixmap(":IconFiles/forward.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionFwd.setIcon(icon11)

        icon12 = QtGui.QIcon()
        icon12.addPixmap(QtGui.QPixmap(":IconFiles/back.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionBck.setIcon(icon12)

        icon13 = QtGui.QIcon()
        icon13.addPixmap(QtGui.QPixmap(":IconFiles/edit.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionEdit.setIcon(icon13)

        icon14 = QtGui.QIcon()
        icon14.addPixmap(QtGui.QPixmap(":IconFiles/reset.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionReset.setIcon(icon14)

        icon15 = QtGui.QIcon()
        icon15.addPixmap(QtGui.QPixmap(":IconFiles/home.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionHome.setIcon(icon15)

        icon16 = QtGui.QIcon()
        icon16.addPixmap(QtGui.QPixmap(":IconFiles/print.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.actionPrint.setIcon(icon16)

        icon17 = QtGui.QIcon()
        icon17.addPixmap(QtGui.QPixmap(":IconFiles/vscurve.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionVS.setIcon(icon17)

        icon18 = QtGui.QIcon()
        icon18.addPixmap(QtGui.QPixmap(":IconFiles/cyclecurve.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionCS.setIcon(icon18)


# 周期界面类
class Cyclewindow(QtWidgets.QMainWindow, CycleWin):
    def __init__(self):
        super(Cyclewindow, self).__init__()
        self.setupUi(self)
        logicon = QtGui.QIcon()
        logicon.addPixmap(QtGui.QPixmap(":IconFiles/BZT.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(logicon)
        self.icon_from_file()
        self.actionCycleSave.triggered.connect(self.save_log)
        self.actionCopy.triggered.connect(self.copy_cliperboard)

    # 事件处理函数，向指定路径中写入该周期
    def save_log(self, str_list=list):
        filepath = QtWidgets.QFileDialog.getSaveFileName(self, "Save file", "d:/", "txt files(*.txt)")
        if filepath != ('', ''):
            f = open(filepath[0], "w")
            f.write(str(self.textEdit.toPlainText()))
            f.close()
            self.statusBar.showMessage(filepath[0] + "成功保存该周期！")
        else:
            pass

    # 事件处理函数，复制当前周期内容
    def copy_cliperboard(self):
        cliper = QtWidgets.QApplication.clipboard()
        cliper.setText(str(self.textEdit.toPlainText()))
        self.statusBar.showMessage("成功复制周期！")

    # 用于将图标资源文件打包
    def icon_from_file(self):
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":IconFiles/copy.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionCopy.setIcon(icon)

        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":IconFiles/save.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionCycleSave.setIcon(icon1)

if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    window = Mywindow()
    window.show()
    sys.exit(app.exec_())