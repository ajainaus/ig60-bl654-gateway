'''cli for BT510'''
import logging
import sys
import json
import time
import signal
import re
import serial
import fire
import bt510.log
import bt510.vsp
import bt510.at
from bt510.response import ResponseData
import bt510.manager as cmd_mgr

APP_VERSION = 0.4

# create logger
LOGGER = logging.getLogger('cli')
LOGGER.setLevel(logging.CRITICAL)


def signal_handler(_sig, _frame):
    ''' handles ctr-C '''
    LOGGER.debug("received ctr-C")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def get_sensor_config(config, addr):
    ''' from config, return config- returns None if sensor doesn't exist in config '''
    sensor_list = config['Sensors']
    for sensor in sensor_list:
        if sensor['address'] == addr:
            return sensor
    return None


def load_config():
    ''' load config file '''
    try:
        with open('config.json') as t_file:
            config = json.load(t_file)
            return config
    except IOError:
        print(
            "Error: expecting the configuration file: config.json in the local directory"
        )
        sys.exit(1)


def get_port(config):
    ''' return target port from config '''
    try:
        port = config['port']
        return port
    except KeyError as err:
        print("config file needs to specify port")
        LOGGER.critical(err)
        sys.exit(3)


def bootloader(addr, phy="1M", verbose=0):
    '''put BT510 into bootloader mode '''
    check_phy(phy)
    check_verbose(verbose)

    print("send cmd to put into bootloader ")
    request = bt510.vsp.get_bootloader_command()
    start_and_get(addr, phy, request)


def check_verbose(verbose):
    ''' currently supporting two levels of verbosity: all or nothing'''
    if verbose not in [0, 1]:
        print("verbositiy levels: 0 ,1 ")
        raise ValueError()
    if verbose == 1:
        LOGGER.setLevel(logging.DEBUG)
    return True


def check_phy(phy):
    ''' check phy settings '''
    if phy not in ['LE', '1M']:
        print(("parameter error:{} is not valid \nuse --phy=1M or --phy=LE ".
              format(phy)))
        raise ValueError()


def load_and_start():
    ''' load confiuration file, start app '''
    config = load_config()
    port = get_port(config)
    port = open_port(port)
    start_sb_app(port)
    return port


def start_and_get(addr, phy, request):
    ''' start things up, send the request and print the results '''
    port = load_and_start()
    if cmd_mgr.connect(port, addr, phy):
        print(request)
        resp = cmd_mgr.write_cmd(port, request)
        print(resp)
        cmd_mgr.disconnect(port)


def get_param(addr, param, phy="1M", verbose=0):
    '''specify the address and a paramater name, this app will read that parameter  '''
    check_phy(phy)
    check_verbose(verbose)
    print(("get param {}".format(param)))
    request = bt510.vsp.get_param_str(param)
    start_and_get(addr, phy, request)


def start_and_set(addr, phy, request):
    ''' start things up, send the request and print the results '''
    port = load_and_start()
    if cmd_mgr.connect(port, addr, phy):
        print(request)
        resp = cmd_mgr.write_cmd(port, request)
        print(resp)
        cmd_mgr.disconnect(port)


def set_param(addr, param, val, phy='1M', verbose=0):
    '''specify the address and a paramater name, this app will write that parameter  '''
    check_phy(phy)
    check_verbose(verbose)
    print(("set param {} {}".format(param,val)))
    request = bt510.vsp.set_param_str(param, val)
    start_and_set(addr, phy, request)


def get_dump(addr, phy="1M", verbose=0):
    '''specify the address and a paramater name, this app will read all parameters  '''
    check_phy(phy)
    check_verbose(verbose)
    print(("get param dump from {}".format(addr)))
    request = bt510.vsp.get_dump_command()
    start_and_get(addr, phy, request)


def configure(addr, phy="1M", verbose=1):
    '''specifiy the target device address, this app will write \
            the configuration specified in config.json to the \
            device. Additionally, it will set the time and reboot the device'''

    check_phy(phy)
    check_verbose(verbose)

    print(("configure {}".format(addr)))
    config = load_config()
    port = get_port(config)
    config = get_sensor_config(config, addr)
    if config is None:
        LOGGER.error("did not find configuration for that sensor ")
        print(("error: did not find configuration for sensor {}".format(addr)))
        sys.exit(2)
    port = open_port(port)
    start_sb_app(port)
    if cmd_mgr.connect(port, addr, phy):
        for param in config:
            if param == "address":
                continue
            request = bt510.vsp.set_param_str(param, config[param])
            print(request)
            LOGGER.debug(request)
            res = cmd_mgr.write_cmd(port, request)
            print(res)
            LOGGER.debug("writing param %s value %s ", param, config[param])

        cmd_set_time = bt510.vsp.get_time_command()
        LOGGER.info(cmd_set_time)
        cmd_mgr.write_cmd(port, cmd_set_time)
        reboot_cmd = bt510.vsp.get_reset_command()
        LOGGER.info(reboot_cmd)
        cmd_mgr.write_cmd(port, reboot_cmd)
        cmd_mgr.disconnect(port)


def start_sb_app(port):
    port.read_all()
    bt510.at.start_app(port)


def open_port(port):
    ''' open serial port '''
    port = serial.Serial(port,
                         115200,
                         timeout=1,
                         parity=serial.PARITY_NONE,
                         rtscts=1)
    port.send_break(duration=0.25)
    return port


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


def handle_adverts(adverts):
    '''filter advert responses for only bt510 responses'''
    print("\nraw adverts")
    print(adverts)
    formated = list(map(cmd_mgr.advert_resp_format, adverts))
    print("\nformatted adverts")
    print(formated)
    bt510_adverts = list(filter(cmd_mgr.is_bt510_advert, formated))
    print("\nbt510 adverts")
    print(bt510_adverts)
    adverts = remove_duplicates(bt510_adverts)
    print("\nadverts")
    print(adverts)
    for advert in adverts:
        resp = ResponseData(advert[0], advert[1], advert[2], advert[3])
        print(resp)


def set_tx_power(port, phy):
    ''' this is for the BL654PA '''
    if phy in ['LE', 'both']:
        cmd_mgr.write_wait_for(port, b"txpower=14\r\n", b"OK\r\n", 20)


def monitor(phy='1M', verbose=1):
    '''monitor advertisements '''
    check_phy(phy)
    check_verbose(verbose)

    port = load_and_start()
    while 1:
        port.read_all()
        lines = cmd_mgr.scan(port, 1000, phy)
        adverts = list(
            [x for x in lines if x.startswith("ADV:") or x.startswith("EXT ADV:")])
        handle_adverts(adverts)
        LOGGER.debug("read {} advertisements".format(len(adverts)))
        time.sleep(0.002)


def bytes_to_str(b_input):
    '''convert bytes to string'''
    if sys.version_info < (3, 0):
        return str(b_input)
    return b_input.decode("utf-8")


def bl654_firmware(port):
    ''' retrive the firmware string for the bl654 '''
    return bt510.at.get_firmware_version(port)


def bl654_app(port):
    ''' retrive the firmware string for the bl654 '''
    port.write(b"version\r\n")
    port.flush()
    fw_ver = port.read_until(b"\n", 20)
    LOGGER.debug(fw_ver)
    if fw_ver:
        res = re.search(r'\d.\d', bytes_to_str(fw_ver))
        if not res:
            return ""
        return res.group()
    return ""


def production_log():
    port = load_and_start()
    phy = '1M'
    while 1:
        port.read_all()
        lines = cmd_mgr.scan(port, 2500, phy)
        adverts = list(
            [x for x in lines if x.startswith("ADV:") or x.startswith("EXT ADV:")])
        formated = list(map(cmd_mgr.advert_resp_format, adverts))
        bt510_adverts = list(filter(cmd_mgr.is_bt510_advert, formated))
        adverts = remove_duplicates(bt510_adverts)
        for ad in adverts:
            bt510.log.log_mac(ad[0])
        time.sleep(0.5)


def version():
    '''retrive version information'''
    config = load_config()
    port = get_port(config)
    with serial.Serial(port,
                       115200,
                       timeout=0.5,
                       parity=serial.PARITY_NONE,
                       rtscts=1) as sp:
        sp.send_break(duration=0.25)
        sp.write(b"atz\r\n")
        sp.flush()
        sp.read_until(b"00\n", 10)
        bl_fw = bl654_firmware(sp)
        start_sb_app(sp)
        bl_app = bl654_app(sp)
        print(("BL654 firmware version: {}".format(bl_fw)))
        print(("SmartBasic app version: {}".format(bl_app)))
        print(("CLI version:{}".format(APP_VERSION)))


COMMAND_OPTIONS = {
    "monitor": monitor,
    "configure": configure,
    "get": get_param,
    "bootloader": bootloader,
    "version": version,
    "log": production_log,
    "dump": get_dump,
    "set": set_param
}


def main():
    '''main'''
    fire.Fire(COMMAND_OPTIONS)


if __name__ == '__main__':
    main()
