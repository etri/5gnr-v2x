# Copyright 2025 ETRI. 
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

""" Sensor Sharing Service Performance Data Analysis by Log-files(.csv) """

import os
import numpy
import haversine
import folium
import pandas
from socket import *
from scapy.all import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from screeninfo import get_monitors
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWebEngineWidgets import QWebEngineView
import mplcursors
import statistics

# PyQT Windows Size
monitor_size_width = get_monitors()[0].width
monitor_size_height = get_monitors()[0].height
BLANK_SPACE = 15
WIN_SIZE_W = monitor_size_width - BLANK_SPACE*2
WIN_SIZE_H = int(monitor_size_height / 2) - BLANK_SPACE
GRAPH_WIN_SIZE_W = int(monitor_size_width / 2) - BLANK_SPACE
GRAPH_WIN_SIZE_H = int(monitor_size_height / 2) - BLANK_SPACE*3
MAP_WIN_SIZE_W = int(monitor_size_width) - BLANK_SPACE
MAP_WIN_SIZE_H = int(monitor_size_height / 2) - BLANK_SPACE*3
MAX_PDR_G = 100
MAX_Latency_G = 10
MAX_Throughput_G = 50
MAX_Distance_G = 50

# Down sampling
DOWN_SAMPLING_FLAG = True
AVERAGE_WINDOW = 1000

colortable = 0



webView1 = 0
webView2 = 0
webView3 = 0
webView4 = 0

pdr_log = []
latency_log = []
throughput_log = []
distance_log = []

pdr_drawer = 0
latency_drawer = 0
throughput_drawer = 0
distance_drawer = 0
cursors = []

def resource_path(relative_path):
    """ resource(icon, html) path """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class Logwindow(QWidget):
    """ Log window layout, graph & map """
    def __init__(self):
        """ init """
        super().__init__()
        # UI Arrangement
        self.layout = QGridLayout()
        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()
        self.layout.setColumnStretch(0, 2)
        self.layout.setColumnStretch(1, 4)
        self.layout.addLayout(self.left_layout, 0, 0)
        self.layout.addLayout(self.right_layout, 0, 1)
        # Final UI Layout Arrangement
        self.setLayout(self.layout)
        #self.setWindowFlag(Qt.FramelessWindowHint)
        self.setFixedSize(WIN_SIZE_W, WIN_SIZE_H)
        self.move(BLANK_SPACE, int(monitor_size_height/2) + BLANK_SPACE)
        # Log Graph Window Setting
        self.log_graph_window = LogGraphWindow()
        self.log_graph_window.show()
        # Map Window Setting
        self.map_window = MapWindow()
        self.map_window.show()

    def closeEvent(self, event):
        event.accept()


class LogGraphWindow(QWidget):
    """ Graph Window UI """
    def __init__(self):
        """ init """
        super().__init__()
        style = dict(ha='center', va='center', fontsize=28, color='Gray')
        self.throughput_data = []
        self.distance_data = []
        self.pdr_data = []
        self.latency_data = []
        self.current_time = []
        global throughput_log
        global distance_log
        global pdr_log
        global latency_log
        global pdr_drawer
        global latency_drawer
        global throughput_drawer
        global distance_drawer

        # UI declaration
        self.pdr_graph_figure = Figure()
        self.pdr_graph_figure.text(0.5, 0.5, 'PDR', style)
        self.pdr_graph_canvas = FigureCanvas(self.pdr_graph_figure)
        self.pdr_subplot = self.pdr_graph_figure.add_subplot()
        self.pdr_graph_figure.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
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

        # AVERAGE Line setting
        PDR_AVER = QLabel("PDR AVER = ")        
        font = QFont("Arial", 20, QFont.Bold)
        PDR_AVER.setFont(font)
        PDR_AVER.setStyleSheet("""
            QLabel {
                color: #000000;              
                background-color: #ffffff;   
                padding: 10px;               
                border-radius: 15px;         
                border: 2px solid #ffffff;   
            }
        """) 
        PDR_AVER.setFont(font)
        PDR_AVER.setAlignment(Qt.AlignCenter)

        LATENCY_AVER = QLabel("LATENCY AVER = ")        
        font = QFont("Arial", 20, QFont.Bold)
        LATENCY_AVER.setFont(font)
        LATENCY_AVER.setStyleSheet("""
            QLabel {
                color: #000000;              
                background-color: #ffffff;   
                padding: 10px;               
                border-radius: 15px;         
                border: 2px solid #ffffff;   
            }
        """) 
        LATENCY_AVER.setFont(font)
        LATENCY_AVER.setAlignment(Qt.AlignCenter)

        Throughput_AVER = QLabel("Throughput AVER = ")        
        font = QFont("Arial", 20, QFont.Bold)
        Throughput_AVER.setFont(font)
        Throughput_AVER.setStyleSheet("""
            QLabel {
                color: #000000;              
                background-color: #ffffff;   
                padding: 10px;               
                border-radius: 15px;         
                border: 2px solid #ffffff;   
            }
        """) 
        Throughput_AVER.setFont(font)
        Throughput_AVER.setAlignment(Qt.AlignCenter)

        Distance_AVER = QLabel("Distance AVER = ")        
        font = QFont("Arial", 20, QFont.Bold)
        Distance_AVER.setFont(font)
        Distance_AVER.setStyleSheet("""
            QLabel {
                color: #000000;              
                background-color: #ffffff;   
                padding: 10px;               
                border-radius: 15px;         
                border: 2px solid #ffffff;   
            }
        """) 
        Distance_AVER.setFont(font)
        Distance_AVER.setAlignment(Qt.AlignCenter)

        # UI Arrangement
        self.layout = QGridLayout()
        self.layout.addWidget(self.pdr_graph_canvas, 0, 0)
        self.layout.addWidget(self.throughput_graph_canvas, 0, 2)
        self.layout.addWidget(self.latency_graph_canvas, 1, 0)
        self.layout.addWidget(self.distance_graph_canvas, 1, 2)

        pdr_drawer = pdrdrawer(self.pdr_subplot,self.pdr_graph_canvas)
        latency_drawer = latencydrawer(self.latency_subplot,self.latency_graph_canvas)
        throughput_drawer = throughputdrawer(self.throughput_subplot,self.throughput_graph_canvas)
        distance_drawer = distancedrawer(self.distance_subplot,self.distance_graph_canvas)

        # Final UI Layout Arrangement
        self.setLayout(self.layout)
        self.setWindowTitle("V2X Performance Analysis")
        icon_path = 'resource/etri.ico'  # 
        self.setWindowIcon(QIcon(icon_path))
        self.setBaseSize(GRAPH_WIN_SIZE_W, GRAPH_WIN_SIZE_H)
        self.move(BLANK_SPACE, BLANK_SPACE)

        # Init Graph Window
        self.init_graph()

    def init_graph(self):
        """ init graph """
        self.pdr_subplot.set_ylim(0, MAX_PDR_G + MAX_PDR_G/20)
        self.pdr_subplot.set_ylabel("Packet Delivery Ratio(%)")

        self.throughput_subplot.set_ylim(0, MAX_Throughput_G + MAX_Throughput_G/20)
        self.throughput_subplot.set_ylabel("Throughput(Mbps)")

        self.latency_subplot.set_ylim(0, MAX_Latency_G + MAX_Latency_G/20)
        self.latency_subplot.set_ylabel("Latency(ms)")

        self.distance_subplot.set_ylim(0, MAX_Distance_G + MAX_Distance_G/20)
        self.distance_subplot.set_ylabel("Distance(Meters)")


class MapWindow(QWidget):
    """ Map Window UI """
    def __init__(self):
        """ init """
        super().__init__()
        global webView1
        global webView2
        global webView3
        global webView4
        
        self.csv_button0 = QPushButton("Select log file", self)
        self.csv_button0.clicked.connect(lambda: self.openFile())
        self.csv_button1 = QPushButton("Select Multi log file", self)
        self.csv_button1.clicked.connect(lambda: self.openFile_comp())

        '''web view display- add neuron, 2025.01'''
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox" 

        # WebViews and Titles
        webView1 = QWebEngineView()
        webView1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        webView1.load(QUrl.fromLocalFile(resource_path('./resource/Logmap0.html')))
        webView1_title = QLabel("PDR")

        font = QFont("Arial", 20, QFont.Bold)
        webView1_title.setFont(font)
        webView1_title.setStyleSheet("""
            QLabel {
                color: #f0f0f0;              
                background-color: #333333;   
                padding: 10px;               
                border-radius: 15px;         
                border: 2px solid #ffffff;   
            }
        """) 
        webView1_title.setFont(font)
        webView1_title.setAlignment(Qt.AlignCenter)
        
        webView2 = QWebEngineView()
        webView2.load(QUrl.fromLocalFile(resource_path('./resource/Logmap1.html')))
        webView2_title = QLabel("Latency")
        webView2_title.setStyleSheet("""
            QLabel {
                color: #f0f0f0;              
                background-color: #333333;   
                padding: 10px;               
                border-radius: 15px;         
                border: 2px solid #ffffff;   
            }
        """) 
        webView2_title.setFont(font)
        webView2_title.setAlignment(Qt.AlignCenter)
        
        webView3 = QWebEngineView()
        webView3.load(QUrl.fromLocalFile(resource_path('./resource/Logmap2.html')))
        webView3_title = QLabel("Throughput")
        webView3_title.setStyleSheet("""
            QLabel {
                color: #f0f0f0;              
                background-color: #333333;   
                padding: 10px;               
                border-radius: 15px;         
                border: 2px solid #ffffff;   
            }
        """) 
        webView3_title.setFont(font)
        webView3_title.setAlignment(Qt.AlignCenter)
        
        webView4 = QWebEngineView()
        webView4.load(QUrl.fromLocalFile(resource_path('./resource/Logmap3.html')))
        webView4_title = QLabel("Distance")
        webView4_title.setStyleSheet("""
            QLabel {
                color: #f0f0f0;              
                background-color: #333333;   
                padding: 10px;               
                border-radius: 15px;         
                border: 2px solid #ffffff;   
            }
        """) 

        webView4_title.setFont(font)
        webView4_title.setAlignment(Qt.AlignCenter)

        # Layout for each WebView
        layout1 = QVBoxLayout()
        layout1.addWidget(webView1_title)
        layout1.addWidget(webView1)
        
        layout2 = QVBoxLayout()
        layout2.addWidget(webView2_title)
        layout2.addWidget(webView2)
        
        layout3 = QVBoxLayout()
        layout3.addWidget(webView3_title)
        layout3.addWidget(webView3)

        layout4 = QVBoxLayout()
        layout4.addWidget(webView4_title)
        layout4.addWidget(webView4)

        # Create the table widget
        self.pdr_label = QTableWidget(5, 4)  # Initial empty table
        self.pdr_label.setHorizontalHeaderLabels(['Label', 'Color', 'Label', 'Color'])
        self.latency_label = QTableWidget(5, 2)  # Initial empty table
        self.latency_label.setHorizontalHeaderLabels(['Label', 'Color', 'Label', 'Color'])        
        self.throughput_label = QTableWidget(5, 4)  # Initial empty table
        self.throughput_label.setHorizontalHeaderLabels(['Label', 'Color', 'Label', 'Color'])      
        self.distance_label = QTableWidget(5, 4)  # Initial empty table
        self.distance_label.setHorizontalHeaderLabels(['Label', 'Color', 'Label', 'Color'])      
        
        # Generate colors and populate table
        self.pdr_color = self.create_gradient_colors_with_intervals(MAX_PDR_G)
        self.latency_color = self.create_gradient_colors_with_intervals(MAX_Latency_G)
        self.throughput_color = self.create_gradient_colors_with_intervals(MAX_Throughput_G)
        self.distance_color = self.create_gradient_colors_with_intervals(MAX_Distance_G)

        self.populate_table(self.pdr_label, self.pdr_color, 5, 4)
        self.populate_table(self.latency_label, self.latency_color, 5, 2)
        self.populate_table(self.throughput_label, self.throughput_color, 5, 4)
        self.populate_table(self.distance_label, self.distance_color, 5, 4)

        # Downsampling function button
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText('Enter new value')
        self.checkbox = QCheckBox('Down Sampling', self)
        self.checkbox.stateChanged.connect(self.update_flag)  # Check down sampling             

        # Main Layout
        self.layout = QGridLayout()
        self.layout.addLayout(layout1, 0, 0, 8, 1)
        self.layout.addLayout(layout2, 0, 1, 8, 1)
        self.layout.addLayout(layout3, 0, 2, 8, 1)
        self.layout.addLayout(layout4, 0, 3, 8, 1)
        self.layout.addWidget(self.csv_button0, 0, 4, 1, 1)
        self.layout.addWidget(self.csv_button1, 1, 4, 1, 1)
        self.layout.addWidget(self.input_field, 2, 4, 1, 1)
        self.layout.addWidget(self.checkbox, 3, 4, 1, 1)

        self.layout.addWidget(self.pdr_label, 8, 0, 1, 1)
        self.layout.addWidget(self.latency_label, 8, 1, 1, 1)
        self.layout.addWidget(self.throughput_label, 8, 2, 1, 1)
        self.layout.addWidget(self.distance_label, 8, 3, 1, 1)
        
        # Final UI Layout Arrangement
        self.setLayout(self.layout)
        self.setBaseSize(MAP_WIN_SIZE_W, MAP_WIN_SIZE_H)
        self.move(0, int(monitor_size_height / 2) + BLANK_SPACE)
        
        # Log Graph Window Setting
        self.log_graph_window = LogGraphWindow()
        self.log_graph_window.show()

    # File Explorer
    def openFile(self):
        """ open log-files (.csv) - one folder """
        global DOWN_SAMPLING_FLAG
        global AVERAGE_WINDOW
        
        if self.checkbox.isChecked():
            DOWN_SAMPLING_FLAG = True  # If downsampling is true
            input_value = self.input_field.text()
            if input_value:
                try:
                    AVERAGE_WINDOW = int(input_value)  # AVERAGE WINDOW Setting
                except ValueError:
                    print('Invalid input: Please enter a number')
        else: DOWN_SAMPLING_FLAG = False
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(self, "file select", "", "CSV file (*.csv)", options=options)
        if files:
            self.processCSV(files)

    # File Explorer (Compare)
    def openFile_comp(self):
        """ open log-files (.csv) - multiple folders """
        global DOWN_SAMPLING_FLAG
        global AVERAGE_WINDOW
        if self.checkbox.isChecked():
            DOWN_SAMPLING_FLAG = True  # If downsampling is true
            input_value = self.input_field.text()
            if input_value:
                try:
                    AVERAGE_WINDOW = int(input_value)  # AVERAGE WINDOW Setting
                    print(f'Global value updated to: {AVERAGE_WINDOW}')
                except ValueError:
                    print(traceback.format_exc())
        else:
            DOWN_SAMPLING_FLAG = False
        options = QFileDialog.Options()
        files1, _ = QFileDialog.getOpenFileNames(self, "file select 1", "", "CSV file (*.csv)", options=options)
        if files1:
            pdr_drawer.clear()
            latency_drawer.clear()
            distance_drawer.clear()
            throughput_drawer.clear()
            self.processCSV_comp(files1)
        files2, _ = QFileDialog.getOpenFileNames(self, "file select 2", "", "CSV file (*.csv)", options=options)
        if files2:
            self.processCSV_comp(files2)

    def update_flag(self):
        """ update down-sampling state """
        global DOWN_SAMPLING_FLAG   
        global AVERAGE_WINDOW
        if self.checkbox.isChecked():
            DOWN_SAMPLING_FLAG = True  # If downsampling is true
            input_value = self.input_field.text()
            if input_value:
                try:
                    AVERAGE_WINDOW = int(input_value) # AVERAGE WINDOW Setting
                except ValueError:
                    print(traceback.format_exc())
        else:
            DOWN_SAMPLING_FLAG = False  

    # CSV data Parsing
    def processCSV(self, files):
        """ data parsing from .csv files """
        global pdr_log
        global latency_log
        global throughput_log
        global distance_log
        global pdr_log1
        global latency_log1
        global throughput_log1
        global distance_log1
        global cursors

        data_list = []
        for file in files:
            with open(file, 'r', newline='', encoding='utf-8') as csvfile:
                original_data = pandas.read_csv(csvfile)
                data_list.append(original_data)
                
        combined_df = pandas.concat(data_list, ignore_index=True)

        total_files = len(combined_df)
        progress_dialog = QProgressDialog("Processing files...", "Cancel", 0, total_files, self)
        progress_dialog.setWindowTitle("Processing")
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)
        progress_dialog.setWindowFlags(progress_dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        GPS_log = combined_df[['rx_latitude','rx_longitude']].values
        pdr_log = combined_df['PDR'].values
        latency_log = combined_df['Latency'].values        
        throughput_log = combined_df['Throughput'].values        
        distance_log = combined_df['Distance'].values
        
        pdr_log, latency_log, throughput_log, distance_log, GPS_log = remove_negative_indices(pdr_log,latency_log,throughput_log,distance_log, GPS_log)
        pdr_log, latency_log, throughput_log, distance_log, GPS_log = remove_anomalies_from_multiple(pdr_log, latency_log, throughput_log, distance_log, GPS_log)
        if DOWN_SAMPLING_FLAG == True:
            pdr_log, latency_log, throughput_log, distance_log, GPS_log = downsampling(pdr_log, latency_log, throughput_log, distance_log, GPS_log, AVERAGE_WINDOW)
        
        # Make variable
        middle_point = GPS_log.shape[0]//2
        before_long = 0
        before_lat = 0
        # Make Color Table
        color_table = [0] * GPS_log.shape[0]
        color_table1 = [0] * GPS_log.shape[0]
        color_table2 = [0] * GPS_log.shape[0]
        color_table3 = [0] * GPS_log.shape[0]
        
        colortable = [
            "#FF0000",  # Red (Worst case)
            "#FF4500",  # Dark Orange
            "#FFA500",  # Orange
            "#FFD700",  # Gold
            "#FFFF00",  # Yellow
            "#ADFF2F",  # Lime
            "#40E0D0",  # Turquoise
            "#008000",  # Green
            "#006400",   # Dark Green
            "#0000FF"  # Blue (Best case)
        ]
        for x in range(0,len(pdr_log)):
            if pdr_log[x] >=0  and (MAX_PDR_G*1)/10 > pdr_log[x]:
                color_table[x] = colortable[0] # Red                
            elif pdr_log[x] >= (MAX_PDR_G*1)/10  and (MAX_PDR_G*2)/10 > pdr_log[x]:
                color_table[x] = colortable[1] # Orange
            elif pdr_log[x] >= (MAX_PDR_G*2)/10  and (MAX_PDR_G*3)/10 > pdr_log[x]:
                color_table[x] = colortable[2] # Yellow
            elif pdr_log[x] >= (MAX_PDR_G*3)/10  and (MAX_PDR_G*4)/10 > pdr_log[x]:
                color_table[x] = colortable[3] # Green
            elif pdr_log[x] >= (MAX_PDR_G*4)/10  and (MAX_PDR_G*5)/10 > pdr_log[x]:
                color_table[x] = colortable[4] # Green
            elif pdr_log[x] >= (MAX_PDR_G*5)/10  and (MAX_PDR_G*6)/10 > pdr_log[x]:
                color_table[x] = colortable[5] # Green
            elif pdr_log[x] >= (MAX_PDR_G*6)/10  and (MAX_PDR_G*7)/10 > pdr_log[x]:
                color_table[x] = colortable[6] # Green
            elif pdr_log[x] >= (MAX_PDR_G*7)/10  and (MAX_PDR_G*8)/10 > pdr_log[x]:
                color_table[x] = colortable[7] # Green
            elif pdr_log[x] >= (MAX_PDR_G*8)/10  and (MAX_PDR_G*9)/10 > pdr_log[x]:
                color_table[x] = colortable[8] # Green
            else:
                color_table[x] = colortable[9] # Blue

        for x in range(0,len(latency_log)):
            if latency_log[x] >=0  and (MAX_Latency_G*6)/10 > latency_log[x]:
                color_table1[x] = "#0000FF" # Blue
            elif latency_log[x] >= (MAX_Latency_G*6)/10  and (MAX_Latency_G*7)/10 > latency_log[x]:
                color_table1[x] = "#00FF00" # Green
            elif latency_log[x] >= (MAX_Latency_G*7)/10  and (MAX_Latency_G*8)/10 >latency_log[x]:
                color_table1[x] = "#FFFF00" # Yellow
            elif latency_log[x] >= (MAX_Latency_G*8)/10  and (MAX_Latency_G*9)/10 > latency_log[x]:
                color_table1[x] = "#FFA500" # Orange
            else:
                color_table1[x] = "#FF0000" # Red

        for x in range(0,len(throughput_log)):
            if throughput_log[x] >=0  and (MAX_Throughput_G*1)/10 > throughput_log[x]:
                color_table2[x] = colortable[0] # Red                
            elif throughput_log[x] >= (MAX_Throughput_G*1)/10  and (MAX_Throughput_G*2)/10 > throughput_log[x]:
                color_table2[x] = colortable[1] # Orange
            elif throughput_log[x] >= (MAX_Throughput_G*2)/10  and (MAX_Throughput_G*3)/10 > throughput_log[x]:
                color_table2[x] = colortable[2] # Yellow
            elif throughput_log[x] >= (MAX_Throughput_G*3)/10  and (MAX_Throughput_G*4)/10 > throughput_log[x]:
                color_table2[x] = colortable[3] # Green
            elif throughput_log[x] >= (MAX_Throughput_G*4)/10  and (MAX_Throughput_G*5)/10 > throughput_log[x]:
                color_table2[x] = colortable[4] # Green
            elif throughput_log[x] >= (MAX_Throughput_G*5)/10  and (MAX_Throughput_G*6)/10 > throughput_log[x]:
                color_table2[x] = colortable[5] # Green
            elif throughput_log[x] >= (MAX_Throughput_G*6)/10  and (MAX_Throughput_G*7)/10 > throughput_log[x]:
                color_table2[x] = colortable[6] # Green
            elif throughput_log[x] >= (MAX_Throughput_G*7)/10  and (MAX_Throughput_G*8)/10 > throughput_log[x]:
                color_table2[x] = colortable[7] # Green
            elif throughput_log[x] >= (MAX_Throughput_G*8)/10  and (MAX_Throughput_G*9)/10 > throughput_log[x]:
                color_table2[x] = colortable[8] # Green
            else:
                color_table[x] = colortable[9] # Blue

        for x in range(0,len(distance_log)):
            if distance_log[x] >=0  and (MAX_Distance_G*1)/10 > distance_log[x]:
                color_table3[x] = colortable[0] # Red                
            elif distance_log[x] >= (MAX_Distance_G*1)/10  and (MAX_Distance_G*2)/10 > distance_log[x]:
                color_table3[x] = colortable[1] # Orange
            elif distance_log[x] >= (MAX_Distance_G*2)/10  and (MAX_Distance_G*3)/10 > distance_log[x]:
                color_table3[x] = colortable[2] # Yellow
            elif distance_log[x] >= (MAX_Distance_G*3)/10  and (MAX_Distance_G*4)/10 > distance_log[x]:
                color_table3[x] = colortable[3] # Green
            elif distance_log[x] >= (MAX_Distance_G*4)/10  and (MAX_Distance_G*5)/10 > distance_log[x]:
                color_table3[x] = colortable[4] # Green
            elif distance_log[x] >= (MAX_Distance_G*5)/10  and (MAX_Distance_G*6)/10 > distance_log[x]:
                color_table3[x] = colortable[5] # Green
            elif distance_log[x] >= (MAX_Distance_G*6)/10  and (MAX_Distance_G*7)/10 > distance_log[x]:
                color_table3[x] = colortable[6] # Green
            elif distance_log[x] >= (MAX_Distance_G*7)/10  and (MAX_Distance_G*8)/10 > distance_log[x]:
                color_table3[x] = colortable[7] # Green
            elif distance_log[x] >= (MAX_Distance_G*8)/10  and (MAX_Distance_G*9)/10 > distance_log[x]:
                color_table3[x] = colortable[8] # Green
            else:
                color_table3[x] = colortable[9] # Blue
        
        # Make Folium map
        mymap0 = folium.Map(location=GPS_log[middle_point], zoom_start=17)
        mymap1 = folium.Map(location=GPS_log[middle_point], zoom_start=17)
        mymap2 = folium.Map(location=GPS_log[middle_point], zoom_start=17)
        mymap3 = folium.Map(location=GPS_log[middle_point], zoom_start=17)
        # Add line to the map
        before_lat = GPS_log[1][0]
        before_long = GPS_log[1][1]
        i = 0
        
        for x in range(1,GPS_log.shape[0]):
            try:
                if before_lat != GPS_log[x][0] and before_long != GPS_log[x][1] and abs(before_lat)<=90 and abs(GPS_log[x][0])<=90 and haversine.haversine((before_lat,before_long), (GPS_log[x][0],GPS_log[x][1]), unit = 'm')<100000:
                    tooltip_html = f"""                   
                    PDR = {pdr_log[x]:.2f}<br>
                    Latency = {latency_log[x]:.2f}<br>
                    Throughput = {throughput_log[x]:.2f}<br>
                    Distance = {distance_log[x]:.2f}
                    """              
                    folium.CircleMarker(
                        location=GPS_log[x],  
                        radius=2,
                        color=color_table[x],
                        fill=True,
                        fill_color=color_table[x],
                        fill_opacity=0.6,
                        popup=folium.Popup(tooltip_html, max_width=300)  
                    ).add_to(mymap0)
                    before_lat = GPS_log[x][0]
                    before_long = GPS_log[x][1]
                    folium.CircleMarker(
                        location=GPS_log[x],  
                        radius=2,
                        color=color_table1[x % len(color_table1)],
                        fill=True,
                        fill_color=color_table1[x % len(color_table1)],
                        fill_opacity=0.6,
                        popup=folium.Popup(tooltip_html, max_width=300)  
                    ).add_to(mymap1)
                    before_lat = GPS_log[x][0]
                    before_long = GPS_log[x][1]
                    folium.CircleMarker(
                        location=GPS_log[x],  
                        radius=2,
                        color=color_table2[x % len(color_table2)],
                        fill=True,
                        fill_color=color_table2[x % len(color_table2)],
                        fill_opacity=0.6,
                        popup=folium.Popup(tooltip_html, max_width=300)  
                    ).add_to(mymap2)
                    before_lat = GPS_log[x][0]
                    before_long = GPS_log[x][1]
                    folium.CircleMarker(
                        location=GPS_log[x],  
                        radius=2,
                        color=color_table3[x % len(color_table3)],
                        fill=True,
                        fill_color=color_table3[x % len(color_table3)],
                        fill_opacity=0.6,
                        popup=folium.Popup(tooltip_html, max_width=300)  
                    ).add_to(mymap3)
                    before_lat = GPS_log[x][0]
                    before_long = GPS_log[x][1]                                                               
                progress_dialog.setValue(i + 1)
                i = i +1
                QCoreApplication.processEvents()
            except Exception as e:
                print(f"Failed to open log window{e}")
                raise

        progress_dialog.close()
        
        try:
            mymap0.save('./resource/Logmap0.html')
            mymap1.save('./resource/Logmap1.html')
            mymap2.save('./resource/Logmap2.html')
            mymap3.save('./resource/Logmap3.html')
            cursors = []
            for cursor in cursors:
                cursor.remove()
            cursors = []
        except Exception as e:
            print(f"why? {e}")
            raise #for python solution of too general exception Exception 


        cursors.append(pdr_drawer.event())
        QCoreApplication.processEvents()
        cursors.append(latency_drawer.event())
        QCoreApplication.processEvents()
        cursors.append(throughput_drawer.event())
        QCoreApplication.processEvents()
        cursors.append(distance_drawer.event())
        QCoreApplication.processEvents()

        
        webView1.load(QUrl.fromLocalFile(resource_path('./resource/Logmap0.html')))
        webView2.load(QUrl.fromLocalFile(resource_path('./resource/Logmap1.html')))
        webView3.load(QUrl.fromLocalFile(resource_path('./resource/Logmap2.html')))
        webView4.load(QUrl.fromLocalFile(resource_path('./resource/Logmap3.html')))
        
    def processCSV_comp(self, files):
        """ data parsing from .csv files in multiple folders """
        global pdr_log
        global latency_log
        global throughput_log
        global distance_log
        global pdr_log1
        global latency_log1
        global throughput_log1
        global distance_log1
        global cursors
        
        data_list = []
        for file in files:
            with open(file, 'r', newline='', encoding='utf-8') as csvfile:
                original_data = pandas.read_csv(csvfile)
                data_list.append(original_data)
                
        combined_df = pandas.concat(data_list, ignore_index=True)

        GPS_log = combined_df[['rx_latitude','rx_longitude']].values
        pdr_log = combined_df['PDR'].values
        latency_log = combined_df['Latency'].values        
        throughput_log = combined_df['Throughput'].values        
        distance_log = combined_df['Distance'].values
        
        pdr_log, latency_log, throughput_log, distance_log, GPS_log = remove_negative_indices(pdr_log,latency_log,throughput_log,distance_log, GPS_log)
        pdr_log, latency_log, throughput_log, distance_log, GPS_log = remove_anomalies_from_multiple(pdr_log, latency_log, throughput_log, distance_log, GPS_log)
        if DOWN_SAMPLING_FLAG == True:
            pdr_log, latency_log, throughput_log, distance_log, GPS_log = downsampling(pdr_log, latency_log, throughput_log, distance_log, GPS_log, AVERAGE_WINDOW)

        cursors = []
        for cursor in cursors:
            cursor.remove()
        cursors = []
        cursors.append(pdr_drawer.draw())
        cursors.append(latency_drawer.draw())
        cursors.append(distance_drawer.draw())
        cursors.append(throughput_drawer.draw())

    def create_gradient_colors_with_intervals(self, max_value):
        """ graph colors by stages """
        num_intervals = 10
        colors = [
            "#FF0000",  # Red (Worst case)
            "#FF4500",  # Dark Orange
            "#FFA500",  # Orange
            "#FFD700",  # Gold
            "#FFFF00",  # Yellow
            "#ADFF2F",  # Lime
            "#40E0D0",  # Turquoise
            "#008000",  # Green
            "#006400",   # Dark Green
            "#0000FF"  # Blue (Best case)
        ]
        qcolors = [QColor(color) for color in colors]
        # Generate interval ranges (5 unit ranges for each interval)
        ranges = [f'{int(i*max_value/10)}-{int((i+1)*max_value/10)}' for i in range(num_intervals)]
        
        return list(zip(ranges, qcolors))

    
    def populate_table(self, label, color, row, col):
        """ graph colors by performance value range """
        num_rows = row
        if col == 4:
            for row in range(num_rows):
                # Fill Label 1 and Color 1 (Column 1 and Column 2)
                index1 = row * 2
                if index1 < len(color):
                    range_label1, color1 = color[index1]
                    label.setItem(row, 0, QTableWidgetItem(range_label1))
                    color_item1 = QTableWidgetItem()
                    color_item1.setBackground(color1)
                    label.setItem(row, 1, color_item1)
                
                # Fill Label 2 and Color 2 (Column 3 and Column 4)
                index2 = index1 + 1
                if index2 < len(color):
                    range_label2, color2 = color[index2]
                    label.setItem(row, 2, QTableWidgetItem(range_label2))
                    color_item2 = QTableWidgetItem()
                    color_item2.setBackground(color2)
                    label.setItem(row, 3, color_item2)
        else:
            label_index = len(color) - 1  #
            color_index = 0  
            
            for current_row in range(num_rows):
                # Fill Label 1 and Color 1 (Column 1 and Column 2)
                if label_index >= 0 and color_index < len(color):
                    range_label1, _ = color[label_index]
                    label.setItem(current_row, 0, QTableWidgetItem(range_label1))
                    
                    _, color1 = color[color_index]
                    color_item1 = QTableWidgetItem()
                    color_item1.setBackground(color1)
                    label.setItem(current_row, 1, color_item1)
                    
                    label_index -= 1  
                    color_index += 1  

                # Fill Label 2 and Color 2 (Column 3 and Column 4)
                if label_index >= 0 and color_index < len(color):
                    range_label2, _ = color[label_index]
                    label.setItem(current_row, 2, QTableWidgetItem(range_label2))
                    
                    _, color2 = color[color_index]
                    color_item2 = QTableWidgetItem()
                    color_item2.setBackground(color2)
                    label.setItem(current_row, 3, color_item2)
                    
                    label_index -= 1
                    color_index += 1

class pdrdrawer():
    """ updae pdr graph """
    def __init__(self, pdr_subplot, pdr_graph_canvas):
        """ init """
        self.pdr_subplot = pdr_subplot
        self.pdr_graph_canvas = pdr_graph_canvas
        self.pdr_data = []
        self.current_time = []
        self.trig = True
        self.annotations = []
        
    def clear(self):
        """ clear graph """
        self.pdr_subplot.clear()
        
    def draw(self):
        """ draw pdr graph """
        self.pdr_data = pdr_log
        self.current_time = range(len(self.pdr_data))
        self.pdr_subplot.set_ylim(0, MAX_PDR_G+5)
        self.pdr_subplot.plot(self.current_time, self.pdr_data)
        self.pdr_subplot.set_ylabel("Packet Delivery Ratio(%)")
        self.pdr_subplot.fill_between(self.current_time, self.pdr_data, alpha=0.5)
        y_mean = statistics.mean(pdr_log)
        self.pdr_subplot.axhline(y=y_mean, color='red', linestyle='--', label=f'PDR Mean: {y_mean:.2f}')        
        self.pdr_subplot.text(1.02, y_mean, f'{y_mean:.2f}', transform=self.pdr_subplot.get_yaxis_transform(), color='red', fontsize=12, verticalalignment='center')        
        self.pdr_graph_canvas.draw()
        cursor = mplcursors.cursor(self.pdr_subplot, hover=False)
        cursor.connect("add", self.on_click)
        return(cursor)
    
    def event(self):
        """ draw event """
        self.clear()
        self.draw()

    def on_click(self, sel):
        """ click event """
        sel.annotation.set_text(f'x={sel.target[0]:.2f}\nPDR={sel.target[1]:.2f}%')
        sel.annotation.get_bbox_patch().set(fc="white", alpha=0.6)       
        self.annotations.append(sel.annotation)
        sel.annotation.figure.canvas.mpl_connect('button_press_event', lambda event: self.on_annotation_click(event, sel.annotation))

    def on_annotation_click(self, event, annotation):
        """ annotation click event """
        if annotation.contains(event)[0]:
            annotation.set_visible(False)
            self.pdr_graph_canvas.draw_idle()


class latencydrawer():
    """ updae latency graph """
    def __init__(self, latency_subplot, latency_graph_canvas):
        """ init """
        self.latency_subplot = latency_subplot
        self.latency_graph_canvas = latency_graph_canvas
        self.latency_data = []
        self.current_time = []
        self.trig = True
        self.annotations = []

    def clear(self):
        """ clear graph """
        self.latency_subplot.clear()
        
    def draw(self):
        """ draw latency graph """
        self.latency_data = latency_log
        self.current_time = range(len(self.latency_data))
        self.latency_subplot.set_ylim(0, MAX_Latency_G+1)
        self.latency_subplot.plot(self.current_time, self.latency_data)
        self.latency_subplot.set_ylabel("Latency(ms)")
        self.latency_subplot.fill_between(self.current_time, self.latency_data, alpha=0.5)
        y_mean = statistics.mean(latency_log)
        self.latency_subplot.axhline(y=y_mean, color='red', linestyle='--', label=f'Latency Mean: {y_mean:.2f}')
        self.latency_subplot.text(1.02, y_mean, f'{y_mean:.2f}', transform=self.latency_subplot.get_yaxis_transform(), color='red', fontsize=12, verticalalignment='center')     
        self.latency_graph_canvas.draw()
        cursor = mplcursors.cursor(self.latency_subplot, hover=False)
        cursor.connect("add", self.on_click)
        return(cursor)
    
    def event(self):
        """ draw enent """
        self.clear()
        self.draw()

    def on_click(self, sel):
        """ click event """
        sel.annotation.set_text(f'x={sel.target[0]:.2f}\nLatency={sel.target[1]:.2f}%')
        sel.annotation.get_bbox_patch().set(fc="white", alpha=0.6)
        self.annotations.append(sel.annotation)
        sel.annotation.figure.canvas.mpl_connect('button_press_event', lambda event: self.on_annotation_click(event, sel.annotation))

    def on_annotation_click(self, event, annotation):
        """ annotation click event """
        if annotation.contains(event)[0]:
            annotation.set_visible(False)
            self.latency_graph_canvas.draw_idle()

        
class throughputdrawer():
    """ update throughput graph """
    def __init__(self, throughput_subplot, throughput_graph_canvas):
        """ init """
        self.throughput_subplot = throughput_subplot
        self.throughput_graph_canvas = throughput_graph_canvas
        self.throughput_data = []
        self.current_time = []
        self.trig = True
        self.annotations = []

    def clear(self):
        """ clear graph """
        self.throughput_subplot.clear()
        
    def draw(self):
        """ draw throughput graph """
        self.throughput_data = throughput_log
        self.current_time = range(len(self.throughput_data))
        self.throughput_subplot.set_ylim(0, MAX_Throughput_G+1)
        self.throughput_subplot.plot(self.current_time, self.throughput_data)
        self.throughput_subplot.set_ylabel("Throughput(Mbps)")
        self.throughput_subplot.fill_between(self.current_time, self.throughput_data, alpha=0.5)
        y_mean = statistics.mean(throughput_log)
        self.throughput_subplot.axhline(y=y_mean, color='red', linestyle='--', label=f'Throughput Mean: {y_mean:.2f}')
        self.throughput_subplot.text(1.02, y_mean, f'{y_mean:.2f}', transform=self.throughput_subplot.get_yaxis_transform(), color='red', fontsize=12, verticalalignment='center')             
        self.throughput_graph_canvas.draw()
        cursor = mplcursors.cursor(self.throughput_subplot, hover=False)
        cursor.connect("add", self.on_click)
        return(cursor)
    
    def event(self):
        """ draw event """
        self.clear()
        self.draw()

    def on_click(self, sel):
        """ click event """
        sel.annotation.set_text(f'x={sel.target[0]:.2f}\nThroughput={sel.target[1]:.2f}%')
        sel.annotation.get_bbox_patch().set(fc="white", alpha=0.6)
        self.annotations.append(sel.annotation)
        sel.annotation.figure.canvas.mpl_connect('button_press_event', lambda event: self.on_annotation_click(event, sel.annotation))

    def on_annotation_click(self, event, annotation):
        """ annotation click event """
        if annotation.contains(event)[0]:
            annotation.set_visible(False)
            self.throughput_graph_canvas.draw_idle()    
    
class distancedrawer():
    """ update distance graph """
    def __init__(self, distance_subplot, distance_graph_canvas):
        """ init """
        self.distance_subplot = distance_subplot
        self.distance_graph_canvas = distance_graph_canvas
        self.distance_data = []
        self.current_time = []
        self.trig = True
        self.annotations = []
    
    def clear(self):
        """ clear graph """
        self.distance_subplot.clear()
        
    def draw(self):
        """ draw distance graph """
        self.distance_data = distance_log
        self.current_time = range(len(self.distance_data))
        self.distance_subplot.set_ylim(0, MAX_Distance_G+1)
        self.distance_subplot.plot(self.current_time, self.distance_data)
        self.distance_subplot.set_ylabel("Distance(Meters)")
        self.distance_subplot.fill_between(self.current_time, self.distance_data, alpha=0.5)
        y_mean = statistics.mean(distance_log)
        self.distance_subplot.axhline(y=y_mean, color='red', linestyle='--', label=f'Distance Mean: {y_mean:.2f}')
        self.distance_subplot.text(1.02, y_mean, f'{y_mean:.2f}', transform=self.distance_subplot.get_yaxis_transform(), color='red', fontsize=12, verticalalignment='center')     
        self.distance_graph_canvas.draw()
        cursor = mplcursors.cursor(self.distance_subplot, hover=False)
        cursor.connect("add", self.on_click)
        return(cursor)
          
    def event(self):
        """ draw event """
        self.clear()
        self.draw()

    def on_click(self, sel):
        """ click event """
        sel.annotation.set_text(f'x={sel.target[0]:.2f}\nDistance={sel.target[1]:.2f}%')
        sel.annotation.get_bbox_patch().set(fc="white", alpha=0.6)
        self.annotations.append(sel.annotation)
        sel.annotation.figure.canvas.mpl_connect('button_press_event', lambda event: self.on_annotation_click(event, sel.annotation))
    def on_annotation_click(self, event, annotation):    
        """ annotation click event """    
        if annotation.contains(event)[0]:
            annotation.set_visible(False)
            self.distance_graph_canvas.draw_idle()

def remove_anomalies_from_multiple(data0, data1, data2, data3, data4, threshold=3):
    """ remove error value from log file """
    if not (len(data0) == len(data1) == len(data2) == len(data3) == len(data4)):
        raise ValueError("log csv file error")
    
    def calculate_z_scores(data):
        """ calculate standard value """
        mean = statistics.mean(data)
        std_dev = statistics.stdev(data)
        return [(x - mean) / std_dev for x in data]

    z_scores1 = calculate_z_scores(data1)
    z_scores2 = calculate_z_scores(data2)
    z_scores3 = calculate_z_scores(data3)

    filtered_data0 = []
    filtered_data1 = []
    filtered_data2 = []
    filtered_data3 = []
    filtered_data4 = []

    for i in range(len(data1)):
        if abs(z_scores1[i]) < threshold and abs(z_scores2[i]) < threshold and abs(z_scores3[i]) < threshold:
            filtered_data0.append(data0[i])
            filtered_data1.append(data1[i])
            filtered_data2.append(data2[i])
            filtered_data3.append(data3[i])
            filtered_data4.append(data4[i])

    return filtered_data0, filtered_data1, filtered_data2, filtered_data3, numpy.array(filtered_data4)

def downsampling(data0, data1, data2, data3, data4, window_size):
    """ using downsampling for graph display """
    smoothed_data0 = []
    smoothed_data1 = []
    smoothed_data2 = []
    smoothed_data3 = []
    smoothed_data4 = []
    smoothed0 = data0[0]
    smoothed1 = data1[0]
    smoothed2 = data2[0]
    smoothed3 = data3[0]
    smoothed4 = data4[0]
    
    for i in range(len(data0)):
        if i % window_size == 0:
            smoothed_data0.append(smoothed0/window_size)
            smoothed_data1.append(smoothed1/window_size)
            smoothed_data2.append(smoothed2/window_size)
            smoothed_data3.append(smoothed3/window_size)
            smoothed_data4.append(smoothed4)
            smoothed0 = 0
            smoothed1 = 0
            smoothed2 = 0
            smoothed3 = 0
            smoothed4 = 0
        else:
            smoothed0 = smoothed0 + data0[i]
            smoothed1 = smoothed1 + data1[i]
            smoothed2 = smoothed2 + data2[i]
            smoothed3 = smoothed3 + data3[i]
            smoothed4 = data4[i]
    try:
        smoothed_data0.append(smoothed0/(i%window_size))
        smoothed_data1.append(smoothed1/(i%window_size))
        smoothed_data2.append(smoothed2/(i%window_size))
        smoothed_data3.append(smoothed3/(i%window_size))
        smoothed_data4.append(smoothed4)
    except BaseException:
        print(traceback.format_exc())
    return smoothed_data0, smoothed_data1, smoothed_data2, smoothed_data3, numpy.array(smoothed_data4)

def remove_negative_indices(w, x, y, z, a):
    """ remove negative value """
    if not (len(w) == len(x) == len(y) == len(z) == len(a)):
        raise ValueError("log csv file error")
    filtered_w = []
    filtered_x = []
    filtered_y = []
    filtered_z = []
    filtered_a = []
    
    for i in range(len(w)):
        if w[i] >= 0 and x[i]>= 0 and y[i]>=0:
            filtered_w.append(w[i])
            filtered_x.append(x[i])
            filtered_y.append(y[i])
            filtered_z.append(z[i])
            filtered_a.append(a[i])
    
    return filtered_w, filtered_x, filtered_y, filtered_z, numpy.array(filtered_a)

