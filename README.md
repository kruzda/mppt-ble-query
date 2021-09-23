# mppt-ble-query
Query data from a PV Logic MPPT Pro solar charge controller over BLE and provide Prometheus scrapeable output on port 8000

## Instructions:

1. Install dependencies:
* [gatt-python](https://github.com/getsenic/gatt-python)
* [prometheus-client](https://github.com/prometheus/client_python)

2. Set the MAC address of the Bluetooth network interface of the PV Logic device within mppt-ble.py
3. Either set the password to 000000 on the device or snoop the correct init_commands that your app uses
