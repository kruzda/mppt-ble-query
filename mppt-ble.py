#!/usr/bin/env python3
import gatt
import time
import os
from threading import Timer
import signal
import sys
import json
from prometheus_client import start_http_server, Gauge


uptime = Gauge('uptime', 'Uptime Counter')
pv_u = Gauge('pv_u', 'Solar Cell Voltage')
pv_i = Gauge('pv_i', 'Solar Cell Amps')
pv_p = Gauge('pv_p', 'Solar Cell Power')
b1_u = Gauge('b1_u', 'Battery 1 Voltage')
b1_i = Gauge('b1_i', 'Battery 1 Amps')
b2_u = Gauge('b2_u', 'Battery 2 Voltage')
b2_i = Gauge('b2_i', 'Battery 2 Amps')
some_mode_1 = Gauge('some_mode_1', 'Unknown status #1')
some_mode_2 = Gauge('some_mode_2', 'Unknown status #2')
some_mode_3 = Gauge('some_mode_3', 'Unknown status #3')
some_mode_4 = Gauge('some_mode_4', 'b1 charging')
some_mode_5 = Gauge('some_mode_5', 'Temp')
some_mode_6 = Gauge('some_mode_6', 'Unknown status #6')
some_mode_7 = Gauge('some_mode_7', 'b2 charging')
some_mode_8 = Gauge('some_mode_8', 'Unknown status #8')
random_1 = Gauge('random_1', 'Likely random value #1')
random_2 = Gauge('random_2', 'Likely random value #2')


manager = gatt.DeviceManager(adapter_name='hci0')

init_commands = [
    "c00108ddf67d71c94b4b324192c0",
    "c02502a02030d3c0",
    "c05206a03030303030305c91c0"
]

init_commands.reverse()

query_command = "c02002a020fcd3c0"

value = ""


def get_value():
    return value


def set_value(v):
    global value
    value = v


def process_value(v):
    data = [str(i).zfill(3) for i in [int(b) for b in v]]
    if len(data) == 32:
        for i in range(len(data)):
            if data[i] == 219 and data[i+1] == 220:
                data.pop(i)
                data.pop(i)
                break
    if len(data) == 30:
        prom_metrics = {
            "uptime": hex_to_dec(value[3:7]),
            "pv_u": float(hex_to_dec(value[9:11])/100),
            "pv_i": float(hex_to_dec(value[11:13])/100),
            "pv_p": int(float(hex_to_dec(value[9:11])/100)*float(hex_to_dec(value[11:13])/100)),
            "b1_u": float(hex_to_dec(value[14:16])/100),
            "b1_i": float(hex_to_dec(value[16:18])/100),
            "b2_u": float(hex_to_dec(value[20:22])/100),
            "b2_i": float(hex_to_dec(value[22:24])/100),
            "some_mode_1": int(value[7]),
            "some_mode_2": int(value[8]),
            "some_mode_3": int(value[18]),
            "some_mode_4": int(value[19]),
            "some_mode_5": (int(value[13]) - 32) * (5/9),
            "some_mode_6": int(value[24]),
            "some_mode_7": int(value[25]),
            "some_mode_8": int(value[26]),
            "random_1": int(value[27]),
            "random_2": int(value[28]),
        }
        for k in prom_metrics.keys():
            if type(prom_metrics[k]) not in [list, dict, str]:
                globals()[k].set(prom_metrics[k])


def hex_to_dec(h):
    r = 0
    for i, v in enumerate(h):
        x = len(h)-i-1
        r += int(v)*(255**x)
    return r

    
class AnyDevice(gatt.Device):
    def services_resolved(self):
        super().services_resolved()
        self.frequency = 0
        self.set_frequency(int(os.environ.get('MPPT_BLE_FREQ', 5)))
        self.prevtime = int(time.monotonic()) - (self.frequency * 2)
        self.prevvalue = []

        service = next(
            s for s in self.services
            if s.uuid == '0000fff0-0000-1000-8000-00805f9b34fb')

        characteristic = next(
            c for c in service.characteristics
            if c.uuid == '0000fff1-0000-1000-8000-00805f9b34fb')

        characteristic.enable_notifications()

    def characteristic_value_updated(self, characteristic, value):
        self.interpret(value)

    def interpret(self, value):
        thistime = int(time.monotonic())
        timeout = Timer(self.frequency, process_value, [get_value()])
        if thistime - self.prevtime < self.frequency:
            set_value([b for b in self.prevvalue] + [b for b in value])
            timeout.cancel()
        else: 
            set_value(value)
            timeout.start()
            self.prevvalue = value
        self.prevtime = thistime

    def characteristic_write_value_succeeded(self, characteristic):
        if init_commands:
            init_command = init_commands.pop()
            characteristic.write_value(bytearray.fromhex(init_command))
            time.sleep(1)
        else:
            characteristic.write_value(bytearray.fromhex(query_command))
            self.get_frequency()
            time.sleep(self.frequency)

    def get_frequency(self):
        self.frequency = int(os.environ.get('MPPT_BLE_FREQ', self.frequency))

    def set_frequency(self, freq):
        self.frequency = freq

    def characteristic_write_value_failed(self, characteristic, error):
        sys.exit(f"Characteristic write value failed: {characteristic}, {error}")

    def characteristic_enable_notifications_succeeded(self, characteristic):
        init_command = init_commands.pop()
        characteristic.write_value(bytearray.fromhex(init_command))

    def characteristic_enable_notifications_failed(self, characteristic, error):
        sys.exit(f"Characteristic notification enable failed: {characteristic}, {error}")


if __name__ == '__main__':
    start_http_server(8000)
    try:
        device = AnyDevice(mac_address='98:7b:f3:5d:ca:02', manager=manager)
        device.connect()
        manager.run()
    except KeyboardInterrupt:
        pass
    finally:
        manager.stop()
        device.disconnect()
