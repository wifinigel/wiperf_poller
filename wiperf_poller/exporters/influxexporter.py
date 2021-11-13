import datetime
import sys
from wiperf_poller.helpers.timefunc import time_synced, now_as_msecs

# module import vars
influx_modules = True
import_err = ''

try:
    from influxdb import InfluxDBClient
except ImportError as error:
    influx_modules = False
    import_err = error

# TODO: Error checking if write to Influx fails 
# TODO: convert to class

def time_lookup():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")


def influxexporter(localhost, host, port, username, password, database, use_ssl, dict_data, source, file_logger):

    if not influx_modules:
        file_logger.error(" ********* MAJOR ERROR ********** ")
        file_logger.error("One or more Influx Python .are not installed on this system. Influx export failed, exiting")
        file_logger.error("(Execute the following command from the command line of the WLAN Pi: 'sudo pip3 install influxdb')")
        file_logger.error(import_err)
        sys.exit()

    client = InfluxDBClient(host, port, username, password, database, ssl=use_ssl, verify_ssl=False, timeout=100)
    file_logger.debug("Creating InfluxDB API client...")
    file_logger.debug("Remote host: -{}-".format(host))
    file_logger.debug("Port: -{}-".format(port))
    file_logger.debug("Database: -{}-".format(database))
    file_logger.debug("User: -{}-".format(username))

    data_point = {
        "measurement": source,
        "tags": { "host": localhost },
        "fields": {},
    }

    # if time-source sync'ed, add timestamp
    if time_synced():
        data_point['time'] = dict_data['time']
 
    # put results data in to payload to send to Influx
    data_point['fields'] = dict_data

    # send to Influx
    try:
        if client.write_points([data_point], time_precision='ms'):    
            file_logger.info("Data sent to influx OK")
        else:
            file_logger.info("Issue with sending data sent to influx...")
            return False

    except Exception as err:
        file_logger.error("Issue sending data to Influx: {}".format(err))
        return False
    
    # close the http session
    client.close()
    
    file_logger.debug("Data structure sent to Influx:")
    file_logger.debug(data_point)

    return True

    
