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

""" Sensor Sharing Service for Sender Widnow(Send video-data) """

import cv2
import numpy
import serial
from socket import *
from scapy.all import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import packet_header_struct
from pygrabber.dshow_graph import FilterGraph


# PyQT Windows Size
WIN_SIZE_H = 800    # Height
WIN_SIZE_W = 600    # Width

# GPS Sensor Variable
SER_PORT = 'COM4'   # Serial Port
SER_BAUD = 9600     # Serial Baud Rate

# 5G NR Device Connection Variable
DEVICE_ADDR = '192.168.1.11'
DEVICE_PORT = 47347
SOCKET_SEND_DELAY = 0

# Video Data Size
SENDER_FRAME_MSEC = 120  # Only 'int' value & Milliseconds ( 60 Frame -> 1000 milliseconds / 60 frames = 16.66666....)
SEND_FRAME_WIDTH = 300
SEND_FRAME_HEIGHT = 300

# RTT Variable
RTT_TIMER = 0

# Packet Variable
WS_REQ = b"\xf1\xf1\x00\x01\x00\x00\x00\x00\x00\x00\x14\x97\x00\x00\x00\x00"
WS_RESP_MAGIC_NUM = b'\xf1\xf2'
PING_INDICATOR = b'\x03\x02'


pkt_seq_num = 0
latitude = 12.0
longitude = 34.0
camera_list = {}

def resource_path(relative_path):
    """ resource(icon, png) path """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def rescale_frame(original_frame, width, height):
    """ update frame size """
    return cv2.resize(original_frame, (width, height), interpolation=cv2.INTER_AREA)

def find_camera_list():
    """ find camera list """
    global camera_list
    camera_list = {}
    devices = FilterGraph().get_input_devices()
    for device_index, device_name in enumerate(devices):
        camera_list[device_index] = device_name

def send_5g(send_sock, video_data):
    """ send video_data """
    global pkt_seq_num
    global latitude
    global longitude
    pkt_seq_num_temp = pkt_seq_num.to_bytes(4, byteorder='big')
    send_data = b'\x03\x01' + pkt_seq_num_temp + video_data
    pkt_seq_num = (pkt_seq_num + 1) % 1000000

    db_v2x_tmp_p = packet_header_struct.DB_V2X(
        eDeviceType=htonl(0x0001),
        eTeleCommType=htonl(0x0002),
        unDeviceId=0x0000,
        ulTimeStamp=0x0000,
        eServiceId=htonl(0x0005),
        eActionType=htonl(0x0001),
        eRegionId=htonl(0x0004),
        ePayloadType=htonl(0x000b),
        eCommId=htonl(0x0001),
        usDbVer=0x0001,
        usHwVer=0x0111,
        usSwVer=0x0001,
        ulPayloadLength=int(latitude * 1000000),
        ulPayloadCrc32=int(longitude * 1000000),
    )

    v2x_tx_pdu_p = packet_header_struct.V2X_TxPDU(
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
        length=len(bytes(db_v2x_tmp_p)) + len(send_data)
    )

    serialized = bytes(v2x_tx_pdu_p) + bytes(db_v2x_tmp_p) + send_data
    try:
        send_sock.send(serialized)
    except BaseException:
        print(traceback.format_exc())
    if SOCKET_SEND_DELAY != 0:
        time.sleep(SOCKET_SEND_DELAY)


class GPSWorker(QThread):
    """ GPS Processing for position """
    def __init__(self):
        """ init """
        super().__init__()

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


class CaptureWorker(QThread):
    """ from video-data to frame data """
    def __init__(self, sock, cap, label):
        """ init """
        super().__init__()
        global pkt_seq_num
        pkt_seq_num = 0
        self.video_cap = cap
        self.video_label = label
        self.sock = sock
        self.trig = True

    def run(self):
        """ capture video """
        # 2023.06.08 frame 100 msec
        while self.trig:
            cv2.waitKey(SENDER_FRAME_MSEC)
            ret, frame = self.video_cap.read()
            if ret:
                try:
                    np_frame = numpy.asarray(rescale_frame(frame, SEND_FRAME_WIDTH, SEND_FRAME_HEIGHT))
                except BaseException:
                    print(traceback.format_exc())
                try:
                    # Update video label
                    frame = cv2.cvtColor(np_frame, cv2.COLOR_BGR2RGB)
                    image = QImage(frame, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(image)
                    pixmap = pixmap.scaled(self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio)
                    self.video_label.setPixmap(pixmap)
                except BaseException:
                    print(traceback.format_exc())

                try:
                    for i in range(SEND_FRAME_HEIGHT):
                        data = np_frame[i].flatten().tobytes()
                        line_num = struct.pack(">h", i)
                        send_5g(self.sock, line_num + data)
                except BaseException:
                    print(traceback.format_exc())

        self.video_label.setPixmap(QPixmap(resource_path('resource/stop_icons.png')))
        self.video_cap.release()

    def stop(self):
        """ stop capture """
        self.trig = False
        self.quit()
        self.wait(100)


class PingWorker(QThread):
    """ Ping Processing for latency """
    def __init__(self, sock):
        """ init """
        super().__init__()
        self.sock = sock
        send_ping_length = 14
        v2x_tx_pdu_p = packet_header_struct.V2X_TxPDU(
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
            length=send_ping_length
        )

        self.header = bytes(v2x_tx_pdu_p)

        self.trig = True

    def run(self):
        """ RTT message processing """
        while self.trig:
            # RTT 패킷 수신
            try:
                packet = self.sock.recv(1024)

                if packet[-6:][:2] == PING_INDICATOR :
                    # Delay calculate time data
                    recv_time = datetime.now().strftime("%S%f")
                    byte_rt = int(recv_time).to_bytes(length=4, byteorder="big", signed=False)
                    send_time = datetime.now().strftime("%S%f")
                    byte_st = int(send_time).to_bytes(length=4, byteorder="big", signed=False)
                    # RTT packet delivery
                    payload_data = b'\x03\x02' + packet[-4:] + byte_rt + byte_st

                    send_data = self.header + payload_data
                    self.sock.send(send_data)
                    time.sleep(RTT_TIMER)
            except BaseException:
                print(traceback.format_exc())

    def stop(self):
        """ stop ping """
        self.trig = False
        self.quit()
        self.wait(100)


class SenderWindow(QWidget):
    """ Sender Window configuration  """
    def __init__(self):
        """ init """
        super().__init__()

        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((DEVICE_ADDR, DEVICE_PORT))
                break
            except BaseException:
                print(traceback.format_exc())
        self.sock.send(WS_REQ)
        try:
            ws_resp = self.sock.recv(1024)
            if ws_resp[0:2] != WS_RESP_MAGIC_NUM:
                print("Fail")
        except BaseException:
            print(traceback.format_exc())

        # UI declaration #
        # Video Screen Area
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setPixmap(QPixmap(resource_path('resource/stop_icons.png')))
        # Play video & send video
        self.button_play = QPushButton("Play & Send")
        self.button_play.clicked.connect(self.play_send_video)
        # Stop play & send video
        self.button_pause = QPushButton("Pause")
        self.button_pause.clicked.connect(self.pause_video)
        self.button_pause.setDisabled(True)
        # Reset Camera list
        self.button_find = QPushButton("Find Camera")
        self.button_find.clicked.connect(self.find_camera)
        # Video file path
        self.video_file_address = QLineEdit()
        self.video_file_address.setPlaceholderText("Saved Video File Path(If send video file)")
        # Type of transmission data(Camera / Video)
        self.type_combo = QComboBox(self)
        find_camera_list()
        for i in camera_list:
            self.type_combo.addItem(camera_list[i])
        self.type_combo.addItem("Saved Video")

        # UI Arrangement #
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.video_file_address)
        self.layout.addWidget(self.type_combo)
        self.layout.addWidget(self.button_play)
        self.layout.addWidget(self.button_pause)
        self.layout.addWidget(self.button_find)

        # Final UI Layout Arrangement #
        self.setLayout(self.layout)
        self.setWindowTitle("Sender Window")
        self.setFixedSize(QSize(WIN_SIZE_H, WIN_SIZE_W))

        # GPS thread
        self.gps_worker_th = GPSWorker()
        self.gps_worker_th.start()


    def play_send_video(self):
        """ send camera video """
        # Define OpenCV by type of transmission data(Camera / Video) #
        if self.type_combo.currentText() == "Saved Video":
            self.send_data_type = self.video_file_address.text()
            try:
                self.video_cap = cv2.VideoCapture(self.send_data_type)
            except BaseException:
                print(traceback.format_exc())
                return
        else:
            for i in camera_list:
                if self.type_combo.currentText() == camera_list[i]:
                    try:
                        self.video_cap = cv2.VideoCapture(cv2.CAP_DSHOW+i)
                        break
                    #except Exception as e:
                    except BaseException:
                        print(traceback.format_exc())
                        
                        return

        # Start Capture Thread
        self.cap_th = CaptureWorker(self.sock, self.video_cap, self.label)
        self.ping_th = PingWorker(self.sock)
        self.cap_th.start()
        self.ping_th.start()
        self.button_play.setDisabled(True)
        self.button_pause.setDisabled(False)

    def pause_video(self):
        """ pause video """
        self.cap_th.stop()
        self.ping_th.stop()
        self.button_play.setDisabled(False)
        self.button_pause.setDisabled(True)

    def find_camera(self):
        """ select camera """
        find_camera_list()
        self.type_combo.clear()
        for i in camera_list:
            self.type_combo.addItem(camera_list[i])
        self.type_combo.addItem("Saved Video")


    def closeEvent(self, event):
        """ close sender window """
        event.accept()
