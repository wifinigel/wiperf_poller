from wiperf_poller.testers.speedtester import SpeedtesterIpv4

class SpeedtesterIpv6(SpeedtesterIpv4):
    """
    Class to implement speedtest server tests for wiperf
    """

    def __init__(self, file_logger, config_vars, resolve_name, adapter_obj):

        self.file_logger = file_logger
        self.config_vars = config_vars
        self.test_name = "Speedtest (IPv6)"
        config_vars['connectivity_lookup_ipv6']
        self.resolve_name = resolve_name
        self.adapter_obj = adapter_obj
        self.adapter_ip = self.adapter_obj.get_adapter_ipv6_ip()
        self.librespeed_ip_ver = '--ipv6'

        self.speedtest_enabled = config_vars['speedtest_enabled_ipv6']
        self.provider = config_vars['provider_ipv6']
        self.server_id = config_vars['server_id_ipv6']
        self.librespeed_args = config_vars['librespeed_args_ipv6']
        self.speedtest_data_file = config_vars['speedtest_data_file_ipv6']
        self.http_proxy = config_vars['http_proxy_ipv6']
        self.https_proxy = config_vars['https_proxy_ipv6']
        self.no_proxy = config_vars['no_proxy_ipv6']