from ig60.shadow import IgShadow
from BT510.shadow import Bt500GgShadow
from BT510.vsp import handle_vsp_response
from BT510.vsp import set_param_str
from BT510.vsp import get_time_command
from BT510.vsp import get_reset_command
from BT510.response import ResponseData
import BT510.scan_response as bt510
import bluetooth.manager as bluetooth
import time
import json
import serial
import logging
import os
import sys
import threading
import greengrasssdk
import signal
import copy
import traceback
import py2to3util

client = greengrasssdk.client('iot-data')

# Serial Port class
port = None
''' these values work well to connect, usually first or second try '''
CONN_TIMEOUT_MS = 4000
MIN_CONN_INT_US = 7500
MAX_CONN_INT_US = 0
# link supervisor timeout
N_SUPER_TOUT_US = 500

GW_UPDATE_TIME_MIN = 15
GW_UPDATE_TIMEOUT = GW_UPDATE_TIME_MIN * 60

gw_shadow_update_time = time.time() - (
    2 * GW_UPDATE_TIMEOUT)  # long enough to force update first time

#if os.uname()[4] == 'x86_64':
#    import localReport as report
#    at_commands = []
#else:
import greengrass as report

logging.basicConfig(
    format='%(asctime)s|%(name).10s|%(levelname).5s: %(message)s',
    level=logging.WARNING)
log = logging.getLogger('app')
log.setLevel(logging.INFO)

node_id = os.getenv('AWS_IOT_THING_NAME') or 'NO_THING_NAME'
config_file = os.getenv('CONFIG_FILE', 'config.json')

print("startup and running")

def is_bt510_advert(advert):

    if len(advert) < 3:
        return False
    advert_data = advert[1]
    if len(advert_data) < 12:
        return False

    print('advert_data_ambient')
    print(advert_data)


    return (advert_data[8] == 'F' and advert_data[9] == 'F'
            and advert_data[10] == '7' and advert_data[11] == '7')

def remove_ext(advert):
    ''' remove EXT_ADV '''
    if advert.startswith("EXT ADV:"):
        return advert[8:]
    return advert


def remove_AD(data):
    ''' remove AD prefix '''
    if data.startswith("AD:"):
        ret_index = data[3:].find(":")
        if ret_index != -1:
            return data[4 + ret_index:]  # it's 3 +1 + ret_index
        return data[3:]
    return data


def remove_RS(rs):
    ''' remove RS prefix '''
    if rs.startswith("RS:"):
        return rs[3:]
    return ""


def remove_ADV(advert):
    ''' remove ADV prefix '''
    if advert.startswith("ADV:"):
        return advert[4:]
    return advert


def advert_resp_format(advert):
    if advert.startswith("ADV:"):
        split_advert = advert.split()
        if len(split_advert) == 4:
            return (remove_ADV(split_advert[0]), remove_AD(split_advert[1]),
                    remove_RS(split_advert[3]), "")
        return ()
    if advert.startswith("EXT ADV:"):
        split_advert = advert.split()
        if len(split_advert) == 4:
            return (remove_ADV(split_advert[1]), remove_AD(split_advert[2]),
                    remove_RS(split_advert[3]), "ext")
        return ()
    return ()


def remove_duplicates(adverts):
    ''' check duplicate adverts and filter - checking MAC and TLVs (not rssi) '''
    checked = []
    ret_ind = []
    for i, advert in enumerate(adverts):
        check = advert[0] + advert[1]
        if check not in checked:
            checked.append(check)
            ret_ind.append(i)
    ret = []
    for i in ret_ind:
        ret.append(adverts[i])
    return ret


def make_json_req(json):
    json_hex = "".join(hex(ord(c))[2:] for c in json)
    req = "gattc writecmd 1 16 {}\r".format(json_hex)
    return py2to3util.str_to_bytes(req)


def split_scan_resp(resp):
    split = resp.split(" ")
    return split[0], split[1], split[3]


def write_wait(sp, buff, wait):
    sp.read_all()
    sp.write(buff)
    time.sleep(wait)
    size = sp.in_waiting
    res = sp.read(size)
    res = res.decode("utf-8").replace('\r', ' ').replace('\n', ' ')
    if "ERROR" in res or "timeout" in res:
        log.error(buff.decode('utf-8').replace('\r', '') + " - " + res)
        return ""
    else:
        log.info(buff.decode('utf-8').replace('\r', '') + " - " + res)
        return res


def write_wait_for(sp, buff, resp, size):
    sp.flush()
    sp.write(buff)
    res = sp.read_until(resp, size)
    res = res.decode("utf-8").replace('\r', ' ').replace('\n', ' ')
    if "ERROR" in res:
        log.error(buff.decode('utf-8').replace('\r', '') + " - " + res)
        return False
    else:
        log.info(buff.decode('utf-8').replace('\r', '') + " - " + res)
        return True


def find_conn_number(response):
    ''' from resposne find connection number '''
    if '(' in response and ')' in response:
        left = response.find('(')
        right = response.find(')')
        return response[left + 1:right]
    log.error("connection response lacks handle %s", response)
    return "0009FF00"


def write_conn(port, buff):
    ''' write a connection attempt, returns handle if succcess, "" if not '''
    port.read_all()
    port.write(buff)
    port.flush()
    # wait for the timeout period + 20ms
    time.sleep(CONN_TIMEOUT_MS / 1000 + 0.02)
    size = port.in_waiting
    res = port.read(size).decode('utf-8')
    log.debug("request: %s - response: %s", buff,
              res.replace('\n', '').replace('\r', ' '))
    if "timeout" in res:
        return ""
    if "ERROR" in res:
        log.error(res)
        return ""
    if "Connect:" in res:
        return find_conn_number(res)
    return ""


def enumerate_phy(phy):
    '''provides enumeration for phy setting'''
    if phy == '1M':
        return 0
    if phy == 'LE':
        return 1
    log.error("%d not possible for phy")
    return 0


def disconnect(port):
    ''' disconnect serial port '''
    write_wait_for(port, py2to3util.str_to_bytes("disconnect 1\r"),
                   b"EVBLEMSGID->DISCONNECT\n", 100)


#def connect(sp, address):
def connect(sp, address, phy):
    time.sleep(0.5)
    i = 0
    #    sp.read_all()
    phy_enum = enumerate_phy(phy)
    #    write_wait_for(sp, b'ble pair iocap 2\r', b'OK', 100)
    write_wait_for(sp, b'pair iocap 2\r', b'OK\r', 100)
    write_wait_for(sp, b'gattc open 0 0\r', b'OK\r', 100)
    #connect = "connect {} 500 500 300 5000\r".format(address)
    con_req = "connect ext {} {} {} {} {} {} 0\r".format(
        address, CONN_TIMEOUT_MS, MIN_CONN_INT_US, MAX_CONN_INT_US,
        N_SUPER_TOUT_US, phy_enum)
    handle = ""
    #    res = write_wait(sp, bytes_to_str(connect), 1.8)
    #    if res == False:
    #        return False
    time.sleep(1.0)
    sp.read_all()
    print("write attempts")
    while not handle and i < 10:
        print(("attempt {}".format(i)))
        handle = write_conn(sp, py2to3util.str_to_bytes(con_req))
        time.sleep(0.5)
        i += 1
    if not handle:
        print(("connection timeout after {} tries".format(i)))
        return False


    res = write_wait_for(sp, b'pair 1 1\r',
                         b'\n +++ Auth Key Request, type= 1', 100)
    if not res:
        disconnect(sp)
        return False
    res = write_wait_for(
        sp, b'pair passkey 1 123456\r',
        b'\nOK\r\n>\n +++ Encrypted Connection\n +++ Updated Bond', 200)

    if not res:
        disconnect(sp)
        return False
    time.sleep(0.25)

    res = write_wait_for(sp, b'gattc writecmd 1 14 0100\r', b'OK\r', 100)
    return res

BT_devices = {}
ig = IgShadow()


def get_sensor_shadow(addr):
    if addr in BT_devices:
        return BT_devices[addr]
    else:
        shadow = Bt500GgShadow(addr)
        BT_devices[addr] = shadow
        return shadow


def make_req_handle_resp(sp, request, shadow):
    resp = write_wait(sp, make_json_req(request), 1.2)
    json = handle_vsp_response(resp)
    shadow.handle_json(json)


def make_onetime_config(sp, shadow):
    try:
        with open(config_file) as fp:
            config = json.load(fp)
    except IOError:
        print(
            "Error: expecting the configuration file: config.json in the local directory"
        )
        return
    for param in config['config_onetime']:
        request = set_param_str(param, config['config_onetime'][param])
        make_req_handle_resp(sp, request, shadow)


def vsp_work(sp, phy, shadow):
    need = shadow.need_something()
    pending = shadow.pending()

    if need or pending:
        shadow.set_gatewayId(node_id)
        res = connect(sp, shadow.address, phy)
        if res != False:
            # Always set time
            make_req_handle_resp(sp, get_time_command(), shadow)

            # If we have pending messages, send them first
            if pending:
                for m in shadow.pending():
                    make_req_handle_resp(sp, m, shadow)
                shadow.pending_clear()

            # If need anything or just sent something, read everything
            if pending or need:
                for m in shadow.need_list():
                    make_req_handle_resp(sp, m, shadow)

            # If we've never configured this sensor, do some initial setting
            if shadow.need_default_config():
                make_onetime_config(sp, shadow)
                for m in shadow.need_list():
                    make_req_handle_resp(sp, m, shadow)

            # If the device needs a reset, do that now
            if shadow.need_reset():
                make_req_handle_resp(sp, get_reset_command(), shadow)
                shadow.reset_issued()

            write_wait(sp, py2to3util.str_to_bytes("disconnect 1\r"), 1)


def handle_adverts(sp, adverts):
    global gw_shadow_update_time

    if not adverts:
        return

    gw_shadow_update_needed = False

    formated = list(map(advert_resp_format, adverts))
    bt510_adverts = list(filter(is_bt510_advert, formated))
    adverts = remove_duplicates(bt510_adverts)

    if not adverts:
        return

    print(("BT510 advertisements: {}".format(adverts)))

    for advert in adverts:
        addr = advert[0]
        tlvs = advert[1]
        rssi = advert[2]
        ext = advert[3]

    # Find the sensor device shadow object that matches
    shadow = get_sensor_shadow(addr)
    shadow.clear_changed()

    # Parse the advertisement data
    resp = ResponseData(addr, tlvs, rssi, ext)
    print(resp)

    # Fetch advertisement parameters
    _type, flags, epoch, event = resp.get_type_epoch_record()
    shadow.event(_type, flags, epoch, event)
    report.response(shadow.address, shadow.serialize(False))

        # Update the gateway shadow if something changed or it's been a while
    if (time.time() - gw_shadow_update_time) >= GW_UPDATE_TIMEOUT:
        gw_shadow_update_needed = True

    if gw_shadow_update_needed:
        report.response(node_id, ig.serialize(False))
        gw_shadow_update_time = time.time()


with bluetooth.BTManager() as bt:
    # check the name of the smartbasic file loaded
    resFile = bt.at_command("at+dir")
    print(("at+dir resp: {}".format(resFile)))
    # should be r.29.4.6.49E855E3
    resFile = resFile.replace("\n06\t", "")
    resFile = resFile.replace("\r\n00\r", "")
    print(("at+dir resp: {}".format(resFile)))

    # read the firmware
    resFw = bt.at_command("ati 3")
    print(("ati 3 resp: {}".format(repr(resFw))))
    # \n10\t3\t29.4.6.0\r\n00\r
    resFw = resFw.replace("\n10\t3\t", "").replace("\r\n00\r", "")
    print(("ati 3 resp: {}".format(repr(resFw))))
    # should be 29.4.6.0

    # read the smartbasic version
    resSb = bt.at_command("ati 13")
    print(("ati 13 resp: {}".format(repr(resSb))))
    # \n10\t13\t49E8 55E3 \r\n00\r
    resSb = resSb.replace("\n10\t13\t", "").replace("\r\n00\r",
                                                    "").replace(" ", "")
    print(("ati 13 resp: {}".format(repr(resSb))))
    # should be 49E855E3

    filename = "cmd.manager.{}.{}.uwc".format(resFw, resSb)
    shortname = "r.{}.{}".format(resFw, resSb)

    # if running a known version, let it run
    # if os.path.exists("./smartbasic/cmd.manage{}.uwc".format(resFile)):

    # if using the USB dongle, don't firmware update
    if os.getenv('BL654_PORT') == '/dev/ttyUSB0':
        bt.start_app(resFile)

    # if the running version matches the required version, let it run
    elif resFile == shortname:
        bt.start_app(resFile)
    else:
        filename_to_flash = "./smartbasic/{}".format(filename)

        # if there is a file to flash for the firmware + smartbasic
        if os.path.exists(filename_to_flash):

            # This writes the BL654 Firmware Image
            at_commands = [
                "AT+cFG 211 247", "AT+cFG 212 244", "AT+cFG 213 1",
                "AT+cFG 214 1", "AT+CFG 216 251", "ATZ"
            ]

            for cmd in at_commands:
                res = bt.at_command(cmd)
            res = bt.at_command("at&f 1")
            res = bt.load_file(shortname, filename_to_flash)
            bt.start_app(shortname)
        else:
            # error condition, no local image available
            print(("error: no filename_to_flash found: {}".format(
                filename_to_flash)))


def get_input_topic(context):
    try:
        if context.client_context.custom and context.client_context.custom[
                'subject']:
            topic = context.client_context.custom['subject']
    except Exception as e:
        logging.error('Topic could not be parsed. ' + repr(e))
    return topic


def get_input_message(event):
    try:
        message = event['test-key']
    except Exception as e:
        logging.error('Message could not be parsed. ' + repr(e))
    return message

def function_handler(event, context):

    return


class SerialThread(threading.Thread):
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.running = True
        self.sp = serial.Serial(port,
                                baudrate,
                                timeout=10,
                                parity=serial.PARITY_NONE,
                                rtscts=1)
        threading.Thread.__init__(self)

    def start_port(self):
        self.running = True
        self.start()

    def stop_port(self):
        self.running = False

    def run(self):
        print("serial thread starts")
        while self.running:
            self.sp.read_all()
            self.sp.write(b'scan startex 3000 0 7 "0,0,0,0,0"\r')
            res = self.sp.read_until(b'stopped via timeout')
            if (res != None):
                res = res.decode('utf-8')
                lines = res.split("\n")
                adverts = list([x for x in lines if x.find("ADV:") >= 0])
                print(("number of adverts {}".format(len(adverts))))
                if len(adverts) >= 1:
                    handle_adverts(self.sp, adverts)
            time.sleep(1)

        print("serial thread ends")


# Termination handler
def on_sigterm(signal, frame):
    global port
    logging.warn('SIGTERM received, stopping serial thread.')
    if port:
        port.stop_port()
    # Need to exit since this overrides the framework handler
    sys.exit(0)


signal.signal(signal.SIGTERM, on_sigterm)

time.sleep(1)

print("opening /dev/ttyS2:115200:8n1\r")
port = os.getenv('BL654_PORT', '/dev/ttyS2')
port = SerialThread(port, 115200)
port.start_port()

report.request(node_id)

if __name__ == "__main__":
    pass
