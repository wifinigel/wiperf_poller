"""
Poll status class - reports status messages of current poll cycle to mgt platform
"""
import time
from wiperf_poller.helpers.timefunc import get_timestamp

class PollStatus():

    '''
    Poll status class - reports status messages of current poll cycle to mgt platform
    '''

    def __init__(self, config_vars, file_logger):

        self.file_logger = file_logger
        self.config_vars = config_vars
        self.status_dict = {
            'time': get_timestamp(config_vars),
            'ip': 'Unknown',
            'network': 'Fail',
            'speedtest': 'N/A',
            'ping': 'N/A',
            'dns': 'N/A',
            'http': 'N/A',
            'iperf_tcp': 'N/A',
            'iperf_udp': 'N/A',
            'dhcp': 'N/A',
            'smb': 'N/A',
            'auth': 'N/A',
            'probe_mode': 'N/A',
            'mgt_if': 'N/A'
        }

        self.start_time = time.time()

    def ip(self, value):
        self.status_dict['ip'] = str(value)
    
    def network(self, value):
        self.status_dict['network'] = str(value)

    def speedtest(self, value):
        self.status_dict['speedtest'] = str(value)
    
    def ping(self, value):
        self.status_dict['ping'] = str(value)

    def dns(self, value):
        self.status_dict['dns'] = str(value)
    
    def http(self, value):
        self.status_dict['http'] = str(value)
    
    def iperf_tcp(self, value):
        self.status_dict['iperf_tcp'] = str(value)
    
    def iperf_udp(self, value):
        self.status_dict['iperf_udp'] = str(value)
    
    def dhcp(self, value):
        self.status_dict['dhcp'] = str(value)
    
    def smb(self, value):
        self.status_dict['smb'] = str(value)
    
    def auth(self, value):
        self.status_dict['auth'] = str(value)
    
    def probe_mode(self, value):
        self.status_dict['probe_mode'] = str(value)
    
    def mgt_if(self, value):
        self.status_dict['mgt_if'] = str(value)
    
    def dump(self, exporter_obj):

        # calc run time
        self.status_dict['run_time'] = int(time.time() - self.start_time)

        self.file_logger.info("########## poll status ##########")

        self.file_logger.info("Sending poll status info to mgt platform")

        column_headers = list(self.status_dict.keys())
        results_dict =  self.status_dict

        # dump the results
        data_file = 'wiperf-poll-status'
        test_name = "wiperf-poll-status"

        if exporter_obj.send_results(self.config_vars, results_dict, column_headers, data_file, test_name, self.file_logger):
            self.file_logger.info("Poll status info sent.")
            return True
        else:
            self.file_logger.error("Issue sending poll status info.")
            return False


    