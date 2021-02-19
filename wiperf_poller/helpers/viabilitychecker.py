"""
Check viability of test to be run
"""
import re
from wiperf_poller.helpers.route import (
    resolve_name_ipv4, 
    is_ipv4, 
    is_ipv6, 
    check_correct_mode_interface_ipv4
)
from wiperf_poller.helpers.ipv6.route_ipv6 import (
    resolve_name_ipv6, 
    check_correct_mode_interface_ipv6
)

class TestViabilityCheckerIpv4(object):
    """
    This class will check the viability of test that is going to be performed based 
    on the IPv4 environment

    It will take a host name/IP and determine if:

    1. The test interface has an IPv4 address
    2. IPv4 tests are enabled globally
    3. The host passed is an IPv4 host (lookup name if required)
    4. The test will use the correct test interface based on the IPv4 address of the host
    """

    def __init__(self, config_vars, file_logger):

        self.file_logger = file_logger
        self.config_vars = config_vars

    def check_test_host_viable(self, host, lookup=True):
        """
        Check if the host passed is viable as a test target based on IPv4 testing & routing

        Args:
            host (string): target host name or IPv4 address
            lookup (bool, optional): If set to False no name lookup will be performed and no routing check will be performed. Defaults to True.

        Returns:
            [bool]: True = checks passed, False = checked failed (reasons logged)
        """
        self.file_logger.info('  Performing IPv4 test target viability check')

        ipv4_tests_possible = self.config_vars['ipv4_tests_possible']
        ipv4_tests_enabled = self.config_vars['ipv4_enabled']

        ip_address = ''

        if not ipv4_tests_enabled == 'yes':
            self.file_logger.error('  Test not viable as IPv4 tests not enabled')
            return False

        if is_ipv6(host):
            raise ValueError("IPv6 address passed to IPv4 viability check)")

        if is_ipv4(host):
            # check if host is IPv4 address
            if ipv4_tests_possible: 
                ip_address = host
                pass
            else:
                self.file_logger.error('  Supplied target address is IPv4 ({}), but IPv4 testing not available (check interface for IPv4 address)'.format(host))
                return False
        else: 
            # must be a hostname at this point, so attempt ipv4 name lookup
            if not lookup:
                return True # bail with a blind confirmation if name lookup disabled
            
            ip_address =  resolve_name_ipv4(host, self.file_logger)

            if is_ipv4(ip_address):
                if ipv4_tests_possible:
                    pass
                else:
                    self.file_logger.error('  Supplied hostname ({}) resolves as IPv4 address {}, but IPv4 testing not available (check interface for IPv4 address)'.format(host, ip_address))
                    return False
            else:
                # everything we tried failed, not viable (but not sure what went wrong to get here...shouldn't be possible)
                self.file_logger.error("  Unknown viability error (ipv4): {}".format(host))
                return False
        
        # to get here, must be IPv4 address and IPv4 testing enabled - check that routing goes over correct interface
        if check_correct_mode_interface_ipv4(ip_address, self.config_vars, self.file_logger):
            return True
        else:
            self.file_logger.warning("  Unable to run test to {} as route to destination not over correct interface".format(ip_address))
            return False

class TestViabilityCheckerIpv6(object):
    """
    This class will check the viability of test that is going to be performed based 
    on the IPv6 environment

    It will take a host name/IP and determine if:

    1. The test interface has an IPv6 address
    2. IPv4 tests are enabled globally
    3. The host passed is an IPv6 host (lookup name if required)
    4. The test will use the correct test interface based on the IPv6 address of the host
    """

    def __init__(self, config_vars, file_logger):

        self.file_logger = file_logger
        self.config_vars = config_vars

    def check_test_host_viable(self, host, lookup=True):
        """
        Check if the host passed is viable as a test target based on IPv6 testing & routing

        Args:
            host (string): target host name or IPv6 address
            lookup (bool, optional): If set to False no name lookup will be performed and no routing check will be performed. Defaults to True.

        Returns:
            [bool]: True = checks passed, False = checked failed (reasons logged)
        """
        self.file_logger.info('  Performing IPv6 test target viability check')

        ipv6_tests_possible = self.config_vars['ipv6_tests_possible']
        ipv6_tests_enabled = self.config_vars['ipv6_enabled']

        ip_address = ''

        if not ipv6_tests_enabled == 'yes':
            self.file_logger.error('  Test not viable as IPv6 tests not enabled')
            return False
        
        if is_ipv4(host):
            raise ValueError("IPv6 address passed to IPv6 viability check)")
        
        if is_ipv6(host):
            # check if host is IPv6 address
            if ipv6_tests_possible: 
                ip_address = host
                pass
            else:
                self.file_logger.error('  Supplied target address is IPv6 ({}), but IPv6 testing not available (check interfaces have IPv6 address)'.format(host))
                return False
        else: 
            # must be a hostname at this point, so attempt ipv6 name lookup
            if not lookup:
                return True # bail with a blind confirmation if name lookup disabled
            
            ip_address =  resolve_name_ipv6(host, self.file_logger)

            if is_ipv6(ip_address):
                if ipv6_tests_possible:
                    pass
                else:
                    self.file_logger.error('  Supplied hostname ({}) resolves as IPv6 address {}, but IPv6 testing not available (check interfaces have IPv6 address)'.format(host, ip_address))
                    return False
            else:                   
                # everything we tried failed, not viable (but not sure what went wrong to get here...shouldn't be possible)
                self.file_logger.error("  Unknown viability error (ipv6): {}".format(host))
                return False
        
        # to get here, must be IPv6 address and IPv6 testing enabled - check that routing goes over correct interface
        if check_correct_mode_interface_ipv6(ip_address, self.config_vars, self.file_logger):
            return True
        else:
            self.file_logger.warning("  Unable to run test to {} as route to destination not over correct interface".format(ip_address))
            return False


class TestViabilityChecker(object):

    def __init__(self, config_vars, file_logger):

        self.file_logger = file_logger
        self.config_vars = config_vars
        self.checker_obj = None
    
    def check_test_host_viable(self, host, ip_ver_preference='', lookup=True):
        """
        Method to figure out which checker class is best to use, based on which IP version
        is most appropriate

        Args:
            host (string): Hostname, IPv4 address or IPv6 address
            ip_ver_preference (string): IP version preferred for check (useful when passing hostnames) 
            lookup (bool, optional): [description]. Defaults to True.
        """
        ip_ver_to_use = 'ipv4'

        # if 'host' is an IP address format, make selection based on address type
        if is_ipv4(host):
            pass
        elif is_ipv6(host):
            ip_ver_to_use = 'ipv6'
        else:
            # OK, we're a hostname to get this far - check the IP ver preference
            if ip_ver_preference=='ipv6':
                ip_ver_to_use = 'ipv6'
            else:
                pass # we must be ipv4 or unspecified
        
        if ip_ver_to_use == 'ipv6':
            self.checker_obj = TestViabilityCheckerIpv6(self.config_vars, self.file_logger)
        else:
            self.checker_obj = TestViabilityCheckerIpv4(self.config_vars, self.file_logger)
        
        # do viability check
        return self.checker_obj.check_test_host_viable(host, lookup)
