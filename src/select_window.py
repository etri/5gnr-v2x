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

""" Main for Sensor Sharing Service Performance Monitoring"""

import os
import sys
import sender_window
import receiver_window
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon

def resource_path(relative_path):
    """ resource(icon, png) path """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


class SelectWindow(QWidget):
    """ select window sender or receiver """
    def __init__(self):
        """ init """
        super().__init__()

        self.setWindowTitle('Electronics and Telecommunications Research Institute')
        self.setWindowIcon(QIcon(resource_path('./resource/etri.png')))
        self.setFixedSize(700, 360)

        select_layout = QGridLayout()
        self.setLayout(select_layout)

        # Sender Button
        sender_select_button = QPushButton("Sender Window", self)
        sender_select_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sender_font = sender_select_button.font()
        sender_font.setPointSize(45)
        sender_select_button.setFont(sender_font)
        sender_select_button.setStyleSheet(
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
        sender_select_button.clicked.connect(lambda: self.show_sender_window(sender_select_button))
        select_layout.addWidget(sender_select_button)

        # Receiver Button
        receiver_select_button = QPushButton("Receiver Window", self)
        receiver_select_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        receiver_font = receiver_select_button.font()
        receiver_font.setPointSize(45)
        receiver_select_button.setFont(receiver_font)
        receiver_select_button.setStyleSheet(
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
        receiver_select_button.clicked.connect(lambda: self.show_receiver_window(receiver_select_button))
        select_layout.addWidget(receiver_select_button)

    def show_sender_window(self, button):
        """ show_sender """
        try:
            self.sender_window = sender_window.SenderWindow()
            self.sender_window.show()
        #except Exception as e:
        except BaseException:
            #print(f"Failed to open sender window{e}")
            print(f"Failed to open sender window")
            return
        self.close()

    def show_receiver_window(self, button):
        """ show_receier """
        try:
            self.receiver_video_window = receiver_window.ReceiverVideoWindow()
            self.receiver_video_window.show()
        #except Exception as e:
        except BaseException:
            #print(f"Failed to open receiver window{e}")
            print(f"Failed to open receiver window")
            return
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    sel_window = SelectWindow()
    sel_window.show()
    sys.exit(app.exec_())
