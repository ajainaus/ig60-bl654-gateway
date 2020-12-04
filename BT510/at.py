''' ati interface '''
import re
import sys
import time
import serial
import py2to3util

def get_err(response):
    if '\t' in response:
        error = response.split('\t')[1].strip()
    try:
        error_code = int(error, 16)
        return get_BL654_error(error_code)
    except ValueError as err:
        pass
    return ""


def get_BL654_error(error):
    with open('codes.csv', 'r') as f:
        # the fist line doesn't have an error code
        f.readline()
        for line in f:
            code = line.split('=')
            try:
                err_code_int = int(code[0])
                if err_code_int == error:
                    return code[1]
            except ValueError as err:
                pass
        return ""


class AtException(Exception):
    def __init__(self, err):
        self.err_str = err

    def __str__(self):
        return get_err(self.err_str)


def timeit(fun):
    def timed(*args, **kw):
        ts = time.time()
        res = fun(*args, **kw)
        te = time.time()
        print(('{} {} ms'.format(fun.__name__, (te - ts) * 1000)))
        return res

    return timed


def write_cmd(port, cmd, expected):
    ''' cmd '''
    cmd_cr = cmd + '\r\n'
    b_cmd = py2to3util.str_to_bytes(cmd_cr)
    b_expected = py2to3util.str_to_bytes(expected)
    port.write(b_cmd)
    port.flush()
    res = port.read_until(b_expected)
    if res:
        return py2to3util.bytes_to_str(res)
    else:
        return ""


def cmd_resp(port, cmd, until, reg):
    at_resp = write_cmd(port, cmd, until)
    resp = re.search(reg, at_resp)
    if resp:
        return resp.group()
    else:
        print(at_resp)
        raise AtException(at_resp)


def get_firmware_version(port):
    try:
        return cmd_resp(port, "ati 3", "00\r", r"\d.\d.\d.\d")
    except AtException as ate:
        print(ate)
        return ""


def reset(port):
    return cmd_resp(port, "atz", "00\r", "00\r")


def start_app(port):
    try:
        return cmd_resp(port, "coded", "OK\r\n", r"LAIRD BL654")
    except AtException as ate:
        print(ate)
        port.write(b"\r\n")
        port.flush()
        reset(port)
        try:
            return cmd_resp(port, "coded", "OK\r\n", r"LAIRD BL654")
        except AtException as ate:
            print(ate)
            print("unable to start SmartBasic and receive expected response")
            sys.exit(5)


def main():
    print("startup")
    port = '/dev/ttyUSB0'
    with serial.Serial(port,
                       115200,
                       timeout=1,
                       parity=serial.PARITY_NONE,
                       rtscts=1) as port:
        resp = start_app(port)
        print(resp)


if __name__ == '__main__':
    main()
