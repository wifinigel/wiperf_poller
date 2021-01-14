"""
Miscellaneous time functions
"""

import time
import subprocess
from wiperf_poller.helpers.os_cmds import TIMEDATECTL_CMD

def time_synced():

    # check if clock sync status is true from "timedatectl status" command
    cmd = "{} status".format(TIMEDATECTL_CMD)
    cmd_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True).decode()

    for line in cmd_output.split('\n'):
       if ("System clock" in line) and ("yes" in line):
            return True
    
    return False

def now_as_nsecs():
    return int(time.time() * 1000000000)

def now_as_usecs():
    return int(time.time() * 1000000)

def now_as_msecs():
    return int(time.time() * 1000)

def now_as_secs():
    return int(time.time())

def get_timestamp(config_vars):

    if config_vars['time_format'] == "influxdb":
        return now_as_msecs()

    elif config_vars['time_format'] == "splunk":
        return now_as_secs()
    
    elif config_vars['time_format'] == "influxdb2":
        return now_as_msecs()
    
    else:
        return now_as_secs()