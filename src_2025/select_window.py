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

""" Main for Sensor Sharing Service Performance Data Analysis """

import os
import sys
import log_window
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon

def resource_path(relative_path):    
    """ resource(icon, png) path """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class SelectWindow(QWidget):    
    """ select Log window """
    def __init__(self):
        """ init """
        super().__init__()

        self.setWindowTitle('Electronics and Telecommunications Research Institute')
        self.setWindowIcon(QIcon(resource_path('./resource/etri.png')))
        self.setFixedSize(800, 300)

        select_layout = QGridLayout()
        self.setLayout(select_layout)

        # Log Button
        Log_select_button = QPushButton("Log Window 5G-NR", self)
        Log_select_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        Log_font = Log_select_button.font()
        Log_font.setPointSize(45)
        Log_select_button.setFont(Log_font)
        Log_select_button.setStyleSheet(
            "QPushButton"
            "{"
            "background-color : rgb(169,169,169);"
            "border-color : rgb(0, 0, 0);"
            "border-style : solid;"
            "border-width : 2px;"
            "border-radius : 15px"
            "}"
            "QPushButton::hover"
            "{"
            "background-color : rgb(192,192,192);"
            "}"
            "QPushButton::pressed"
            "{"
            "background-color : rgb(240, 240, 240);"
            "}"
        )
        Log_select_button.clicked.connect(lambda: self.show_log_window(Log_select_button))
        select_layout.addWidget(Log_select_button)

    def show_log_window(self, button):
        """ show_service performance grape """
        try:
            self.log_video_window = log_window.MapWindow()
            self.log_video_window.show()
        except BaseException:
            print(f"Failed to open receiver window")
            return
        
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    sel_window = SelectWindow()
    sel_window.show()
    sys.exit(app.exec_())
