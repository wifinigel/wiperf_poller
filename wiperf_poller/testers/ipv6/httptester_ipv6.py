'''
A simple class to perform a http get and return the time taken
'''
from wiperf_poller.testers.httptester import HttpTesterIpv4
from wiperf_poller.helpers.ipv6.route_ipv6 import resolve_name_ipv6 as resolve_name
from wiperf_poller.helpers.ipv6.viabilitychecker_ipv6 import TestViabilityCheckerIpv6 as TestViabilityChecker

import socket
import requests
import urllib3
import requests.packages.urllib3.util.connection as urllib3_cn

class HttpTesterIpv6(HttpTesterIpv4):
    '''
    A simple class to perform a http get and return the time taken
    '''

    def __init__(self, file_logger):

        self.file_logger = file_logger

        self.http_target = ''
        self.http_get_duration = 0
        self.http_server_response_time = 0
        self.http_status_code = 0
        self.TestViabilityChecker = TestViabilityChecker
        self.urllib3_cn = urllib3_cn

        self.urllib3_cn.allowed_gai_family = socket.AF_INET6

        self.test_name = "DNS (IPv6)"


