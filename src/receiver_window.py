# Copyright 2024 ETRI. 
# License-identifier:GNU General Public License v3.0 or later
# yssong00@etri.re.kr

# This program is free software: you can redistribute it and/or modify 
# it under the terms of the GNU General Public License as published 
# by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; 
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. 
# If not, see <https://www.gnu.org/licenses/>.

""" Sensor Sharing Service for Receiver Widnow(Performance Monitoring) """

import os
import cv2
import csv
import json
import time
import math
import numpy
import serial
import pickle
import struct
import psutil
import requests
import haversine
import datetime as dt
import packet_header_struct
from socket import *
from scapy.all import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from collections import deque
from screeninfo import get_monitors
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebEngineWidgets import QWebEngineScript

# PyQT Windows Size
monitor_size_width = get_monitors()[0].width
monitor_size_height = get_monitors()[0].height
BLANK_SPACE = 15
GRAPH_WIN_SIZE_W = monitor_size_width - BLANK_SPACE*2
GRAPH_WIN_SIZE_H = int(monitor_size_height / 2) - BLANK_SPACE
VIDEO_WIN_SIZE_W = int(monitor_size_width / 2) - BLANK_SPACE
VIDEO_WIN_SIZE_H = int(monitor_size_height / 2) - BLANK_SPACE*3
NAVIGATION_WIN_SIZE_W = int(monitor_size_width / 2) - BLANK_SPACE
NAVIGATION_WIN_SIZE_H = int(monitor_size_height / 2) - BLANK_SPACE*3

# Socket Value
DEVICE_ADDR = '192.168.1.11'
DEVICE_PORT = 47347

# Packet Value
MAX_PACKET_SIZE = 1502
MAX_PAYLOAD_SIZE = 1300

# Camera Capture Size
RECV_FRAME_WIDTH = 300
RECV_FRAME_HEIGHT = 300

# GPS Sensor Variable
SER_PORT = 'COM4'  # Serial Port
SER_BAUD = 9600  # Serial Baud Rate

# Log Cycle
HEADER_LOG_CYCLE = 60  # Seconds

# RTT Variable
RTT_TIMER = 1

# Packet Variable
WS_REQ = b"\xf1\xf1\x00\x01\x00\x00\x00\x00\x00\x00\x14\x97\x00\x00\x00\x00"
WS_RESP_MAGIC_NUM = b'\xf1\xf2'
RX_MAGIC_NUM = b'\xf3\xf2'
VIDEO_DATA_INDICATOR = b'\x03\x01'
PING_INDICATOR = b'\x03\x02'

# Graph Data Variable
NET_IF = "이더넷 2"

# Navigation HTML File Path
HTML_FILE_PATH = './resource/Tmap.html'

# Bad Condition Data Variable
WEATHER_API_URL = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst'
WEATHER_API_SERVICE_KEY = 'QEPmvbFk9szqqPD8q9+s2ezoOOoY7VcAt4Rt1QPseyZ5LQucie5H9OjnJj/GO4H1I41QrmGWQxhCF9FGp42ZQA=='
WEATHER_CONDITION_WAIT_TIMER = 5
WEATHER_CONDITION_ERROR_RESEND_TIMER = 10
WEATHER_CONDITION_RESEND_TIMER = 600
ROAD_API_URL = 'https://apis.openapi.sk.com/tmap/traffic'
ROAD_API_SERVICE_KEY = 'fOsIyENUEf8ArejvlqGDU4p66eOsMRjB5kII22do'
ROAD_CONDITION_WAIT_TIMER = 5
ROAD_CONDITION_RESEND_TIMER = 120



sender_latitude = 37.570286992195
sender_longitude = 126.98361037914
latitude = 37.570286992195
longitude = 126.98361037914
road_condition = 0
weather_condition = 0
pdr_result = 0.0
throughput_result = 0.0
latency_result = 0.0
distance_result = 0.0
result_queue = deque()
webView = 0
wes_tag = True

def resource_path(relative_path):
    """ resource(icon, png) path """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class GPSWorker(QThread):
    """ GPS Processing for position """
    def __init__(self):
        """ init """
        super().__init__()
        global SER_PORT
        global SER_BAUD

        self.trig = True
        while True:
            try:
                self.ser = serial.Serial(SER_PORT, SER_BAUD)
                break
            except BaseException:
                print(traceback.format_exc())

    def run(self):
        """ GPS Data Processing """
        global latitude
        global longitude

        while self.trig:
            try:
                if self.ser.readable():  # Read data only readable chance
                    ser_resp = self.ser.readline()  # Read GPS data from GPS sensor
                    resp_data = ser_resp.decode().split(sep=',')  # Decode and Split data to use
                    if resp_data[0] == '$GPGLL':  # Read only GPGLL data
                        # Calculate GPS data ( DMS -> Degree )
                        # latitude & longitude
                        if resp_data[1]!=None and resp_data[3]!=None:
                            lat_val1 = math.trunc(float(resp_data[1]) / 100)
                            lat_val2 = float(resp_data[1]) % 100
                            lat_val2 = lat_val2 / 60
                            # longitude
                            long_val1 = math.trunc(float(resp_data[3]) / 100)
                            long_val2 = float(resp_data[3]) % 100
                            long_val2 = long_val2 / 60
                            
                            if (latitude != lat_val1 + lat_val2) and (longitude != long_val1 + long_val2):
                                if abs(lat_val1 + lat_val2)<=90 and abs(long_val1 + long_val2)<=180:
                                    latitude = lat_val1 + lat_val2
                                    longitude = long_val1 + long_val2
            except BaseException:
                print("GPS Error")
        self.ser.close()

    def stop(self):
        """ stop gps """
        self.trig = False
        self.quit()
        self.wait(100)

def create_log_folder():
    """ 5g-nr v2v sensor sharing service performance log file """
    now = dt.datetime.now() 
    try: 
        if not os.path.exists(now.strftime('%Y.%m.%d')): 
            os.makedirs(now.strftime('%Y.%m.%d')) 
    except OSError: 
        print('Error:Cannot creat directory.' + now.strftime('%Y.%m.%d')) 
    return now.strftime('%Y.%m.%d')

class SaveHeaderWorker(QThread):
    """ Add Message Header to log """
    info_signal = pyqtSignal(str)

    def __init__(self, info_box, header_q):
        """ init """
        super().__init__()

        self.info_box = info_box
        self.header_q = header_q
        self.trig = True

    def run(self):
        """ update logfile """
        global result_queue
        i = 0

        while self.trig:
            num_header = len(self.header_q)
            if num_header > 0:
                try:
                    now = dt.datetime.now()
                    past = now - dt.timedelta(minutes=1)
                    file_name = ("ETRI_OBU_01(RX용)_" + past.strftime('%Y.%m.%d.%H.%M') + "_"
                                 + now.strftime('%Y.%m.%d.%H.%M') + "_" + str(HEADER_LOG_CYCLE) + "seconds.csv")
                    folder_name = create_log_folder()
                    file_path = './'+folder_name+'/'+file_name
                    f = open(file_path, 'w', encoding='utf-8', newline='')
                    wr = csv.writer(f)
                    header_list = ['No.', 'eDeviceType', 'eTeleCommType', 'unDeviceId', 'ulTimeStamp',
                                   'eServiceId', 'eActionType', 'eRegionId', 'ePayloadType', 'eCommId', 'usDbVer',
                                   'usHwVer', 'usSwVer', 'ulPayloadLength', 'ulPayloadCrc32',
                                   'Road Condition', 'Weather Condition',
                                   'PDR', 'Throughput', 'Latency', 'Distance', 'Mileage']
                    wr.writerow(header_list)

                    i = 0
                    while True:
                        try:
                            header_log = self.header_q.popleft()

                            # DB_V2X  (length = 54)
                            eDeviceType = struct.unpack(">i", header_log[0][38:42])[0]
                            eTeleCommType = struct.unpack(">i", header_log[0][42:46])[0]
                            unDeviceId = struct.unpack(">i", header_log[0][46:50])[0]
                            eServiceId = struct.unpack(">i", header_log[0][58:62])[0]
                            eActionType = struct.unpack(">i", header_log[0][62:66])[0]
                            eRegionId = struct.unpack(">i", header_log[0][66:70])[0]
                            ePayloadType = struct.unpack(">i", header_log[0][70:74])[0]
                            eCommId = struct.unpack(">i", header_log[0][74:78])[0]
                            usDbVer = struct.unpack(">H", header_log[0][78:80])[0]
                            usHwVer = struct.unpack(">H", header_log[0][80:82])[0]
                            usSwVer = struct.unpack(">H", header_log[0][82:84])[0]
                            ulPayloadLength = struct.unpack(">i", header_log[0][84:88])[0]
                            ulPayloadCrc32 = struct.unpack(">i", header_log[0][88:92])[0]

                            # Calculated Results
                            road_condition_log = header_log[1]
                            weather_condition_log = header_log[2]
                            pdr_result_log = header_log[3]
                            throughput_result_log = header_log[4]
                            latency_result_log = header_log[5]
                            distance_result_log = header_log[6]
                            ulTimeStamp = header_log[9]

                            if i == 0:
                                mileage_log = 0
                                before_latitude = header_log[7]
                                before_longitude = header_log[8]
                            else:
                                mileage_log = mileage_log + haversine.haversine((before_latitude, before_longitude),
                                                                                (header_log[7], header_log[8]), unit='m')
                                before_latitude = header_log[7]
                                before_longitude = header_log[8]

                            log = [
                                i,
                                eDeviceType,
                                eTeleCommType,
                                unDeviceId,
                                ulTimeStamp,
                                eServiceId,
                                eActionType,
                                eRegionId,
                                ePayloadType,
                                eCommId,
                                usDbVer,
                                usHwVer,
                                usSwVer,
                                ulPayloadLength,
                                ulPayloadCrc32,
                                road_condition_log,
                                weather_condition_log,
                                pdr_result_log,
                                throughput_result_log,
                                latency_result_log,
                                distance_result_log,
                                mileage_log
                            ]

                            if now < header_log[9]:
                                break
                            else:
                                wr.writerow(log)
                                i = i+1
                        except BaseException:
                            break

                    f.close()
                    self.info_signal.emit(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n - Saving Log File\n(" + file_name + ")\n - Mileage : " + str(mileage_log))
                    time.sleep(HEADER_LOG_CYCLE)
                except BaseException:
                    print(traceback.format_exc())

    def stop(self):
        """ stop logfile """
        self.trig = False
        self.quit()
        self.wait(10)


class ViewWorker(QThread):
    """ View receive video-data """
    def __init__(self, frame, label):
        """ init """
        super().__init__()
        self.frame = frame
        self.video_label = label
        self.trig = True

    def run(self):
        """ show frame """
        while self.trig:
            try:
                show_frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
                image = QImage(show_frame, show_frame.shape[1], show_frame.shape[0], QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(image)
                self.video_label.setPixmap(pixmap)
            except BaseException:
                print(traceback.format_exc())
            time.sleep(0.02)
        self.video_label.setPixmap(QPixmap(resource_path('./resource/stop_icons.png')))

    def stop(self):
        """ stop video """
        self.trig = False
        self.quit()
        self.wait(10)


class ReceiveWorker(QThread):
    """ Receive Message Processing """
    def __init__(self, sock, frame, pkt_num_q, header_q):
        """ init """
        super().__init__()
        global DEVICE_ADDR
        global DEVICE_PORT
        global RECV_FRAME_WIDTH
        global RECV_FRAME_HEIGHT
        global WS_RESP_MAGIC_NUM
        global RX_MAGIC_NUM
        global VIDEO_DATA_INDICATOR
        global wes_tag

        self.show_frame = frame
        self.pkt_num_q = pkt_num_q
        self.header_q = header_q
        self.sock = sock
        self.trig = True
        while wes_tag:
            try:
                self.sock.send(WS_REQ)
                ws_resp = self.sock.recv(1024)
                if ws_resp[0:2] != WS_RESP_MAGIC_NUM:
                    continue
                wes_tag = False
                break
            except BaseException:
                print(traceback.format_exc())

    def run(self):
        """ Receive packet and processing """
        global sender_latitude
        global sender_longitude
        global latency_result

        break_pre_pkt_temp = ""
        while self.trig:
            # Receive Packet
            try:
                packet = self.sock.recv(1024 * 12)
            except BaseException:
                print(traceback.format_exc())
                continue

            packet_ptr = 0
            receive_time = datetime.now().strftime("%S%f")
            
            while True:
                try:
                    if packet[packet_ptr:packet_ptr + 2] == RX_MAGIC_NUM:
                        if packet[packet_ptr+38:packet_ptr+40] == PING_INDICATOR:
                            packet_header = packet[packet_ptr:packet_ptr + 38]
                            payload_length = int.from_bytes(packet_header[36:38], "big")
                            payload = packet[packet_ptr + 38:packet_ptr + 38 + payload_length]


                            sender_recv_time = int.from_bytes(payload[6:10], "big", signed=False)
                            sender_send_time = int.from_bytes(payload[10:14], "big", signed=False)
                            receiver_send_time = int.from_bytes(payload[2:6], "big", signed=False)
                            receiver_delay = int(receive_time) - receiver_send_time

                            if receiver_delay < 0:
                                receiver_delay += 60000000
                            sender_delay = sender_send_time - sender_recv_time
                            if sender_delay < 0:
                                sender_delay += 60000000
                            RTT = receiver_delay - sender_delay
                            latency_result = RTT / 2000
                            packet_ptr = packet_ptr + 38 + payload_length
                        else:
                            packet_header = packet[packet_ptr:packet_ptr + 38]
                            db_c2x_header = packet[packet_ptr + 38:packet_ptr + 38 + 54]
                            payload_length = int.from_bytes(packet_header[36:38], "big") - 54
                            payload = packet[packet_ptr + 38 + 54:packet_ptr + 38 + 54 + payload_length]

                            if len(packet[packet_ptr:]) < 38 + 54 + payload_length:
                                break_pre_pkt_temp = packet[packet_ptr:]
                                break

                            # Get and Save data
                            self.header_q.append([packet_header + db_c2x_header, road_condition, weather_condition,
                                                pdr_result, throughput_result, latency_result, distance_result,
                                                latitude, longitude, dt.datetime.now()])

                            sender_latitude = float(int.from_bytes(db_c2x_header[46:50], "big")) / 1000000
                            sender_longitude = float(int.from_bytes(db_c2x_header[50:54], "big")) / 1000000

                            if payload[0:2] != VIDEO_DATA_INDICATOR:
                                print("Receive RTT")
                            elif payload[0:2] == VIDEO_DATA_INDICATOR:
                                self.pkt_num_q.append(int.from_bytes(payload[2:6], "big"))
                                try:
                                    frame_line_num = struct.unpack(">h", payload[6:8])[0]
                                    frame_line_data = numpy.frombuffer(payload[8:], dtype=numpy.uint8)
                                    frame_line_data = numpy.reshape(frame_line_data, (RECV_FRAME_WIDTH, -1))
                                    self.show_frame[frame_line_num] = frame_line_data
                                except BaseException:
                                    print(traceback.format_exc())
                            else:
                                print("Wrong Indicator")
                            packet_ptr = packet_ptr + 38 + 54 + payload_length
                            if packet_ptr >= len(packet):
                                break
                    else:
                        packet_ptr = packet_ptr+1
                        if packet_ptr >= len(packet):
                            break
                except BaseException:
                    print(traceback.format_exc())
                    continue


    def stop(self):
        """ stop receive data """
        self.trig = False
        self.quit()
        self.wait(10)


class PingWorker(QThread):
    """ Ping Processing for latency """
    def __init__(self, sock):
        """ init """
        super().__init__()
        self.sock = sock

        self.v2x_tx_pdu_p = packet_header_struct.V2X_TxPDU(
            magic_num=htons(0xf2f2),
            ver=0x0001,
            psid=5271,
            e_v2x_comm_type=0,
            e_payload_type=4,
            elements_indicator=0,
            tx_power=20,
            e_signer_id=0,
            e_priority=0,
            channel_load=0,
            reserved1=0,
            expiry_time=0,
            transmitter_profile_id=100,
            peer_l2id=0,
            reserved2=0,
            reserved3=0,
            crc=0,
            length=6
        )
        self.trig = True

    def run(self):
        """ RTT message processing """
        while self.trig:
            try:
                RST_T = datetime.now().strftime("%S%f")  # receiver send time
                RST = int(RST_T).to_bytes(length=4, byteorder="big", signed=False)
                RTT_Packet = bytes(self.v2x_tx_pdu_p) + PING_INDICATOR + RST
                self.sock.send(RTT_Packet)
                time.sleep(RTT_TIMER)
            except BaseException:
                print(traceback.format_exc())
                continue

    def stop(self):
        """ stop ping """
        self.trig = False
        self.quit()
        self.wait(10)


class ReceiverVideoWindow(QWidget):
    """ Receive Video Window  """
    def __init__(self):
        """ init  """
        super().__init__()
        self.show_frame = numpy.zeros((RECV_FRAME_HEIGHT, RECV_FRAME_WIDTH, 3), numpy.uint8)
        self.pkt_num_q = deque()
        self.header_q = deque()

        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((DEVICE_ADDR, DEVICE_PORT))
                break
            except BaseException:
                print(traceback.format_exc())

        # UI declaration
        # Video Screen Area
        self.label = QLabel()
        self.label.setScaledContents(True)
        self.label.setPixmap(QPixmap(resource_path('./resource/stop_icons.png')))
        # Play video & receive video
        self.button_play = QPushButton("Receive")
        self.button_play.clicked.connect(self.play_receive_video)
        # Stop play & receive video
        self.button_pause = QPushButton("Pause")
        self.button_pause.clicked.connect(self.pause_video)
        self.button_pause.setDisabled(True)
        # Information Box
        self.info_box = QTextEdit()
        self.info_box.setReadOnly(True)

        # UI Arrangement
        self.layout = QGridLayout()
        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()
        self.left_layout.addWidget(self.button_play)
        self.left_layout.addWidget(self.button_pause)
        self.left_layout.addWidget(self.info_box)
        self.right_layout.addWidget(self.label)
        self.layout.setColumnStretch(0, 2)
        self.layout.setColumnStretch(1, 4)
        self.layout.addLayout(self.left_layout, 0, 0)
        self.layout.addLayout(self.right_layout, 0, 1)

        # Final UI Layout Arrangement
        self.setLayout(self.layout)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setFixedSize(VIDEO_WIN_SIZE_W, VIDEO_WIN_SIZE_H)
        self.move(BLANK_SPACE, int(monitor_size_height/2) + BLANK_SPACE)

        # Receiver Graph Window Setting
        self.receiver_graph_window = ReceiverGraphWindow(self.pkt_num_q)
        self.receiver_graph_window.show()

        # Receiver Navigation Window Setting
        self.navigation_window = NavigationWindow()
        self.navigation_window.show()

        # GPS thread
        self.gps_worker_th = GPSWorker()
        self.gps_worker_th.start()

    def play_receive_video(self):
        """ play video & thread start  """
        self.show_frame = numpy.zeros((RECV_FRAME_HEIGHT, RECV_FRAME_WIDTH, 3), numpy.uint8)
        self.pkt_num_q.clear()
        self.header_q.clear()
        self.info_box.append(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " : Start Receiving")
        self.rec_th = ReceiveWorker(self.sock, self.show_frame, self.pkt_num_q, self.header_q)
        self.view_th = ViewWorker(self.show_frame, self.label)
        self.ping_th = PingWorker(self.sock)
        self.save_header_th = SaveHeaderWorker(self.info_box, self.header_q)
        self.save_header_th.info_signal.connect(self.update_infobox)
        self.rec_th.start()
        self.view_th.start()
        self.ping_th.start()
        self.save_header_th.start()
        self.button_play.setDisabled(True)
        self.button_pause.setDisabled(False)

    def pause_video(self):
        """ stop video & thread """
        self.info_box.append(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " : Stop Receiving")
        self.rec_th.stop()
        self.ping_th.stop()
        self.view_th.stop()
        self.save_header_th.stop()
        self.button_play.setDisabled(False)
        self.button_pause.setDisabled(True)

    def update_infobox(self, log):
        """ update log text  """
        self.info_box.setText(log)

    def closeEvent(self, event):
        """ cose Receive video window """
        event.accept()


class PDRWorker(QThread):
    """ Display PDR Graph """
    def __init__(self, pkt_num_q, pdr_subplot, pdr_graph_canvas):
        """ init  """
        super().__init__()
        self.pkt_num_q = pkt_num_q
        self.pdr_subplot = pdr_subplot
        self.pdr_graph_canvas = pdr_graph_canvas
        self.pdr_data = []
        self.current_time = []
        self.trig = True

    def run(self):
        """ PDR Graph processing """
        global pdr_result

        while self.trig:
            try:
                pkt_count = 0
                start_num = 0
                end_num = 0
                if len(self.pkt_num_q) != 0:
                    pkt_count = 1
                    start_num = self.pkt_num_q.popleft()
                    end_num = start_num
                while True:
                    if len(self.pkt_num_q) == 0:
                        break
                    end_num = self.pkt_num_q.popleft()
                    pkt_count = pkt_count + 1
                if end_num < start_num:
                    end_num = end_num + 1000000
                pdr_result = (pkt_count * 100) / (end_num - start_num + 1)

                if len(self.pdr_data) == 60:
                    del self.pdr_data[0]
                    del self.current_time[0]
                self.pdr_data.append(pdr_result)
                self.current_time.append(dt.datetime.now())

                self.pdr_subplot.clear()
                self.pdr_subplot.set_ylim(0, 105)
                self.pdr_subplot.plot(self.current_time, self.pdr_data)
                self.pdr_subplot.text(dt.datetime.now() - dt.timedelta(seconds=0.01), pdr_result + 2,
                                      "{:.3f}%".format(pdr_result))

                self.pdr_subplot.set_ylabel("Packet Delivery Ratio(%)")
                self.pdr_subplot.fill_between(self.current_time, self.pdr_data, alpha=0.5)

                self.pdr_graph_canvas.draw()
            except BaseException:
                print(traceback.format_exc())
            time.sleep(1)

    def stop(self):
        """ stop PDR Grapn  """
        self.trig = False
        self.quit()
        self.wait(10)


class ThroughputWorker(QThread):
    """ Display Throughput Graph """
    def __init__(self, throughput_subplot, throughput_graph_canvas):
        """ init """
        super().__init__()
        self.throughput_subplot = throughput_subplot
        self.throughput_graph_canvas = throughput_graph_canvas
        self.throughput_data = []
        self.current_time = []
        self.trig = True

    def run(self):
        """ Throughput Graph processing"""
        global throughput_result

        while self.trig:
            try:
                initial_stats = psutil.net_io_counters(pernic=True)

                # Wait for the specified interval
                time.sleep(1)

                # Get the updated network statistics
                updated_stats = psutil.net_io_counters(pernic=True)

                for interface, initial in initial_stats.items():
                    if interface == NET_IF:
                        updated = updated_stats[interface]
                        throughput_result = updated.bytes_recv - initial.bytes_recv
                        break
                    throughput_result = 0.0
                throughput_result = float(throughput_result / 125000)

                if len(self.throughput_data) == 60:
                    del self.throughput_data[0]
                    del self.current_time[0]
                self.throughput_data.append(throughput_result)
                self.current_time.append(dt.datetime.now())

                self.throughput_subplot.clear()
                self.throughput_subplot.set_ylim(0, 50)
                self.throughput_subplot.plot(self.current_time, self.throughput_data)
                self.throughput_subplot.text(dt.datetime.now() - dt.timedelta(seconds=0.01), throughput_result + 2,
                                             "{:.3f}Mbps".format(throughput_result))

                self.throughput_subplot.set_ylabel("Throughput(Mbps)")
                self.throughput_subplot.fill_between(self.current_time, self.throughput_data, alpha=0.5)

                self.throughput_graph_canvas.draw()
            except BaseException:
                print(traceback.format_exc())

    def stop(self):
        """ stop Throughput Graph """
        self.trig = False
        self.quit()
        self.wait(10)


class DistanceWorker(QThread):
    """ Display Dsitance Graph """
    def __init__(self, distance_subplot, distance_graph_canvas):
        """ init """
        super().__init__()

        self.distance_subplot = distance_subplot
        self.distance_graph_canvas = distance_graph_canvas
        self.distance_data = []
        self.current_time = []
        self.trig = True

    def run(self):
        """ Calculate V2V distance """
        global sender_latitude
        global sender_longitude
        global latitude
        global longitude
        global distance_result

        while self.trig:
            try:
                distance_result = haversine.haversine((sender_latitude, sender_longitude),
                                                      (latitude, longitude), unit='m')

                if len(self.distance_data) == 60:
                    del self.distance_data[0]
                    del self.current_time[0]
                self.distance_data.append(distance_result)
                self.current_time.append(dt.datetime.now())

                self.distance_subplot.clear()
                self.distance_subplot.set_ylim(0, 105)
                self.distance_subplot.plot(self.current_time, self.distance_data)
                self.distance_subplot.text(dt.datetime.now() - dt.timedelta(seconds=0.01), distance_result + 2,
                                           "{:.3f}m".format(distance_result))

                self.distance_subplot.set_ylabel("Distance(Meters)")
                self.distance_subplot.fill_between(self.current_time, self.distance_data, alpha=0.5)

                self.distance_graph_canvas.draw()
            except BaseException:
                print(traceback.format_exc())
            time.sleep(1)

    def stop(self):
        """ stop distance graph """
        self.trig = False
        self.quit()
        self.wait(10)


class LatencyWorker(QThread):
    """ Display Latency Graph """
    def __init__(self, latency_subplot, latency_graph_canvas):
        """ init """
        super().__init__()
        self.latency_subplot = latency_subplot
        self.latency_graph_canvas = latency_graph_canvas
        self.latency_data = []
        self.current_time = []
        self.trig = True

    def run(self):
        """ Calculate RTT Time """
        global latency_result

        while self.trig:
            try:
                self.latency_data.append(latency_result)
                self.current_time.append(dt.datetime.now())

                self.latency_subplot.clear()
                self.latency_subplot.set_ylim(0, 40)
                self.latency_subplot.plot(self.current_time, self.latency_data)
                self.latency_subplot.text(dt.datetime.now() - dt.timedelta(seconds=0.01), latency_result + 2,
                                          "{:.3f}ms".format(latency_result))

                self.latency_subplot.set_ylabel("Latency(ms)")
                self.latency_subplot.fill_between(self.current_time, self.latency_data, alpha=0.5)

                self.latency_graph_canvas.draw()
            except BaseException:
                print(traceback.format_exc())
            time.sleep(1)

    def stop(self):
        """ stop latency Graph """
        self.trig = False
        self.quit()
        self.wait(10)


class ReceiverGraphWindow(QWidget):
    """ Receive Window Configuration """
    def __init__(self, pkt_num_q):
        """ init """
        super().__init__()
        self.pkt_num_q = pkt_num_q
        style = dict(ha='center', va='center', fontsize=28, color='Gray')

        # UI declaration
        self.pdr_graph_figure = Figure()
        self.pdr_graph_figure.text(0.5, 0.5, 'PDR', style)
        self.pdr_graph_canvas = FigureCanvas(self.pdr_graph_figure)
        self.pdr_subplot = self.pdr_graph_figure.add_subplot()

        self.throughput_graph_figure = Figure()
        self.throughput_graph_figure.text(0.5, 0.5, 'Throughput', style)
        self.throughput_graph_canvas = FigureCanvas(self.throughput_graph_figure)
        self.throughput_subplot = self.throughput_graph_figure.add_subplot()

        self.latency_graph_figure = Figure()
        self.latency_graph_figure.text(0.5, 0.5, 'Latency', style)
        self.latency_graph_canvas = FigureCanvas(self.latency_graph_figure)
        self.latency_subplot = self.latency_graph_figure.add_subplot()

        self.distance_graph_figure = Figure()
        self.distance_graph_figure.text(0.5, 0.5, 'Distance', style)
        self.distance_graph_canvas = FigureCanvas(self.distance_graph_figure)
        self.distance_subplot = self.distance_graph_figure.add_subplot()


        # UI Arrangement
        self.layout = QGridLayout()
        self.layout.addWidget(self.pdr_graph_canvas, 0, 0)
        self.layout.addWidget(self.throughput_graph_canvas, 0, 1)
        self.layout.addWidget(self.latency_graph_canvas, 1, 0)
        self.layout.addWidget(self.distance_graph_canvas, 1, 1)

        # Final UI Layout Arrangement
        self.setLayout(self.layout)
        self.setWindowTitle("Receiver Graph Window")
        self.setFixedSize(GRAPH_WIN_SIZE_W, GRAPH_WIN_SIZE_H)
        self.move(BLANK_SPACE, BLANK_SPACE)

        # Init Graph Window
        self.init_graph()

    def init_graph(self):
        """ init graph """
        self.pdr_subplot.set_ylim(0, 105)
        self.pdr_subplot.set_ylabel("Packet Delivery Ratio(%)")

        self.throughput_subplot.set_ylim(0, 50)
        self.throughput_subplot.set_ylabel("Throughput(Mbps)")

        self.latency_subplot.set_ylim(0, 100)
        self.latency_subplot.set_ylabel("Latency(ms)")

        self.distance_subplot.set_ylim(0, 100)
        self.distance_subplot.set_ylabel("Distance(Meters)")

        self.pdr_worker_th = PDRWorker(self.pkt_num_q, self.pdr_subplot, self.pdr_graph_canvas)
        self.pdr_worker_th.start()

        self.distance_worker_th = DistanceWorker(self.distance_subplot, self.distance_graph_canvas)
        self.distance_worker_th.start()

        self.latency_worker_th = LatencyWorker(self.latency_subplot, self.latency_graph_canvas)
        self.latency_worker_th.start()

        self.throughput_worker_th = ThroughputWorker(self.throughput_subplot, self.throughput_graph_canvas)
        self.throughput_worker_th.start()


class NavigatioWorker(QThread):
    """ Display Vehicle on the map"""
    def __init__(self, label):
        """ init """
        super().__init__()
        global webView
        global latitude
        global longitude
        global sender_latitude
        global sender_longitude

    def run(self):
        """ Vehicle position on the map"""
        global webView
        global latitude
        global longitude
        global sender_latitude
        global sender_longitude

        while True:
            try:
                script = f"receiving({latitude},{longitude},{sender_latitude},{sender_longitude})"
                webView.page().runJavaScript(script)
            except BaseException:
                print(traceback.format_exc())
            time.sleep(1)


class WeatherWorker(QThread):
    """ Display Weather Condition """
    def __init__(self, label):
        """ init """
        super().__init__()
        global weather_condition
        self.condition_label = label

        self.trig = True
        while True:
            try:
                weather_condition = 0
                self.weather_img = QPixmap(resource_path('./resource/weather_0.png'))
                self.condition_label.setPixmap(self.weather_img)
                break
            #except:
            except BaseException:
                print(traceback.format_exc())

    def run(self):
        """ Weather API Processing """
        global latitude
        global longitude
        global weather_condition

        while self.trig:
            try:
                base_date = time.strftime('%Y%m%d')
                base_time = time.strftime('%H%M')
                params = {
                    'serviceKey': WEATHER_API_SERVICE_KEY,
                    'pageNo': '1',
                    'numOfRows': '1000',
                    'dataType': 'JSON',
                    'base_date': base_date,
                    'base_time': base_time,
                    'nx': int(latitude),
                    'ny': int(longitude)
                }
            except BaseException:
                continue

            try:
                response = requests.get(WEATHER_API_URL, params=params, timeout=WEATHER_CONDITION_WAIT_TIMER)
            except BaseException:
                time.sleep(WEATHER_CONDITION_ERROR_RESEND_TIMER)
                continue
            try:
                result = str(response.content, 'utf-8')
                result = json.loads(result)

                if (result['response']['header']['resultCode'] == '00'):
                    for i in result['response']['body']['items']['item']:
                        if i.get('category') == 'PTY':
                            weather_condition = int(i.get('obsrValue'))
                            if weather_condition == 1:
                                self.weather_img = QPixmap(resource_path('./resource/weather_1.png'))
                            elif weather_condition == 2:
                                self.weather_img = QPixmap(resource_path('./resource/weather_2.png'))
                            elif weather_condition == 3:
                                self.weather_img = QPixmap(resource_path('./resource/weather_3.png'))
                            elif weather_condition == 5:
                                self.weather_img = QPixmap(resource_path('./resource/weather_5.png'))
                            elif weather_condition == 6:
                                self.weather_img = QPixmap(resource_path('./resource/weather_6.png'))
                            elif weather_condition == 7:
                                self.weather_img = QPixmap(resource_path('./resource/weather_7.png'))
                            else:
                                self.weather_img = QPixmap(resource_path('./resource/weather_0.png'))
                            while True:
                                try:
                                    self.condition_label.setPixmap(self.weather_img)
                                    break
                                except BaseException:
                                    print("Retry to change image")
                            break
                elif (result['response']['header']['resultCode'] == '03'):
                    print("No API data")
                else:
                    print(result['response']['header']['resultCode'] + ' Content Error')
            except BaseException:
                continue
            time.sleep(WEATHER_CONDITION_RESEND_TIMER)

    def stop(self):
        """ stop weather """
        self.trig = False
        self.quit()
        self.wait(100)


class RoadWorker(QThread):
    """ Display Road Condition """
    def __init__(self, label):
        """ init """
        super().__init__()
        global road_condition
        self.road_label = label

        self.trig = True
        while True:
            try:
                road_condition = 0
                self.road_img = QPixmap(resource_path('./resource/road_0.png'))
                self.road_label.setPixmap(self.road_img)
                break
            except BaseException:
                print(traceback.format_exc())

    def run(self):
        """ Road Traffic API Processing """
        global latitude
        global longitude
        global road_condition

        congestion_degree = 0
        congestion_counter = 0
        headers = {
            "appKey": ROAD_API_SERVICE_KEY
        }

        while self.trig:
            try:
                congestion_degree = 0
                congestion_counter = 0
                params = {
                    "version": "1",
                    "format": "json",
                    "reqCoordType": "WGS84GEO",
                    "resCoordType": "WGS84GEO",
                    "zoomLevel": 17,
                    "trafficType": "AUTO",
                    "centerLon": longitude,
                    "centerLat": latitude
                }

                try:
                    response = requests.get(ROAD_API_URL, headers=headers, params=params, timeout=ROAD_CONDITION_WAIT_TIMER)
                except BaseException:
                    continue
                if response.status_code == 200:
                    data = response.json()

                    for feature in data["features"]:
                        properties = feature["properties"]
                        if feature["geometry"]["type"] == "LineString":
                            for Coordinates in feature["geometry"]["coordinates"]:
                                if haversine.haversine((latitude, longitude), (Coordinates[1], Coordinates[0]), unit='m') <= 50:
                                    congestion_counter = congestion_counter + 1
                                    congestion_degree = congestion_degree + properties["congestion"]

                    if congestion_counter != 0:
                        congestion_degree = math.ceil(congestion_degree / congestion_counter)

                    if congestion_degree == 0:
                        self.road_img = QPixmap(resource_path('./resource/road_0.png'))
                    elif congestion_degree == 1:
                        self.road_img = QPixmap(resource_path('./resource/road_1.png'))
                    elif congestion_degree == 2:
                        self.road_img = QPixmap(resource_path('./resource/road_2.png'))
                    elif congestion_degree == 3:
                        self.road_img = QPixmap(resource_path('./resource/road_3.png'))
                    elif congestion_degree == 4:
                        self.road_img = QPixmap(resource_path('./resource/road_4.png'))
                    self.road_label.setPixmap(self.road_img)
                time.sleep(ROAD_CONDITION_RESEND_TIMER)
            except BaseException:
                continue

    def stop(self):
        """ stop road condition """
        self.trig = False
        self.quit()
        self.wait(100)


class NavigationWindow(QWidget):
    """ MAP + Road Condtion + Weather Condition """
    def __init__(self):
        """ init """
        super().__init__()
        global webView
        global latitude
        global longitude

        # UI declaration
        self.weather_label = QLabel()
        self.weather_label.setAlignment(Qt.AlignCenter)
        self.road_label = QLabel()
        self.road_label.setAlignment(Qt.AlignCenter)
        webView = QWebEngineView()
        webView.load(QUrl.fromLocalFile(resource_path(HTML_FILE_PATH)))

        # UI Arrangement
        self.layout = QGridLayout()
        self.layout.addWidget(webView, 0, 0, 2, 1)
        self.layout.addWidget(self.weather_label, 0, 1, 1, 1)
        self.layout.addWidget(self.road_label, 1, 1, 1, 1)

        # Final UI Layout Arrangement
        self.setLayout(self.layout)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setFixedSize(NAVIGATION_WIN_SIZE_W, NAVIGATION_WIN_SIZE_H)
        self.move(int(monitor_size_width/2), int(monitor_size_height/2) + BLANK_SPACE)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.receiving)
        self.timer.start(1000)  # Cycle : 1 second

        # Weather Condition Thread
        self.weather_worker_th = WeatherWorker(self.weather_label)
        self.weather_worker_th.start()

        # Road Condition Thread
        self.road_worker_th = RoadWorker(self.road_label)
        self.road_worker_th.start()

    def receiving(self):
        """ Current Position """
        global webView
        global latitude
        global longitude
        global sender_latitude
        global sender_longitude

        script = f"receiving({latitude},{longitude},{sender_latitude},{sender_longitude})"
        try:
            webView.page().runJavaScript(script)
        except BaseException:
            print(traceback.format_exc())
