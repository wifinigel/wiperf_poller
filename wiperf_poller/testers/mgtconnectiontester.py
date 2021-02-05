import sys
import time
import subprocess
from socket import gethostbyname
import requests

from wiperf_poller.helpers.networkadapter import NetworkAdapter
from wiperf_poller.helpers.route import (
    check_correct_mgt_interface, 
    inject_mgt_static_route_ipv4, 
    inject_mgt_static_route_ipv6, 
    is_ipv6, 
    is_ipv4,
    resolve_name)
from wiperf_poller.helpers.os_cmds import NC_CMD

class MgtConnectionTester(object):
    """
    Class to implement network mgt connection tests for wiperf
    """

    def __init__(self, config_vars, file_logger):

        self.config_vars = config_vars
        self.file_logger = file_logger
        self.data_host = config_vars['data_host']
        self.data_port = config_vars['data_port']
        self.exporter_type = config_vars['exporter_type']
        self.mgt_interface = config_vars['mgt_if']

    def check_mgt_connection(self, lockf_obj, watchdog_obj):

        mgt_interface_obj = NetworkAdapter(self.mgt_interface, self.file_logger)
        mgt_interface_obj.get_if_status()

        # To avoid any issues later, convert host name to IP
        # (IP address returned if already IP)
        self.data_host = resolve_name(self.data_host, self.file_logger)

        #~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*
        #         
        # IPV4 Checks
        #
        #~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*

        #################################################
        # Check mgt physical interface up & connected
        #################################################
        # get 
        if is_ipv6(self.data_host):
            self.file_logger.info("  Reporting server is IPv6, will check connectivity later")
        
        else:
            # Check if mgt_if up        
            if not mgt_interface_obj.interface_up():
                self.file_logger.error("Interface for mgt traffic ({}) appears to be down, unable to proceed.".format(self.mgt_interface))
                watchdog_obj.inc_watchdog_count()
                mgt_interface_obj.bounce_error_exit(lockf_obj)  # exit here
            
            #####################################################
            # check if route to IPv4 address of server is via 
            # mgt_if...fix with route injection if not
            ####################################################
            if not check_correct_mgt_interface(self.data_host, self.mgt_interface, self.file_logger):

                self.file_logger.warning("  We are not using the interface required for IPv4 mgt traffic due to a routing issue in this unit - attempt route addition to fix issue")

                if inject_mgt_static_route_ipv4(self.data_host, self.config_vars, self.file_logger):

                    self.file_logger.info("  Checking if IPv4 route injection worked...")

                    if check_correct_mgt_interface(self.data_host, self.mgt_interface, self.file_logger):
                        self.file_logger.info("  IPv4 Routing issue corrected OK.")
                    else:
                        self.file_logger.warning("  We still have an IPv4 routing issue. Will have to exit as mgt traffic over correct interface not possible")
                        self.file_logger.warning("  Suggest making static routing additions or adding an additional metric to the interface causing the issue.")
                        self.file_logger.warning("  (*** Note ***: check you have configured the correct mgt interface if this message persists)")
                        lockf_obj.delete_lock_file()
                        sys.exit()
        
        del mgt_interface_obj
        
        #~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*
        #
        # IPV6 Checks
        #
        #~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*
        #################################################
        # Check mgt physical interface up & connected
        #################################################
        if is_ipv4(self.data_host):
            self.file_logger.info("  Reporting server is IPv4, nothing more to check.")
        
        else:
            self.file_logger.info("  Checking IPv6 connectivity for mgt/reporting traffic")

            if not is_ipv6(self.data_host):
                raise ValueError("Management IP not in IPv6 format.")

            # Check if mgt_if up
            mgt_interface_obj = NetworkAdapter(self.mgt_interface, self.file_logger)
            mgt_interface_obj.get_if_status()

            if not mgt_interface_obj.interface_up():
                self.file_logger.error("Interface for mgt traffic ({}) appears to be down, unable to proceed.".format(self.mgt_interface))
                watchdog_obj.inc_watchdog_count()
                mgt_interface_obj.bounce_error_exit(lockf_obj)  # exit here
            
            #####################################################
            # check if route to IPv6 address of server is via 
            # mgt_if...fix with route injection if not
            ####################################################
            if not check_correct_mgt_interface(self.data_host, self.mgt_interface, self.file_logger):

                self.file_logger.warning("  We are not using the interface required for IPv6 mgt traffic due to a routing issue in this unit - attempt route addition to fix issue")

                if inject_mgt_static_route_ipv6(self.data_host, self.config_vars, self.file_logger):

                    self.file_logger.info("  Checking if  IPv6 route injection worked...")

                    if check_correct_mgt_interface(self.data_host, self.mgt_interface, self.file_logger):
                        self.file_logger.info("   IPv6 Routing issue corrected OK.")
                    else:
                        self.file_logger.warning("  We still have an  IPv6 routing issue. Will have to exit as mgt traffic over correct interface not possible")
                        self.file_logger.warning("  Suggest making static routing additions or adding an additional metric to the interface causing the issue.")
                        self.file_logger.warning("  (*** Note ***: check you have configured the correct mgt interface if this message persists)")
                        lockf_obj.delete_lock_file()
                        sys.exit()

        #####################################################
        # check if route to IPv6 address of server is via 
        # mgt_if...fix with route injection if not
        ####################################################
        # if we are using hec, make sure we can access the hec network port, otherwise we are wasting our time
        if self.exporter_type == 'splunk':
            self.file_logger.info("  Checking port connection to Splunk server {}, port: {}".format(self.data_host, self.data_port))

            try:
                subprocess.check_output('{} -zvw10 {} {}'.format(NC_CMD, self.data_host, self.data_port), stderr=subprocess.STDOUT, shell=True).decode()
                self.file_logger.info("  Port connection to server {}, port: {} checked OK.".format(self.data_host, self.data_port))
            except subprocess.CalledProcessError as exc:
                output = exc.output.decode()
                self.file_logger.error("Port check to server failed. Err msg: {}".format(str(output)))
                return False

            # check our token is valid
            payload = dict()
            response = dict()
            token = self.config_vars.get('splunk_token')    
            headers = {'Authorization':'Splunk '+ token}
            if is_ipv6(self.data_host): self.data_host = "[{}]".format(self.data_host)
            url = "https://{}:{}/services/collector/event".format(self.data_host, self.data_port)

            # send auth request
            response = requests.post(url, data=payload, headers=headers, verify=False)
            response_code = response.status_code

            failed_auth_codes = [401, 403]
            passed_auth = True
            
            if response_code == 400:
                self.file_logger.info("Splunk token check: ok.")
            elif response_code in failed_auth_codes:
                self.file_logger.error("Splunk token check: Token appears invalid or is not enabled, please check you are using correct Token and that it is enabled on Splunk server")
                passed_auth = False
            else:
                self.file_logger.error("Splunk token check: Bad response code from Splunk server...are its services definitely up? Check Splunk server.")
                passed_auth = False

            if not passed_auth:
                self.file_logger.error("Splunk token check: Auth check to server failed. (Exiting...)")
                return False
            
            return True
        
        elif self.exporter_type == 'influxdb':
            self.file_logger.info("  Checking port connection to InfluxDB server {}, port: {}".format(self.data_host, self.data_port))

            try:
                subprocess.check_output('{} -zvw10 {} {}'.format(NC_CMD, self.data_host, self.data_port), stderr=subprocess.STDOUT, shell=True).decode()
                self.file_logger.info("  Port connection to server {}, port: {} checked OK.".format(self.data_host, self.data_port))
            except subprocess.CalledProcessError as exc:
                output = exc.output.decode()
                self.file_logger.error(
                    "Port check to server failed. Err msg: {}".format(str(output)))
                return False

            return True

        elif self.exporter_type == 'influxdb2':
            self.file_logger.info("  Checking port connection to InfluxDB2 server {}, port: {}".format(self.data_host, self.data_port))

            try:
                subprocess.check_output('{} -zvw10 {} {}'.format(NC_CMD, self.data_host, self.data_port), stderr=subprocess.STDOUT, shell=True).decode()
                self.file_logger.info("  Port connection to server {}, port: {} checked OK.".format(self.data_host, self.data_port))
            except subprocess.CalledProcessError as exc:
                output = exc.output.decode()
                self.file_logger.error(
                    "Port check to server failed. Err msg: {}".format(str(output)))
                return False

            return True
        
        else:
            self.file_logger.info("  Unknown exporter type configured in config.ini: {} (exiting)".format(self.exporter_type))
            sys.exit()


