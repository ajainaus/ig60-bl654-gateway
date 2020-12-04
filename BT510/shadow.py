import json
import time
from json import JSONEncoder
import logging
from .vsp import set_param_str, get_param_str

logging.basicConfig(
    format='%(asctime)s|%(name).10s|%(levelname).5s: %(message)s',
    level=logging.WARNING)
log = logging.getLogger('shadow')
log.setLevel(logging.INFO)

# Event types
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
SENSOR_EVENT_BATTERY_GOOD = 12
SENSOR_EVENT_ADV_ON_BUTTON = 13
SENSOR_EVENT_BATTERY_BAD = 16
SENSOR_EVENT_RESET_BUTTON = 17

# Attributes common to sensor and shadow
JSON_SENSOR_NAME = "sensorName"
JSON_LOCATION = "location"
JSON_ADVERTISING_INTERVAL = "advertisingInterval"
JSON_ADVERTISING_DURATION = "advertisingDuration"
JSON_CONNECTION_TIMEOUT = "connectionTimeout"
JSON_PASSKEY = "passkey"
JSON_LOCK = "lock"
JSON_BATTERY_SENSE_INTERVAL = "batterySenseInterval"
JSON_TEMPERATURE_AGGREGATION_COUNT = "temperatureAggregationCount"
JSON_TEMPERATURE_SENSE_INTERVAL = "temperatureSenseInterval"
JSON_HIGH_TEMPERATURE_ALARM_THRESHOLD_1 = "highTemperatureAlarmThreshold1"
JSON_HIGH_TEMPERATURE_ALARM_THRESHOLD_2 = "highTemperatureAlarmThreshold2"
JSON_LOW_TEMPERATURE_ALARM_THRESHOLD_1 = "lowTemperatureAlarmThreshold1"
JSON_LOW_TEMPERATURE_ALARM_THRESHOLD_2 = "lowTemperatureAlarmThreshold2"
JSON_DELTA_TEMPERATURE_ALARM_THRESHOLD = "deltaTemperatureAlarmTheshold" # sip
JSON_ODR = "odr"
JSON_SCALE = "scale"
JSON_ACTIVATION_THRESHOLD = "activationThreshold"
JSON_RETURN_TO_SLEEP_DURATION = "returnToSleepDuration"
JSON_TEMP_CC = "tempCc"
JSON_BATTERY_VOLTAGE_MV = "batteryVoltageMv"
JSON_HW_VERSION = "hwVersion"
JSON_FIRMWARE_VERSION = "firmwareVersion"
JSON_RESET_REASON = "resetReason"
JSON_MTU = "mtu"
JSON_ACCELEROMETER_SELF_TEST_STATUS = "accelerometerSelfTestStatus"
JSON_FLAGS = "flags"
JSON_RESET_COUNT = "resetCount"
JSON_USE_CODED_PHY = "useCodedPhy"
JSON_TX_POWER = "txPower"
JSON_NETWORK_ID = "networkId"
JSON_CONFIG_VERSION = "configVersion"
JSON_BOOTLOADER_VERSION = "bootloaderVersion"

# Shadow-only attributes
JSON_GATEWAY_ID = "gatewayId"
JSON_THING_TYPE = "thingType"
JSON_EVENT_LOG = "eventLog"
JSON_EVENT_LOG_SIZE = "eventLogSize"

# Event-based attributes (shadow only)
JSON_EVENT_BATTERY_GOOD = "batteryGood"
JSON_EVENT_BATTERY_BAD = "batteryBad"
JSON_EVENT_ALARM_HIGH_TEMP_1 = "alarmHighTemp1"
JSON_EVENT_ALARM_HIGH_TEMP_2 = "alarmHighTemp2"
JSON_EVENT_ALARM_HIGH_TEMP_CLEAR = "alarmHighTempClear"
JSON_EVENT_ALARM_LOW_TEMP_1 = "alarmLowTemp1"
JSON_EVENT_ALARM_LOW_TEMP_2 = "alarmLowTemp2"
JSON_EVENT_ALARM_LOW_TEMP_CLEAR = "alarmLowTempClear"
JSON_EVENT_ALARM_DELTA_TEMP = "alarmDeltaTemp"
JSON_EVENT_ADVERTISE_ON_BUTTON = "advertiseOnButton"

# Flag-based attributes (shadow only)
JSON_FLAG_RTC_SET = "rtcSet"
JSON_FLAG_ACTIVE_MODE = "activeMode"
JSON_FLAG_LOW_BATTERY_ALARM = "batteryLowAlarmState"
JSON_FLAG_ALARM_LOW_TEMP_STATE_1 = "alarmLowTempState1"
JSON_FLAG_ALARM_LOW_TEMP_STATE_2 = "alarmLowTempState2"
JSON_FLAG_ALARM_HIGH_TEMP_STATE_1 = "alarmHighTempState1"
JSON_FLAG_ALARM_HIGH_TEMP_STATE_2 = "alarmHighTempState2"
JSON_FLAG_ALARM_DELTA_TEMP = "alarmDeltaTempState"
JSON_FLAG_MAGNET = "magnet"
JSON_FLAG_MOVEMENT = "movement"

# List of attributes from the sensor
SENSOR_WRITABLE_ATTRIBUTES = [
    JSON_SENSOR_NAME,
    JSON_LOCATION,
    JSON_ADVERTISING_INTERVAL,
    JSON_ADVERTISING_DURATION,
    JSON_CONNECTION_TIMEOUT,
    JSON_PASSKEY,
    JSON_LOCK,
    JSON_BATTERY_SENSE_INTERVAL,
    JSON_TEMPERATURE_AGGREGATION_COUNT,
    JSON_TEMPERATURE_SENSE_INTERVAL,
    JSON_HIGH_TEMPERATURE_ALARM_THRESHOLD_1,
    JSON_HIGH_TEMPERATURE_ALARM_THRESHOLD_2,
    JSON_LOW_TEMPERATURE_ALARM_THRESHOLD_1,
    JSON_LOW_TEMPERATURE_ALARM_THRESHOLD_2,
    JSON_DELTA_TEMPERATURE_ALARM_THRESHOLD,
    JSON_ODR,
    JSON_SCALE,
    JSON_ACTIVATION_THRESHOLD,
    JSON_RETURN_TO_SLEEP_DURATION,
    JSON_TEMP_CC,
    JSON_BATTERY_VOLTAGE_MV,
    JSON_HW_VERSION,
    JSON_FIRMWARE_VERSION,
    JSON_RESET_REASON,
    JSON_MTU,
    JSON_ACCELEROMETER_SELF_TEST_STATUS,
    JSON_FLAGS,
    JSON_RESET_COUNT,
    JSON_USE_CODED_PHY,
    JSON_TX_POWER,
    JSON_NETWORK_ID,
    JSON_CONFIG_VERSION,
    JSON_BOOTLOADER_VERSION,
]

# List of attributes writable through the shadow
SHADOW_WRITABLE_ATTRIBUTES = [
    JSON_SENSOR_NAME,
    JSON_LOCATION,
    JSON_ADVERTISING_INTERVAL,
    JSON_ADVERTISING_DURATION,
    JSON_CONNECTION_TIMEOUT,
    JSON_PASSKEY,
    JSON_LOCK,
    JSON_BATTERY_SENSE_INTERVAL,
    JSON_TEMPERATURE_AGGREGATION_COUNT,
    JSON_TEMPERATURE_SENSE_INTERVAL,
    JSON_HIGH_TEMPERATURE_ALARM_THRESHOLD_1,
    JSON_HIGH_TEMPERATURE_ALARM_THRESHOLD_2,
    JSON_LOW_TEMPERATURE_ALARM_THRESHOLD_1,
    JSON_LOW_TEMPERATURE_ALARM_THRESHOLD_2,
    JSON_DELTA_TEMPERATURE_ALARM_THRESHOLD,
    JSON_ODR,
    JSON_SCALE,
    JSON_ACTIVATION_THRESHOLD,
    JSON_RETURN_TO_SLEEP_DURATION,
    JSON_USE_CODED_PHY,
    JSON_TX_POWER,
    JSON_NETWORK_ID,
    JSON_CONFIG_VERSION,
]

# List of attributes that require a reset after changing
SHADOW_ATTRIBUTES_NEED_RESET = [
    JSON_SENSOR_NAME,
    JSON_ADVERTISING_INTERVAL,
    JSON_ADVERTISING_DURATION,
    JSON_PASSKEY,
    JSON_USE_CODED_PHY,
]

# Mapping of attributes to write when events occur
EVENT_TO_ATTRIBUTE_MAP = {
    SENSOR_EVENT_ALARM_HIGH_TEMP_1: JSON_EVENT_ALARM_HIGH_TEMP_1,
    SENSOR_EVENT_ALARM_HIGH_TEMP_2: JSON_EVENT_ALARM_HIGH_TEMP_2,
    SENSOR_EVENT_ALARM_HIGH_TEMP_CLEAR: JSON_EVENT_ALARM_HIGH_TEMP_CLEAR,
    SENSOR_EVENT_ALARM_LOW_TEMP_1: JSON_EVENT_ALARM_LOW_TEMP_1,
    SENSOR_EVENT_ALARM_LOW_TEMP_2: JSON_EVENT_ALARM_LOW_TEMP_2,
    SENSOR_EVENT_ALARM_LOW_TEMP_CLEAR: JSON_EVENT_ALARM_LOW_TEMP_CLEAR,
    SENSOR_EVENT_ALARM_DELTA_TEMP: JSON_EVENT_ALARM_DELTA_TEMP,
    SENSOR_EVENT_BATTERY_GOOD: JSON_EVENT_BATTERY_GOOD,
    SENSOR_EVENT_BATTERY_BAD: JSON_EVENT_BATTERY_BAD,
    SENSOR_EVENT_ADV_ON_BUTTON: JSON_EVENT_ADVERTISE_ON_BUTTON,
}

FLAG_TO_ATTRIBUTE_MAP = {
    0x0001: JSON_FLAG_RTC_SET,
    0x0002: JSON_FLAG_ACTIVE_MODE,
    0x0080: JSON_FLAG_LOW_BATTERY_ALARM,
    0x0100: JSON_FLAG_ALARM_HIGH_TEMP_STATE_1,
    0x0200: JSON_FLAG_ALARM_HIGH_TEMP_STATE_2,
    0x0400: JSON_FLAG_ALARM_LOW_TEMP_STATE_1,
    0x0800: JSON_FLAG_ALARM_LOW_TEMP_STATE_2,
    0x1000: JSON_FLAG_ALARM_DELTA_TEMP,
    0x4000: JSON_FLAG_MOVEMENT,
    0x8000: JSON_FLAG_MAGNET
}

def data_to_hex_str(data):
    if len(data) == 4:
        val = data[0] + data[1] * 256
        return "{:04X}".format(val)
    else:
        return "0"

def type_to_hex_str(type):
    return "{:X}".format(type)

class Bt500GgShadow(JSONEncoder):
    def __init__(self, address, type = 'bt510_sensor_v1'):
        self.changed = True
        self.recent_events = {}
        self.address = address
        self.reported = {}
        self.desired = {}
        self.reported[JSON_THING_TYPE] = type
        self.max_log = 50
        self.shadow_url = "{}".format(self.address)
        self.reported[JSON_EVENT_LOG_SIZE] = 0
        self.reported[JSON_EVENT_LOG] = []
        self.pending_msgs = []
        self.reset_needed = False

        self.event_handler = {
            SENSOR_EVENT_TEMPERATURE: self.temp_event,
            SENSOR_EVENT_ALARM_HIGH_TEMP_1: self.temp_event,
            SENSOR_EVENT_ALARM_HIGH_TEMP_2: self.temp_event,
            SENSOR_EVENT_ALARM_HIGH_TEMP_CLEAR: self.temp_event,
            SENSOR_EVENT_ALARM_LOW_TEMP_1: self.temp_event,
            SENSOR_EVENT_ALARM_LOW_TEMP_2: self.temp_event,
            SENSOR_EVENT_ALARM_LOW_TEMP_CLEAR: self.temp_event,
            SENSOR_EVENT_ALARM_DELTA_TEMP: self.temp_event,
            SENSOR_EVENT_BATTERY_GOOD: self.batt_event,
            SENSOR_EVENT_ADV_ON_BUTTON: self.batt_event,
            SENSOR_EVENT_BATTERY_BAD: self.batt_event,
        }


    # Event handling
    def event(self, bt_type, flags, epoch, data):
        # Update flag status
        for f in FLAG_TO_ATTRIBUTE_MAP:
            k = FLAG_TO_ATTRIBUTE_MAP[f]
            val = (f & flags) != 0
            if k not in self.reported or self.reported[k] != val:
                self.reported[k] = val
                self.changed = True

        # Handle event
        bt_type_hex = type_to_hex_str(bt_type)
        if bt_type_hex in self.recent_events and \
           self.recent_events[bt_type_hex] == epoch:
            # We've already seen this event. Skip it.
            return False

        if bt_type in self.event_handler:
            handler = self.event_handler[bt_type]
            handler(bt_type, data)

        self.recent_events[bt_type_hex] = epoch
        data_str = data_to_hex_str(data)
        self.add_event(str(bt_type_hex), epoch, data_str)
        return True

    def add_event(self, bt_type, epoch, data):
        event = [bt_type, epoch, data]
        if self.reported[JSON_EVENT_LOG_SIZE] < self.max_log:
            self.reported[JSON_EVENT_LOG_SIZE] += 1
        else:
            self.reported[JSON_EVENT_LOG] = self.reported[JSON_EVENT_LOG][1:]
        self.reported[JSON_EVENT_LOG].append(event)
        self.changed = True

    def batt_event(self, event, data):
        # Format the battery voltage in mV
        batt = data[0] + data[1] * 256

        # Always write batteryVoltageMv
        if JSON_BATTERY_VOLTAGE_MV not in self.reported or \
           self.reported[JSON_BATTERY_VOLTAGE_MV] != batt:
            self.reported[JSON_BATTERY_VOLTAGE_MV] = batt
            self.changed = True

        # Update event-based values
        if event in EVENT_TO_ATTRIBUTE_MAP:
            k = EVENT_TO_ATTRIBUTE_MAP[event]
            if k not in self.reported or self.reported[k] != batt:
                self.reported[k] = batt
                self.changed = True

    def temp_event(self, event, data):
        temp = data[0] + data[1] * 256

        # Always write tempCc
        if JSON_TEMP_CC not in self.reported or \
           self.reported[JSON_TEMP_CC] != temp:
            self.reported[JSON_TEMP_CC] = temp
            self.changed = True

        # Update event-based values
        if event in EVENT_TO_ATTRIBUTE_MAP:
            k = EVENT_TO_ATTRIBUTE_MAP[event]
            if k not in self.reported or self.reported[k] != temp:
                self.reported[k] = temp
                self.changed = True


    # Sensor data handling
    def handle_json(self, json):
        for k in json:
            if k in SENSOR_WRITABLE_ATTRIBUTES:
                val = json[k]

                if k not in self.reported or self.reported[k] != val:
                    self.reported[k] = val
                    self.changed = True

                if k in self.desired and self.desired[k] == self.reported[k]:
                    self.desired[k] = None
                    self.changed = True


    # Change flag management
    def clear_changed(self):
        self.changed = False

    def is_changed(self):
        return self.changed

    def pending(self):
        return self.pending_msgs

    def pending_clear(self):
        self.pending_msgs = []

    def need_something(self):
        for a in SENSOR_WRITABLE_ATTRIBUTES:
            if a not in self.reported:
                return True
        return False

    def need_list(self):
        list = []
        chunk_size = 4
        chunks = [SENSOR_WRITABLE_ATTRIBUTES[i * chunk_size:(i + 1) * chunk_size]
            for i in range((len(SENSOR_WRITABLE_ATTRIBUTES) + chunk_size - 1) // chunk_size)]
        for c in chunks:
            msg = get_param_str(c)
            list.append(msg)
        return list

    def need_default_config(self):
        return self.reported[JSON_CONFIG_VERSION] == 0

    def set_gatewayId(self, id):
        self.reported[JSON_GATEWAY_ID] = id

    # Shadow handling
    def serialize(self, clear_desired):
        if clear_desired:
            self.desired = { }
            state_doc = {"reported": self.reported, "desired": None }
        else:
            state_doc = {"reported": self.reported, "desired": self.desired }
        ret = {"state": state_doc}
        return json.dumps(ret, default=lambda o: o.__dict__)

    def shadow_update_reported(self, data):
        # Ignore "reported" shadow state for now
        pass

    def shadow_update_desired(self, data):
        for d in data:
            if d in SHADOW_WRITABLE_ATTRIBUTES:
                val = data[d]
                if (d not in self.reported or self.reported[d] != val) and \
                   (d not in self.desired or self.desired[d] != val):
                    if d in SHADOW_ATTRIBUTES_NEED_RESET:
                        self.reset_needed = True
                    self.desired[d] = val
                    msg = set_param_str(d, data[d])
                    self.pending_msgs.append(msg)
                    # This is not considered a change, don't set changed = True
                else:
                    if self.desired[d] != None:
                        self.desired[d] = None
                        self.changed = True
            else:
                # This wasn't a valid thing to set, so clear it
                if d in self.desired.keys() and self.desired[d] != None:
                    self.desired[d] = None
                    self.changed = True

    def need_reset(self):
        return self.reset_needed

    def reset_issued(self):
        self.reset_needed = False
        # Consider re-reading all of the settings following the reset

