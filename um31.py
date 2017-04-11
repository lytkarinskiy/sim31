import re
import json
import time
import serial
import crcmod.predefined
import uuid_db

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
                password='00000000'):
        """Connect to UM-31 with specified serial port parameters

        Args:
            port (str):
            baudrate (int):
            bytesize (serial):
            parity (serial):
            password (str):

        """
        self.__password = password
        self.__connection.port = port
        self.__connection.baudrate = baudrate
        self.__connection.bytesize = bytesize
        self.__connection.parity = parity
        self.__connection.close()
        try:
            self.__connection.close()
            self.__connection.open()
            print("Connected to ", port)
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
        return self.__execute_cmd("RDIAGN", "END")

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

        def _description_string(id_block, sn_block):
            meter_descr = id_block.split()[1]
            meter_descr = meter_descr.split(";")
            serial_number = sn_block.split()[1]
            # check dev_dict index length and append if necessary (bug in UM31 firmware)
            dev_index = format(int(meter_descr[3]), "02d")
            # if len(dev_index) < 2:
            #     dev_index = "0" + dev_index
            meter_descr = self.__dev_dict[dev_index] \
                 + ", ID=" + format(int(meter_descr[0]), "04d") + "/" + format(int(meter_descr[1]), "04d") \
                 + ", S/N=" + serial_number \
                 + ", bus=" + self.__bus_dict[meter_descr[2]]
            return meter_descr

        key, data = self._clean_data(data)

        def _spec_string(id_block):
            meter_descr = id_block.split()[1]
            meter_descr = meter_descr.split(";")
            dev_index = format(int(meter_descr[3]), "02d")
            return self.__dev_dict[dev_index]

        json_list = []
        data_dict = OrderedDict([("_spec", None)])
        full_dict = OrderedDict([("meterUUID", None),
                                 ("meterDescription", None),
                                 ("transmittedAt", None),
                                 ("data", None)])

        time_format = "%Y-%m-%dT%H:%M:%SZ"
        uuid_dict = uuid_db.UUIDict("um31.uuid")
        if key.startswith("READCURR"):
            for row in data:
                if len(row) > 2:
                    # Format time
                    splited_time_row = row[0].split()
                    transmitted_at = splited_time_row[1] + splited_time_row[2]
                    # Check if time is synced
                    if splited_time_row[3] == "2":
                        transmitted_at = datetime.strptime(transmitted_at, "%d.%m.%Y%H:%M:%S")
                        time_delta = timedelta(hours=-3)
                        transmitted_at = transmitted_at + time_delta
                        transmitted_at = datetime.strftime(transmitted_at, time_format)
                    else:
                        transmitted_at = datetime.utcnow().strftime(time_format)
                    # Format meterDescription
                    meter_description = _description_string(row[1], row[2])
                    # Format values
                    for val in row[3:]:
                        val = val.split()
                        data_dict[val[0]] = round(float(val[1]), 1)

                    data_dict.update({"_spec" : _spec_string(row[1])})
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
                    # Format meterDescription
                    meter_description = _description_string(row[0], row[1])
                    # Format values
                    for val in row[2:]:
                        val = val.split()
                        data_dict[val[0]] = round(float(val[1]), 1)

                    data_dict.update({"_spec": _spec_string(row[0])})
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
