from json import JSONEncoder
import json
import time
import logging

class IgShadow(JSONEncoder):
    def __init__(self):
        self.address = "IG"
        self.bt510 = {
            "sensorTtl": 3600,
            "sensors": [],
            "codedPhySupported": True
        }
        self.max_size = 100


    def serialize(self, clear_desired):
        # Filter the sensor list by TTL
        self.bt510["sensors"] = [s for s in self.bt510["sensors"]
            if s[2] == True or
               s[1] >= (time.time() - self.bt510["sensorTtl"])]

        # Build the state structure
        reported_state = {
            "bt510": self.bt510
        }
        if clear_desired:
            reported = {"reported": reported_state, "desired": None }
        else:
            reported = {"reported": reported_state}
        ret = {"state": reported}

        # Convert to JSON
        return json.dumps(ret, default=lambda o: o.__dict__)

    def is_sensor_enabled(self, addr):
        for s in self.bt510["sensors"]:
            if s[0] == addr:
                return s[2]
        return False

    def update_sensor(self, addr, epoch):
        l = [ addr, epoch, False ]
        if len(self.bt510["sensors"]) >= self.max_size:
            self.bt510["sensors"] = self.bt510["sensors"][1:]
        do_append = True
        for s in self.bt510["sensors"]:
            if s[0] == addr:
                s[1] = epoch
                do_append = False
        if do_append:
            self.bt510["sensors"].append(l)
        return do_append

    def update_sensor_whitelist(self, addr, epoch, enabled):
        list_updated = False
        l = [ addr, epoch, enabled ]
        if len(self.bt510["sensors"]) >= self.max_size:
            self.bt510["sensors"] = self.bt510["sensors"][1:]
            list_updated = True
        do_append = True
        for s in self.bt510["sensors"]:
            if s[0] == addr:
                if int(s[2]) != int(enabled):
                    list_updated = True
                    if int(enabled) == 0:
                        logging.info("Disabling sensor {}".format(addr))
                    else:
                        logging.info("Enabling sensor {}".format(addr))
                s[2] = enabled
                do_append = False
        if do_append:
            self.bt510["sensors"].append(l)
            list_updated = True
        return list_updated

    def enabled_sensor_list(self):
        return [x[0] for x in [x for x in self.bt510['sensors'] if x[2] != False]]
