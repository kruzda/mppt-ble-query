#!/usr/bin/env python3                                                 
import gatt                                                                
import time
                                                                            
manager = gatt.DeviceManager(adapter_name='hci0')                            
                                          
init_commands = [                             
    "c00108ddf67d71c94b4b324192c0",                                
    "c02502a02030d3c0",
    "c05206a03030303030305c91c0"                                                
]                                                                                

init_commands.reverse()                                             
                
query_command = "c02002a020fcd3c0"

class AnyDevice(gatt.Device):
    def services_resolved(self):
        super().services_resolved()

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
        print("Characteristic value changed:", characteristic, [b for b in value])

    def characteristic_write_value_succeeded(self, characteristic):
        print("Characteristic write value succeeded", characteristic)
        if init_commands:
            init_command = init_commands.pop()
            print("Trying to write", init_command)
            characteristic.write_value(bytearray.fromhex(init_command))
            time.sleep(1)
        else:
            print("Trying to write", query_command)
            characteristic.write_value(bytearray.fromhex(query_command))
            time.sleep(1)

    def characteristic_write_value_failed(self, characteristic, error):
        print("Characteristic write value failed: ", characteristic, error)

    def characteristic_enable_notifications_succeeded(self, characteristic):
        print("Characteristic notification enable succeeded", characteristic)
        init_command = init_commands.pop()
        print("Trying to write", init_command)
        characteristic.write_value(bytearray.fromhex(init_command))

    def characteristic_enable_notifications_failed(self, characteristic, error):
        print("Characteristic notification enable failed", characteristic, error)

device = AnyDevice(mac_address='98:7b:f3:5d:ca:02', manager=manager)
device.connect()

manager.run()
