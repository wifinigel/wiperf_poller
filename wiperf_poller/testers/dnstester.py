import time
import socket
from wiperf_poller.helpers.timefunc import get_timestamp
from wiperf_poller.helpers.route import (
    resolve_name,
    resolve_name_ipv4,
    resolve_name_ipv6 ,
    check_correct_mode_interface_ipv4,
    is_ipv4,
    is_ipv6
)

class DnsTester(object):
    '''
    A class to perform a number of DNS lookups and return the lookup times
    '''

    def __init__(self, file_logger, config_vars):

        self.file_logger = file_logger

        self.target = []
        self.dns_result = 0
        
        self.config_vars = config_vars
        self.test_name = "DNS"
        self.num_dns_targets = int(config_vars['dns_targets_count']) + 1
        self.data_file = config_vars['dns_data_file']
        self.resolve_name = resolve_name


    def dns_single_lookup(self, target, ip_ver="dual"):
        '''
        This function will run a series of DNS lookups against the targets supplied
        and return the results in a dictionary.

        Usage:
            tester_obj.dns_lookup(bbc.co.uk')

        If the lookup fails, a False condition is returned with no further
        information. The lookup time is returned (results are in mS):

        '''
        self.target = target

        self.file_logger.debug("  DNS test target: {}".format(self.target))
        self.file_logger.debug("  Performing DNS lookup for: {}".format(target))

        if is_ipv4(target) or is_ipv6(target):
            self.file_logger.error("  DNS test error - IP address passed to name lookup test. Invalid value (names only)")
            return False

        if ip_ver  == "ipv4":
            self.file_logger.info("  IPv4 name lookup")
            self.resolve_name = resolve_name_ipv4
        elif ip_ver  == "ipv6":
            self.file_logger.info("  IPv6 name lookup")
            self.resolve_name = resolve_name_ipv6
        elif ip_ver  == "dual":
            # just use generic resolve name func that does both
            self.file_logger.info("  Dual stack name lookup")
            self.resolve_name = resolve_name
        else:
            raise ValueError("Unknown ip ver value: {}".format(ip_ver))

        start = time.time()
        ip_address = self.resolve_name(target, self.file_logger, self.config_vars)
        
        if not ip_address:
            return False

        end = time.time()
        time_taken = int(round((end - start) * 1000))
        self.dns_result = time_taken

        self.file_logger.debug("  DNS lookup for: {} succeeded. (Result: {}, Time: {})".format(target, ip_address, time_taken))

        return self.dns_result
    
    def run_tests(self, status_file_obj, exporter_obj):

        self.file_logger.info("Starting DNS tests...")
        status_file_obj.write_status_file("DNS tests")
      
        tests_passed = True

        # read in all target data
        for dns_index in range(1, self.num_dns_targets):

            target_name = 'dns_target{}'.format(dns_index)
            target_ip_ver = 'dns_target{}_ip_ver'.format(dns_index)

            dns_target = self.config_vars[target_name]
            dns_target_ip_ver = self.config_vars[target_ip_ver]

            # move on to next if no DNS entry data
            if dns_target == '':
                continue

            dns_result = self.dns_single_lookup(dns_target, dns_target_ip_ver)

            if dns_result:

                result_str = ' {}: {}ms'.format(dns_target, dns_result)

                # drop abbreviated results in log file
                self.file_logger.info("  DNS results: {}".format(result_str))

                results_dict = {
                    'time': get_timestamp(self.config_vars),
                    'dns_index': int(dns_index),
                    'dns_target': str(dns_target),
                    'lookup_time_ms': int(dns_result)
                }

                # define column headers for CSV
                column_headers = list(results_dict.keys())

                # dump the results
                if exporter_obj.send_results(self.config_vars, results_dict, column_headers, self.data_file, self.test_name, self.file_logger):
                    self.file_logger.info("  DNS test ended.\n")
                else:
                    self.file_logger.error("  Issue sending DNS results.")
                    tests_passed = False

            else:
                self.file_logger.error("  DNS test error - no results (check logs) - exiting DNS tests")
                tests_passed = False

        return tests_passed

