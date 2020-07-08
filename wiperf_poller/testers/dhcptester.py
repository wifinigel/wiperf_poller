"""
A simple class to perform a DHCP release & renew and return the renewal time
"""
import time
import subprocess
from wiperf_poller.helpers.wirelessadapter import WirelessAdapter
from wiperf_poller.helpers.os_cmds import DHCLIENT_CMD


class DhcpTester(object):
    """
    A class to perform a DHCP release & renew and return the renewal time
    """

    def __init__(self, file_logger, platform="rpi"):

        self.platform = platform
        self.file_logger = file_logger

        self.interface = ''
        self.duration = ''
        self.platform = platform

    def bounce_interface(self, interface, file_logger):
        """
        Log an error before bouncing the wlan interface
        """
        import sys

        adapter = WirelessAdapter(interface, file_logger, self.platform)
        self.file_logger.error("Bouncing WLAN interface")
        adapter.bounce_wlan_interface()
        self.file_logger.error("Interface bounced: {}".format(interface))

        # TODO: this exit will leave lock file in place - need to remove it
        # exit as something bad must have happened...
        sys.exit()

    def dhcp_renewal(self, interface, mode='passive'):
        """
        This function will release the current DHCP address and request a renewal.
        The renewal duration is timed and the result (in mS) returned

        Usage:
            tester_obj = DhcpTester(logger, debug=False)
            tester_obj.dhcp_renewal("wlan0")

        If the renewal fails, the wlan interface will be bounced and the whole script will exit
        """

        self.interface = interface
            
        start = 0.0
        end = 0.0

        self.file_logger.info("Renewing dhcp address...(mode = {}, interface= {})".format(mode, self.interface))
        try:
            # renew address
            start = time.time()

            p = subprocess.Popen([DHCLIENT_CMD, '-v', self.interface, '-pf', '/tmp/dhclient.pid'], stderr=subprocess.PIPE)
            while True:
                line = p.stderr.readline()
                self.file_logger.debug("dhcp:", line.rstrip())
                if b'DHCPACK' in line:
                    break
                
                # If we get here, DHCP ACK not seen - issue warning
                if not line:
                    self.file_logger.warning("dhcp: DHCP ACK not detected in renewal output.")
                    break

            end = time.time()          
            self.file_logger.info("Address renewed.")

            try:
                subprocess.check_output("pkill -9 -f 'dhclient.pid'", shell=True)
            except subprocess.CalledProcessError as exc:
                self.file_logger.info("Output from zombie processes kill: {}".format(exc))
        
        except Exception as ex:
            self.file_logger.error("Issue renewing IP address: {}".format(ex))

            # If renewal fails, bounce interface to recover - script will exit
            self.bounce_interface(self.interface, self.file_logger)

        self.duration = int(round((end - start) * 1000))

        self.file_logger.info("Renewal time: {}mS".format(self.duration))

        return self.duration

    def run_tests(self, status_file_obj, config_vars, exporter_obj):

        self.file_logger.info("Starting DHCP renewal test...")
        status_file_obj.write_status_file("DHCP renew")

        # check mode to see which interface we need to use
        if config_vars['probe_mode'] == 'wireless':
            interface = config_vars['wlan_if']
        else:
            interface = config_vars['eth_if']

        tests_passed = True

        self.file_logger.info("Interface under test: {}".format(interface))
        renewal_result = self.dhcp_renewal(interface, mode=config_vars['dhcp_test_mode'])

        if renewal_result:

            column_headers = ['time', 'renewal_time_ms']

            results_dict = {
                'time': int(time.time()),
                'renewal_time_ms': renewal_result,
            }

            # dump the results
            data_file = config_vars['dhcp_data_file']
            test_name = "DHCP"

            if exporter_obj.send_results(config_vars, results_dict, column_headers, data_file, test_name, self.file_logger):
                self.file_logger.info("DHCP test ended.")
            else:
                self.file_logger.error("Error sending DHCP results")
                tests_passed = False
        else:
            self.file_logger.error("DHCP test error - no results (check logs)")
            tests_passed = False
    
        return tests_passed

    def get_duration(self):
        """
        Get DHCP renewal duration
        """
        return self.duration
