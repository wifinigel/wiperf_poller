"""
Set of functions to export results data to a variety of destinations
"""
import csv
import json
import os
import sys
from socket import gethostname

from wiperf_poller.exporters.splunkexporter import SplunkExporter
from wiperf_poller.exporters.influxexporter2 import influxexporter2
from wiperf_poller.exporters.influxexporter import influxexporter
from wiperf_poller.exporters.spoolexporter import SpoolExporter
from wiperf_poller.helpers.route import is_ipv6
from wiperf_poller.exporters.cacheexporter import CacheExporter

class ResultsExporter(object):
    """
    Class to implement universal resuts exporter for wiperf
    """

    def __init__(self, file_logger, watchdog_obj, lockf_obj, spooler_obj, platform):

        self.platform = platform
        self.file_logger = file_logger
        self.watchdog_obj = watchdog_obj
        self.lockf_obj = lockf_obj
        self.cache_obj = CacheExporter(file_logger)
        self.spooler_obj = spooler_obj
    
    def send_results_to_splunk(self, host, token, port, dict_data, file_logger, source):

        file_logger.info("Sending results event to Splunk: {} (dest host: {}, dest port: {})".format(source, host, port))
        splunk_exp_obj=SplunkExporter(host, token, file_logger, port)
        return splunk_exp_obj.export_result(dict_data, source)

    def send_results_to_influx(self, localhost, host, port, username, password, database, use_ssl, dict_data, source, file_logger):

        file_logger.info("Sending results data to Influx host: {}, port: {}, database: {})".format(host, port, database))
        if is_ipv6(host): host = "[{}]".format(host)
        return influxexporter(localhost, host, port, username, password, database, use_ssl, dict_data, source, file_logger)
    
    def send_results_to_influx2(self, localhost, url, token, bucket, org, dict_data, source, file_logger):

        file_logger.info("Sending results data to Influx url: {}, bucket: {}, source: {})".format(url, bucket, source))
        return influxexporter2(localhost, url, token, bucket, org, dict_data, source, file_logger)
    
    def send_results_to_spooler(self, config_vars, data_file, dict_data, file_logger):

        file_logger.info("Sending results data to spooler: {} (as mgt platform not available)".format(data_file))
        return self.spooler_obj.spool_results(config_vars, data_file, dict_data, self.watchdog_obj, self.lockf_obj)


    def send_results(self, config_vars, results_dict, column_headers, data_file, test_name, file_logger, delete_data_file=False):

        sent_ok = False

        # dump the results to local cache if enabled
        if config_vars['cache_enabled'] =='yes':
            file_logger.info("Sending results to local file cache.")
            self.cache_obj.dump_cache_results(config_vars, data_file, results_dict, column_headers)

        # dump the results to appropriate destination
        if config_vars['exporter_type'] == 'splunk':

            file_logger.info("Splunk update: {}, source={}".format(data_file, test_name))
            sent_ok = self.send_results_to_splunk(config_vars['data_host'], config_vars['splunk_token'], config_vars['data_port'],
                results_dict, file_logger, data_file)
        
        elif config_vars['exporter_type'] == 'influxdb':
            
            file_logger.info("InfluxDB update: {}, source={}".format(data_file, test_name))

            sent_ok = self.send_results_to_influx(gethostname(), config_vars['data_host'], config_vars['data_port'], 
                config_vars['influx_username'], config_vars['influx_password'], config_vars['influx_database'], config_vars['influx_ssl'], results_dict, data_file, file_logger)
        
        elif config_vars['exporter_type'] == 'influxdb2':
            
            file_logger.info("InfluxDB2 update: {}, source={}".format(data_file, test_name))

            # construct url
            host = config_vars['data_host']
            scheme = 'https' if config_vars['influx2_ssl'] else 'http'
            if is_ipv6(host): host = "[{}]".format(host)
            influx_url = "{}://{}:{}".format(scheme, host, config_vars['data_port'])

            sent_ok = self.send_results_to_influx2(gethostname(), influx_url, config_vars['influx2_token'],
                    config_vars['influx2_bucket'], config_vars['influx2_org'], results_dict, data_file, file_logger)
        
        elif config_vars['exporter_type'] == 'spooler':

            # Do nothing, but drop through to spooler export at end
            pass
        
        else:
            file_logger.info("Unknown exporter type in config file: {}".format(config_vars['exporter_type']))
            self.lockf_obj.delete_lock_file()
            sys.exit()

        if sent_ok:
            # we sent our data to  reporting plarform OK
            return True
        else:
            # sending to reporting server failed, try spooling result as last resort
            return self.send_results_to_spooler(config_vars, data_file, results_dict, file_logger)
