import json
import calendar
import time
import sys

def handle_id(json_resp, ids):
    for p in ids:
        print((json_resp[p]))


def fmt_list(params):
    pstr = ""
    for p in params:
        pstr += '"{}", '.format(p)
    return pstr[:-2]


def get_param_str(params):
    if type(params) is list:
        list_str = fmt_list(params)
        ret = r'{"jsonrpc": "2.0", "method": "get", "id": ' +\
            "{}".format(get_id()) + r', "params": [' + "{}".format(list_str) + r']}'
    else:
        ret = r'{"jsonrpc": "2.0", "method": "get", "id": ' +\
            "{}".format(get_id()) + r', "params": "' + "{}".format(params) + r'"}'
    return ret


def is_string(st):
    if sys.version_info >= (3, 0):
        return type(st) is str
    else:
        return type(st) is str
# for now operate only on python 3.x
#         return type(st) is unicode    


def set_param_str(param, val):
    if is_string(val):
        return r'{"jsonrpc": "2.0", "method": "set", "id": ' + "{}".format(
            get_id()) + r' , "params": {"' + "{}".format(
                param) + r'":"' + "{}".format(val) + r'"}}'
    else:
        return r'{"jsonrpc": "2.0", "method": "set", "id": ' + "{}".format(
            get_id()) + r' , "params": {"' + "{}".format(
                param) + r'":' + "{}".format(val) + r'}}'


def get_time_command():
    mytime = calendar.timegm(time.gmtime())
    return r'{"jsonrpc": "2.0", "method": "setEpoch", "params": ' + r'[ {} ]'.format(
        mytime) + r', "id": {}'.format(get_id()) + ' }'


def get_reset_command():
    return r'{"jsonrpc": "2.0", "method": "reboot", "id":' + '{}'.format(
        get_id()) + r' }'


def get_dump_command():
    return r'{"jsonrpc": "2.0", "method": "dump", "id":' + '{}'.format(
        get_id()) + r' }'


def get_bootloader_command():
    return r'{"jsonrpc": "2.0", "method": "reboot","params":[1] ,"id": 9 }'


def return_only_json(resp):
    start = resp.find('{')
    if start == -1:
        return ""
    return resp[start:]


def json_parse(json_str):
    try:
        ret = json.loads(json_str)
        return ret
    except json.decoder.JSONDecodeError as e:
        print(e)
        return {}


def handle_vsp_response(resp):
    json_str = return_only_json(resp)
    if len(json_str) < 4:
        return {}
    return json_parse(json_str)


tid = 0

def get_id():
    global tid
    tid += 1
    return tid

if __name__ == '__main__':
    pass
