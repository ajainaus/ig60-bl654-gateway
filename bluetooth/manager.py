import os
import serial
import re
from functools import partial
from . import error as bt_error
import time
import py2to3util
# import dbus


def strip_extra_characters(str):
    str = re.sub('\d+\t', "", str)
    str = re.sub('[\r"0"]', "", str)
    return str

def generic_handler(cmd, err):
    return bt_error.get_BL654_error_from_response(err)


class BTManager():
    def __enter__(self):
        # self.bus = dbus.SystemBus()
        # self.device_svc = dbus.Interface(self.bus.get_object('com.lairdtech.device.DeviceService',
        #     '/com/lairdtech/device/DeviceService'), 'com.lairdtech.device.public.DeviceInterface')
        #
        # if self.device_svc.SetBtBootMode(1) != 0:
        #     raise Exception('Failed SetBtBootMode to 1 via DBus')
        #
        port = os.getenv('BL654_PORT', '/dev/ttyS2')
        print(("Running with port: {}".format(port)))
        # time.sleep(1)
        self.sp = serial.Serial(port,
                                115200,
                                timeout=2,
                                parity=serial.PARITY_NONE,
                                rtscts=1)
        self.sp.send_break(duration=0.25)
        return self

    def __exit__(self, type, value, traceback):
        self.sp.close()

    def send_single_cmd(self, cmd, meta, handler):
        cmd_line = cmd + ' ' + meta + '\r\n'
        print(("sending single command {}".format(repr(cmd_line))))
        self.sp.write(py2to3util.str_to_bytes(cmd_line))
        self.sp.flush()
        res = self.sp.read_until(b'00\r', 100)
        print(("response {}  size {} end".format(repr(res), len(res))))
        if b'01\t' not in res:
            return (True, "")
        else:
            err_string = handler(cmd, res)
        return (False, err_string)

    def reset(self):
        return self.send_single_cmd('atz', '', generic_handler)

    def read_dir(self):
        self.sp.write(b'at+dir\r\n')
        self.sp.flush()
        res = self.sp.read_until(b'00\r', 500)
        if b'01\t' in res:
            return (False, bt_error.get_BL654_error_from_response(res))
        res_str = res.decode('utf-8')
        res = res_str.split('\n')
        res = list(map(strip_extra_characters, res))
        return (True, list([x for x in res if x != '']))

    def del_file(self, name):
        return self.send_single_cmd('at+del', '"{}"'.format(name),
                                    generic_handler)

    def load_file(self, name, file):
        print(("file to load {} with name {}".format(file, name)))
        try:
            with open(file, 'rb') as f:
                res = self.sp.write(b'atz \r\n')
                self.sp.flush()
                time.sleep(0.5)
                res = self.sp.readall()
                print(("open file response: {}".format(repr(res))))
                fowcmd = 'at+fow \"' + name + '\"\r\n'
                res = self.sp.write(py2to3util.str_to_bytes(fowcmd))
                self.sp.flush()
                time.sleep(4)
                res = self.sp.readall()
                print(("open file response: {}".format(repr(res))))

                for block in iter(partial(f.read, 50), b''):
                    str_block = block.hex()
                    strblock = 'at+fwrh \"' + str_block + '\"\r\n'
                    print(("write chunk {}".format(repr(str_block))))
                    self.sp.write(py2to3util.str_to_bytes(strblock))
                    self.sp.flush()
                    res = self.sp.read_until(b'00\r', 100)
                    print(("write chunk response {}".format(repr(res))))
                    if b'01\r' in res:
                        return False
                res = self.send_single_cmd('at+fcl', '', generic_handler)
                print(res)
                return res

#        except IOError as e:
        except IOError:
            print("IO error ")

    def at_command(self, cmd):
        print(("at cmd:{}".format(cmd)))
        cmd = cmd + "\r\n"
        self.sp.write(py2to3util.str_to_bytes(cmd))
        self.sp.flush()
        time.sleep(3)
        size = self.sp.in_waiting
        print(("size reponse {}".format(size)))
        res = self.sp.read(size)
        print(("response raw:{}".format(repr(res))))
        return py2to3util.bytes_to_str(res)

    def start_app(self, cmd):
        print(("starting app:{}".format(cmd)))
        cmd = 'at+run \"' + cmd + "\"\r\n"
        self.sp.write(py2to3util.str_to_bytes(cmd))
        self.sp.flush()
        time.sleep(1)
        size = self.sp.in_waiting
        print(("size reponse {}".format(size)))
        res = self.sp.read(size)
        print(("response raw:{}".format(repr(res))))
