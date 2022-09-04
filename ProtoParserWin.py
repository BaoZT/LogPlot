# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'e:\99-MyPythonProjects\LogPlot\ProtoParserWin.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(649, 486)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.splitter = QtWidgets.QSplitter(self.centralwidget)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setObjectName("splitter")
        self.textEdit = QtWidgets.QTextEdit(self.splitter)
        self.textEdit.setObjectName("textEdit")
        self.treeWidget = QtWidgets.QTreeWidget(self.splitter)
        self.treeWidget.setMinimumSize(QtCore.QSize(0, 300))
        self.treeWidget.setMidLineWidth(2)
        self.treeWidget.setObjectName("treeWidget")
        self.treeWidget.header().setHighlightSections(True)
        self.treeWidget.header().setMinimumSectionSize(31)
        self.verticalLayout.addWidget(self.splitter)
        self.verticalLayout.setStretch(0, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 649, 26))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.toolBar = QtWidgets.QToolBar(MainWindow)
        self.toolBar.setObjectName("toolBar")
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        self.actionParse = QtWidgets.QAction(MainWindow)
        self.actionParse.setObjectName("actionParse")
        self.toolBar.addAction(self.actionParse)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.treeWidget.headerItem().setText(0, _translate("MainWindow", "帧类型"))
        self.treeWidget.headerItem().setText(1, _translate("MainWindow", "字段名"))
        self.treeWidget.headerItem().setText(2, _translate("MainWindow", "比特数"))
        self.treeWidget.headerItem().setText(3, _translate("MainWindow", "字段值"))
        self.treeWidget.headerItem().setText(4, _translate("MainWindow", "含义结果"))
        self.toolBar.setWindowTitle(_translate("MainWindow", "toolBar"))
        self.actionParse.setText(_translate("MainWindow", "开始解析"))

