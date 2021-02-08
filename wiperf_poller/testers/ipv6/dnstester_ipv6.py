from wiperf_poller.testers.dnstester import DnsTesterIpv4
from wiperf_poller.helpers.ipv6.route_ipv6 import resolve_name_ipv6 as resolve_name


class DnsTesterIpv6(DnsTesterIpv4):
    '''
    A class to perform a number of DNS lookups and return the lookup times

    Extends class: wiperf_poller.testers.dnstester
    '''

    def __init__(self):

        super().__init__()

        self.test_name = "DNS (IPv6)"

