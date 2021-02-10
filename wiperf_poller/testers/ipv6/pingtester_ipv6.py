'''
A simple class to perform an network ICMP Ping and return a number of
result characteristics
'''

from wiperf_poller.testers.pingtester import PingTesterIpv4
from wiperf_poller.helpers.ipv6.route_ipv6 import resolve_name_ipv6 as resolve_name
from wiperf_poller.helpers.ipv6.viabilitychecker_ipv6 import TestViabilityCheckerIpv6 as TestViabilityChecker

class PingTesterIpv6(PingTesterIpv4):
    '''
    A class to ping a host - a basic wrapper around a CLI ping command
    '''

    def __init__(self, file_logger):

        self.file_logger = file_logger
        self.host = ''
        self.pkts_tx = ''
        self.pkts_rx = ''
        self.pkt_loss = ''
        self.test_time = ''
        self.rtt_min = ''
        self.rtt_avg = ''
        self.rtt_max = ''
        self.rtt_mdev = ''
        self.resolve_name = resolve_name
        self.TestViabilityChecker = TestViabilityChecker

        self.test_name = "Ping (IPv6)"
