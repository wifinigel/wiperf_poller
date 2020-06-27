"""
Poll status class - reports status messages of current poll cycle to mgt platform
"""
from wiperf_poller.exporters.exportresults import ResultsExporter

class PollStatus():

    '''
    A class to implement a watchdog feature for the wiperf agent process
    '''

    def __init__(self, config_vars, file_logger):

        self.file_logger = file_logger
        self.config_vars = config_vars
        self.status_dict = {
            'ip': 'Unknown',
            'network': 'Fail',
            'speedtest': 'N/A',
            'ping': 'N/A',
            'dns': 'N/A',
            'http': 'N/A',
            'iperf_tcp': 'N/A',
            'iperf_udp': 'N/A',
            'dhcp': 'N/A'
        }

        # exporter object
        self. exporter_obj = ResultsExporter(file_logger, config_vars['platform'])

    def ip(self, value):
        self.status_dict['ip'] = value
    
    def network(self, value):
        self.status_dict['network'] = value

    def speedtest(self, value):
        self.status_dict['speedtest'] = value
    
    def ping(self, value):
        self.status_dict['ping'] = value

    def dns(self, value):
        self.status_dict['dns'] = value
    
    def http(self, value):
        self.status_dict['http'] = value
    
    def iperf_tcp(self, value):
        self.status_dict['iperf_tcp'] = value
    
    def iperf_udp(self, value):
        self.status_dict['iperf_udp'] = value
    
    def dhcp(self, value):
        self.status_dict['dhcp'] = value
    
    def dump(self):

        self.file_logger.info("Sending poll status info to mgt platform")

        column_headers = ['ip', 'network', 'speedtest', 'ping', 'dns', 'iperf_tcp', 'iperf_udp', 'dhcp']

        results_dict =  self.status_dict

        # dump the results
        data_file = 'wiperf-poll-status'
        test_name = "wiperf-poll-status"
        self.exporter_obj.send_results(self.config_vars, results_dict, column_headers, data_file, test_name, self.file_logger)

        self.file_logger.info("Poll status info sent.")


    