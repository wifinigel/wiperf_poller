"""
A class to perform data export to Splunk using the HTTP event logger (HEC).
"""
from wiperf_poller.helpers.os_cmds import NC_CMD
from wiperf_poller.helpers.route import is_ipv6
from wiperf_poller.helpers.timefunc import time_synced
import json
import requests
import subprocess
import socket
import time
from requests.exceptions import HTTPError
import urllib3

class SplunkExporter(object):
    """
    Class to implement event export to Splunk
    """

    def __init__(self, host, token, file_logger, port='8088', secure=True):

        # Splunk connection params
        self.host = host
        self.token = token
        self.port = port
        self.secure = secure

        self.hostname = socket.gethostname()
        
        self.file_logger = file_logger
  

    def _url_generator(self, path='/'):

        scheme = 'http'

        if self.secure:
            scheme = 'https'

        if is_ipv6(self.host): 
            self.host = "[{}]".format(self.host)

        url = "{}://{}:{}{}".format(scheme, self.host, self.port, path)

        return url

    def check_splunk_port(self):

        self.file_logger.debug("  Checking port connection to Splunk server {}, port: {}".format(self.host, self.port))

        try:
            subprocess.check_output('{} -zvw10 {} {}'.format(NC_CMD, self.host, self.port), stderr=subprocess.STDOUT, shell=True).decode()
            self.file_logger.debug("  Port connection to server {}, port: {} checked OK.".format(self.host, self.port))
            return True
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            self.file_logger.error("Port check to Splunk server failed. Err msg: {}".format(str(output)))
            return False
    
    def ping_http_port(self):

        self.file_logger.debug('Checking for http(s) reponse on port: {}'.format(self.port))

        # stop errors if using https
        if self.secure:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        url = self._url_generator('/services/collector/event')
        self.file_logger.debug('testing URL: {}'.format(url))

        try:
            response = requests.get(url, verify=False, timeout=5)

            if response.status_code == 200:
                self.file_logger.debug('URL is good')
                return True
            else:
                self.file_logger.debug('Bad response: {}'.format(response.status_code))
                return False

        except Exception as err:
            self.file_logger.error('http error occurred: {}'.format(err))
        
        return False

    def check_token(self):

        # stop errors if using https
        if self.secure:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        url = self._url_generator(path='/services/collector/event')

        token = self.token    
        headers = {'Authorization':'Splunk '+ token}

        # send auth request
        try:
            self.file_logger.debug('Sending http post to check token validity.')
            response = requests.post(url, data={}, headers=headers, verify=False)
        except Exception as err:
            self.file_logger.error('http error occurred when sending token check data: {}'.format(err))
            return False
        response_code = response.status_code

        failed_auth_codes = [401, 403]
        passed_auth = True

        self.file_logger.debug('Checking Splunk auth token is valid...')
        
        if response_code == 400:
            self.file_logger.debug("Splunk token check: ok.")
        elif response_code in failed_auth_codes:
            self.file_logger.error("Splunk token check: Token appears invalid or is not enabled, please check you are using correct Token and that it is enabled on Splunk server")
            passed_auth = False
        else:
            self.file_logger.error("Splunk token check: Bad response code from Splunk server...are its services definitely up? Check Splunk server.")
            passed_auth = False

        if not passed_auth:
            self.file_logger.error("Splunk token check: Auth check to server failed.")
            return False
        
        return True
    
    def export_result(self, results_dict, source):

        # stop errors if using https
        if self.secure:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        url = self._url_generator(path='/services/collector/event')

        token = self.token    
        headers = {'Authorization':'Splunk '+ token}

        # create event to send to Splunk
        event_data = { 'host': self.hostname, 'source': source, 'event': results_dict }

        if time_synced():
            event_data['time'] = results_dict['time']
        
        json_event_data = json.dumps(event_data)

        # send results data
        try:
            self.file_logger.debug('Sending http post with results data.')
            response = requests.post(url, data=json_event_data, headers=headers, verify=False)
        except Exception as err:
            self.file_logger.error('http error occurred when sending results data: {}'.format(err))
            return False

        response_code = response.status_code
        
        if response_code == 200:
            self.file_logger.debug("Data sent OK.")
            return True
        else:
            self.file_logger.error("Data send failed - http code: {}".format(response_code))
            return False