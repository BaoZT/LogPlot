# LogPlot
创建该工具用于读取纪录文件数据并绘图，用于研发人员分析控车过程
## 基本功能
### 各种速度曲线绘制
能够按照周期读取数据，并按照距离或者周期绘制曲线，同时可以通过光标移位查看每个周期的数据，也可以锁定光标来单步查找。并支持曲线放大、缩小、拖拽等
增加计划和MVB同周期刷新
### 增加离线事件
提供应答器和JD应答器、呼叫包及计划更新
### 增加实时解析功能
支持实时控车数据，MVB数据和计划信息解析查看，并绘制控车曲线
### 提供MVB和UTC小工具
支持MVB记录中端口配置
### 数据包搜索解析
未完成，目前仅能读取记录中解析好的数据包内容

## V3.0.0待实现功能

此版本主要是解决实时显示分析功能，除此之外，兼容现场调试对于设备状态检查的功能。

1. 实时功能上：

   >  应答器数据列表实时更新
   >
   > IO采集量实时更新，4个门按钮，1个发车按钮，2个开关
   >
   > ATP/ATO速传数据比对检查（做到分析界面）

2. 检查功能上

>IO采集量实时更新，4个门按钮，1个发车按钮，2个开关
>
>ATP/ATO速传数据比对检查（做到分析界面）
>
>电台状态、MVB连接状态、车辆允许反馈—既有内容，已实现。

