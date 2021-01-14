"""
Error messages class - reports error messages detected in current poll cycle
"""
import time
import os
import re
from wiperf_poller.helpers.timefunc import get_timestamp

class ErrorMessages():

    '''
    Error messages class - reports error messages detected in current poll cycle
    '''

    def __init__(self, config_vars, error_log_file, file_logger):

        self.error_log_file = error_log_file
        self.config_vars = config_vars
        self.file_logger = file_logger
        self.error_messages_limit = int(config_vars['error_messages_limit'])


    def dump(self, exporter_obj):

        self.file_logger.info("####### poll error messages #######")
        

        # check if we have an error log
        if os.path.isfile(self.error_log_file):

            # read the error message file in
            try:
                with open(self.error_log_file, 'r') as err_file:
                    lines = err_file.readlines()
            except Exception as ex:
                self.file_logger.error("Issue reading error_msg file: {}, abandoning operation.".format(ex))
                return False
            
            # filter out log file lines that don't start with date
            message_list = []

            for line in lines:
                if re.search(r'^\d\d\d\d-\d\d-\d\d', line) :
                    message_list.append(line.strip()[:150])
            
            if len(message_list) > 0:
                self.file_logger.info("Sending poll error messages to mgt platform")
            else:
                self.file_logger.info("No error messages to dump")

            # limit to last n messages
            if len(message_list) > self.error_messages_limit:
                message_list = message_list[-self.error_messages_limit:]

            # send error messages
            for error_message in message_list:

                column_headers = [ 'time', 'error_message' ]
                results_dict =  { 'time': get_timestamp(self.config_vars), 'error_message': error_message }

                # dump the results
                data_file = 'wiperf-poll-errors'
                test_name = "wiperf-poll-errors"

                if exporter_obj.send_results(self.config_vars, results_dict, column_headers, data_file, test_name, self.file_logger):
                    self.file_logger.info("Error message info sent.")

                else:
                    self.file_logger.error("Issue sending error message info.")
                    return False
            
            return True

        else:
            self.file_logger.error("No error log detected.")
            return True
            



        


    