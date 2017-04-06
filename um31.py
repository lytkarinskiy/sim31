"""Class for connection and reading information from UM-31GSM Device"""

import re
import json
import time
import datetime
import serial
import crcmod.predefined
from collections import OrderedDict


class UM31:
    def __init__(self):
        self.password = '00000000'
        self.__connection = serial.Serial()
        self.__crc = crcmod.predefined.mkCrcFun('modbus')

    def connect(self,
                port=None,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                password='00000000'):
        """Connect to UM-31 with specified serial port parameters

        Args:
            port (str):
            baudrate (int):
            bytesize (serial):
            parity (serial):
            password (str):

        """
        self.password = password
        self.__connection.port = port
        self.__connection.baudrate = baudrate
        self.__connection.bytesize = bytesize
        self.__connection.parity = parity
        self.__connection.close()
        try:
            self.__connection.open()
        except serial.SerialException:
            print("Can't open connection")

    def disconnect(self):
        """Disconnect from UM-31 immediately"""
        self.__connection.close()

    def __pack_command(self, command):
        """Internal function for packing command in desirable format.

        Args:
            command (str): Supported command from documentation.

        Returns:
            bytes: The return value. Formatted command to write in UM-31.

        """
        sep = ","
        command_ = self.password + sep + command
        crc = self.__crc(command_.encode('utf-8'))
        full = command_ + format(crc, 'x') + "\x0A\x0A"
        return full.encode("utf-8")

    def __execute_cmd(self, cmd_word, stop_word):
        stop_word = stop_word.encode("utf-8")
        cmd = self.__pack_command(cmd_word)
        self.__connection.write(cmd)
        time.sleep(1)
        data = cmd_word.encode("utf-8")
        while True:
            str_ = self.__connection.readline()
            if stop_word not in str_:
                data += str_
            else:
                break
        return data

    def read_current_values(self):
        """Read current values.

        Returns:
            str: The return value. Unformatted payload from UM-31.

        """
        return self.__execute_cmd("READCURR", "READCURREND")

    def read_month_values(self, month):
        """Read values for selected month.

        Args:
            month (int): Month to read values for, should be in range(1..12).

        Returns:
            str: The return value. Unformatted payload from UM-31.

        """
        return self.__execute_cmd("READMONTH=" + format(month, "02d"), "READMONTHEND")

    def clean_data(self, data):
        inter0 = data.decode("utf-8", "ignore")
        if inter0.startswith("READCURR"):
            inter1 = re.sub(r"[\s<\x00-\x1f]", " ", inter0)
            inter2 = re.sub(r"END(.*?)(BL|READCURREND)", " ", inter1)
            inter3 = re.sub(r"END.+", "", inter2)
            inter4 = re.split("=", " ".join(inter3.split()))
            return inter4[1:]
        elif inter0.startswith("READMONTH"):
            inter1 = re.sub(r"[\s<\x00-\x1f]", " ", inter0)
            inter2 = re.sub(r"END(.*?)(BL|READCURREND)", " ", inter1)
            inter3 = re.sub(r"END.+", "", inter2)
            inter4 = re.split("=", " ".join(inter3.split()))
            return inter4[1:]
        else:
            return None

    def export_json(self, data):
        data = self.clean_data(data)
        d = []
        for row in data:
            if "SNUM" in row:
                row_list = re.split(r" DT |ID |SNUM |A\+[0-2] ", row)[1:]
                # Format transmittedAt
                tm = row_list[0].strip()
                if tm.endswith("2"):
                    tm = datetime.datetime.strptime(tm, "%d.%m.%Y %H:%M:%S 2")
                    td = datetime.timedelta(hours=-3)
                    tm = tm + td
                    tm = datetime.datetime.strftime(tm, "%Y-%m-%dT%H:%M:%SZ")
                else:
                    tm = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                # Format meterDescription
                md = row_list[1].strip()
                md = md.split(";")
                sn = row_list[2].strip()
                md = self.__dev_dict[md[3]] \
                     + " with ID" + md[0] + "/" + md[1] \
                     + " , S/N" + sn \
                     + " at " + self.__bus_dict[md[2]]

                dd = OrderedDict([("_spec", "Mercury"),
                                  ("T0", round(float(row_list[3]), 1)),
                                  ("T1", round(float(row_list[4]), 1)),
                                  ("T2", round(float(row_list[5]), 1))])

                od = OrderedDict([("meterUUID", "todo"),
                                  ("meterDescription", md),
                                  ("transmittedAt", tm),
                                  ("data", dd)])
                d.append(json.dumps(od, indent=4))
            else:
                pass
        return d

    __bus_dict = dict([("0", "CAN1"),
                       ("1", "CAN2"),
                       ("2", "CAN3"),
                       ("3", "CAN4"),
                       ("4", "RS-485")
                       ])

    __dev_dict = dict([("00", "undefined"),
                       ("01", "Mercury-200"),
                       ("03", "Mercury-230"),
                       ("04", "CET-4TM"),
                       ("05", "CE-303"),
                       ("06", "CE-301"),
                       ("07", "CE-6805"),
                       ("08", "CE-102"),
                       ("09", "UMTV-10"),
                       ("10", "PSCH-4TM"),
                       ("11", "CE-102M"),
                       ("17", "PSCH-3TA"),
                       ("19", "BARS"),
                       ("91", "USPD Mercury 225.2")
                       ])
