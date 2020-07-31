'''
A simple class to perform a http get and return the time taken
'''
import time
import socket
import warnings
import requests
from requests.exceptions import HTTPError
import urllib3

class HttpTester(object):
    '''
    A simple class to perform a http get and return the time taken
    '''

    def __init__(self, file_logger, platform="rpi"):

        self.platform = platform
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

        # TODO: Perform 3 tests and avg best 2 to remove anomalies?
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
            self.file_logger.error('HTTP error occurred: {}'.format(http_err))
        except Exception as err:
            self.file_logger.error('Other error occurred: {}'.format(err))

        end = time.time()
        time_taken = int(round((end - start) * 1000))
        self.http_get_duration = time_taken

        # if we got a status code of zero, then something went wrong
        # therefore we need to drop our results to avoid bad duration results
        if self.http_status_code == 0:
            self.http_status_code = False
            self.http_get_duration = False
            self.http_server_response_time = False

        self.file_logger.debug("http get for: {} : {}mS, server repsonse time: {}ms (code: {}).".format(http_target, self.http_get_duration, self.http_server_response_time, self.http_status_code))

        # return status code & elapsed duration in mS
        return (self.http_status_code, self.http_get_duration, self.http_server_response_time)
    
    def run_tests(self, status_file_obj, config_vars, exporter_obj, watchd, check_correct_mode_interface,):

        self.file_logger.info("Starting HTTP tests...")
        status_file_obj.write_status_file("HTTP tests")

        http_targets = [config_vars['http_target1'], config_vars['http_target2'],
                        config_vars['http_target3'], config_vars['http_target4'], config_vars['http_target5']]

        http_index = 0
        delete_file = True
        all_tests_fail = True
        tests_passed = True

        for http_target in http_targets:

            http_index += 1

            # move on to next if no HTTP entry data
            if http_target == '':
                continue

            # check test will go over correct interface
            target_hostname = http_target.split('/')[2]
            if check_correct_mode_interface(target_hostname, config_vars, self.file_logger):
                pass
            else:
                self.file_logger.error(
                    "Unable to test http to {} as route to destination not over correct interface...bypassing http tests".format(http_target))
                # we will break here if we have an issue as something bad has happened...don't want to run more tests
                config_vars['test_issue'] = True
                tests_passed = False
                break

            self.file_logger.info("Starting http test to : {}".format(http_target))

            http_result = self.http_get(http_target)

            if http_result:

                column_headers = ['time', 'http_index', 'http_target', 'http_get_time_ms', 'http_status_code', 'http_server_response_time_ms']

                http_status_code = http_result[0]
                http_get_time = http_result[1]
                http_server_response_time = http_result[2]

                # test if http get returned a code - False = bad http get test
                if http_status_code:
                    # summarise result for log
                    result_str = ' {}: {}ms (status code: {})'.format(http_target, http_get_time, http_status_code)

                    # drop abbreviated results in log file
                    self.file_logger.info("HTTP results: {}".format(result_str))

                    results_dict = {
                        'time': int(time.time()),
                        'http_index': http_index,
                        'http_target': http_target,
                        'http_get_time_ms': http_get_time,
                        'http_status_code': http_status_code,
                        'http_server_response_time_ms': http_server_response_time
                    }

                    # dump the results
                    data_file = config_vars['http_data_file']
                    test_name = "HTTP"
                    if exporter_obj.send_results(config_vars, results_dict, column_headers, data_file, test_name, self.file_logger, delete_data_file=delete_file):
                        self.file_logger.info("HTTP results sent OK.")
                    else:
                        self.file_logger.error("Issue sending HTTP results")
                        tests_passed = False

                    all_tests_fail = False

                else:
                    self.file_logger.error("HTTP test had issue and failed, check agent.log")
                    tests_passed = False

                self.file_logger.info("HTTP test ended.")

                # Make sure we don't delete data file next time around
                delete_file = False

            else:
                self.file_logger.error(
                    "HTTP test error - no results (check logs) - exiting HTTP tests")
                config_vars['test_issue'] = True
                config_vars['test_issue_descr'] = "HTTP test failure"
                tests_passed = False
                break

        # if all tests fail, and there are more than 2 tests, signal a possible issue
        if all_tests_fail and (http_index > 1):
            self.file_logger.error("Looks like quite a few http tests failed, incrementing watchdog.")
            watchd.inc_watchdog_count()
        
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
