import sys
import time
from socket import gethostbyname

from wiperf_poller.helpers.wirelessadapter import WirelessAdapter
from wiperf_poller.helpers.networkadapter import NetworkAdapter
from wiperf_poller.testers.mgtconnectiontester import MgtConnectionTester
from wiperf_poller.helpers.route import (check_correct_mode_interface_ipv4,
    check_correct_mode_interface_ipv6,
    check_correct_mgt_interface,
    inject_default_route_ipv4,
    inject_default_route_ipv6,
    inject_mgt_static_route_ipv4,
    inject_mgt_static_route_ipv6,
    is_ipv4,
    is_ipv6,
    resolve_name)
from wiperf_poller.testers.pingtester import PingTester
from wiperf_poller.helpers.timefunc import time_synced
from wiperf_poller.helpers.timefunc import get_timestamp

class NetworkConnectionTester(object):
    """
    Class to implement network connection tests for wiperf
    """

    def __init__(self, file_logger, testing_interface, probe_mode):

        self.file_logger = file_logger
        self.probe_mode = probe_mode
        self.testing_interface = testing_interface

        if probe_mode == 'wireless':
            self.adapter_obj = WirelessAdapter(testing_interface, self.file_logger)
        elif probe_mode == 'ethernet':
            self.adapter_obj = NetworkAdapter(testing_interface, self.file_logger)
        else:
            raise ValueError("Unknown adapter type: {}".format(self.probe_mode))
    
    def _check_wireless_conn_up(self, watchdog_obj, lockf_obj):

        self.file_logger.info("  Checking wireless connection available.")
        if self.adapter_obj.get_wireless_info() == False:

            self.file_logger.error("  Unable to get wireless info due to failure with ifconfig command")
            watchdog_obj.inc_watchdog_count()
            self.adapter_obj.bounce_error_exit(lockf_obj)  # exit here

        self.file_logger.info("Checking we're connected to the wireless network")
        if self.adapter_obj.get_bssid() == 'NA':
            self.file_logger.error("  Problem with wireless connection: not associated to network")
            watchdog_obj.inc_watchdog_count()
            self.adapter_obj.bounce_error_exit(lockf_obj)  # exit here
        
        return True
    
    def _check_interface_conn_up(self, watchdog_obj, lockf_obj):

        self.file_logger.info("Checking interface connection available.")
        if self.adapter_obj.get_adapter_info() == False:

            self.file_logger.error("Unable to get interface info due to failure with ifconfig command")
            watchdog_obj.inc_watchdog_count()
            self.adapter_obj.bounce_error_exit(lockf_obj)  # exit here
        
        # check the interface is up, otherwise fail, as we can't do anything
        self.file_logger.info("Checking interface link is up.")
        if self.adapter_obj.interface_up() == False:

            self.file_logger.error("Interface appears to be down, unable to proceed.")
            watchdog_obj.inc_watchdog_count()
            self.adapter_obj.bounce_error_exit(lockf_obj)  # exit here

        return True

    def run_tests(self, watchdog_obj, lockf_obj, config_vars, exporter_obj):

        #~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*
        #         
        # IPV4 Checks
        #
        #~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*

        #################################################
        # Check testing physical interface up & connected
        #################################################
        # wireless: if we have no network connection (i.e. no bssid), no point in proceeding...exit
        if self.probe_mode == 'wireless':

            self._check_wireless_conn_up(watchdog_obj, lockf_obj)

        # ethernet: if we have no network connection (i.e. link down or no IP), no point in proceeding...exit
        else:
            self._check_interface_conn_up(watchdog_obj, lockf_obj)

        self.file_logger.info("  Checking we have an IP address.")

        ##########################################################
        # Check testing interface has ipv4 address (if ipv4 used)
        ##########################################################
        if self.adapter_obj.get_adapter_ipv4_ip():

            ############################
            # Check DNS is working
            ############################
            # final ipv4 connectivity check: see if we can resolve an address
            # (network connection and DNS must be up)
            self.file_logger.info("  Checking we can do a DNS (ipv4)lookup to {}".format(config_vars['connectivity_lookup']))

            # Run a ping to seed arp cache - not interested in result
            ping_obj = PingTester(self.file_logger)
            ping_obj.ping_host(config_vars['connectivity_lookup'], 1)

            ######################################################################
            # Try a DNS lookup (IPv4) against configured name for Internet checks 
            ######################################################################
            ip_address = resolve_name(config_vars['connectivity_lookup'], self.file_logger, ip_family="ipv4")
            
            if not ip_address:
                # hmmm....things went bad, lookup failed...bounce interface & exit
                self.file_logger.error("  DNS seems to be failing, bouncing interface {}.".format(self.testing_interface))
                watchdog_obj.inc_watchdog_count()
                self.adapter_obj.bounce_error_exit(lockf_obj)  # exit here

            # check we are going to the Internet over the correct interface for ipv4 tests
            if check_correct_mode_interface_ipv4(ip_address, config_vars, self.file_logger):

                self.file_logger.info("  Correct interface ({}) being used for ipv4 tests.".format(self.testing_interface))
            
            else:
                ######################################################################
                # We seem to be using wrong interface for testing, fix default route 
                ######################################################################
                self.file_logger.warning("  We are not using the interface required to perform our tests due to a routing issue in this unit - attempt route addition to fix issue")
                
                if inject_default_route_ipv4(config_vars['connectivity_lookup'], config_vars, self.file_logger):
                
                    self.adapter_obj.bounce_interface()
                    self.file_logger.info("  Checking if ipv4 route injection worked...")

                    if check_correct_mode_interface_ipv4(ip_address, config_vars, self.file_logger):
                        self.file_logger.info("  Routing issue (ipv4) corrected OK.")
                    else:
                        self.file_logger.warning("  We still have an ipv4 routing issue. Will have to exit as testing over correct interface not possible")
                        self.file_logger.warning("  Suggest making static routing additions or adding an additional metric to the interface causing the issue.")
                        lockf_obj.delete_lock_file()
                        sys.exit()
        
        else:
            # if we have no IPv4 address address, issue warning
            self.file_logger.warning("  No IPv4 address found on {} adapter. Unless this is an IPv6 environment, you will have issues.".format(self.probe_mode))
        
        #~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*
        #
        # IPV6 Checks
        #
        #~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*
        if self.adapter_obj.get_adapter_ipv6_ip():

            #############################
            # Check DNS is working (ipv6)
            #############################
            # final ipv6 connectivity check: see if we can resolve an address
            # (network connection and DNS must be up)
            self.file_logger.info("  Checking we can do an ipv6 DNS lookup to {}".format(config_vars['connectivity_lookup_ipv6']))

            # Run a ping to seed arp cache - not interetsed in result
            ping_obj = PingTester(self.file_logger)
            ping_obj.ping_host(config_vars['connectivity_lookup_ipv6'], 1)

            ######################################################################
            # Try a DNS lookup (IPv6) against configured name for Internet checks 
            ######################################################################
            ip_address = resolve_name(config_vars['connectivity_lookup_ipv6'], self.file_logger, ip_family="ipv6")
            
            if not ip_address:
                # hmmm....things went bad, lookup failed...bounce interface & exit
                self.file_logger.error("  DNS (ipv6) seems to be failing, bouncing interface.")
                watchdog_obj.inc_watchdog_count()
                self.adapter_obj.bounce_error_exit(lockf_obj)  # exit here

            # check we are going to the Internet over the correct interface for ipv4 tests
            if check_correct_mode_interface_ipv6(ip_address, config_vars, self.file_logger):

                self.file_logger.info("  Correct interface being used for ipv6 tests.")
            
            else:
                ##########################################################################
                # We seem to be using wrong interface for testing, fix ipv6 default route 
                ##########################################################################
                self.file_logger.warning("  We are not using the interface required to perform our ipv6 tests due to a routing issue in this unit - attempt route addition to fix issue")
                
                if inject_default_route_ipv6(config_vars['connectivity_lookup_ipv6'], config_vars, self.file_logger):
                
                    self.adapter_obj.bounce_interface()
                    self.file_logger.info("  Checking if ipv6 route injection worked...")

                    if check_correct_mode_interface_ipv6(ip_address, config_vars, self.file_logger):
                        self.file_logger.info("  Routing issue (ipv6) corrected OK.")
                    else:
                        self.file_logger.warning("  We still have an ipv6 routing issue. Will have to exit as testing over correct interface not possible")
                        self.file_logger.warning("  Suggest making static routing additions or adding an additional metric to the interface causing the issue.")
                        lockf_obj.delete_lock_file()
                        sys.exit()

        else:
            if not self.adapter_obj.get_adapter_ipv4_ip():

                self.file_logger.error("  No ipv4 or ipv6 address, bouncing interface.")
                watchdog_obj.inc_watchdog_count()
                self.adapter_obj.bounce_error_exit(lockf_obj)  # exit here
            
            else:
                # no ipv4 but have an ipv6 address
                self.file_logger.warning("  Testing interface only has IPv4 address, IPv6 tests will fail if performed.")      

        # report adapter info if this is a wireless connection
        if self.probe_mode == 'wireless':
            # hold all results in one place
            results_dict = {}

            results_dict['time'] = get_timestamp(config_vars)
            results_dict['ssid'] = self.adapter_obj.get_ssid()
            results_dict['bssid'] = self.adapter_obj.get_bssid()
            results_dict['freq_ghz'] = self.adapter_obj.get_freq()
            results_dict['center_freq_ghz'] = self.adapter_obj.get_center_freq()
            results_dict['channel'] = self.adapter_obj.get_channel()
            results_dict['channel_width'] = self.adapter_obj.get_channel_width()
            results_dict['tx_rate_mbps'] = self.adapter_obj.get_tx_bit_rate()
            results_dict['rx_rate_mbps'] = self.adapter_obj.get_rx_bit_rate()
            results_dict['tx_mcs'] = self.adapter_obj.get_tx_mcs()
            results_dict['rx_mcs'] = self.adapter_obj.get_rx_mcs()
            results_dict['signal_level_dbm'] = self.adapter_obj.get_signal_level()
            results_dict['tx_retries'] = self.adapter_obj.get_tx_retries()
            results_dict['ip_address_ipv4'] = self.adapter_obj.get_ipaddr_ipv4()
            results_dict['ip_address_ipv6'] = self.adapter_obj.get_ipaddr_ipv6()
            results_dict['location'] = config_vars['location']

            # define column headers
            column_headers = list(results_dict.keys())

            # dump out adapter info to log file
            self.file_logger.info("########## Wireless Connection ##########")
            self.file_logger.info("Wireless connection data: SSID:{}, BSSID:{}, Freq:{}, Center Freq:{}, Channel: {}, Channel Width: {}, Tx Phy rate:{}, \
                Rx Phy rate:{}, Tx MCS: {}, Rx MCS: {}, RSSI:{}, Tx retries:{}, IP address:{}".format(
                results_dict['ssid'], results_dict['bssid'], results_dict['freq_ghz'], results_dict['center_freq_ghz'], results_dict['channel'], 
                results_dict['channel_width'],  results_dict['tx_rate_mbps'], results_dict['rx_rate_mbps'], results_dict['tx_mcs'],
                results_dict['rx_mcs'], results_dict['signal_level_dbm'], results_dict['tx_retries'], results_dict['ip_address']))
            # dump the results
            data_file = config_vars['network_data_file']
            test_name = "Network Tests"
            if exporter_obj.send_results(config_vars, results_dict, column_headers, data_file, test_name, self.file_logger):
                self.file_logger.info("Connection results sent OK.")
                return True
            else:
                self.file_logger.error("Issue sending connection results. Exiting")
                lockf_obj.delete_lock_file()
                sys.exit()