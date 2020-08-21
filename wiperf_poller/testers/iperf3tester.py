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
from iperf3 import Client

from wiperf_poller.testers.pingtester import PingTester
from wiperf_poller.helpers.route import inject_test_traffic_static_route

class IperfTester(object):
    """
    A class to perform a tcp & udp iperf3 tests
    """

    def __init__(self, file_logger, platform):

        self.platform = platform
        self.file_logger = file_logger


    def tcp_iperf_client_test(self, server_hostname, duration=10, port=5201, debug=False):

        protocol = 'tcp'
        result= ''

        iperf_client = Client()

        iperf_client.server_hostname = server_hostname
        iperf_client.port = port
        iperf_client.protocol = protocol
        iperf_client.duration = duration

        if debug:
            self.file_logger.debug("TCP iperf server test params: server: {}, port: {}, protocol: {}, duration: {}".format(server_hostname, port, protocol, duration))

        try:
            result = iperf_client.run()
        except Exception as ex:
            self.file_logger.error("iperf TCP test error: {}".format(ex))
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

    def udp_iperf_client_test(self, server_hostname, duration=10, port=5201, bandwidth=10000000, debug=False):

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

        try:
            result = iperf_client.run()
        except Exception as ex:
            self.file_logger.error("iperf UDP test error: {}".format(ex))
            result = False

        del iperf_client

        return result

    def run_tcp_test(self, config_vars, status_file_obj, check_correct_mode_interface, exporter_obj):

            duration = int(config_vars['iperf3_tcp_duration'])
            port = int(config_vars['iperf3_tcp_port'])
            server_hostname = config_vars['iperf3_tcp_server_hostname']

            self.file_logger.info("Starting iperf3 tcp test ({}:{})...".format(server_hostname, str(port)))
            status_file_obj.write_status_file("iperf3 tcp")

            # check test to iperf3 server will go via wlan interface
            if check_correct_mode_interface(server_hostname, config_vars, self.file_logger):

                # run iperf test
                result = self.tcp_iperf_client_test(server_hostname, duration=duration, port=port, debug=False)

                if result.error:

                    self.file_logger.error("Error with iperf3 tcp test: {}".format(result.error))
                    return False

                else:
                    results_dict = {}

                    column_headers = ['time', 'sent_mbps', 'received_mbps', 'sent_bytes', 'received_bytes', 'retransmits']

                    results_dict['time'] = int(time.time())
                    results_dict['sent_mbps'] =  float(round(result.sent_Mbps, 1))
                    results_dict['received_mbps']   =  float(round(result.received_Mbps, 1))
                    results_dict['sent_bytes'] =  int(result.sent_bytes)
                    results_dict['received_bytes'] =  int(result.received_bytes)
                    results_dict['retransmits'] =  int(result.retransmits)

                    # drop abbreviated results in log file
                    self.file_logger.info("Iperf3 tcp results - rx_mbps: {}, tx_mbps: {}, retransmits: {}, sent_bytes: {}, rec_bytes: {}".format(
                        results_dict['received_mbps'], results_dict['sent_mbps'], results_dict['retransmits'], results_dict['sent_bytes'],
                        results_dict['received_bytes']))

                    # dump the results
                    data_file = config_vars['iperf3_tcp_data_file']
                    test_name = "iperf3_tcp"
                    if exporter_obj.send_results(config_vars, results_dict, column_headers, data_file, test_name, self.file_logger):
                        self.file_logger.info("Iperf3 tcp test ended.")
                        return True
                    else:
                        self.file_logger.error("Error sending iperf3 tcp test result.")
                        return False
                    
            else:
                self.file_logger.error("Unable to run iperf test to {} as route to destination not over correct interface...bypassing test".format(server_hostname))
                inject_test_traffic_static_route(server_hostname, config_vars, self.file_logger)
                config_vars['test_issue'] = True
                config_vars['test_issue_descr'] = "TCP iperf test failure"
                return False
    
    def run_udp_test(self, config_vars, status_file_obj, check_correct_mode_interface, exporter_obj):

        duration = int(config_vars['iperf3_udp_duration'])
        port = int(config_vars['iperf3_udp_port'])
        server_hostname = config_vars['iperf3_udp_server_hostname']
        bandwidth = int(config_vars['iperf3_udp_bandwidth'])

        self.file_logger.info("Starting iperf3 udp test ({}:{})...".format(server_hostname, str(port)))
        status_file_obj.write_status_file("iperf3 udp")

        if check_correct_mode_interface(server_hostname, config_vars, self.file_logger):

            # Run a ping to the iperf server to get an rtt to feed in to MOS score calc
            ping_obj = PingTester(self.file_logger, platform=self.platform)
            ping_obj.ping_host(server_hostname, 1) # one ping to seed arp cache
            
            ping_result = ping_obj.ping_host(server_hostname, 5)

            # ping results
            if ping_result:
                rtt_avg_ms = round(float(ping_result['rtt_avg']), 2)
            else:
                rtt_avg_ms=0

            # Run the iperf test
            result = self.udp_iperf_client_test(server_hostname, duration=duration, port=port, bandwidth=bandwidth, debug=False)

            if result.error:

                self.file_logger.error("Error with iperf3 udp test: {}".format(result.error))
                return False

            else:
                results_dict = {}

                column_headers = ['time', 'bytes', 'mbps', 'jitter_ms', 'packets', 'lost_packets', 'lost_percent']

                results_dict['time'] = int(time.time())
                results_dict['bytes'] =  int(result.bytes)
                results_dict['mbps']   =  float(round(result.Mbps, 1))
                results_dict['jitter_ms'] =  float(round(result.jitter_ms, 1))
                results_dict['packets'] =  int(result.packets)
                results_dict['lost_packets'] =  int(result.lost_packets)
                results_dict['lost_percent'] =  float(round(result.lost_percent, 1))
                results_dict['mos_score'] = float(self.calculate_mos(rtt_avg_ms,results_dict['jitter_ms'], results_dict['lost_percent']))

                # workaround for crazy jitter figures sometimes seen
                if results_dict['jitter_ms'] > 2000:
                    self.file_logger.error("Received very high jitter value({}), set to none".format(results_dict['jitter_ms']))
                    results_dict['jitter_ms'] = 0.0

                # drop results in log file
                self.file_logger.info("Iperf3 udp results - mbps: {}, packets: {}, lost_packets: {}, lost_percent: {}, jitter: {}, bytes: {}".format(
                    results_dict['mbps'], results_dict['packets'], results_dict['lost_packets'], results_dict['lost_percent'],
                    results_dict['jitter_ms'], results_dict['bytes']))

                # dump the results
                data_file = config_vars['iperf3_udp_data_file']
                test_name = "iperf_udp"
                if exporter_obj.send_results(config_vars, results_dict, column_headers, data_file, test_name, self.file_logger):
                    self.file_logger.info("Iperf3 udp test ended.")
                    return True
                else:
                    self.file_logger.error("Issue sending iperf3 UDP results.")
                    return False

        else:
            self.file_logger.error("Unable to run iperf test to {} as route to destination not over correct interface...bypassing test".format(server_hostname))
            inject_test_traffic_static_route(server_hostname, config_vars, self.file_logger)
            config_vars['test_issue'] = True
            config_vars['test_issue_descr'] = "UDP iperf test failure"
            return False