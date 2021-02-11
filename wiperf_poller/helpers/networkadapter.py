import re
import subprocess
import sys
import time
from wiperf_poller.helpers.os_cmds import IP_CMD, ROUTE_CMD, IF_DOWN_CMD, IF_UP_CMD


class NetworkAdapter(object):

    '''
    A class to monitor and manipulate a generic network adapter for wiperf
    '''

    def __init__(self, if_name, file_logger, platform="rpi"):

        self.if_name = if_name
        self.file_logger = file_logger
        self.platform = platform

        self.if_status = ''  # str
        self.ip_addr = ''  # str
        self.ip_addr_ipv6 = ''  # str
        self.def_gw = ''  # str

        self.file_logger.debug("#### Initialized NetworkAdapter instance... ####")

    def field_extractor(self, field_name, pattern, cmd_output_text):

        re_result = re.search(pattern, cmd_output_text)

        if not re_result is None:
            field_value = re_result.group(1)

            self.file_logger.debug("{} = {}".format(field_name, field_value))

            return field_value
        else:

            return None

    def get_if_status(self):

        ####################################################################
        # Get interface status using 'ip link show <if name>' command
        ####################################################################
        # TODO: replace with info from psutil
        try:
            cmd = "{} link show {}".format(IP_CMD, self.if_name)
            if_info = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True).decode()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error_descr = "Issue getting interface info using ip command: {}".format(output)

            self.file_logger.error("{}".format(error_descr))
            self.file_logger.error("Returning error...")
            return False

        self.file_logger.debug("Network interface config info: {}".format(if_info))

        # Extract interface up/down status (unless already set)
        if not self.if_status:
            pattern = r'state (.*?) mode'
            field_name = "if_status"
            extraction = self.field_extractor(field_name, pattern, if_info)
            if extraction:
                self.if_status = extraction
            else:
                self.if_status = "Unknown"

        return True

    
    def interface_up(self):

        """
        Checks if network interface is up (assumes self.get_if_status() has been run)

        Returns:
            True: interface up
            False: interface down
        """
        if self.if_status == "UP":
            return True
        elif self.if_status == "DOWN":
            return False
        # exception for loopback i/f as always up
        elif self.if_name == 'lo':
            return True
        else: 
            err_string = "Unknown status: {} (should be 'UP' or 'DOWN')".format(self.if_status)
            self.file_logger.error(err_string)

            raise ValueError(err_string)


    def get_adapter_ipv4_ip(self):
        '''
        This method parses the output of the 'ip -4 a show 'command to figure out 
        the IPv4 address of the networkadapter.

        As this is a wrapper around a CLI command, it is likely to break at
        some stage
        '''
        self.file_logger.info("Getting adapter IPv4 info: {}".format(self.if_name))

        #TODO: Use psutil for the interface info
        # Get interface info
        try:
            cmd = "{} -4 a show  {}".format(IP_CMD, self.if_name)
            self.ifconfig_info = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True).decode()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error_descr = "Issue getting interface info (ipv4) using ip command to get IP info: {}".format(output)
            self.file_logger.error("{}".format(error_descr))
            if re.match('.* (does not exist)', output):
                self.file_logger.error("Exiting.")
                sys.exit()

            return False

        self.file_logger.debug("Interface config info: {}".format(self.ifconfig_info))

        # Extract IP address info (e.g. inet 10.255.250.157)
        ip_re = re.search(r'inet .*?(\d+\.\d+\.\d+\.\d+)', self.ifconfig_info)
        if ip_re is None:
            self.file_logger.error("No IPv4 address found")
            return False
        else:
            self.ip_addr = ip_re.group(1)

        # Check to see if IP address is APIPA (169.254.x.x)
        apipa_re = re.search(r'169\.254', self.ip_addr)
        if not apipa_re is None:
            self.file_logger.error("IP address found appears to be APIPA")
            return False

        self.file_logger.debug("IP Address = " + self.ip_addr)

        return self.ip_addr
    
    def get_adapter_ipv6_ip(self):
        '''
        This method parses the output of the 'ip -6 a show 'command to figure out 
        the IPv4 address of the networkadapter.

        As this is a wrapper around a CLI command, it is likely to break at
        some stage
        '''
        #TODO: Use psutil for the interface info

        self.file_logger.info("Getting adapter IPv6 info: {}".format(self.if_name))

        # Get interface info
        try:
            cmd = "{} -6 a show  {}".format(IP_CMD, self.if_name)
            self.ifconfig_info = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True).decode()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error_descr = "Issue getting interface info (ipv6) using ip command to get IP info: {}".format(output)
            self.file_logger.error("{}".format(error_descr))
            if re.match('.* (does not exist)', output):
                self.file_logger.error("Exiting.")
                sys.exit()
            
            return False

        self.file_logger.debug("Interface config info: {}".format(self.ifconfig_info))

        # Extract IP address info (e.g. inet6 2001:1:1:1:1::6/64 scope global)
        ip_re = re.search(r'inet6 .*?(\d+\:+.*?\/\d+ +scope +global)', self.ifconfig_info)
        if ip_re is None:
            self.file_logger.info("  (Info only) No IPv6 global address found on {}".format(self.if_name))
            return False
        else:
            self.ip_addr_ipv6 = ip_re.group(1)
        
        self.file_logger.debug("IP Address = " + self.ip_addr_ipv6)

        return self.ip_addr_ipv6

    def get_route_info_ipv4(self):
        '''
        This method parses the output of the route command to figure out the
        IPv4 address of the network adapter default gateway.

        As this is a wrapper around a CLI command, it is likely to break at
        some stage
        '''

        # Get route info (used to figure out default gateway)
        try:
            cmd = "{} -n | grep ^0.0.0.0 | grep {}".format(ROUTE_CMD, self.if_name)
            self.route_info = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True).decode()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error_descr = "Issue getting default gateway info using route command (Prob due to multiple interfaces being up or wlan interface being wrong). Error: {}".format(
                str(output))

            self.file_logger.error(error_descr)
            self.file_logger.error("Returning error...")
            return False

        self.file_logger.debug("Route info: {}".format(self.route_info))

        # Extract def gw
        def_gw_re = re.search(
            r'0\.0\.0\.0\s+(\d+\.\d+\.\d+\.\d+)\s', self.route_info)
        if def_gw_re is None:
            self.def_gw = "NA"
        else:
            self.def_gw = def_gw_re.group(1)

        self.file_logger.debug("Default GW = " + self.def_gw)
    
    def get_route_info_ipv6(self):
        '''
        This method parses the output of the route command to figure out the
        IPv6 address of the network adapter default gateway.

        As this is a wrapper around a CLI command, it is likely to break at
        some stage
        '''

        # Get route info (used to figure out default gateway)
        try:
            cmd = "{} -6 -n | grep ^::/0 | grep {}".format(ROUTE_CMD, self.if_name)
            self.route_info = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True).decode()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error_descr = "Issue getting default gateway info using route command (Prob due to multiple interfaces being up or wlan interface being wrong). Error: {}".format(
                str(output))

            self.file_logger.error(error_descr)
            self.file_logger.error("Returning error...")
            return False

        self.file_logger.debug("Route info: {}".format(self.route_info))

        # Extract def gw
        def_gw_re = re.search(
            r'(\d+\:+.*?\d+)\s ', self.route_info)
        if def_gw_re is None:
            self.def_gw = "NA"
        else:
            self.def_gw = def_gw_re.group(1)

        self.file_logger.debug("Default GW = " + self.def_gw)

    def bounce_interface(self):
        '''
        If we run in to connectivity issues, we may like to try bouncing the
        network interface to see if we can recover the connection.

        Note: wlanpi must be added to sudoers group using visudo command on RPI
        '''

        self.file_logger.info("Bouncing interface {}".format(self.if_name))

        if_down_cmd = "{} {};".format(IF_DOWN_CMD, self.if_name)
        if_up_cmd = "{} {}".format(IF_UP_CMD, self.if_name)

        try:
            self.file_logger.warning("Taking interface down...")
            subprocess.check_output(if_down_cmd, stderr=subprocess.STDOUT, shell=True).decode()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error_descr = "i/f down command appears to have failed. Error: {} (signalling error)".format(str(output))
            self.file_logger.error(error_descr)
            return False
        
        # allow interface time to completely drop, release dhcp etc.
        time.sleep(10)

        try:
            self.file_logger.warning("Bringing interface up...")
            subprocess.check_output(if_up_cmd, stderr=subprocess.STDOUT, shell=True).decode()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error_descr = "i/f up command appears to have failed. Error: {} (signalling error)".format(str(output))
            self.file_logger.error(error_descr)
            return False

        self.file_logger.info("Interface bounce completed OK.")
        return True
    
    def bounce_error_exit(self, lockf_obj):
        '''
        Log an error before bouncing the interface and then exiting as we have an unrecoverable error with the network connection
        '''
        import sys

        self.file_logger.error("Attempting to recover by bouncing network interface...")
        self.bounce_interface()
        self.file_logger.error("Bounce completed. Exiting script.")

        # clean up lock file & exit
        lockf_obj.delete_lock_file()
        sys.exit()

    def get_ipaddr_ipv4(self):
        return self.ip_addr
    
    def get_ipaddr_ipv6(self):
        return self.ip_addr_ipv6

