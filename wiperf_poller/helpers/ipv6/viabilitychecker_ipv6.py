"""
Check viability of test to be run
"""
import re
from wiperf_poller.helpers.ipv6.route_ipv6 import (
    resolve_name_ipv6, 
    is_ipv4, 
    is_ipv6, 
    check_correct_mode_interface_ipv6
)

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
