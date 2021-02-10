'''
A simple class to perform an network Smb copy and return a number of
result characteristics
'''

from wiperf_poller.testers.smbtester import SmbTesterIpv4
from wiperf_poller.helpers.ipv6.route_ipv6 import inject_test_traffic_static_route_ipv6 as inject_test_traffic_static_route
from wiperf_poller.helpers.ipv6.viabilitychecker_ipv6 import TestViabilityCheckerIpv6 as TestViabilityChecker


class SmbTesterIpv6(SmbTesterIpv4):
    '''
    A class to perform an SMB copy from a host - a basic wrapper around a CLI copy and mount command
    '''

    def __init__(self):

        super().__init__()
        self.test_name = "SMB"
