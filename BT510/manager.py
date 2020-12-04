''' implement the python interface to the SmartBasic cmd manager application '''
import time
import logging
import sys
import re

''' these values work well to connect, usually first or second try '''
CONN_TIMEOUT_MS = 4000
MIN_CONN_INT_US = 7500
MAX_CONN_INT_US = 0
# link supervisor timeout
N_SUPER_TOUT_US = 500

MANAGER = logging.getLogger("cli")


def timeit(fun):
    ''' timing clouser - for profiling '''
    def timed(*args, **kw):
        start = time.time()
        res = fun(*args, **kw)
        end = time.time()
        print(('{} {} ms'.format(fun.__name__, (end - start) * 1000)))
        return res

    return timed


def bytes_to_str(string):
    ''' convert bytes to string - regarless of version '''
    if sys.version_info < (3, 0):
        return bytes(string)
    return bytes(string, "utf-8")


def make_req(json):
    ''' SB command requires data portion as hexstring '''
    json_hex = "".join(hex(ord(c))[2:] for c in json)
    req = "gattc writecmd 1 16 {}\r".format(json_hex)
    return bytes_to_str(req)


def write_cmd(port, buff):
    ''' writes individual commands '''
    port.read_all()
    cmd = make_req(buff)
    if len(cmd) > 50:
        chunk_size = 200
        chunks = [
            cmd[i:i + chunk_size] for i in range(0, len(cmd), chunk_size)
        ]
        for chunk in chunks:
            port.write(chunk)
    else:
        port.write(cmd)

    port.flush()
    time.sleep(0.3)
    size = port.in_waiting
    res = port.read(size).decode('utf-8').replace('\n', ' ').replace('\r', ' ')
    res = res.lstrip("OK  >hConn=0001FF00")
    return res


def find_conn_number(response):
    ''' from resposne find connection number '''
    if '(' in response and ')' in response:
        left = response.find('(')
        right = response.find(')')
        return response[left + 1:right]
    MANAGER.error("connection response lacks handle %s", response)
    return "0009FF00"


def find_handle(response):
    ''' from resposne, find handle '''
    if 'handle=' in response:
        left = response.find('handle=')
        return int(re.search(r'\d+', response[left:]).group())
    MANAGER.error("conection response lacks handle number %s", response)
    return 0


def write_conn(port, buff):
    ''' write a connection attempt, returns handle if succcess, "" if not '''
    port.read_all()
    port.write(buff)
    port.flush()
    # wait for the timeout period + 20ms
    time.sleep(CONN_TIMEOUT_MS / 1000 + 0.02)
    size = port.in_waiting
    res = port.read(size).decode('utf-8')
    MANAGER.debug("request: %s - response: %s", buff,
                  res.replace('\n', '').replace('\r', ' '))
    if "timeout" in res:
        return ""
    if "ERROR" in res:
        MANAGER.error(res)
        return ""
    if "Connect:" in res:
        return find_conn_number(res)
    return ""


def write_wait_for(port, buff, resp, size):
    ''' write and wait for particluar response '''
    port.read_all()
    port.write(buff)
    port.flush()
    res = port.read_until(resp, size).decode('utf-8').replace('\n',
                                                              ' ').replace(
        '\r', ' ')
    if "ERROR" in res:
        MANAGER.error(buff.decode('utf-8').replace('\r', '') + " - " + res)
        return False
    MANAGER.debug("request: %s response: %s",
                  buff.decode('utf-8').replace('\r', ''), res)

    return True


def disconnect(port):
    ''' disconnect serial port '''
    write_wait_for(port, bytes_to_str("disconnect 1\r"),
                   b"EVBLEMSGID->DISCONNECT\n", 100)


def enumerate_phy(phy):
    '''provides enumeration for phy setting'''
    if phy == '1M':
        return 0
    if phy == 'LE':
        return 1
    MANAGER.error("%d not possible for phy")
    return 0


def connect(port, address, phy):
    ''' make vsp connection '''
    time.sleep(0.02)
    i = 0
    phy_enum = enumerate_phy(phy)
    res = write_wait_for(port, b'pair iocap 2\r', b'OK\r', 100)
    write_wait_for(port, b'gattc open 0 0\r', b'OK\r', 100)
    con_req = "connect ext {} {} {} {} {} {} 0\r".format(
        address, CONN_TIMEOUT_MS, MIN_CONN_INT_US, MAX_CONN_INT_US,
        N_SUPER_TOUT_US, phy_enum)
    handle = ""
    while not handle and i < 10:
        print(("attempt {}".format(i)))
        handle = write_conn(port, bytes_to_str(con_req))
        i += 1
    if not handle:
        print(("connection timeout after {} tries".format(i)))
        return False

    res = write_wait_for(port, b'pair 1 1\r',
                         b'\n +++ Auth Key Request, type= 1', 100)
    if not res:
        disconnect(port)
        return False
    res = write_wait_for(port, b'pair passkey 1 123456\r',
                         b'\nOK\r\n>\n +++ Encrypted Connection\n +++ Updated Bond', 200)

    if not res:
        disconnect(port)
        return False
    time.sleep(0.25) 
    res = write_wait_for(port, b'gattc writecmd 1 14 0100\r', b'OK\r', 100)
    return handle


PHY_OPTS = {
    '1M': 4,
    'LE': 6,
    'both': 7,
}


def scan(port, timestamp, phy):
    ''' scan for advertisements '''
    if phy not in PHY_OPTS:
        print(("phy option error{} ".format(phy)))
        return []
    phy_opt = PHY_OPTS[phy]
    cmd = 'scan startex {} 0 {}  "0" 0\r'.format(timestamp, phy_opt)
    port.write(cmd.encode('utf-8'))
    port.flush()
    res = port.read_until(b'stopped via timeout', 6000)
    res = res.decode('utf-8')
    lines = res.split('\n')
    return lines


def remove_adv(advert):
    ''' SB response prefixes ADV: - remove this '''
    if advert.startswith("ADV:"):
        return advert[4:]
    return advert


def remove_ext(advert):
    ''' remove EXT_ADV '''
    if advert.startswith("EXT ADV:"):
        return advert[8:]
    return advert


def remove_ad(data):
    ''' remove AD prefix '''
    if data.startswith("AD:"):
        ret_index = data[3:].find(":")
        if ret_index != -1:
            return data[4 + ret_index:]  # it's 3 +1 + ret_index
        return data[3:]
    return data


def remove_rs(rs):
    ''' remove RS prefix '''
    if rs.startswith("RS:"):
        return rs[3:]
    return ""


def advert_resp_format(advert):
    if advert.startswith("ADV:"):
        split_advert = advert.split()
        if len(split_advert) == 4:
            return (remove_adv(split_advert[0]), remove_ad(split_advert[1]),
                    remove_rs(split_advert[3]), "")
        return ()
    if advert.startswith("EXT ADV:"):
        split_advert = advert.split()
        if len(split_advert) == 4:
            return (remove_adv(split_advert[1]), remove_ad(split_advert[2]),
                    remove_rs(split_advert[3]), "ext")
        return ()
    return ()


def is_bt510_advert(ad_resp):

    print(("ad_resp len: {}".format(len(ad_resp))))
    if len(ad_resp) < 3:
        return False
    advert = ad_resp[1]
    print(("addr: {}".format(ad_resp[0])))
    print(("advert: {}".format(advert)))
    if len(advert) < 12:
        return False
    return (advert[8] == 'F' and advert[9] == 'F' and advert[10] == '7'
            and advert[11] == '7')
