import logging
import logging.handlers
import os
from datetime import datetime
# Set up logger with appropriate handler
if not os.path.exists("logs"):
    os.makedirs("logs") 

timeN = datetime.now()
time_s = timeN.strftime("%m_%d")
LOG_FILENAME = "logs/bt510_prod_log_{}".format(time_s)

my_logger = logging.getLogger()
my_logger.setLevel(logging.DEBUG)
FORMMATTER = logging.Formatter(
    '%(asctime)s, %(message)s')
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME,
                                               maxBytes=1000000,
                                               backupCount=1000)

handler.setFormatter(FORMMATTER)
my_logger.addHandler(handler)
console = logging.StreamHandler()
my_logger.addHandler(console)

mac_list = []


def log_mac(mac):
    if mac not in mac_list:
        mac_list.append(mac)
        my_logger.debug(str(mac))
