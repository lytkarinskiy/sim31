import re
import json
import time
import struct
import serial
import crcmod.predefined
import uuidict

from datetime import datetime, timedelta
from collections import OrderedDict


class UM31:
    """Class for connection and reading information from UM-31GSM Device"""

    def __init__(self):
        self.__password = '00000000'
        self.__connection = serial.Serial()

    def connect(self,
                port=None,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                password='00000000',
                timeout=15):
        """Connect to UM-31 with specified serial port parameters

        Args:
            port (str):
            baudrate (int):
            bytesize (serial):
            parity (serial):
            password (str):
            timeout (int):

        """
        self.__password = password
        self.__connection.port = port
        self.__connection.baudrate = baudrate
        self.__connection.bytesize = bytesize
        self.__connection.parity = parity
        self.__connection.timeout = timeout
        try:
            self.__connection.close()
            self.__connection.open()
            print("Connected to", port, "at", time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
        except serial.SerialException:
            print("Can't open connection")

    def disconnect(self):
        """Disconnect from UM-31 immediately"""
        self.__connection.close()

    def __pack_command(self, cmd_word):
        """Internal function for packing command in desirable format.

        Args:
            cmd_word (str): Supported command from documentation.

        Returns:
            bytes: The return value. Formatted command to write in UM-31.

        """
        crc_func = crcmod.predefined.mkCrcFun('modbus')
        sep = ","

        cmd_text = self.__password + sep + cmd_word
        crc = crc_func(cmd_text.encode('utf-8'))
        packed_cmd = cmd_text + format(crc, 'x') + "\x0A\x0A"
        # print(packed_cmd.encode("utf-8"))
        return packed_cmd.encode("utf-8")

    def __execute_cmd(self, cmd_word, stop_word):
        stop_word = stop_word.encode("utf-8")
        cmd = self.__pack_command(cmd_word)
        self.__connection.write(cmd)
        time.sleep(1)
        data = cmd_word.encode("utf-8")
        while True:
            current_line = self.__connection.readline()
            # print(current_line)
            if stop_word not in current_line:
                data += current_line
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

    def read_diagnostic(self):
        """Read diagnostic data.

        Returns:
            str: The return value. Unformatted payload from UM-31.

        """
        return self.__execute_cmd("RDIAGN", "END")

    def read_ntpserver_list(self, record_num):
        return self.__execute_cmd(" RNTPSRV=" + str(record_num), "None")

    def read_time(self):
        cmd_word = "GETDATETIME"
        cmd = self.__pack_command(cmd_word)
        self.__connection.write(cmd)
        time.sleep(1)
        data = self.__connection.readline() + self.__connection.readline()
        return data

    # noinspection PyMethodMayBeStatic
    def _clean_data(self, data):
        """Clean output data

        Args:
            data (bytearray): Raw rows from UM-31

        Returns:
            inter5[0][0] (str): Key raw to determine which command was used to read the data
            inter5[2:] (list of lists of str): cleaned data separated by TAG (TD, SNUM, etc..)

        """
        inter0 = data.decode("utf-8", "ignore")
        if inter0.startswith("READ"):
            # Remove whitespaces
            inter1 = re.sub(r"[\s]", " ", inter0)
            # Remove CRC and open/close words
            inter2 = re.sub(r"END(.*?)BL", " ", inter1)
            # Remove last close word
            inter3 = re.sub(r"END.+", "", inter2)
            # Split to separate measurements at "=" sign
            inter4 = re.split("=", " ".join(inter3.split()))
            inter5 = []
            # Split each measurement in to list of measurement fields at "<" sign, remove empty fields
            for i in inter4:
                inter5.append(list(filter(lambda elem: elem.strip(), re.split("<", i))))
            return inter5[0][0], inter5[2:]
        else:
            return None

    def export_json(self, data):

        def _parse_description(id_block, sn_block):
            serial_number_ = sn_block.split()[1]
            meter_descr = id_block.split()[1]
            meter_descr = meter_descr.split(";")
            dev_index = format(int(meter_descr[3]), "02d")
            device_ = self.__dev_dict[dev_index]
            int_code_ = format(int(meter_descr[0]), "04d") + "/" + format(int(meter_descr[1]), "04d")
            bus_ = self.__bus_dict[meter_descr[2]]
            return device_, serial_number_, int_code_, bus_

        def _description_string(device_, serial_number_, int_code_, bus_):
            meter_descr = device_ \
                          + ", ID=" + int_code_ \
                          + ", S/N=" + serial_number_ \
                          + ", bus=" + bus_
            return meter_descr

        key, data = self._clean_data(data)
        time_format = "%Y-%m-%dT%H:%M:%SZ"
        json_list = []
        data_dict = OrderedDict([("_spec", "electricity_meter")])
        full_dict = OrderedDict([("meterUUID", None),
                                 ("meterDescription", None),
                                 ("transmittedAt", None),
                                 ("data", None)])
        info_dict = OrderedDict()
        uuid_dict = uuidict.UUIDict("um31.uuid")
        if key.startswith("READCURR"):
            for row in data:
                if len(row) > 2:
                    # Format time
                    splited_time_row = row[0].split()
                    transmitted_at = splited_time_row[1] + splited_time_row[2]
                    # Check if time is synced
                    if splited_time_row[3] == "2":
                        transmitted_at = datetime.strptime(transmitted_at, "%d.%m.%Y%H:%M:%S")
                        try:
                            # h_offset = -time.localtime().tm_gmtoff
                            h_offset = -3
                        except:
                            h_offset = -3
                        time_delta = timedelta(hours=h_offset)
                        transmitted_at = transmitted_at + time_delta
                        transmitted_at = datetime.strftime(transmitted_at, time_format)
                    else:
                        transmitted_at = datetime.utcnow().strftime(time_format)
                    # Format meterDescription
                    device, serial_number, int_code, bus = _parse_description(row[1], row[2])
                    meter_description = _description_string(device, serial_number, int_code, bus)
                    # Format values
                    for val in row[3:]:
                        val = val.split()
                        data_dict[val[0]] = round(float(val[1]), 1)
                    info_dict.update({"DEV": device, "SNUM": serial_number, "INT_ID": int_code, "BUS": bus})
                    data_dict.update({"info": info_dict})
                    full_dict.update({"meterUUID": uuid_dict.get_uuid(meter_description),
                                      "meterDescription": meter_description,
                                      "transmittedAt": transmitted_at,
                                      "data": data_dict})
                    json_list.append(json.dumps(full_dict, indent=4))
                else:
                    pass

        elif key.startswith("READMONTH"):
            for row in data:
                if len(row) > 1:
                    # Format time
                    transmitted_at = datetime.utcnow().strftime(time_format)
                    device, serial_number, int_code, bus = _parse_description(row[0], row[1])
                    meter_description = _description_string(device, serial_number, int_code, bus)
                    # Format values
                    for val in row[2:]:
                        val = val.split()
                        data_dict[val[0]] = round(float(val[1]), 1)
                    info_dict.update({"DEV": device, "SNUM": serial_number, "INT_ID": int_code, "BUS": bus})
                    data_dict.update({"info": info_dict})
                    full_dict.update({"meterUUID": uuid_dict.get_uuid(meter_description),
                                      "meterDescription": meter_description,
                                      "transmittedAt": transmitted_at,
                                      "data": data_dict})
                    json_list.append(json.dumps(full_dict, indent=4))
                else:
                    pass
        else:
            pass

        return json_list

    # def __custom_crc(self, init_crc=0xFFFF):
    #     # ~ Table of CRC values for high–order byte
    #     auchCRCHi = [
    #         0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81,
    #         0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0,
    #         0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01,
    #         0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41,
    #         0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81,
    #         0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0,
    #         0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01,
    #         0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,
    #         0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81,
    #         0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0,
    #         0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01,
    #         0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
    #         0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81,
    #         0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0,
    #         0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01,
    #         0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
    #         0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81,
    #         0x40]
    #
    #     # ~ Table of CRC values for low–order byte
    #     auchCRCLo = [
    #         0x00, 0xC0, 0xC1, 0x01, 0xC3, 0x03, 0x02, 0xC2, 0xC6, 0x06, 0x07, 0xC7, 0x05, 0xC5, 0xC4,
    #         0x04, 0xCC, 0x0C, 0x0D, 0xCD, 0x0F, 0xCF, 0xCE, 0x0E, 0x0A, 0xCA, 0xCB, 0x0B, 0xC9, 0x09,
    #         0x08, 0xC8, 0xD8, 0x18, 0x19, 0xD9, 0x1B, 0xDB, 0xDA, 0x1A, 0x1E, 0xDE, 0xDF, 0x1F, 0xDD,
    #         0x1D, 0x1C, 0xDC, 0x14, 0xD4, 0xD5, 0x15, 0xD7, 0x17, 0x16, 0xD6, 0xD2, 0x12, 0x13, 0xD3,
    #         0x11, 0xD1, 0xD0, 0x10, 0xF0, 0x30, 0x31, 0xF1, 0x33, 0xF3, 0xF2, 0x32, 0x36, 0xF6, 0xF7,
    #         0x37, 0xF5, 0x35, 0x34, 0xF4, 0x3C, 0xFC, 0xFD, 0x3D, 0xFF, 0x3F, 0x3E, 0xFE, 0xFA, 0x3A,
    #         0x3B, 0xFB, 0x39, 0xF9, 0xF8, 0x38, 0x28, 0xE8, 0xE9, 0x29, 0xEB, 0x2B, 0x2A, 0xEA, 0xEE,
    #         0x2E, 0x2F, 0xEF, 0x2D, 0xED, 0xEC, 0x2C, 0xE4, 0x24, 0x25, 0xE5, 0x27, 0xE7, 0xE6, 0x26,
    #         0x22, 0xE2, 0xE3, 0x23, 0xE1, 0x21, 0x20, 0xE0, 0xA0, 0x60, 0x61, 0xA1, 0x63, 0xA3, 0xA2,
    #         0x62, 0x66, 0xA6, 0xA7, 0x67, 0xA5, 0x65, 0x64, 0xA4, 0x6C, 0xAC, 0xAD, 0x6D, 0xAF, 0x6F,
    #         0x6E, 0xAE, 0xAA, 0x6A, 0x6B, 0xAB, 0x69, 0xA9, 0xA8, 0x68, 0x78, 0xB8, 0xB9, 0x79, 0xBB,
    #         0x7B, 0x7A, 0xBA, 0xBE, 0x7E, 0x7F, 0xBF, 0x7D, 0xBD, 0xBC, 0x7C, 0xB4, 0x74, 0x75, 0xB5,
    #         0x77, 0xB7, 0xB6, 0x76, 0x72, 0xB2, 0xB3, 0x73, 0xB1, 0x71, 0x70, 0xB0, 0x50, 0x90, 0x91,
    #         0x51, 0x93, 0x53, 0x52, 0x92, 0x96, 0x56, 0x57, 0x97, 0x55, 0x95, 0x94, 0x54, 0x9C, 0x5C,
    #         0x5D, 0x9D, 0x5F, 0x9F, 0x9E, 0x5E, 0x5A, 0x9A, 0x9B, 0x5B, 0x99, 0x59, 0x58, 0x98, 0x88,
    #         0x48, 0x49, 0x89, 0x4B, 0x8B, 0x8A, 0x4A, 0x4E, 0x8E, 0x8F, 0x4F, 0x8D, 0x4D, 0x4C, 0x8C,
    #         0x44, 0x84, 0x85, 0x45, 0x87, 0x47, 0x46, 0x86, 0x82, 0x42, 0x43, 0x83, 0x41, 0x81, 0x80,
    #         0x40]
    #
    #     ##########################################################################
    #
    #     uchCRCHi = 0xFF  # high byte of CRC initialized
    #     uchCRCLo = 0xFF  # low byte of CRC initialized
    #     uIndex = 0x0000  # will index into CRC lookup table
    #
    #     for ch in data:
    #         uIndex = uchCRCLo ^ ord(ch)
    #         uchCRCLo = uchCRCHi ^ auchCRCHi[uIndex]
    #         uchCRCHi = auchCRCLo[uIndex]
    #     return (uchCRCHi << 8 | uchCRCLo)

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
