'''parsing for scan response '''
from construct import ConstructError

from construct import Struct, GreedyString, Byte, Switch, BitStruct, BitsInteger,\
    Flag, Array, GreedyRange, Int32ul, Int16ul

FLAGS_TYPE = 1
MFG_DEFINED_TYPE = 0XFF
SHORT_LOCAL_NAME_TYPE = 8
NAME_TYPE = 9
COMPANY_ID = 0x77
OTHER_ID = 0x1C
LEN_BT510_EXT_FW_1_2 = 35
LEN_BT510_EXT_FW_1_4 = 38
LEN_EXT_SCAN_RESP_E4 = 16


# def is_bt510_scan_resp(advert):
#    '''method to determine if advert is from Bt510'''
#    if len(advert) < 12:
#        return False
#    return (advert[8] == 'F' and advert[9] == 'F' and advert[10] #== '7'
#            and advert[11] == '7')


unknown = Struct("byte1" / Byte, "byte2" / Byte)

BT510 = Struct(
    "company_id1" / Byte,
    "company_id2" / Byte,
    "protocol_id" / Int16ul,
    "network_id" / Int16ul,
    "flags" / Int16ul,
    "bt_addr" / Array(6, Byte),
    "record_type" / Byte,
    "record_number" / Int16ul,
    "epoch" / Int32ul,
    "data" / Array(4, Byte),
    "res" / Byte,
)

BT510_EXT_FW_1_2 = Struct(
    "company_id1" / Byte,
    "company_id2" / Byte,
    "protocol_id" / Int16ul,
    "network_id" / Int16ul,
    "flags" / Int16ul,
    "bt_addr" / Array(6, Byte),
    "record_type" / Byte,
    "record_number" / Int16ul,
    "epoch" / Int32ul,
    "data" / Array(4, Byte),
    "res" / Byte,
    "extra" / Array(8, Byte),
)
BT510_EXT_FW_1_4 = Struct(
    "company_id1" / Byte, "company_id2" / Byte, "protocol_id" / Int16ul,
    "network_id" / Int16ul, "flags" / Int16ul, "bt_addr" / Array(6, Byte),
    "record_type" / Byte, "record_number" / Int16ul, "epoch" / Int32ul,
    "data" / Array(4, Byte), "res" / Byte, "product_id" / Int16ul,
    "firmware_version_major" / Byte, "firmware_version_minor" / Byte,
    "firmware_version_patch" / Byte, "firmware_type" / Byte,
    "configuration_version" / Byte, "bootloader_version_major" / Byte,
    "bootloader_version_minor" / Byte, "bootloader_version_patch" / Byte,
    "hardware_version" / Byte)

EXT_SCAN_RESP_E4 = Struct(
    "company_id1" / Byte, "company_id2" / Byte, "protocol_id" / Int16ul,
    "product_id" / Int16ul, "firmware_version_major" / Byte,
    "firmware_version_minor" / Byte, "firmware_version_patch" / Byte,
    "firmware_type" / Byte, "configuration_version" / Byte,
    "bootloader_version_major" / Byte, "bootloader_version_minor" / Byte,
    "bootloader_version_patch" / Byte, "hardware_version" / Byte)

ADVERT = Struct(
    "length" / Byte,
    "type" / Byte,
    "value" / Switch(lambda ctx: ctx.type, {
        FLAGS_TYPE:
        BitStruct(
            "reserved" / BitsInteger(3),
            "le_br_edr_support_host" / Flag,
            "le_br_edr_support_controller" / Flag,
            "br_edr_not_supported" / Flag,
            "le_general_discoverable_mode" / Flag,
            "le_limited_discoverable_mode" / Flag,
        ),
        MFG_DEFINED_TYPE:
        Switch(lambda ctx: ctx.length, {
            27: BT510,
            LEN_BT510_EXT_FW_1_2: BT510_EXT_FW_1_2,
            LEN_BT510_EXT_FW_1_4: BT510_EXT_FW_1_4,
            LEN_EXT_SCAN_RESP_E4: EXT_SCAN_RESP_E4,
            3: unknown
        },
               default=Array(lambda ctx: ctx.length - 1, Byte)),
        SHORT_LOCAL_NAME_TYPE:
        GreedyString("utf8"),
        NAME_TYPE:
        GreedyString("utf8")
    },
                     default=Array(lambda ctx: ctx.length - 1, Byte)),
)

advert_frame = GreedyRange(ADVERT)


def parse(hex_string):
    barr = bytes(bytearray.fromhex(hex_string))
    frame = advert_frame.parse(barr)
    return frame
