from wiperf_poller.testers.speedtester import SpeedtesterIpv4

class SpeedtesterIpv6(SpeedtesterIpv4):
    """
    Class to implement speedtest server tests for wiperf
    """

    def __init__(self, file_logger, config_vars, resolve_name):

        self.file_logger = file_logger
        self.config_vars = config_vars
        self.test_name = "Speedtest (IPv6)"
        self.wan_target = 'ipv6.google.com'
        self.resolve_name = resolve_name
