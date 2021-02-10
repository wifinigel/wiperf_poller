from wiperf_poller.testers.dnstester import DnsTesterIpv4
from wiperf_poller.helpers.ipv6.route_ipv6 import resolve_name_ipv6 as resolve_name


class DnsTesterIpv6(DnsTesterIpv4):
    '''
    A class to perform a number of DNS lookups and return the lookup times

    Extends class: wiperf_poller.testers.dnstester
    '''

    def __init__(self, file_logger, config_vars):

        self.file_logger = file_logger

        self.target = []
        self.dns_result = 0
        
        self.test_name = "DNS (IPv6)"
        self.test_name_prefix = "dns_target"
        self.num_dns_targets = int(config_vars['dns_targets_count']) + 1
        self.data_file = config_vars['dns_data_file']
        self.resolve_name = resolve_name

