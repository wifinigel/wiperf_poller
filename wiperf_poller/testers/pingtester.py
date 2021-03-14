'''
A simple class to perform an network ICMP Ping and return a number of
result characteristics
'''

import time
import re
import subprocess
from sys import stderr
from wiperf_poller.helpers.os_cmds import PING_CMD
from wiperf_poller.helpers.timefunc import get_timestamp

from wiperf_poller.helpers.route import (
    resolve_name,
    resolve_name_ipv4,
    resolve_name_ipv6 ,
    is_ipv4,
    is_ipv6
)
from wiperf_poller.helpers.viabilitychecker import TestViabilityChecker


class PingTesterIpv4(object):
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

        self.ip_ver = 'dual' # dual, ipv4, ipv6 
        self.resolve_name = resolve_name

        self.test_name = "Ping"

    def ping_host(self, host, count, ping_timeout=1, ping_interval=0.2, silent=False):
        '''
        This function will run a ping test and return an analysis of the results

        If the ping fails, a False condition is returned with no further
        information. If the ping succeeds, the following dictionary is returned:

        {   'host': self.host,
            'pkts_tx': self.pkts_tx,
            'pkts_rx': self.pkts_rx,
            'pkt_loss': self.pkt_loss,
            'test_time': self.test_time,
            'rtt_min': self.rtt_min,
            'rtt_avg': self.rtt_max,
            'rtt_max': self.rtt_max,
            'rtt_mdev': self.rtt_mdev}

        '''

        self.host = host

        self.file_logger.debug("Pinging host: " + str(host) + " (count=" + str(count) + ")")

        # Execute the ping
        try:
            cmd_string = "{} -q -c {} -W {} -i {} {}".format(PING_CMD, count, ping_timeout, ping_interval, host)
            ping_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            if silent == False:
                error = "Hit an error when pinging {} : {}".format(str(host), str(output))
                self.file_logger.error(error)

            #stderr.write(str(error))

            # Things have gone bad - we just return a false status
            return False

        self.file_logger.debug("Ping command output:")
        self.file_logger.debug(ping_output)

        packets_summary_str = ping_output[3]

        # Extract packets transmitted
        pkts_tx_re = re.search(
            r'(\d+) packets transmitted', packets_summary_str)
        if pkts_tx_re is None:
            self.pkts_tx = "NA"
        else:
            self.pkts_tx = pkts_tx_re.group(1)

        # Extract packets received
        pkts_rx_re = re.search(r'(\d+) received', packets_summary_str)
        if pkts_rx_re is None:
            self.pkts_rx = "NA"
        else:
            self.pkts_rx = pkts_rx_re.group(1)

        # Extract packet loss
        pkt_loss_re = re.search(r'(\d+)\% packet loss', packets_summary_str)
        if pkt_loss_re is None:
            self.pkt_loss = "NA"
        else:
            self.pkt_loss = pkt_loss_re.group(1)

        # Extract test time (duration)
        test_time_re = re.search(r'time (\d+)ms', packets_summary_str)
        if test_time_re is None:
            self.test_time = "NA"
        else:
            self.test_time = test_time_re.group(1)

        self.file_logger.debug("Packets transmitted: " + str(self.pkts_tx))
        self.file_logger.debug("Packets received: " + str(self.pkts_rx))
        self.file_logger.debug("Packet loss(%): " + str(self.pkt_loss))
        self.file_logger.debug("Test duration (mS): " + str(self.test_time))

        perf_summary_str = ping_output[4]
        perf_data_re = re.search(r'= ([\d\.]+?)\/([\d\.]+?)\/([\d\.]+?)\/([\d\.]+)',
                                 perf_summary_str)

        if test_time_re is None:
            self.rtt_min = "NA"
            self.rtt_avg = "NA"
            self.rtt_max = "NA"
            self.rtt_mdev = "NA"
        else:
            self.rtt_min = perf_data_re.group(1)
            self.rtt_avg = perf_data_re.group(2)
            self.rtt_max = perf_data_re.group(3)
            self.rtt_mdev = perf_data_re.group(4)

        self.file_logger.debug("rtt_min : " + str(self.rtt_min))
        self.file_logger.debug("rtt_avg : " + str(self.rtt_avg))
        self.file_logger.debug("rtt_max : " + str(self.rtt_max))
        self.file_logger.debug("rtt_mdev : " + str(self.rtt_mdev))

        self.file_logger.info('  ping_host: {}, pkts_tx: {}, pkts_rx: {}, pkt_loss: {}, rtt_avg: {}'.format(
            self.host, self.pkts_tx, self.pkts_rx, self.pkt_loss, self.rtt_avg))

        return {
            'host': self.host,
            'pkts_tx': self.pkts_tx,
            'pkts_rx': self.pkts_rx,
            'pkt_loss': self.pkt_loss,
            'test_time': self.test_time,
            'rtt_min': self.rtt_min,
            'rtt_max': self.rtt_max,
            'rtt_avg': self.rtt_avg,
            'rtt_mdev': self.rtt_mdev}

    def run_tests(self, status_file_obj, config_vars, adapter, exporter_obj):

        self.file_logger.info("Starting ping test...")
        status_file_obj.write_status_file("Ping tests")

        # read in ping hosts (format: 'ping_host1') & perform intial ping if test viable
        num_ping_targets = int(config_vars['ping_targets_count']) + 1

        ping_count = config_vars['ping_count']
        tests_passed = True
        ping_hosts = []

        for target_num in range(1, num_ping_targets):
            
            target_name = 'ping_host_{}'.format(target_num)
            target_name_ip_ver = 'ping_host_ip_ver_{}'.format(target_num)

            ping_host = config_vars[target_name]
            ping_host_ip_ver = config_vars[target_name_ip_ver]
            
            if ping_host == '':
                continue

            if ping_host_ip_ver  == "ipv4":
                self.resolve_name = resolve_name_ipv4
            elif ping_host_ip_ver  == "ipv6":
                self.resolve_name = resolve_name_ipv6
            else:
                # just use generic resolve name func that does both IPv4/v6
                self.resolve_name = resolve_name

            ping_host_ip = self.resolve_name(ping_host, self.file_logger, config_vars)

            if not ping_host_ip:
                self.file_logger.error("  Lookup error for: {} (bypassing...)".format(ping_host))
                continue
               
            # check if test to host is viable (based on probe ipv4/v6 support)
            checker = TestViabilityChecker(config_vars, self.file_logger)
            if not checker.check_test_host_viable(ping_host, ping_host_ip_ver):
                self.file_logger.error("  Ping target test not viable, will not be tested ({} / {})".format(ping_host, ping_host_ip))
                config_vars['test_issue'] += 1
                config_vars['test_issue_descr'] = "Ping"
                tests_passed = False
                continue
            
            # initial ping to populate arp cache and avoid arp timeput for first test ping
            self.file_logger.info("  Initial ping to host (prime arp cache): {} ({})".format(ping_host, ping_host_ip))

            # perform ping test
            self.ping_host(ping_host_ip, 1, silent=True)
            self.file_logger.info("  Initial ping test complete.\n")
                       
            # Entry looks good for testing, add to list of test targets
            ping_hosts.append( { 'hostname': ping_host, 'ip': ping_host_ip } )

        # run actual ping tests to ping test targets
        ping_index = 0

        for ping_host in ping_hosts:

            ping_index += 1

            self.file_logger.info("ping test to host: {} ({})".format(ping_host['hostname'], ping_host['ip']))

            ping_result = self.ping_host(ping_host['ip'], ping_count)

            if not ping_result:
                continue

            # put hostname back in (swap out IP)
            ping_result['host'] = ping_host['hostname']

            results_dict = {}

            # ping results
            if ping_result:
                results_dict['time'] = get_timestamp(config_vars)
                results_dict['ping_index'] = int(ping_index)
                results_dict['ping_host'] = str(ping_result['host'])
                results_dict['pkts_tx'] = int(ping_result['pkts_tx'])
                results_dict['pkts_rx'] = int(ping_result['pkts_rx'])
                results_dict['percent_loss'] = int(ping_result['pkt_loss'])
                results_dict['test_time_ms'] = int(ping_result['test_time'])
                results_dict['rtt_min_ms'] = round(float(ping_result['rtt_min']), 2)
                results_dict['rtt_avg_ms'] = round(float(ping_result['rtt_avg']), 2)
                results_dict['rtt_max_ms'] = round(float(ping_result['rtt_max']), 2)
                results_dict['rtt_mdev_ms'] = round(float(ping_result['rtt_mdev']), 2)

                # define column headers for CSV
                column_headers = list(results_dict.keys())

                # dump the results
                data_file = config_vars['ping_data_file']
                if exporter_obj.send_results(config_vars, results_dict, column_headers, data_file, self.test_name, self.file_logger):
                    self.file_logger.info("  Ping test ended.\n")
                else:
                    self.file_logger.error("  Issue sending ping results.")
                    tests_passed = False

                self.file_logger.debug("  Main: Ping test results:")
                self.file_logger.debug(ping_result)
                
            else:
                self.file_logger.error("  Ping test failed.")
                tests_passed = False
                
        return tests_passed

    def get_host(self):
        ''' Get host name/address '''
        return self.host

    def get_pkts_tx(self):
        ''' Get transmitted packet count'''
        return self.pkts_tx

    def get_pkts_rx(self):
        ''' Get received packet count '''
        return self.pkts_rx

    def get_pkt_loss(self):
        ''' Get percentage packet loss detected during test '''
        return self.pkt_loss

    def get_test_time(self):
        ''' Get the test duration in seconds '''
        return self.test_time

    def get_rtt_min(self):
        ''' Get the minimum round trip time observed during the test '''
        return self.rtt_min

    def get_rtt_max(self):
        ''' Get the maximum round trip time observed during the test '''
        return self.rtt_max

    def get_rtt_avg(self):
        ''' Get the average round trip time observed during the test '''
        return self.rtt_avg

    def get_rtt_mdev(self):
        ''' Get the median round trip time observed during the test '''
        return self.rtt_mdev

