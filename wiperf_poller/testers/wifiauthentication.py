'''
A simple class to perform an network Smb copy and return a number of
result characteristics
'''

import time
import re
import subprocess
from sys import stderr
from wiperf_poller.helpers.os_cmds import GREP_CMD,WPA_CMD
import datetime

class AuthTester(object):
    '''
    A class to perform a wifi authentication disconnect and reconnect and measure time to connect- a basic wrapper around a CLI WPA-CLI command
    '''

    def __init__(self, file_logger, platform="rpi"):

        self.platform = platform
        self.file_logger = file_logger
        self.test_starttime = ''
        self.test_endtime = ''
        self.time_to_transfer = ''

    def time_to_authenticate(self):
        '''
        This function will disconnect and reconnect to the wifi network and measure elapsed time from logs

        If the reconnect failed, a False condition is returned with no further
        information. If the Smb succeeds, the following dictionary is returned:

        {  'test_time': self.test_time,
        '''


        self.file_logger.debug("wpa_cli disconnected: ")

        # Execute the wpa_cli disconnect
        try:
            cmd_string = "{} disconnect".format(WPA_CMD)
            Smb_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error = "Hit an error when wpa_cli disconnect : {} ".format( str(output))
            self.file_logger.error(error)
            stderr.write(str(error))

            # Things have gone bad - we just return a false status
            return False
        time_reference=time.time
        self.file_logger.debug("wpa_cli disconnect:")
        self.file_logger.debug(Smb_output)

        # Execute the cp mount
        self.file_logger.debug("wpa_cli reconnect: ") 
        try:
            cmd_string = "{} reconnect".format(WPA_CMD)
            start_time= time.time()
            Smb_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
            end_time=time.time()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error = "Hit an error with wpa_cli reconnect : {}".format( str(output))
            self.file_logger.error(error)
            stderr.write(str(error))

        cmd_string = "{} \"wlan0: Trying to associate with \" /var/log/daemon.log ".format(GREP_CMD)
        Smb_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
        result=Smb_output[len(Smb_output)-1].split()
        start_date_time = datetime.datetime.strptime(result[0] + " " + result[1], '%Y-%m-%d %H:%M:%S.%f')
 
        end_date_time=start_date_time
        while end_date_time<=start_date_time:
            cmd_string = "{} \"wlan0: CTRL-EVENT-CONNECTED\" /var/log/daemon.log ".format(GREP_CMD)
            Smb_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
            result=Smb_output[len(Smb_output)-1].split()
            end_date_time = datetime.datetime.strptime(result[0] + " " + result[1], '%Y-%m-%d %H:%M:%S.%f')

        elapse_time = (end_date_time-start_date_time).total_seconds()

        self.file_logger.info('Time to authenticate : {}, start time {} end time: {}'.format(
            elapse_time, start_date_time,end_date_time))

        return {
            'time_to_connect':elapse_time}

    def run_tests(self, status_file_obj, config_vars, adapter, check_correct_mode_interface, exporter_obj, watchd):

        self.file_logger.info("Starting Authentication benchmark...")
        status_file_obj.write_status_file("Authentication tests")


        # define colum headers for CSV
        column_headers = ['time to authenticate']
        
        all_tests_fail = True
        results_dict = {}
        delete_file=True
        test_result=self.time_to_authenticate()

        # Time to authenticateresults
        if test_result:
            results_dict['time'] = int(time.time())
            results_dict['time_to_authenticate'] = test_result['time_to_connect']
            time.sleep(2)
            # dump the results
            data_file = config_vars['auth_test_data_file']
            test_name = "Time to authenticate"
            if exporter_obj.send_results(config_vars, results_dict, column_headers, data_file, test_name, self.file_logger, delete_data_file=delete_file):
                self.file_logger.info("time to authenticate test ended.")
            else:                    
                self.file_logger.error("Issue sending time to authenticate results.")
                tests_passed = False
            # Make sure we don't delete data file next time around
            delete_file = False
            self.file_logger.debug("Main: time to authenticate results:")
            self.file_logger.debug(test_result)    
            # signal that at least one test passed
            all_tests_fail = False
        else:
            self.file_logger.error("Time to authenticate test failed.")
            tests_passed = False
            
        # if all tests fail, and there are more than 2 tests, signal a possible issue
        
        return tests_passed
