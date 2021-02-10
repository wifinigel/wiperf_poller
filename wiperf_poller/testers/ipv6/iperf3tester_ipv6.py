'''
Functions to perform iperf3 tcp & udp tests and return a number of result characteristics

Note this originally used the iperf3 python module, but there were many issues with the
jitter stats in the udp test, so I decided to use my own wrapper around the iperf 
program itself, which returns results in json format with no issues.
'''
from wiperf_poller.testers.iperf3tester import IperfTesterIpv4
from wiperf_poller.testers.ipv6.pingtester_ipv6 import PingTesterIpv6 as PingTester
from wiperf_poller.helpers.ipv6.viabilitychecker_ipv6 import TestViabilityCheckerIpv6 as TestViabilityChecker
from wiperf_poller.helpers.ipv6.route_ipv6 import inject_test_traffic_static_route_ipv6 as inject_test_traffic_static_route

class IperfTesterIpv6(IperfTesterIpv4):
    """
    A class to perform a tcp & udp iperf3 tests
    """

    def __init__(self, file_logger):

        self.file_logger = file_logger

        self.tcp_test_name = "iperf3_tcp (IPv6)"
        self.udp_test_name = "iperf3_udp (IPv6)"

        self.TestViabilityChecker = TestViabilityChecker
        self.PingTester = PingTester
        self.inject_test_traffic_static_route = inject_test_traffic_static_route

