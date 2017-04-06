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
        if inter0.startswith("READ"):
            inter1 = re.sub(r"[\s]", " ", inter0)
            inter2 = re.sub(r"END(.*?)BL", " ", inter1)
            inter3 = re.sub(r"END.+", "", inter2)
            inter4 = re.split("=", " ".join(inter3.split()))
            inter5 = []
            for i in inter4:
                inter5.append(list(filter(lambda elem: elem.strip(), re.split("<", i))))
            return inter5[2:]
        else:
            return None

    def export_json(self, data):

        data = self.clean_data(data)
        d = []
        dd = OrderedDict([("_spec", "Mercury")])
        od = OrderedDict([("meterUUID", None),
                          ("meterDescription", None),
                          ("transmittedAt", None),
                          ("data", None)])

        for row in data:
            if "DT" in row[0] and len(row) > 2:
                # Format time
                tm = row[0].split()[1]
                if tm.endswith("2"):
                    tm = datetime.datetime.strptime(tm, "%d.%m.%Y %H:%M:%S 2")
                    td = datetime.timedelta(hours=-3)
                    tm = tm + td
                    tm = datetime.datetime.strftime(tm, "%Y-%m-%dT%H:%M:%SZ")
                else:
                    tm = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                # Format meterDescription
                md = row[1].split()[1]
                md = md.split(";")
                sn = row[2].split()[1]
                md = self.__dev_dict[md[3]] \
                     + ", ID=" + md[0] + "/" + md[1] \
                     + ", S/N=" + sn \
                     + ", bus=" + self.__bus_dict[md[2]]
                # Format values
                for val in row[3:]:
                    val = val.split()
                    dd[val[0]] = round(float(val[1]), 1)
                od.update({"meterUUID": "todo", "meterDescription": md, "transmittedAt": tm, "data": dd})
                d.append(json.dumps(od, indent=4))

            elif "ID" in row[0] and len(row) > 1:
                # Format time
                tm = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                # Format meterDescription
                md = row[0].split()[1]
                md = md.split(";")
                print(md)
                sn = row[1].split()[1]
                md = self.__dev_dict["0"+md[3]] \
                     + ", ID=" + md[0] + "/" + md[1] \
                     + ", S/N=" + sn \
                     + ", bus=" + self.__bus_dict[md[2]]
                # Format values
                for val in row[2:]:
                    val = val.split()
                    dd[val[0]] = round(float(val[1]), 1)
                od.update({"meterUUID": "todo", "meterDescription": md, "transmittedAt": tm, "data": dd})
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
