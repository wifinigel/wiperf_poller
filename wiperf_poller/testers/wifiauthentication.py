'''
A simple class to perform an network auth copy and return a number of
result characteristics
'''

import time
import re
import subprocess
from wiperf_poller.helpers.os_cmds import GREP_CMD,WPA_CMD
from wiperf_poller.helpers.timefunc import get_timestamp
import datetime

class AuthTester(object):
    '''
    A class to perform a wifi authentication disconnect and reconnect and measure time to connect- a basic 
    wrapper around a CLI WPA-CLI command
    '''

    def __init__(self, file_logger, platform="rpi"):

        self.platform = platform
        self.file_logger = file_logger


    def time_to_authenticate(self, interface="wlan0"):
        '''
        This function will disconnect and reconnect to the wifi network and measure elapsed time from logs
        If the reconnect failed, a False condition is returned with no further
        information. If the auth succeeds, the following dictionary is returned:
        { 'auth_time': auth_time }
        '''

        self.file_logger.debug("wpa_cli disconnected: ")

        # Execute the wpa_cli disconnect
        try:
            self.file_logger.info("Disconnecting...")
            cmd_string = "{} disconnect".format(WPA_CMD)
            auth_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error = "Hit an error with wpa_cli disconnect : {} ".format( str(output))
            self.file_logger.error(error)

            # Things have gone bad - we just return a false status
            return False
        
        self.file_logger.debug("wpa_cli disconnect:")
        self.file_logger.debug(auth_output)

        # Execute reconnect
        self.file_logger.info("Reconnecting...")
        self.file_logger.debug("wpa_cli reconnect: ") 
        try:
            cmd_string = "{} reconnect".format(WPA_CMD)
            auth_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error = "Hit an error with wpa_cli reconnect : {}".format( str(output))
            self.file_logger.error(error)
            return False

        # sleep to allow logging to complete
        time.sleep(2)

        # grep for association log info
        try:
            #cmd_string = "{} \"{}: Trying to associate with \" /var/log/daemon.log ".format(GREP_CMD, interface)
            cmd_string = "{} \"{}: Associated with \" /var/log/daemon.log ".format(GREP_CMD, interface)
            auth_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
            result = auth_output[len(auth_output)-1].split()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error = "Hit an error with grep of daemon.log : {}".format( str(output))
            self.file_logger.error(error)
            return False
    
        try:
            start_date_time = datetime.datetime.strptime(result[0] + " " + result[1], '%Y-%m-%d %H:%M:%S.%f')
        except:
            self.file_logger.error("""
    
    Conversion of timestamp failed. Have you applied the recommended update to the 
    log format of rsyslog:
    
    - Rsyslogd must log with rfc3339 date format.
    - modify /etc/rsyslogd.conf with the following line
    - Comment out the line $ActionFileDefaultTemplate RSYSLOG_TraditionalFileFormat
        #$ActionFileDefaultTemplate RSYSLOG_TraditionalFileFormat
    - Add the following lines:
        $template CustomFormat,"%timegenerated:1:10:date-rfc3339% %timegenerated:12:24:date-rfc3339% %syslogtag%%msg%\\n"
        $ActionFileDefaultTemplate CustomFormat
    - Restart rsyslog with this CLI command: systemctl restart rsyslog
    """
            )
            return False


        end_date_time = start_date_time

        while end_date_time<=start_date_time:
            #cmd_string = "{} \"{}: CTRL-EVENT-CONNECTED\" /var/log/daemon.log ".format(GREP_CMD, interface)
            cmd_string = "{} \"{}: WPA: Key negotiation completed\" /var/log/daemon.log ".format(GREP_CMD, interface)
            auth_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
            result = auth_output[len(auth_output)-1].split()
            end_date_time = datetime.datetime.strptime(result[0] + " " + result[1], '%Y-%m-%d %H:%M:%S.%f')

        elapsed_time = (end_date_time-start_date_time).total_seconds()

        self.file_logger.info('Time to authenticate : {}, start time {} end time: {}'.format(
            elapsed_time, start_date_time,end_date_time))

        return { 'auth_time': elapsed_time }

    def run_tests(self, status_file_obj, config_vars, adapter, check_correct_mode_interface, exporter_obj, watchd):

        self.file_logger.info("Starting Authentication benchmark...")
        status_file_obj.write_status_file("Auth tests")

        results_dict = {}
        delete_file = True
        test_result = self.time_to_authenticate()

        # Time to authenticate results
        if test_result:
            results_dict['time'] = get_timestamp(config_vars)
            results_dict['auth_time'] = float(test_result['auth_time'])
            time.sleep(2)

            # define column headers for CSV
            column_headers = list(results_dict.keys())

            # dump the results
            data_file = config_vars['auth_data_file']
            test_name = "Time to authenticate"

            if exporter_obj.send_results(config_vars, results_dict, column_headers, data_file, test_name, self.file_logger, delete_data_file=delete_file):
                self.file_logger.info("Time to authenticate test ended.")
                tests_passed = True
            else:                    
                self.file_logger.error("Issue sending time to authenticate results.")
                tests_passed = False
            
            # Make sure we don't delete data file next time around
            delete_file = False
            self.file_logger.debug("Main: time to authenticate results:")
            self.file_logger.debug(test_result)    
        
        else:
            self.file_logger.error("Time to authenticate test failed.")
            tests_passed = False
            # increment watchdog
            watchd.inc_watchdog_count()

        # if all tests fail, and there are more than 2 tests, signal a possible issue

        return tests_passed