'''
A simple class to perform a DNS lookup against a number of targets and return the lookup time
'''
import time
import socket

class DnsTester(object):
    '''
    A class to perform a number of DNS lookups and return the lookup times
    '''

    def __init__(self, file_logger, platform="rpi"):

        self.platform = platform
        self.file_logger = file_logger

        self.target = []
        self.dns_result = 0

    def dns_single_lookup(self, target):
        '''
        This function will run a series of DNS lookups against the targets supplied
        and return the results in a dictionary.

        Usage:
            tester_obj.dns_lookup(bbc.co.uk')

        If the lookup fails, a False condition is returned with no further
        information. The lookup time is returned (results are in mS):

        '''
        # TODO: How do we handle empty targets & lookup failures (e.g. bad name)

        self.target = target

        self.file_logger.debug("DNS test target: {}".format(self.target))
        self.file_logger.debug("Performing DNS lookup for: {}".format(target))

        # TODO: Perform the test 3 times and take avg of best 2 out of 3 to iron
        #       out single-case anonmalies
        start = time.time()
        try:
            socket.gethostbyname(target)
        except Exception as ex:
            self.file_logger.error("DNS test lookup to {} failed. Err msg: {}".format(target, ex))
            self.dns_result = False
            self.file_logger.debug("DNS lookup for: {} failed! - err: {}".format(target, ex))
            return self.dns_result

        end = time.time()
        time_taken = int(round((end - start) * 1000))
        self.dns_result = time_taken

        self.file_logger.debug("DNS lookup for: {} succeeded.".format(target))

        return self.dns_result
    
    def run_tests(self, status_file_obj, config_vars, exporter_obj):

        self.file_logger.info("Starting DNS tests...")
        status_file_obj.write_status_file("DNS tests")

        dns_targets = [config_vars['dns_target1'], config_vars['dns_target2'],
                       config_vars['dns_target3'], config_vars['dns_target4'], config_vars['dns_target5']]

        dns_index = 0
        delete_file = True
        tests_passed = True

        for dns_target in dns_targets:

            dns_index += 1

            # move on to next if no DNS entry data
            if dns_target == '':
                continue

            dns_result = self.dns_single_lookup(dns_target)

            if dns_result:

                column_headers = ['time', 'dns_index',
                                  'dns_target', 'lookup_time_ms']

                # summarise result for log
                result_str = ' {}: {}ms'.format(dns_target, dns_result)

                # drop abbreviated results in log file
                self.file_logger.info("DNS results: {}".format(result_str))

                results_dict = {
                    'time': int(time.time()),
                    'dns_index': dns_index,
                    'dns_target': dns_target,
                    'lookup_time_ms': dns_result
                }

                # dump the results
                data_file = config_vars['dns_data_file']
                test_name = "DNS"
                if exporter_obj.send_results(config_vars, results_dict, column_headers, data_file, test_name, self.file_logger, delete_data_file=delete_file):
                    self.file_logger.info("DNS test ended.")
                else:
                    self.file_logger.error("Issue sending DNS results.")
                    tests_passed = False

                # Make sure we don't delete data file next time around
                delete_file = False

            else:
                self.file_logger.error("DNS test error - no results (check logs) - exiting DNS tests")
                tests_passed = False

        return tests_passed


    def get_dns_result(self):
        ''' Get DNS single lookup result '''
        return self.dns_result
