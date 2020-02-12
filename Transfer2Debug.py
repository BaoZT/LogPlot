from CommonParse import BytesStream
import threading
import time
from PyQt5 import QtCore

# 定义记录消息头结构
msg_head_width = [8, 8, 10, 2, 1, 32, 32, 32, 32, 16, 3]
str_head_name = ['escap_head', 'nid_msg', 'l_msg', 'nid_modle', 'q_standby', 'n_cycle',
                 't_ato', 't_atoutc', 'm_pos', 'v_speed', 'm_atomode']

head_tcms2ato = 'MVB[3346]:039A120D'
head_ato_ctrl = 'MVB[3344]:01CF100D'
head_ato_state = 'MVB[3345]:01CF110D'


class TransRecord(QtCore.QObject):
    FileTransOnePercentSingal = QtCore.pyqtSignal(int)      # 当前文件转义百分之1
    FileTransCompleteSingal = QtCore.pyqtSignal()           # 当前文件完成转义
    FileTransErrSingal = QtCore.pyqtSignal(str)           # 当前转义错误

    def __init__(self):
        super().__init__()
        # 公共变量
        self.dic_msg = {}
        self.dic_mvb = {}
        self.dic_sdu = {}
        self.dic_atp2ato_pkt = {}
        self.dic_ato2atp_pkt = {}
        self.dic_rp = {}
        # 涉及静态变量
        self.g_q_platform = '0'
        self.g_o_jd = '0'
        self.g_o_stn_dis = '0'
        self.g_o_ma = '0'
        self.g_ato_stop_err = '0'
        self.g_stop_use = '0'

    def InerEscapeReverse(self, stream=str):
        """
        反转义函数，将每一条记录数据反转义并返回
        :param stream: 输入十六进制字节字符串
        :return: 返回反转义后的
        """
        # 首先检测帧头帧尾
        if stream[:2] == '7E' and stream[(len(stream)-2):] == '7F':
            pass
        else:
            self.FileTransErrSingal.emit('--->err stream: '+stream)
            return ''
        ori_bytes_str = stream[2:(len(stream)-2)]

        if '7E' in ori_bytes_str:
            idx1 = ori_bytes_str.index('7E')
            if idx1 % 2 == 0:
               self.FileTransErrSingal.emit('fatal error, not a stream!')
            else:
                pass
        # 转义内容
        for idx in range(0, len(ori_bytes_str), 2):
            tmp = ori_bytes_str[idx:idx+2]
            if '7D' == tmp:
                ori_bytes_str = ori_bytes_str[:idx+1] + ori_bytes_str[idx+3:]
            else:
                pass
        return '7E'+ori_bytes_str+'7F'

    @staticmethod
    def BatchLineCount(fileList):
        sum = 0     # 利用了Python的大数运算
        for f in fileList:
            sum = sum + TransRecord.BufLineCount(f)
        return sum

    @staticmethod
    def BufLineCount(file):
        with open(file, 'r') as f:
            lines = 0
            buf_size = 1024 * 1024
            read_f = f.read  # loop optimization
            buf = read_f(buf_size)
            while buf:
                lines += buf.count('\n')
                buf = read_f(buf_size)
            f.seek(0, 0)  # back to head
        return lines

    def CtrlProcessTransfer(self, rawRecord):
        """
        对于每一条原始记录板信息进行处理
        :param rawRecord: 原始记录信息
        :return: 函数执行返回值和数据解析结果 ret_sig:0=政常,-1=错误消息,-2=存在启机过程
        """
        # 清空数据包字典
        self.dic_atp2ato_pkt = {}
        self.dic_ato2atp_pkt = {}

        ret_sig = 0        # 返回值指示
        streamReverseEsc = self.InerEscapeReverse(rawRecord)  # 反转义每一条记录
        if streamReverseEsc == '':
            ret_sig = -1
            return ret_sig
        item = BytesStream(streamReverseEsc)            # 创建解析对象
        # 解析消息头
        #print('*' * 30 + 'MSG_HEAD ' + '*' * 30)
        for idx, content in enumerate(msg_head_width):
            #print(str_head_name[idx] + ':' + str(item.fast_get_segment_by_index(item.curBitsIndex, msg_head_width[idx])))
            self.dic_msg[str_head_name[idx]] = str(item.fast_get_segment_by_index(item.curBitsIndex, msg_head_width[idx]))

        #print('*' * 30 + 'MSG_CONTENT ' + '*' * 30)
        # 解析内容
        while item.curBitsIndex < len(item.get_stream_in_bytes())*8-1:
            nid = item.fast_get_segment_by_index(item.curBitsIndex, 8)
            #print('nid:' + str(nid))
            l_pkt = item.fast_get_segment_by_index(item.curBitsIndex, 13)
            #print('l_pkt:' + str(l_pkt))
            if nid == 0:
                mvb_recv = hex(item.fast_get_segment_by_index(item.curBitsIndex, l_pkt - 21)).upper()[2:]
                if len(mvb_recv) % 2 == 0:
                    self.dic_mvb['tcms2ato'] = head_tcms2ato + mvb_recv
                else:
                    self.dic_mvb['tcms2ato'] = head_tcms2ato + '0' + mvb_recv
            elif nid == 1:
                ato_ctrl = hex(item.fast_get_segment_by_index(item.curBitsIndex, l_pkt - 21)).upper()[2:]
                if len(ato_ctrl) % 2 == 0:
                    self.dic_mvb['ato2tcms_ctrl'] = head_ato_ctrl + ato_ctrl
                else:
                    self.dic_mvb['ato2tcms_ctrl'] = head_ato_ctrl + '0' + ato_ctrl
            elif nid == 2:
                ato_state = hex(item.fast_get_segment_by_index(item.curBitsIndex, l_pkt - 21)).upper()[2:]
                if len(ato_ctrl) % 2 == 0:
                    self.dic_mvb['ato2tcms_state'] = head_ato_state + ato_state
                else:
                    self.dic_mvb['ato2tcms_state'] = head_ato_state + '0'+ato_state
            elif nid == 3:
                item.fast_get_segment_by_index(item.curBitsIndex, 8)
                l_msg = item.fast_get_segment_by_index(item.curBitsIndex, 8)
                # 记录bit数
                bit_idx = item.curBitsIndex
                byte_idx = item.curBytesIndex
                # 以下为lpacket描述范围
                item.fast_get_segment_by_index(item.curBitsIndex, 8)
                all_len = item.fast_get_segment_by_index(item.curBitsIndex, 13)
                # 监测ATP2ATO数据包（L_PACKET）
                while all_len != (item.curBitsIndex - bit_idx):
                    nid = item.fast_get_segment_by_index(item.curBitsIndex, 8)
                    if nid == 0:
                        item.fast_get_segment_by_index(item.curBitsIndex, 13)
                        item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        item.fast_get_segment_by_index(item.curBitsIndex, 24)  # NID_LRBG
                        item.fast_get_segment_by_index(item.curBitsIndex, 15)
                        item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        item.fast_get_segment_by_index(item.curBitsIndex, 15)
                        item.fast_get_segment_by_index(item.curBitsIndex, 15)
                        Q_LENGTH = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        # 列车完整性确认
                        if Q_LENGTH == 1 or Q_LENGTH == 2:
                            L_TRAINT = item.fast_get_segment_by_index(item.curBitsIndex, 15)
                            item.fast_get_segment_by_index(item.curBitsIndex, 7)
                            item.fast_get_segment_by_index(item.curBitsIndex, 2)
                            item.fast_get_segment_by_index(item.curBitsIndex, 4)
                            M_LEVEL =  item.fast_get_segment_by_index(item.curBitsIndex, 3)
                            if M_LEVEL == 1:
                                NID_STM = item.fast_get_segment_by_index(item.curBitsIndex, 8)
                        else:
                            item.fast_get_segment_by_index(item.curBitsIndex, 7)
                            item.fast_get_segment_by_index(item.curBitsIndex, 2)
                            item.fast_get_segment_by_index(item.curBitsIndex, 4)
                            M_LEVEL = item.fast_get_segment_by_index(item.curBitsIndex, 3)
                            if M_LEVEL == 1:
                                NID_STM = item.fast_get_segment_by_index(item.curBitsIndex, 8)
                    elif nid == 1:
                        item.fast_get_segment_by_index(item.curBitsIndex, 13)
                        item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        item.fast_get_segment_by_index(item.curBitsIndex, 24)  # NID_LRBG
                        item.fast_get_segment_by_index(item.curBitsIndex, 24)  # NID_PRVBG
                        item.fast_get_segment_by_index(item.curBitsIndex, 15)
                        item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        item.fast_get_segment_by_index(item.curBitsIndex, 15)
                        item.fast_get_segment_by_index(item.curBitsIndex, 15)
                        Q_LENGTH = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        # 列车完整性确认
                        if Q_LENGTH == 1 or Q_LENGTH == 2:
                            L_TRAINT = item.fast_get_segment_by_index(item.curBitsIndex, 15)
                            item.fast_get_segment_by_index(item.curBitsIndex, 7)
                            item.fast_get_segment_by_index(item.curBitsIndex, 2)
                            item.fast_get_segment_by_index(item.curBitsIndex, 4)
                            M_LEVEL = item.fast_get_segment_by_index(item.curBitsIndex, 3)
                            if M_LEVEL == 1:
                                NID_STM = item.fast_get_segment_by_index(item.curBitsIndex, 8)
                        else:
                            item.fast_get_segment_by_index(item.curBitsIndex, 7)
                            item.fast_get_segment_by_index(item.curBitsIndex, 2)
                            item.fast_get_segment_by_index(item.curBitsIndex, 4)
                            M_LEVEL = item.fast_get_segment_by_index(item.curBitsIndex, 3)
                            if M_LEVEL == 1:
                                NID_STM = item.fast_get_segment_by_index(item.curBitsIndex, 8)
                    elif nid == 2:
                        q_atopermit = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        q_ato_hardpermit = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        q_leftdoorpermit = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        q_rightdoorpermit =  item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        q_door_cmd_dir =  item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        q_tb = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        v_target = item.fast_get_segment_by_index(item.curBitsIndex, 16)
                        d_target = item.fast_get_segment_by_index(item.curBitsIndex, 32)
                        m_level = item.fast_get_segment_by_index(item.curBitsIndex, 3)  # M_LEVEL
                        m_mode = item.fast_get_segment_by_index(item.curBitsIndex, 4)  # M_MODE
                        o_train_pos = item.fast_get_segment_by_index(item.curBitsIndex, 32)
                        v_permitted = item.fast_get_segment_by_index(item.curBitsIndex, 16)
                        d_ma = item.fast_get_segment_by_index(item.curBitsIndex, 16)
                        m_ms_cmd = item.fast_get_segment_by_index(item.curBitsIndex, 2)  # M_MS_CMD
                        d_neu_sec = item.fast_get_segment_by_index(item.curBitsIndex, 16) # D_DEU_SEC
                        m_low_frequency = item.fast_get_segment_by_index(item.curBitsIndex, 8)
                        q_stopstatus = item.fast_get_segment_by_index(item.curBitsIndex, 4)
                        m_atp_stop_err = item.fast_get_segment_by_index(item.curBitsIndex, 16)
                        d_station_mid_pos = item.fast_get_segment_by_index(item.curBitsIndex, 32)
                        d_jz_sig_pos = item.fast_get_segment_by_index(item.curBitsIndex, 32)
                        d_cz_sig_pos = item.fast_get_segment_by_index(item.curBitsIndex, 32)
                        d_tsm = item.fast_get_segment_by_index(item.curBitsIndex, 32)
                        m_cab_state = item.fast_get_segment_by_index(item.curBitsIndex, 2) # M_CAB_STATE
                        m_position = item.fast_get_segment_by_index(item.curBitsIndex, 32)
                        m_tco_state = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        reserve = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        # 解析到2包
                        self.dic_atp2ato_pkt[2] = [q_atopermit, q_ato_hardpermit, q_leftdoorpermit, q_rightdoorpermit,
                                              q_door_cmd_dir, q_tb, v_target, d_target, m_level, m_mode, o_train_pos,
                                              v_permitted, d_ma, m_ms_cmd, d_neu_sec, m_low_frequency, q_stopstatus,
                                              m_atp_stop_err, d_station_mid_pos, d_jz_sig_pos, d_cz_sig_pos, d_tsm,
                                              m_cab_state, m_position, m_tco_state, reserve]
                    elif nid == 3:
                        item.fast_get_segment_by_index(item.curBitsIndex, 32)
                    elif nid == 4:
                        self.dic_sdu['atp_v'] = item.fast_get_segment_by_index(item.curBitsIndex, 16, sign=1)
                        self.dic_sdu['atp_s'] = item.fast_get_segment_by_index(item.curBitsIndex, 32)
                    elif nid == 5:
                        n_units = item.fast_get_segment_by_index(item.curBitsIndex, 8)
                        nid_operational = item.fast_get_segment_by_index(item.curBitsIndex, 32)
                        nid_driver = item.fast_get_segment_by_index(item.curBitsIndex, 32)
                        btm_antenna_position = item.fast_get_segment_by_index(item.curBitsIndex, 8)
                        l_door_dis = item.fast_get_segment_by_index(item.curBitsIndex, 16)
                        l_sdu_wh_size_1 = item.fast_get_segment_by_index(item.curBitsIndex, 16)
                        l_sdu_wh_size_2 = item.fast_get_segment_by_index(item.curBitsIndex, 16)
                        t_cutoff_traction = item.fast_get_segment_by_index(item.curBitsIndex, 16)
                        nid_engine = item.fast_get_segment_by_index(item.curBitsIndex, 24)
                        v_ato_permitted = item.fast_get_segment_by_index(item.curBitsIndex, 4)
                        self.dic_atp2ato_pkt[5] = [n_units, nid_operational, nid_driver, btm_antenna_position, l_door_dis,
                                              l_sdu_wh_size_1, l_sdu_wh_size_2, t_cutoff_traction, nid_engine,
                                              v_ato_permitted]
                    elif nid == 6:
                        item.fast_get_segment_by_index(item.curBitsIndex, 8)
                        item.fast_get_segment_by_index(item.curBitsIndex, 8)
                        item.fast_get_segment_by_index(item.curBitsIndex, 8)
                        item.fast_get_segment_by_index(item.curBitsIndex, 8)
                        item.fast_get_segment_by_index(item.curBitsIndex, 8)
                        item.fast_get_segment_by_index(item.curBitsIndex, 8)
                    elif nid == 7:
                        nid_bg = item.fast_get_segment_by_index(item.curBitsIndex, 24)
                        t_middle = item.fast_get_segment_by_index(item.curBitsIndex, 32)
                        d_pos_adj = item.fast_get_segment_by_index(item.curBitsIndex, 32, sign=1)
                        NID_XUSER = item.fast_get_segment_by_index(item.curBitsIndex, 9)
                        # 解析到7包
                        self.dic_atp2ato_pkt[7] = [nid_bg, t_middle, d_pos_adj, NID_XUSER]
                        if NID_XUSER == 13:
                            q_scale = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                            q_platform = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                            q_door = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                            n_d = item.fast_get_segment_by_index(item.curBitsIndex, 24)
                            d_stop = item.fast_get_segment_by_index(item.curBitsIndex, 15)
                            # 解析到7包
                            self.dic_atp2ato_pkt[7] = [nid_bg, t_middle, d_pos_adj, NID_XUSER, q_scale, q_platform,
                                                       q_door, n_d, d_stop]
                    elif nid == 8:
                        q_tsrs = item.fast_get_segment_by_index(item.curBitsIndex, 1)
                        nid_c = item.fast_get_segment_by_index(item.curBitsIndex, 10)
                        nid_tsrs = item.fast_get_segment_by_index(item.curBitsIndex, 14)
                        nid_radio_h = item.fast_get_segment_by_index(item.curBitsIndex, 32)
                        nid_radio_l = item.fast_get_segment_by_index(item.curBitsIndex, 32)
                        q_sleepssion = item.fast_get_segment_by_index(item.curBitsIndex, 1)
                        m_type = item.fast_get_segment_by_index(item.curBitsIndex, 3)
                        # 解析到8包
                        self.dic_atp2ato_pkt[8] = [q_tsrs, nid_c, nid_tsrs, nid_radio_h, nid_radio_l, q_sleepssion, m_type]
                    elif nid == 9:
                        N_ITER = item.fast_get_segment_by_index(item.curBitsIndex, 5)
                        for i in range(N_ITER):
                            item.fast_get_segment_by_index(item.curBitsIndex, 32)
                            item.fast_get_segment_by_index(item.curBitsIndex, 32)
                            item.fast_get_segment_by_index(item.curBitsIndex, 4)
                    else:
                        print('err!!!!!')
                # 消息校验和监测
                if all_len == (item.curBitsIndex - bit_idx):
                    if (all_len + 16) % 8 == 0:    # 刚好除整数
                        pass
                    else: # 重新校正bit索引
                        padding_bit = int(((all_len + 16 + 7) // 8) * 8) - all_len - 16  # 字节下跳的bit数，减去消息头16bit和内容bit后
                        item.fast_get_segment_by_index(item.curBitsIndex, padding_bit)
                    # 计算分析消息结尾
                    item.fast_get_segment_by_index(item.curBitsIndex, 32)
                    item.fast_get_segment_by_index(item.curBitsIndex, 32)
                    item.fast_get_segment_by_index(item.curBitsIndex, 32)
                    if l_msg == item.curBytesIndex - byte_idx + 2:
                        pass  # 消息校验正确不打印
                    else:
                        print('fatal err！ l_msg %d, real %d' % (l_msg, item.curBytesIndex - byte_idx + 2))
            elif nid == 4:
                item.fast_get_segment_by_index(item.curBitsIndex, 8)
                l_msg = item.fast_get_segment_by_index(item.curBitsIndex, 8)
                # 记录bit数
                bit_idx = item.curBitsIndex
                byte_idx = item.curBytesIndex
                # 以下为lpacket描述范围
                item.fast_get_segment_by_index(item.curBitsIndex, 8)
                all_len = item.fast_get_segment_by_index(item.curBitsIndex, 13)
                # 监测ATO2ATP数据包（L_PACKET）
                while all_len != (item.curBitsIndex - bit_idx):
                    nid = item.fast_get_segment_by_index(item.curBitsIndex, 8)
                    if nid == 130:
                        m_ato_mode = item.fast_get_segment_by_index(item.curBitsIndex, 4)
                        m_door_mode = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        m_door_status = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        m_atoerror = item.fast_get_segment_by_index(item.curBitsIndex, 16)
                        m_ato_stop_error = item.fast_get_segment_by_index(item.curBitsIndex, 16)
                        self.dic_ato2atp_pkt[130] = [m_atoerror, m_ato_mode, m_ato_stop_error, m_door_mode, m_door_status]
                    elif nid == 131:
                        m_ato_tbs = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        m_ato_skip = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        m_ato_plan = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        m_ato_time = item.fast_get_segment_by_index(item.curBitsIndex, 16)
                        m_tcms_com = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        m_gprs_radio = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        m_gprs_session = item.fast_get_segment_by_index(item.curBitsIndex, 2)
                        m_ato_control_strategy = item.fast_get_segment_by_index(item.curBitsIndex, 4)
                        paddings = item.fast_get_segment_by_index(item.curBitsIndex, 16)
                        self.dic_ato2atp_pkt[131] = [m_ato_plan, m_ato_skip, m_ato_tbs, m_ato_time, m_gprs_radio,
                                                     m_gprs_session, m_tcms_com, m_ato_control_strategy, paddings]
                    elif nid == 132:
                        pass
                    elif nid == 133:
                        item.fast_get_segment_by_index(item.curBitsIndex, 10)
                        item.fast_get_segment_by_index(item.curBitsIndex, 14)
                        item.fast_get_segment_by_index(item.curBitsIndex, 64)
                    elif nid == 134:
                        item.fast_get_segment_by_index(item.curBitsIndex, 8)
                        item.fast_get_segment_by_index(item.curBitsIndex, 1)
                        L_TEXT = item.fast_get_segment_by_index(item.curBitsIndex, 8)
                        for i in range(L_TEXT):
                            item.fast_get_segment_by_index(item.curBitsIndex, 8)
                    else:
                        print('err!!!!!')
                # 消息校验和监测
                if all_len == (item.curBitsIndex - bit_idx):
                    if (all_len + 16) % 8 == 0:  # 刚好除整数
                        pass
                    else:  # 重新校正bit索引
                        padding_bit = int(((all_len + 16 + 7) // 8) * 8) - all_len - 16  # 字节下跳的bit数，减去消息头16bit和内容bit后
                        item.fast_get_segment_by_index(item.curBitsIndex, padding_bit)
                    # 计算分析消息结尾
                    item.fast_get_segment_by_index(item.curBitsIndex, 32)
                    item.fast_get_segment_by_index(item.curBitsIndex, 32)
                    item.fast_get_segment_by_index(item.curBitsIndex, 32)
                    if l_msg == item.curBytesIndex - byte_idx + 2:
                        pass  # 消息校验正确不打印
                    else:
                        print('fatal err！ l_msg %d, real %d' % (l_msg, item.curBytesIndex - byte_idx + 2))
            elif nid == 9:
                self.dic_sdu['ato_v'] = item.fast_get_segment_by_index(item.curBitsIndex, 16)
                self.dic_sdu['ato_s'] = item.fast_get_segment_by_index(item.curBitsIndex, 32)
            # elif nid == 25:
            #     rp_start_train = item.fast_get_segment_by_index(item.curBitsIndex, 1)
            #     rp_final_station = item.fast_get_segment_by_index(item.curBitsIndex, 1)
            #     rp_q_pl_legal = item.fast_get_segment_by_index(item.curBitsIndex, 1)
            #     rp_pl_update = item.fast_get_segment_by_index(item.curBitsIndex, 32)
            #     rp_pl_num = item.fast_get_segment_by_index(item.curBitsIndex, 2)
            #     for rp_cnt in range(rp_pl_num):
            #         rp_ob_sys_time = item.fast_get_segment_by_index(item.curBitsIndex, 32)
            #         rp_wayside_time = item.fast_get_segment_by_index(item.curBitsIndex, 32)
            #         rp_pl_legal_arrival_time = item.fast_get_segment_by_index(item.curBitsIndex, 32)
            #         rp_pl_legal_depart_time = item.fast_get_segment_by_index(item.curBitsIndex, 32)
            #         rp_pl_legal_arrival_track = item.fast_get_segment_by_index(item.curBitsIndex, 24)
            #         rp_pl_legal_depart_track = item.fast_get_segment_by_index(item.curBitsIndex, 24)
            #         rp_pl_legal_skip = item.fast_get_segment_by_index(item.curBitsIndex, 2)
            #         rp_pl_legal_task = item.fast_get_segment_by_index(item.curBitsIndex, 2)
            #     rp_pl_out_time = item.fast_get_segment_by_index(item.curBitsIndex, 1)
            #     rp_pl_stn_state = item.fast_get_segment_by_index(item.curBitsIndex, 2)
            #     rp_pl_track_balise = item.fast_get_segment_by_index(item.curBitsIndex, 24)
            #     rp_pl_track_plan = item.fast_get_segment_by_index(item.curBitsIndex, 24)
            #     rp_pl_in_use = item.fast_get_segment_by_index(item.curBitsIndex, 2)
            #     rp_pl_valid = item.fast_get_segment_by_index(item.curBitsIndex, 1)
            #     rp_pl_output_arr_time = item.fast_get_segment_by_index(item.curBitsIndex, 32)
            #     rp_pl_output_depart_time = item.fast_get_segment_by_index(item.curBitsIndex, 32)
            #     rp_pl_output_skip = item.fast_get_segment_by_index(item.curBitsIndex, 2)
            #     rp_pl_output_task = item.fast_get_segment_by_index(item.curBitsIndex, 2)
            elif nid == 53:   # ATO停车状态
                q_stable = str(item.fast_get_segment_by_index(item.curBitsIndex, 2))
                q_real_stable = str(item.fast_get_segment_by_index(item.curBitsIndex, 2))
                ato_stop_err = str(item.fast_get_segment_by_index(item.curBitsIndex, 16, sign=1))
                self.dic_msg['stop_state'] = (q_stable, q_real_stable, ato_stop_err)
            elif nid == 52:
                o_jd_stop = str(item.fast_get_segment_by_index(item.curBitsIndex, 32))
                o_stn_dis_stop = str(item.fast_get_segment_by_index(item.curBitsIndex, 32))
                o_mid_stop = str(item.fast_get_segment_by_index(item.curBitsIndex, 32))
                o_ma_stop = str(item.fast_get_segment_by_index(item.curBitsIndex, 32))
                o_stop_use = str(item.fast_get_segment_by_index(item.curBitsIndex, 32))
                q_platform = str(item.fast_get_segment_by_index(item.curBitsIndex, 1))
                self.dic_msg['stop'] = (o_jd_stop, o_stn_dis_stop, o_mid_stop, o_ma_stop, o_stop_use, q_platform)
            elif nid == 54:
                v_ato_cmd = str(item.fast_get_segment_by_index(item.curBitsIndex, 16))
                v_atp_cmd = str(item.fast_get_segment_by_index(item.curBitsIndex, 16))
                ctrl_machine = str(item.fast_get_segment_by_index(item.curBitsIndex, 6))
                adj_ramp = str(item.fast_get_segment_by_index(item.curBitsIndex, 8, sign=1))
                adj_es_ramp = str(item.fast_get_segment_by_index(item.curBitsIndex, 8, sign=1))
                v_s_target = str(item.fast_get_segment_by_index(item.curBitsIndex, 16))
                o_s_target = str(item.fast_get_segment_by_index(item.curBitsIndex, 32))
                lvl_raw = str(item.fast_get_segment_by_index(item.curBitsIndex, 8, sign=1))
                lvl_filter_b = str(item.fast_get_segment_by_index(item.curBitsIndex, 8, sign=1))
                lvl_filter_p = str(item.fast_get_segment_by_index(item.curBitsIndex, 8, sign=1))
                lvl_filter_ramp = str(item.fast_get_segment_by_index(item.curBitsIndex, 8, sign=1))
                lvl_filter_wind = str(item.fast_get_segment_by_index(item.curBitsIndex, 8, sign=1))
                lvl_filter_gfx = str(item.fast_get_segment_by_index(item.curBitsIndex, 8, sign=1))
                lvl_filter_out = str(item.fast_get_segment_by_index(item.curBitsIndex, 8, sign=1))
                q_ato_cutoff = str(item.fast_get_segment_by_index(item.curBitsIndex, 4))
                o_es_pos = str(item.fast_get_segment_by_index(item.curBitsIndex, 32))
                v_es_speed = str(item.fast_get_segment_by_index(item.curBitsIndex, 16))
                o_ma = str(item.fast_get_segment_by_index(item.curBitsIndex, 32))
                # 解析到了关键包
                self.dic_msg['sc'] = (self.dic_msg['m_pos'], self.dic_msg['v_speed'], v_ato_cmd, v_atp_cmd,
                                      lvl_filter_out, lvl_filter_out, o_es_pos, v_es_speed, adj_ramp, adj_es_ramp,
                                      v_s_target, o_s_target, o_ma, o_ma, ctrl_machine)
            elif nid == 84:
                item.fast_get_segment_by_index(item.curBitsIndex, 8)   # 主控主版本
                item.fast_get_segment_by_index(item.curBitsIndex, 8)   # 主控中版本
                item.fast_get_segment_by_index(item.curBitsIndex, 8)   # 主控小版本
                ret_sig = -2
                return ret_sig   # 存在启机过程，重新生成解析文件
            else:
                item.fast_get_segment_by_index(item.curBitsIndex, l_pkt - 21)
                #print('content:' + hex(item.fast_get_segment_by_index(item.curBitsIndex, l_pkt - 21)))

            # 记录板消息，下一次监测前，判断退出
            if item.curBitsIndex >= len(item.get_stream_in_bytes())*8-1-8-8:
                break
        else:
            pass
        # 解析完成
        return ret_sig

    def TransContent(self, path_read=str, path_write=str):
        """
        读取记录板文件并转义为串口工具可读取文件
        :param path_read: 读取文件路径
        :param path_write: 写入文件路径
        :return: None
        """
        singleFileSum = TransRecord.BufLineCount(path_read)
        # 相邻两次百分比计数，减少信号量发送频次
        percentValue = 0
        oldPercentValue = 0
        singleLineCount = 0
        # 初始化计算结果
        ret_sig = 1
        # 处理文件分割
        trans_part = 0
        tmp_path_write = path_write   # 记录原始路径，用于后续创建
        # 读取记录文件
        with open(path_read, 'r') as fr:
            # 需执行到所有文件处理结束
            while True:
                # 创建转义后的文件,path_write动态计算
                with open(path_write, 'w') as fw:
                    # 遍历记录文件
                    for item in fr:
                        try:
                            ret_sig = self.CtrlProcessTransfer(item.rstrip())
                        except Exception as errInfo:
                            print(errInfo)
                        # 释放进度条
                        singleLineCount = singleLineCount + 1           # 行号加一
                        percentValue = percentValue + 100/singleFileSum # 小数表示，可能不足100或大于100，表示基本累加值
                        if abs(percentValue - oldPercentValue) >= 1:    # 避免信号量海量发送
                            self.FileTransOnePercentSingal.emit(int(percentValue + 1))
                            oldPercentValue = percentValue
                        # 若获取到结果
                        if ret_sig == 0:
                            t_ato = self.dic_msg['t_ato']
                            n_cycle = self.dic_msg['n_cycle']
                            m_atomode = self.dic_msg['m_atomode']
                            dt = time.gmtime(int(self.dic_msg['t_atoutc']) + 3600*8)

                            if 'stop' in self.dic_msg.keys():
                                stop = self.dic_msg['stop']
                                self.g_q_platform = stop[5]
                                self.g_o_ma = stop[3]
                                self.g_o_jd = stop[0]
                                self.g_stop_use = stop[4]
                                self.g_o_stn_dis = stop[1]

                            if 'stop_state' in self.dic_msg.keys():
                                stop_state = self.dic_msg['stop_state']
                                self.g_ato_stop_err = stop_state[2]

                            # 所有完全的情况
                            if '3' == m_atomode or '2' == m_atomode:
                                fw.write('---CORE_TARK CY_B %s,%s---\n' % (t_ato, n_cycle))
                                fw.write('time:%s-%s-%s %s:%s:%s,system:M\n' % (dt.tm_year, dt.tm_mon, dt.tm_mday, dt.tm_hour,
                                                                              dt.tm_min, dt.tm_sec))
                                # 速传信息
                                if self.dic_sdu['atp_v'] and self.dic_sdu['atp_s']:
                                    fw.write('v&p_atp:%d,%d\n' % (self.dic_sdu['atp_v'], self.dic_sdu['atp_s']))
                                if self.dic_sdu['ato_v'] and self.dic_sdu['ato_s']:
                                    fw.write('v&p_ato:%d,%d\n' % (self.dic_sdu['ato_v'], self.dic_sdu['ato_s']))
                                # 模式状态
                                fw.write('FSM{%s %s 1 1 1 1}sg{2 0 1003934828 21000 AA 2B}ss{0 %s}\n' % (m_atomode,
                                                                                                         m_atomode,
                                                                                                         self.g_q_platform))
                                # 数据包
                                if 130 in self.dic_ato2atp_pkt.keys():
                                    fw.write('[O->P]SP130:')
                                    for idx, item in enumerate(self.dic_ato2atp_pkt[130]):
                                        fw.write(str(item)+',')
                                    fw.write('\n')
                                if 131 in self.dic_ato2atp_pkt.keys():
                                    fw.write('[O->P]SP131:')
                                    for item in self.dic_ato2atp_pkt[131]:
                                        fw.write(str(item)+',')
                                    fw.write('\n')
                                if 2 in self.dic_atp2ato_pkt.keys():
                                    fw.write('[P->O]SP2')
                                    for item in self.dic_atp2ato_pkt[2]:
                                        fw.write(',' + str(item))
                                    fw.write('\n')

                                if 5 in self.dic_atp2ato_pkt.keys():
                                    fw.write('[P->O]SP5,n_units %d,nid_operational %d,nid_driver %d,'
                                             'btm_antenna_position %d,l_door_dis %d, l_sdu_wh_size_1 %d,'
                                             'l_sdu_wh_size_2 %d,t_cutoff_traction %d,nid_engine %d,'
                                             'v_ato_permitted %d\n' % (self.dic_atp2ato_pkt[5][0],
                                                                       self.dic_atp2ato_pkt[5][1],
                                                                       self.dic_atp2ato_pkt[5][2],
                                                                       self.dic_atp2ato_pkt[5][3],
                                                                       self.dic_atp2ato_pkt[5][4],
                                                                       self.dic_atp2ato_pkt[5][5],
                                                                       self.dic_atp2ato_pkt[5][6],
                                                                       self.dic_atp2ato_pkt[5][7],
                                                                       self.dic_atp2ato_pkt[5][8],
                                                                       self.dic_atp2ato_pkt[5][9]))
                                if 8 in self.dic_atp2ato_pkt.keys():
                                    fw.write('[P->O]SP8,q_tsrs %d,nid_c %d,nid_tsrs %d,nid_radio_h %x,nid_radio_l %x,'
                                             'q_sleepssion %d, m_type %d\n' % (self.dic_atp2ato_pkt[8][0],
                                                                               self.dic_atp2ato_pkt[8][1],
                                                                               self.dic_atp2ato_pkt[8][2],
                                                                               self.dic_atp2ato_pkt[8][3],
                                                                               self.dic_atp2ato_pkt[8][4],
                                                                               self.dic_atp2ato_pkt[8][5],
                                                                               self.dic_atp2ato_pkt[8][6]))
                                if 7 in self.dic_atp2ato_pkt.keys():
                                    if self.dic_atp2ato_pkt[7][3] == 13:
                                        fw.write('[P->O]SP7,nid_bg %d,t_middle %d,d_pos_adj %d,nid_xuser %d,q_scale %d,'
                                                 'q_platform %d,q_door %d,n_d %d,d_stop %d\n' % (self.dic_atp2ato_pkt[7][0],
                                                                                                self.dic_atp2ato_pkt[7][1],
                                                                                                self.dic_atp2ato_pkt[7][2],
                                                                                                self.dic_atp2ato_pkt[7][3],
                                                                                                self.dic_atp2ato_pkt[7][4],
                                                                                                self.dic_atp2ato_pkt[7][5],
                                                                                                self.dic_atp2ato_pkt[7][6],
                                                                                                self.dic_atp2ato_pkt[7][7],
                                                                                                self.dic_atp2ato_pkt[7][8]))
                                    else:
                                        fw.write('[P->O]SP7,nid_bg %d,t_middle %d,d_pos_adj %d,nid_xuser 0,q_scale 0,'
                                                 'q_platform 0,q_door 0,n_d 0,d_stop 0\n' % (self.dic_atp2ato_pkt[7][0],
                                                                                             self.dic_atp2ato_pkt[7][1],
                                                                                             self.dic_atp2ato_pkt[7][2]))
                                if 'sc' in self.dic_msg.keys():
                                    sc = self.dic_msg['sc']
                                    fw.write('stoppoint:jd=%s ref=%s ma=%s\n' % (self.g_o_jd, self.g_o_stn_dis, self.g_o_ma))
                                    fw.write('SC{%s %s %s %s %s %s %s %s %s %s}t %s %s %s %s,%s} f %s %s %s -12} p1 2}CC\n'
                                            % (sc[0], sc[1], sc[2], sc[3], sc[4], sc[5], sc[6], sc[7], sc[8], sc[9],
                                                sc[10], sc[11], sc[12], sc[13], self.g_stop_use, self.g_ato_stop_err, sc[14],
                                               self.g_q_platform))
                                # MVB 数据
                                if self.dic_mvb['tcms2ato']:
                                    fw.write(self.dic_mvb['tcms2ato']+'\n')
                                if self.dic_mvb['ato2tcms_state']:
                                    fw.write(self.dic_mvb['ato2tcms_state']+'\n')
                                if self.dic_mvb['ato2tcms_ctrl']:
                                    fw.write(self.dic_mvb['ato2tcms_ctrl']+'\n')

                                fw.write('---CORE_TARK CY_E %s,%s---\n' % (t_ato, n_cycle))  # 显示周期尾
                        elif ret_sig == -2:     # 当解析出启机记录时
                            trans_part = trans_part+1
                            path_write = tmp_path_write.replace('.txt', str(trans_part)+'.txt')  # 创建新的文件
                            break
                        else:
                            pass   # 否则直接跳过
                    # 将缓冲写入当前文件
                    fw.flush()
                # 检查是否为文件分割还是其他执行
                if ret_sig == -2:
                    pass    # 其他情况均在遍历中执行完，ret_sig为 0，-1，1
                else:
                    break
        # 当前文件转义完成
        self.FileTransCompleteSingal.emit()


