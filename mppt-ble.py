#!/usr/bin/env python3
import gatt
import time
import logging
import os
from threading import Timer
import signal
import sys



logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

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

def print_value(v):
    print([str(i).zfill(3) for i in [int(b) for b in v]])

def handler(signum, frame):
    print("Ctrl+C pressed. Disconnecting")
    device.disconnect()
    sys.exit()

    
class AnyDevice(gatt.Device):

    def services_resolved(self):
        super().services_resolved()
        self.frequency = 0
        self.set_frequency(int(os.environ.get('MPPT_BLE_FREQ', 5)))
        self.prevtime = int(time.monotonic()) - (self.frequency * 2)
        self.prevvalue = []

        '''
        for service in self.services:
            print("[%s]\tService [%s]" % (self.mac_address, service.uuid))
            for characteristic in service.characteristics:
                print("[%s]\t\tCharacteristic [%s]" % (self.mac_address, characteristic.uuid))
                for descriptor in characteristic.descriptors:
                    print("[%s]\t\t\tDescriptor [%s] (%s)" % (self.mac_address, descriptor.uuid, descriptor.read_value()))
        '''

        service = next(
            s for s in self.services
            if s.uuid == '0000fff0-0000-1000-8000-00805f9b34fb')

        characteristic = next(
            c for c in service.characteristics
            if c.uuid == '0000fff1-0000-1000-8000-00805f9b34fb')

        characteristic.enable_notifications()

    def characteristic_value_updated(self, characteristic, value):
        #logging.info(str([b for b in value]))
        self.interpret(value)
        #print("Characteristic value changed:", characteristic, [b for b in value])

    def interpret(self, value):
        thistime = int(time.monotonic())
        timeout = Timer(self.frequency, print_value, [get_value()])
        if thistime - self.prevtime < self.frequency:
            set_value([b for b in self.prevvalue] + [b for b in value])
            #print([str(i).zfill(3) for i in [int(b) for b in value]])
            timeout.cancel()
        else: 
            set_value(value)
            timeout.start()
            self.prevvalue = value

        self.prevtime = thistime

    def characteristic_write_value_succeeded(self, characteristic):
        #print("Characteristic write value succeeded", characteristic)
        if init_commands:
            init_command = init_commands.pop()
            #print("Trying to write", init_command)
            characteristic.write_value(bytearray.fromhex(init_command))
            time.sleep(1)
        else:
            #print("Trying to write", query_command)
            characteristic.write_value(bytearray.fromhex(query_command))
            self.get_frequency()
            time.sleep(self.frequency)

    def get_frequency(self):
        self.frequency = int(os.environ.get('MPPT_BLE_FREQ', self.frequency))

    def set_frequency(self, freq):
        self.frequency = freq
        print(f"New frequency set to {freq} seconds")

    def characteristic_write_value_failed(self, characteristic, error):
        print("Characteristic write value failed: ", characteristic, error)

    def characteristic_enable_notifications_succeeded(self, characteristic):
        #print("Characteristic notification enable succeeded", characteristic)
        init_command = init_commands.pop()
        #print("Trying to write", init_command)
        characteristic.write_value(bytearray.fromhex(init_command))

    def characteristic_enable_notifications_failed(self, characteristic, error):
        print("Characteristic notification enable failed", characteristic, error)

device = AnyDevice(mac_address='98:7b:f3:5d:ca:02', manager=manager)
device.connect()

signal.signal(signal.SIGINT, handler)

manager.run()
