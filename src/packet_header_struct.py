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

""" Sensor Sharing Service Message Structure"""

from socket import *
from scapy.all import *


# V2X_TxPDU (len = 50)
class V2X_TxPDU(Packet):
    """ V2X TxPDU Structure """

    name = "V2X_TxPDU"
    fields_desc = [
        ShortField("magic_num", 0),
        ShortField("ver", 0),
        IntField("psid", 0),
        XByteField("e_v2x_comm_type", 0),
        XByteField("e_payload_type", 0),
        XByteField("elements_indicator", 0),
        XByteField("tx_power", 0),
        XByteField("e_signer_id", 0),
        XByteField("e_priority", 0),
        XByteField("channel_load", 0),
        XByteField("reserved1", 0),
        LongField("expiry_time", 0),
        IntField("transmitter_profile_id", 0),
        IntField("peer_l2id", 0),
        IntField("reserved2", 0),
        LongField("reserved3", 0),
        IntField("crc", 0),
        ShortField("length", 0)  # payload length : 1 ~ 2302
    ]

# DB_V2X (len = 54)
class DB_V2X(Packet):
    """ V2X Common Service Header(SSOV) """
    name = "DB_V2X"
    fields_desc = [
        IntField("eDeviceType", 1),
        IntField("eTeleCommType", 1),
        IntField("unDeviceId", 1),
        LongField("ulTimeStamp", 1),
        IntField("eServiceId", 1),
        IntField("eActionType", 1),
        IntField("eRegionId", 1),
        IntField("ePayloadType", 1),
        IntField("eCommId", 1),
        ShortField("usDbVer", 1),
        ShortField("usHwVer", 1),
        ShortField("usSwVer", 1),
        IntField("ulPayloadLength", 1),
        IntField("ulPayloadCrc32", 1)
    ]
