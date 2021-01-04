"""
A function to perform data export to Splunk using the HTTP event logger (HEC).
"""

import sys
from wiperf_poller.helpers.timefunc import time_synced, splunk_ts, now_as_msecs

# module import vars
splunk_modules = True
import_err = ''

try:
    from splunk_http_event_collector import http_event_collector
except ImportError as error:
    splunk_modules = False
    import_err = error

# TODO: convert to class
# TODO: error trap

def splunkexporter(host, token, port, dict_data, source, file_logger):
    '''
    A function to perform logging to Splunk using the HTTP event logger (HEC).
    '''

    if not splunk_modules:
        file_logger.error(" ********* MAJOR ERROR ********** ")
        file_logger.error("One or more Splunk Python .are not installed on this system. Splunk export failed, exiting")
        file_logger.error(import_err)
        sys.exit()
    
    # if time-source sync'ed, add timestamp
    timestamp = now_as_msecs()

    # remove redundant timestamp from results data
    del dict_data['time']
    dict_data['timestamp'] = timestamp
    
    event_logger = http_event_collector(token, host)

    payload = {}
    payload.update({"sourcetype": "_json"})
    payload.update({"source": source})
    payload.update({"event": dict_data})
    if time_synced():
        payload.update({"timestamp": timestamp})
    
    event_logger.sendEvent(payload)
    event_logger.flushBatch()

    return True
