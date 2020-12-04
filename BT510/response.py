'''handle scan responses from bt510'''
from construct import Int16sl
from datetime import datetime
from .scan_response import parse

SENSOR_EVENT_RESERVED = 0
SENSOR_EVENT_TEMPERATURE = 1
SENSOR_EVENT_MAGNET = 2
SENSOR_EVENT_MOVEMENT = 3
SENSOR_EVENT_ALARM_HIGH_TEMP_1 = 4
SENSOR_EVENT_ALARM_HIGH_TEMP_2 = 5
SENSOR_EVENT_ALARM_HIGH_TEMP_CLEAR = 6
SENSOR_EVENT_ALARM_LOW_TEMP_1 = 7
SENSOR_EVENT_ALARM_LOW_TEMP_2 = 8
SENSOR_EVENT_ALARM_LOW_TEMP_CLEAR = 9
SENSOR_EVENT_ALARM_DELTA_TEMP = 10
SENSOR_EVENT_ALARM_TEMPERATURE_RATE_OF_CHANGE = 11
SENSOR_EVENT_BATTERY = 12
SENSOR_EVENT_ADV_ON_BUTTON = 13
SENSOR_EVENT_RESET_BUTTON = 14
SENSOR_EVENT_IMPACT = 15
SENSOR_EVENT_BATTERY_BAD = 16
SENSOR_EVENT_RESET = 17

MFG_TYPE = 255
NAME_TYPE = 9
SHORT_LOCAL_NAME_TYPE = 8
STD_RESP_LEN = 27
EXT_RESP_LEN_FW_1_2 = 35
EXT_RESP_LEN_FW_1_4 = 38
LEN_EXT_SCAN_RESP_E4 = 16
EXT_RESP_LEN = [EXT_RESP_LEN_FW_1_2, EXT_RESP_LEN_FW_1_4]

TEMP_PARSE = Int16sl


def calc_temp(byte0, byte1):
    '''calculate temperature from two bytes'''
    hexstr = "{:02X}{:02X}".format(byte0, byte1)
    barr = bytearray.fromhex(hexstr)
    temp = TEMP_PARSE.parse(barr)
    #    temp = byte0 + byte1 * 256
    return temp


def temp_handler(data):
    '''handler for temperature even'''
    temp = calc_temp(data[0], data[1])
    return "temp", "{} degC".format(temp / 100)


def batt_handler(data):
    '''handler for battery'''
    batt = data[0] + data[1] * 256
    return "battery", "{} mV".format(batt)


def move_handler(data):
    '''handler for move event'''
    return "movement", data[0]


def mag_handler(data):
    '''handler for magnet event'''
    if data[0] == 0:
        resp = "arriving"
    else:
        resp = "leaving"
    return "magnet", resp


def no_handler(_data):
    '''handler for unexpected type '''
    pass


def high_temp_handler(data):
    '''handler for high temperature'''
    temp = calc_temp(data[0], data[1])
    return "high temp", "{} degC".format(temp / 100)


def high_temp_clear_handler(_data):
    '''handler for high temp clear'''
    return "high_temp_clear", "true"


def low_temp_handler(data):
    '''handler for low temp event'''
    temp = calc_temp(data[0], data[1])
    return "low temp", "{} degC".format(temp / 100)


def low_temp_clear_handler(data):
    '''handler low temp clear event'''
    return "low_temp_clear", data[0]


def delta_temp_handler(data):
    ''' delta temp handler '''
    return "delta temp", "{}".format(data[0])


def rate_of_change_handler(data):
    '''handler rate of change event'''
    return "temp rate of change", "{}".format(data[0])


def button_handler(data):
    '''hanlder button event'''
    return "button", data[0]


def bad_batt_handler(data):
    '''handler for bad batt event'''
    return "bad battery", data[0]


def reset_handler(data):
    '''handler reset event '''
    return "reset", data[0]


def time_str():
    ''' timestamp for advert event'''
    time_n = datetime.now()
    return time_n.strftime("%m-%d-%Y %H:%M:%S")


EVENT_HANDLERS = {
    SENSOR_EVENT_RESERVED: no_handler,
    SENSOR_EVENT_BATTERY: batt_handler,
    SENSOR_EVENT_MAGNET: mag_handler,
    SENSOR_EVENT_MOVEMENT: move_handler,
    SENSOR_EVENT_TEMPERATURE: temp_handler,
    SENSOR_EVENT_ALARM_HIGH_TEMP_1: high_temp_handler,
    SENSOR_EVENT_ALARM_HIGH_TEMP_2: high_temp_handler,
    SENSOR_EVENT_ALARM_HIGH_TEMP_CLEAR: high_temp_clear_handler,
    SENSOR_EVENT_ALARM_LOW_TEMP_1: low_temp_handler,
    SENSOR_EVENT_ALARM_LOW_TEMP_2: low_temp_handler,
    SENSOR_EVENT_ALARM_LOW_TEMP_CLEAR: low_temp_clear_handler,
    SENSOR_EVENT_ALARM_DELTA_TEMP: delta_temp_handler,
    SENSOR_EVENT_ALARM_TEMPERATURE_RATE_OF_CHANGE: rate_of_change_handler,
    SENSOR_EVENT_ADV_ON_BUTTON: button_handler,
    SENSOR_EVENT_RESET_BUTTON: button_handler,
    SENSOR_EVENT_IMPACT: move_handler,
    SENSOR_EVENT_BATTERY_BAD: bad_batt_handler,
    SENSOR_EVENT_RESET: reset_handler
}


class ResponseData():
    '''class representing basic BT510 scan response data'''
    def __init__(self, addr, data, rssi, ext):
        self.addr = addr
        self.data = data
        self.ext = ext
        self.name = ""
        self.record_type_string = ""
        self.record_data_string = ""
        self.parsed = parse(data)
        self.rssi = rssi
        self.firmware = ""
        self.bootloader = ""
        self.protocol_id = 0x0000
        for list_container in self.parsed:

            if list_container.type == MFG_TYPE and (list_container.length in [
                    STD_RESP_LEN, EXT_RESP_LEN_FW_1_2, EXT_RESP_LEN_FW_1_4
            ]):
                self.handle_mfg_record(list_container.value)
            if list_container.type in [NAME_TYPE, SHORT_LOCAL_NAME_TYPE]:
                self.name = list_container.value

            if list_container.type == MFG_TYPE and (list_container.length in [
                    EXT_RESP_LEN_FW_1_4, LEN_EXT_SCAN_RESP_E4
            ]):

                self.firmware = "{}.{}.{}".format(
                    list_container.value.firmware_version_major,
                    list_container.value.firmware_version_minor,
                    list_container.value.firmware_version_patch)

                self.bootloader = "{}.{}.{}".format(
                    list_container.value.bootloader_version_major,
                    list_container.value.bootloader_version_minor,
                    list_container.value.bootloader_version_patch)

        if self.record_type_string == "":
            print((self.parsed))
            print(data)

    def __repr__(self):
        time_stamp = time_str()
        if self.name == "":
            return "{} Address: {} type: {} {} rssi: {}".format(
                time_stamp, self.addr, self.record_type_string,
                self.record_data_string, self.rssi)

        return "{} Address: {} type: {} {} rssi: {} name: {} firmware: {}".format(
            time_stamp, self.addr, self.record_type_string,
            self.record_data_string, self.rssi, self.name, self.firmware)

    def handle_mfg_record(self, l_container):
        '''set access to Response data fields'''
        self.record_type = l_container.record_type
        self.record_data = l_container.data
        self.flags = l_container.flags
        self.epoch = l_container.epoch
        self.protocol_id = l_container.protocol_id
        handler = EVENT_HANDLERS[l_container.record_type]
        (self.record_type_string,
         self.record_data_string) = handler(l_container.data)

    def get_type_epoch_record(self):
        '''get type epoch record field'''
        return self.record_type, self.flags, self.epoch, self.record_data

    def get_phy(self):
        if self.protocol_id == 0x0002:
            return "LE"
        else:
            return "1M"
