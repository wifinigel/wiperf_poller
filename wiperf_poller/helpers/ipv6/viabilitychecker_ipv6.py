"""
Check viability of test to be run
"""
import re
from wiperf_poller.helpers.ipv6.route_ipv6 import resolve_name_ipv6, is_ipv4, is_ipv6

class TestViabilityCheckerIpv6(object):

    def __init__(self, config_vars, file_logger):

        self.file_logger = file_logger
        self.config_vars = config_vars

    def check_test_host_viable(self, host):

        ipv6_tests_possible = self.config_vars['ipv6_tests_possible']
        ipv6_tests_enabled = self.config_vars['ipv6_enabled']

        if not ipv6_tests_enabled == 'yes':
            self.file_logger.error('  Test not viable as IPv6 tests not enabled')
            return False
        
        if re.match(r'\d+\:+', host):
            # check if host is IPv6 address
            if ipv6_tests_possible: 
                return True
            else:
                self.file_logger.error('  Supplied target address is IPv6 ({}), but IPv6 testing not available (check interface for IPv6 address)'.format(host))
                return False

        else: 
            # must be a hostname at this point, so attempt ipv4 name lookup
            ip_address =  resolve_name_ipv6(host, self.file_logger)

            if is_ipv6(ip_address):
                if ipv6_tests_possible:
                    return True
                else:
                    self.file_logger.error('  Supplied hostname ({}) resolves as IPv6 address {}, but IPv6 testing not available (check interface for IPv6 address)'.format(host, ip_address))
                    return False
                   
        # everything we tried failed, not viable (but not sure what went wrong to get here...shouldn't be possible)
        self.file_logger.error("  Unknown viability error (ipv6): {}".format(host))
        return False
