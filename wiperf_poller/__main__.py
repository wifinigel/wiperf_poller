#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import sys
import time

# our local modules
from wiperf_poller.run_network_tests import run_tests

from wiperf_poller.helpers.bouncer import Bouncer
from wiperf_poller.helpers.config import read_local_config
from wiperf_poller.helpers.error_messages import ErrorMessages
from wiperf_poller.exporters.exportresults import ResultsExporter
from wiperf_poller.helpers.filelogger import FileLogger
from wiperf_poller.helpers.lockfile import LockFile
from wiperf_poller.helpers.networkadapter import NetworkAdapter
from wiperf_poller.helpers.os_cmds import check_os_cmds
from wiperf_poller.helpers.poll_status import PollStatus
from wiperf_poller.helpers.remoteconfig import check_last_cfg_read
from wiperf_poller.exporters.spoolexporter import SpoolExporter
from wiperf_poller.helpers.statusfile import StatusFile
from wiperf_poller.helpers.watchdog import Watchdog
from wiperf_poller.helpers.wirelessadapter import WirelessAdapter
from wiperf_poller.testers.networkconnectiontester import NetworkConnectionTester
from wiperf_poller.testers.mgtconnectiontester import MgtConnectionTester

config_file = "/etc/wiperf/config.ini"
log_file = "/var/log/wiperf_agent.log"
error_log_file = "/tmp/wiperf_err.log"
lock_file = '/tmp/wiperf_poller.lock'
status_file = '/tmp/wiperf_status.txt'
watchdog_file = '/tmp/wiperf_poller.watchdog'
bounce_file = '/tmp/wiperf_poller.bounce'
check_cfg_file = '/tmp/wiperf_poller.cfg'

# Enable debugs
DEBUG = 0

###################################
# File logger
###################################

# set up our error_log file & initialize
file_logger = FileLogger(log_file, error_log_file)
file_logger.info(" ")
file_logger.info("*****************************************************")
file_logger.info(" Starting logging...")
file_logger.info("*****************************************************")

# Pull in our config.ini dict
config_vars = read_local_config(config_file, file_logger)

# set logging to debug if debugging enabled
if DEBUG or (config_vars['debug'] == 'on'):
    file_logger.setLevel(level=logging.DEBUG)
    file_logger.info("(Note: logging set to debug level.)")

# check we are running as root user (sudo)
if os.geteuid() != 0:
    file_logger.error("Not running as root. Run using 'sudo' if running on CLI, or add to crontab using 'sudo crontab -e' for normal, schduled operation...exiting.")
    sys.exit()

# check all our os-level cmds are available
if not check_os_cmds(file_logger):
    file_logger.error("Missing OS command....exiting.")
    sys.exit()

# Lock file object
lockf_obj = LockFile(lock_file, file_logger)

# watchdog object
watchdog_obj = Watchdog(watchdog_file, file_logger)

# status file object
status_file_obj = StatusFile(status_file, file_logger)

# bouncer object
bouncer_obj = Bouncer(bounce_file, config_vars, file_logger)

# spooler object
spooler_obj = SpoolExporter(config_vars, file_logger)

# exporter object
exporter_obj = ResultsExporter(file_logger, watchdog_obj, lockf_obj, spooler_obj)

# adapter object
adapter_obj = ''
probe_mode = config_vars['probe_mode']
wlan_if = config_vars['wlan_if']
eth_if = config_vars['eth_if']

if probe_mode == "ethernet":
    adapter_obj = NetworkAdapter(eth_if, file_logger)
elif probe_mode == "wireless":
    adapter_obj = WirelessAdapter(wlan_if, file_logger)
else:
    file_logger.info("Unknown probe mode: {} (exiting)".format(probe_mode))

config_vars['ipv4_tests_possible'] = False
config_vars['ipv6_tests_possible'] = False

adapter_ipv4_addr = adapter_obj.get_adapter_ipv4_ip()
adapter_ipv6_addr = adapter_obj.get_adapter_ipv6_ip()

if config_vars['ipv4_enabled'] == 'yes':
    if adapter_ipv4_addr:
        config_vars['ipv4_tests_possible'] = True

if config_vars['ipv6_enabled'] == 'yes':
    if adapter_ipv6_addr:
        config_vars['ipv6_tests_possible'] = True

###############################################################################
# Main
###############################################################################
def main():

    global file_logger
    global config_vars
    global watchdog_file
    global config_file
    global check_cfg_file

    # create watchdog if doesn't exist
    watchdog_obj.create_watchdog()

    # check watchdog count...if higher than 3, time for a reboot
    watchdog_count = watchdog_obj.get_watchdog_count()
    file_logger.info("Watchdog count =  {}".format(watchdog_count))

    if watchdog_count > 3:
        file_logger.error("Watchdog count exceeded...rebooting")
        bouncer_obj.reboot()

    ###################################
    # Check if script already running
    ###################################
    if lockf_obj.lock_file_exists():

        # read lock file contents & check how old timestamp is..
        file_logger.error("Existing lock file found...  (watchdog incremented)")
        watchdog_obj.inc_watchdog_count()

        # if timestamp older than 10 mins, break lock
        if lockf_obj.lock_is_old():
            file_logger.error("Existing lock stale, breaking lock...")
            lockf_obj.break_lock()
        else:
            # lock not old enough yet, respect lock & exit
            file_logger.error("Exiting due to lock file indicating script running.")
            file_logger.error("(Delete {} if you are sure script not running)".format(lock_file))
            sys.exit()
    else:
        # create lockfile with current timestamp to stop 2nd process starting
        file_logger.info("No lock file found. Creating lock file.")
        lockf_obj.write_lock_file()
    
    ###################################
    # Check if remote cfg supported
    ###################################
    # if we have a config server specified, check to see if it's time
    # to pull the config
    file_logger.info("Checking if we use remote cfg file...")
    if config_vars['cfg_url']:
        
        # if able to get cfg file, re-read params in case updated
        if check_last_cfg_read(config_file, check_cfg_file, config_vars, file_logger):
            config_vars = read_local_config(config_file, file_logger)

    else:
        file_logger.info("No remote cfg file confgured...using current local ini file.")

    # test issue flag - set if any tests hit major issues
    # to stall further testing
    config_vars['test_issue'] = 0
    config_vars['test_issue_threshold'] = 5 
    config_vars['test_issue_descr'] = ""

    # set up poll health obj
    poll_obj = PollStatus(config_vars, file_logger)
    poll_obj.probe_mode(probe_mode)
    poll_obj.mgt_if(config_vars['mgt_if'])
    
    #############################################
    # Run network checks
    #############################################
    wlan_if = config_vars['wlan_if']
    eth_if = config_vars['eth_if']
    
    if config_vars['probe_mode'] == 'wireless':
        network_if = wlan_if
    else:
        network_if = eth_if
    
    # Note: test_issue flag not set by connection tests, as issues will result in process exit
    network_connection_obj = NetworkConnectionTester(file_logger, network_if, config_vars['probe_mode'])  
    network_connection_obj.run_tests(watchdog_obj, lockf_obj, config_vars, exporter_obj, status_file_obj)
      
    poll_obj.network("OK") 
    
    # update poll summary with IP
    poll_obj.ip(adapter_ipv4_addr)
    poll_obj.ip_v6(adapter_ipv6_addr)

    #############################################
    # Reporting platform connectivity checks
    #############################################
    mgt_connection_obj =  MgtConnectionTester(config_vars, file_logger)
    mgt_connection_obj.check_mgt_connection(lockf_obj, watchdog_obj)

    # report wireless connection info if using a wireless connection
    if config_vars['probe_mode'] == 'wireless':
        file_logger.info("Reporting wireless connection check results")
        network_connection_obj.report_wireless_check_results(lockf_obj, config_vars, exporter_obj)

    ################################################
    # Empty results spool queue if required/enabled
    ################################################
    file_logger.info("######## spooler checks ########")
    if config_vars['results_spool_enabled'] == 'yes':
        spooler_obj.process_spooled_files(exporter_obj)                        
    else:
        file_logger.info("Spooler not enabled.")

    #############################################
    # Run network tests
    #############################################          
    file_logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    file_logger.info("~~~~~    Initiating network tests cycle     ~~~~~")
    file_logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")
    run_tests(config_vars, file_logger, poll_obj, status_file_obj, exporter_obj, lockf_obj, adapter_obj, watchdog_obj)

    #####################################
    # Tidy up before exit
    #####################################
  
    # dump poller status info
    if config_vars['poller_reporting_enabled'] == 'yes':
        poll_obj.dump(exporter_obj)

    # dump error messages
    if config_vars['error_messages_enabled'] == 'yes':
        error_msg_obj = ErrorMessages(config_vars, error_log_file, file_logger)
        error_msg_obj.dump(exporter_obj)

    # get rid of lock file
    status_file_obj.write_status_file("")
    lockf_obj.delete_lock_file()

    file_logger.info("########## end ##########\n\n\n")

    # decrement watchdog as we ran OK
    if config_vars['test_issue'] == False:
        watchdog_obj.dec_watchdog_count()

    # check if we need to reboot (and that it's time to reboot)
    if config_vars['unit_bouncer']:
        bouncer_obj.check_for_bounce()


def run():
    main()

###############################################################################
# End main
###############################################################################
if __name__ == "__main__":
    main()