'''
Functions to perform iperf3 tcp & udp tests and return a number of result characteristics

Note this originally used the iperf3 python module, but there were many issuse with the
jitter stats in the udp test, so I decided to use my own wrapper around the iperf 
program itself, which returns results in json format with no issues.
'''
import os
import json
import subprocess
import time
import signal
from iperf3 import Client
import timeout_decorator

from wiperf_poller.testers.pingtester import PingTesterIpv4 as PingTester
from wiperf_poller.helpers.route import inject_test_traffic_static_route_ipv4 as inject_test_traffic_static_route
from wiperf_poller.helpers.timefunc import get_timestamp
from wiperf_poller.helpers.viabilitychecker import TestViabilityChecker

class IperfTesterIpv4(object):
    """
    A class to perform a tcp & udp iperf3 tests
    """

    def __init__(self, file_logger):

        self.file_logger = file_logger

        self.tcp_test_name = "iperf3_tcp"
        self.udp_test_name = "iperf3_udp"

        self.TestViabilityChecker = TestViabilityChecker
        self.PingTester = PingTester
        self.inject_test_traffic_static_route = inject_test_traffic_static_route


    @timeout_decorator.timeout(60, use_signals=False)
    def tcp_iperf_client_test(self, server_hostname, bind_address, duration=10, port=5201, debug=False):

        result= ''

        iperf_client = Client()

        iperf_client.server_hostname = server_hostname
        iperf_client.port = port
        iperf_client.protocol = 'tcp'
        iperf_client.duration = duration

        if debug:
            self.file_logger.debug("TCP iperf server test params: server: {}, port: {}, protocol: {}, duration: {}".format(server_hostname, port, "TCP", duration))

        self.file_logger.info("  Initiating tcp iperf3 test...")

        result = iperf_client.run()
        if result.error:
            self.file_logger.error("iperf TCP test error: {}".format(result.error))
            result = False

        del iperf_client
        return result


    def calculate_mos(self, rtt_avg_ms, jitter_ms, lost_percent):
        """
        Calculation of approximate MOS score 
        (This was kindly contributed by Mario Gingras, based on this 
        article: https://netbeez.net/blog/impact-of-packet-loss-jitter-and-latency-on-voip/)

        Returns:
            MOS value -- float (1.0 to 4.5)
        """
        #effective_latency=(rtt_avg_ms/2*jitter_ms)+40
        effective_latency=(rtt_avg_ms/2) + (2*jitter_ms) + 10.0

        if effective_latency < 160:
            R = 93.2 - (effective_latency/40)
        else:
            R = 93.2 - ((effective_latency-120)/10)

        R = R - 2.5 * lost_percent

        if R < 0 :
            mos_score=1.0
        elif R <100:
            mos_score = 1 + 0.035*R + 0.000007*R*(R-60)*(100-R)
        else:
            mos_score=4.5
        
        return mos_score

    @timeout_decorator.timeout(60, use_signals=False)
    def udp_iperf_client_test(self, server_hostname, bind_address, duration=10, port=5201, bandwidth=10000000, debug=False):

        iperf_client = Client()

        iperf_client.server_hostname = server_hostname
        iperf_client.port = port
        iperf_client.protocol = 'udp'
        iperf_client.duration = duration
        iperf_client.bandwidth = bandwidth
        iperf_client.blksize = 500
        iperf_client.num_streams = 1
        iperf_client.zerocopy = True

        if debug:
            self.file_logger.debug("UDP iperf server test params: server: {}, port: {}, protocol: {}, duration: {}, bandwidth: {}".format(server_hostname, port, 'udp', duration, bandwidth))

        self.file_logger.info("  Initiating udp iperf3 test...")

        result = iperf_client.run()
        if result.error:
            self.file_logger.error("  iperf UDP test error: {}".format(result.error))
            result = False

        del iperf_client
        return result

    def run_tcp_tests(self, config_vars, status_file_obj, adapter_obj, exporter_obj):

        data_file = config_vars['iperf3_tcp_data_file']
        status_file_obj.write_status_file("iperf3 tcp")

        tests_passed = True

        # get specifed number of targets (format: 'iperf3_tcp1_server')
        num_targets = int(config_vars['iperf3_tcp_targets_count']) + 1

        # read in all target data
        for target_num in range(1, num_targets):
            target_server = 'iperf3_tcp{}_server'.format(target_num)
            target_ip_ver = 'iperf3_tcp{}_ip_ver'.format(target_num)
            target_port = 'iperf3_tcp{}_port'.format(target_num)
            target_duration = 'iperf3_tcp{}_duration'.format(target_num)

            server_hostname = config_vars[target_server]
            ip_ver = config_vars[target_ip_ver]
            port = int(config_vars[target_port])
            duration = int(config_vars[target_duration])    

            bind_address = ''

            if ip_ver == 'ipv4':
                bind_address = adapter_obj.get_adapter_ipv4_ip()
            elif ip_ver == 'ipv6':
                bind_address = adapter_obj.get_adapter_ipv6_ip()
            else:
                raise ValueError("ip_var parameter invalid: {}".format(ip_ver))

            # create test viability checker
            # TODO: include ipv4/v6 preference?
            checker = TestViabilityChecker(config_vars, self.file_logger)
            if not checker.check_test_host_viable(server_hostname, ip_ver_preference=ip_ver):
                self.file_logger.error("  iperf3 tcp test not viable, will not be tested ({})".format(server_hostname))
                tests_passed = False
                continue

            self.file_logger.info("Starting iperf3 tcp test ({}:{})...".format(server_hostname, str(port)))
            
            # run iperf test
            result = False
            try:
                result = self.tcp_iperf_client_test(server_hostname, bind_address, duration=duration, port=port, debug=False)
            except:
                self.file_logger.error("  TCP iperf3 test process timed out.")

            if result:

                results_dict = {}

                results_dict['time'] = get_timestamp(config_vars)
                results_dict['target_server'] = server_hostname
                results_dict['target_index'] = target_num
                results_dict['sent_mbps'] =  float(round(result.sent_Mbps, 1))
                results_dict['received_mbps']   =  float(round(result.received_Mbps, 1))
                results_dict['sent_bytes'] =  int(result.sent_bytes)
                results_dict['received_bytes'] =  int(result.received_bytes)
                results_dict['retransmits'] =  int(result.retransmits)

                # define column headers for CSV
                column_headers = list(results_dict.keys())

                # drop abbreviated results in log file
                self.file_logger.info("  Iperf3 tcp results - server: {}, rx_mbps: {}, tx_mbps: {}, retransmits: {}, sent_bytes: {}, rec_bytes: {}".format(
                    server_hostname, results_dict['received_mbps'], results_dict['sent_mbps'], results_dict['retransmits'], 
                    results_dict['sent_bytes'], results_dict['received_bytes']))

                # dump the results
                if exporter_obj.send_results(config_vars, results_dict, column_headers, data_file, self.tcp_test_name, self.file_logger):
                    self.file_logger.info("  Iperf3 tcp test ended.\n")
                else:
                    self.file_logger.error("  Error sending iperf3 tcp test result.")
            
            else:
                self.file_logger.error("  iperf3 tcp test failed.\n")
                config_vars['test_issue'] += 1
                tests_passed = False

        return tests_passed      
                       
    def run_udp_tests(self, config_vars, status_file_obj, adapter_obj, exporter_obj):

        data_file = config_vars['iperf3_udp_data_file']
        status_file_obj.write_status_file("iperf3 udp")

        tests_passed = True

        # get specifed number of targets (format: 'iperf3_udp1_server')
        num_targets = int(config_vars['iperf3_udp_targets_count']) + 1

        # read in all target data
        for target_num in range(1, num_targets):

            target_server = 'iperf3_udp{}_server'.format(target_num)
            target_ip_ver = 'iperf3_udp{}_ip_ver'.format(target_num)
            target_port = 'iperf3_udp{}_port'.format(target_num)
            target_duration = 'iperf3_udp{}_duration'.format(target_num)
            target_bandwidth = 'iperf3_udp{}_bandwidth'.format(target_num)

            server_hostname = config_vars[target_server]
            ip_ver = config_vars[target_ip_ver]
            port = int(config_vars[target_port])
            duration = int(config_vars[target_duration])
            bandwidth = int(config_vars[target_bandwidth])

            bind_address = ''

            if ip_ver == 'ipv4':
                bind_address = adapter_obj.get_adapter_ipv4_ip()
            elif ip_ver == 'ipv6':
                bind_address = adapter_obj.get_adapter_ipv6_ip()
            else:
                raise ValueError("ip_var parameter invalid: {}".format(ip_ver))

            # create test viability checker
            # TODO: include ipv4/v6 preference?
            checker = TestViabilityChecker(config_vars, self.file_logger)
            if not checker.check_test_host_viable(server_hostname, ip_ver_preference=ip_ver):
                self.file_logger.error("  iperf3 udp test not viable, will not be tested ({})".format(server_hostname))
                tests_passed = False
                continue

            self.file_logger.info("Starting iperf3 udp test ({}:{})...".format(server_hostname, str(port)))

            # Run a ping to the iperf server to get an rtt to feed in to MOS score calc
            ping_obj = self.PingTester(self.file_logger)
            ping_obj.ping_host(server_hostname, 1) # one ping to seed arp cache
            
            ping_result = ping_obj.ping_host(server_hostname, 5)

            # ping results
            if ping_result:
                rtt_avg_ms = round(float(ping_result['rtt_avg']), 2)
            else:
                rtt_avg_ms=0

            # Run the iperf test
            result = False
            try:
                result = self.udp_iperf_client_test(server_hostname, bind_address, duration=duration, port=port, bandwidth=bandwidth, debug=False)
            except:
                self.file_logger.error("  UDP iperf3 test process timed out")

            if result:
                
                results_dict = {}

                results_dict['time'] = get_timestamp(config_vars)
                results_dict['target_server'] = server_hostname
                results_dict['target_index'] = target_num
                results_dict['bytes'] =  int(result.bytes)
                results_dict['mbps']   =  float(round(result.Mbps, 1))
                results_dict['jitter_ms'] =  float(round(result.jitter_ms, 1))
                results_dict['packets'] =  int(result.packets)
                results_dict['lost_packets'] =  int(result.lost_packets)
                results_dict['lost_percent'] =  float(round(result.lost_percent, 1))
                results_dict['mos_score'] = float(round(self.calculate_mos(rtt_avg_ms,results_dict['jitter_ms'], results_dict['lost_percent']), 2))

                # define column headers for CSV
                column_headers = list(results_dict.keys())

                # workaround for crazy jitter figures sometimes seen
                if results_dict['jitter_ms'] > 2000:
                    self.file_logger.error("  Received very high jitter value({}), set to none".format(results_dict['jitter_ms']))
                    results_dict['jitter_ms'] = 0.0

                # drop results in log file
                self.file_logger.info("  Iperf3 udp results - server: {}, mbps: {}, packets: {}, lost_packets: {}, lost_percent: {}, jitter: {}, bytes: {}, mos_score: {}".format(
                    server_hostname, results_dict['mbps'], results_dict['packets'], results_dict['lost_packets'], results_dict['lost_percent'],
                    results_dict['jitter_ms'], results_dict['bytes'], results_dict['mos_score']))

                # dump the results
                data_file = config_vars['iperf3_udp_data_file']

                if exporter_obj.send_results(config_vars, results_dict, column_headers, data_file, self.udp_test_name, self.file_logger):
                    self.file_logger.info("  Iperf3 udp test ended.\n")
                else:
                    self.file_logger.error("  Issue sending iperf3 UDP results.")

            else:
                self.file_logger.error("  iperf3 udp test failed.\n")
                config_vars['test_issue'] += 1
                tests_passed = True
        
        return tests_passed