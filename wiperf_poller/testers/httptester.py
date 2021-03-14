'''
A simple class to perform a http get and return the time taken
'''
import time
import socket
import warnings
import requests
from requests.exceptions import HTTPError
import urllib3
from wiperf_poller.helpers.timefunc import get_timestamp
from wiperf_poller.helpers.viabilitychecker import TestViabilityCheckerIpv4
from wiperf_poller.helpers.ipv6.viabilitychecker_ipv6 import TestViabilityCheckerIpv6
from wiperf_poller.helpers.route import (
    resolve_name,
    resolve_name_ipv4,
    resolve_name_ipv6 ,
    check_correct_mode_interface_ipv4,
    is_ipv4,
    is_ipv6
)
from wiperf_poller.helpers.ipv6.route_ipv6 import check_correct_mode_interface_ipv6

class HttpTesterIpv4(object):
    '''
    A simple class to perform a http get and return the time taken
    '''

    def __init__(self, file_logger):

        self.file_logger = file_logger

        self.http_target = ''
        self.http_get_duration = 0
        self.http_server_response_time = 0
        self.http_status_code = 0


    def http_get(self, http_target):
        '''
        This function will do a http/https get to the specifed target URL

        If the lookup fails, a False condition is returned with no further
        information. The lookup time is returned (results are in mS):

        '''

        self.file_logger.debug("HTTP test target: {}".format(http_target))

        start = time.time()
        try:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(http_target, verify=False, timeout=5)
            self.http_status_code = response.status_code

            # server reposnse time (uS , converted to mS)- http headers, not full page load
            self.http_server_response_time = int(response.elapsed.microseconds/1000)

            # If the response was successful, no Exception will be raised
            response.raise_for_status()
        except HTTPError as http_err:
            self.file_logger.error('  HTTP error occurred: {}'.format(http_err))
        except Exception as err:
            self.file_logger.error('  Other error occurred: {}'.format(err))

        end = time.time()
        time_taken = int(round((end - start) * 1000))
        self.http_get_duration = time_taken

        # if we got a status code of zero, then something went wrong
        # therefore we need to drop our results to avoid bad duration results
        if self.http_status_code == 0:
            self.http_status_code = False
            self.http_get_duration = False
            self.http_server_response_time = False

        self.file_logger.debug("  http get for: {} : {}mS, server repsonse time: {}ms (code: {}).".format(http_target, self.http_get_duration, self.http_server_response_time, self.http_status_code))

        # return status code & elapsed duration in mS
        return (self.http_status_code, self.http_get_duration, self.http_server_response_time)
    
    def run_tests(self, status_file_obj, config_vars, exporter_obj, watchd, check_correct_mode_interface,):

        self.file_logger.info("Starting HTTP tests...")
        status_file_obj.write_status_file("HTTP tests")
       
        all_tests_fail = True
        tests_passed = True

        # get specifed number of targets (format: 'http_target1')
        num_http_targets = int(config_vars['http_targets_count']) + 1

        # read in all target data
        for target_num in range(1, num_http_targets):

            target_name = 'http_target{}'.format(target_num)
            #target_name_ip_ver = 'http_target{}_ip_ver'.format(target_num)

            http_target = config_vars[target_name]
            #http_target_ip_ver = config_vars[target_name_ip_ver]

            # move on to next if no HTTP entry data
            if http_target == '':
                continue

            self.file_logger.info("  HTTP test to : {}".format(http_target))

            """
            Notes: There is little point verifying the interface to be based on the resolved IP address or the 
            IPv4/IPv6 viability:

                1. Interface should be correct due to defaut GW static route setting
                2. HTTP transfer may alternate netween IPv4/v6 connectivity during transfer, so unable to 
                   mandate use of IPv4-only or IPv6-only
            """

            """
            # check test will go over correct interface
            #TODO: Check for correct URL format here: http://xxxx (otherwise split fails below & script exits)
            target_hostname = http_target.split('/')[2]

            # pull out hostname if in format [2001:1:1:1:1::5] for
            # direct ipv6 address
            if "[" in target_hostname:
                target_hostname = target_hostname[1: -1]
            

            if http_target_ip_ver  == "ipv4":
                self.resolve_name = resolve_name_ipv4
            elif http_target_ip_ver  == "ipv6":
                self.resolve_name = resolve_name_ipv6
            else:
                # just use generic resolve name func that does both
                self.resolve_name = resolve_name
            
            http_target_ip = self.resolve_name(target_hostname, self.file_logger, config_vars)

            # Select appropriate viability checker & route checker
            if is_ipv4(http_target_ip):
                TestViabilityChecker = TestViabilityCheckerIpv4
                check_correct_mode_interface = check_correct_mode_interface_ipv4
            elif is_ipv6(http_target_ip):
                TestViabilityChecker = TestViabilityCheckerIpv6
                check_correct_mode_interface = check_correct_mode_interface_ipv6
            else:
                raise ValueError("  Ping host IP does not match known address format: {}".format(http_target_ip))

            # create test viability checker
            checker = TestViabilityChecker(config_vars, self.file_logger)

            # check if test to host is viable (based on probe ipv4/v6 support)
            if not checker.check_test_host_viable(http_target_ip):
                self.file_logger.error("  HTTP target test not viable, will not be tested ({} / {})".format(http_target, http_target_ip))
                continue

            if check_correct_mode_interface(target_hostname, config_vars, self.file_logger):
                pass
            else:
                self.file_logger.error(
                    "  Unable to test http to {} as route to destination not over correct interface...bypassing http test".format(http_target))
                # we will break here if we have an issue as something bad has happened...don't want to run more tests
                config_vars['test_issue'] = True
                tests_passed = False
                continue

            """
            self.file_logger.info("  Starting http test to : {}".format(http_target))

            http_result = self.http_get(http_target)

            if http_result:

                http_status_code = http_result[0]
                http_get_time = http_result[1]
                http_server_response_time = http_result[2]

                # test if http get returned a code - False = bad http get test
                if http_status_code:
                    # summarise result for log
                    result_str = ' {}: {}ms (status code: {})'.format(http_target, http_get_time, http_status_code)

                    # drop abbreviated results in log file
                    self.file_logger.info("  HTTP results: {}".format(result_str))

                    results_dict = {
                        'time': get_timestamp(config_vars),
                        'http_index': int(target_num),
                        'http_target': str(http_target),
                        'http_get_time_ms': int(http_get_time),
                        'http_status_code': int(http_status_code),
                        'http_server_response_time_ms': int(http_server_response_time)
                    }

                    # define column headers for CSV
                    column_headers = list(results_dict.keys())

                    # dump the results
                    data_file = config_vars['http_data_file']
                    if exporter_obj.send_results(config_vars, results_dict, column_headers, data_file, "HTTP", self.file_logger):
                        self.file_logger.info("  HTTP results sent OK.")
                    else:
                        self.file_logger.error("  Issue sending HTTP results")
                        tests_passed = False

                    all_tests_fail = False

                else:
                    self.file_logger.error("  HTTP test had issue and failed, check agent.log")
                    tests_passed = False

                self.file_logger.info("  HTTP test ended.\n")

            else:
                self.file_logger.error(
                    "  HTTP test error - no results (check logs) - exiting HTTP tests")
                config_vars['test_issue'] = True
                config_vars['test_issue_descr'] = "HTTP test failure"
                tests_passed = False
                break
       
        return tests_passed

    def get_http_duration(self):
        ''' Get http page load result '''
        return self.http_get_duration

    def get_http_server_response(self):
        ''' Get http server response time '''
        return self.http_server_response_time

    def get_status_code(self):
        ''' Get http status code '''
        return self.http_status_code
