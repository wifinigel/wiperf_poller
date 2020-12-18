'''
A simple class to count the number of bluetooth and bluetoothle devices visible
This is can be used as a proxy for the number of people/devices in the area
Requires the following

apt install libbluetooth-dev libglib2.0-dev libglib2.0-dev
sudo pip3 install pybluez 
sudo pip3 install bluepy

'''
import time

from bluepy.btle import Scanner, DefaultDelegate
import bluetooth


class ScanDelegate(DefaultDelegate):

    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        pass


class BluetoothScannerTester(object):
    '''
    A class scan Bluetooth and bluetoothle devices
    '''

    def __init__(self, file_logger, platform="rpi"):

        self.platform = platform
        self.file_logger = file_logger

        self.target = []
        self.bluetooth_result = 0

    def run_tests(self, status_file_obj, config_vars, exporter_obj):

        self.file_logger.info("Starting Bluetooth scan tests...")
        status_file_obj.write_status_file("Bluetooth scan tests")

        delete_file = True
        tests_passed = True

        scanner = Scanner().withDelegate(ScanDelegate())

        self.file_logger.debug("Starting Bluetooth le scan ")
        btle_devices = scanner.scan(10.0)
        self.file_logger.debug("Finished Bluetooth le scan ")

        self.file_logger.debug("Starting Bluetooth scan ")
        bt_devices = bluetooth.discover_devices(
                     duration=8, lookup_names=True, flush_cache=True, lookup_class=False)
        self.file_logger.debug("Finished Bluetooth le scan ")

        column_headers = ['bluetooth_device_count', 'bluetoothle_device_count']

        self.file_logger.info("Bluetooth scan results: btle devices {} bluetooth devices {}".format(str(len(btle_devices)),
                                                                                             str(len(bt_devices))))

        results_dict = {
            'bluetooth_device_count': len(bt_devices),
            'bluetoothle_device_count': len(btle_devices)
        }
        test_name = "BLUETOOTHSCANNER"
        # dump the results
        data_file = config_vars['bluetoothscanner_data_file']
        test_name = "BluetoothScanner"
        if exporter_obj.send_results(config_vars, results_dict, column_headers,
                                     data_file, test_name, self.file_logger,
                                     delete_data_file=delete_file):
            self.file_logger.info("Bluetooth scanner test ended.")
        else:
            self.file_logger.error("Issue sending Bluetooth scanner results.")
            tests_passed = False

        return tests_passed
