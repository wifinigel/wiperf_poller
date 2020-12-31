"""
Set of functions to export results data to a variety of destinations
"""
import csv
import json
import os
import sys
from socket import gethostname

from wiperf_poller.exporters.splunkexporter import splunkexporter
from wiperf_poller.exporters.influxexporter2 import influxexporter2
from wiperf_poller.exporters.influxexporter import influxexporter
from wiperf_poller.helpers.route import is_ipv6
from wiperf_poller.exporters.cacheexporter import CacheExporter
#TODO: conditional import of influxexporter if Influx module available

class ResultsExporter(object):
    """
    Class to implement universal resuts exporter for wiperf
    """

    def __init__(self, file_logger, platform):

        self.platform = platform
        self.file_logger = file_logger

    
    def send_results_to_splunk(self, host, token, port, dict_data, file_logger, source):

        file_logger.info("Sending event to Splunk: {} (dest host: {}, dest port: {})".format(source, host, port))
        if is_ipv6(host): host = "[{}]".format(host)
        return splunkexporter(host, token, port, dict_data, source, file_logger)

    def send_results_to_influx(self, localhost, host, port, username, password, database, dict_data, source, file_logger):

        file_logger.info("Sending data to Influx host: {}, port: {}, database: {})".format(host, port, database))
        if is_ipv6(host): host = "[{}]".format(host)
        return influxexporter(localhost, host, port, username, password, database, dict_data, source, file_logger)
    
    def send_results_to_influx2(self, localhost, url, token, bucket, org, dict_data, source, file_logger):

        file_logger.info("Sending data to Influx url: {}, bucket: {}, source: {})".format(url, bucket, source))
        return influxexporter2(localhost, url, token, bucket, org, dict_data, source, file_logger)


    def send_results(self, config_vars, results_dict, column_headers, data_file, test_name, file_logger, delete_data_file=False):

        # dump the results to local cache if enabled
        if config_vars['cache_enabled'] =='yes':
            file_logger.info("Sending results to local file cache.")
            cache_exporter = CacheExporter(config_vars, file_logger)
            cache_exporter.dump_cache_results(data_file, results_dict, column_headers)

        # dump the results to appropriate destination
        if config_vars['exporter_type'] == 'splunk':

            file_logger.info("Splunk update: {}, source={}".format(data_file, test_name))
            return self.send_results_to_splunk(config_vars['data_host'], config_vars['splunk_token'], config_vars['data_port'],
                results_dict, file_logger, data_file)
        
        elif config_vars['exporter_type'] == 'influxdb':
            
            file_logger.info("InfluxDB update: {}, source={}".format(data_file, test_name))

            return self.send_results_to_influx(gethostname(), config_vars['data_host'], config_vars['data_port'], 
                config_vars['influx_username'], config_vars['influx_password'], config_vars['influx_database'], results_dict, data_file, file_logger)
        
        elif config_vars['exporter_type'] == 'influxdb2':
            
            file_logger.info("InfluxDB2 update: {}, source={}".format(data_file, test_name))

            # construct url
            host = config_vars['data_host']
            if is_ipv6(host): host = "[{}]".format(host)
            influx_url = "https://{}:{}".format(host, config_vars['data_port'])

            return self.send_results_to_influx2(gethostname(), influx_url, config_vars['influx2_token'],
                    config_vars['influx2_bucket'], config_vars['influx2_org'], results_dict, data_file, file_logger)
        
        else:
            file_logger.info("Unknown exporter type in config file: {}".format(config_vars['exporter_type']))
            sys.exit()

        return True