#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import logging

# our local ...
from wiperf_poller.testers.speedtester import Speedtester
from wiperf_poller.testers.wirelessconnectiontester import WirelessConnectionTester
from wiperf_poller.testers.ethernetconnectiontester import EthernetConnectionTester
from wiperf_poller.testers.pingtester import PingTester
from wiperf_poller.testers.iperf3tester import IperfTester
from wiperf_poller.testers.dnstester import DnsTester
from wiperf_poller.testers.httptester import HttpTester
from wiperf_poller.testers.dhcptester import DhcpTester

from wiperf_poller.helpers.wirelessadapter import WirelessAdapter
from wiperf_poller.helpers.ethernetadapter import EthernetAdapter
from wiperf_poller.helpers.filelogger import FileLogger
from wiperf_poller.helpers.config import read_local_config
from wiperf_poller.helpers.bouncer import Bouncer
from wiperf_poller.helpers.remoteconfig import check_last_cfg_read
from wiperf_poller.helpers.route import check_correct_mode_interface
from wiperf_poller.helpers.statusfile import StatusFile
from wiperf_poller.helpers.lockfile import LockFile
from wiperf_poller.helpers.watchdog import Watchdog
from wiperf_poller.helpers.os_cmds import check_os_cmds
from wiperf_poller.helpers.poll_status import PollStatus 

from wiperf_poller.exporters.exportresults import ResultsExporter

config_file = "/etc/wiperf/config.ini"
log_file = "/var/log/wiperf_agent.log"
lock_file = '/tmp/wiperf_poller.lock'
status_file = '/tmp/wiperf_status.txt'
watchdog_file = '/tmp/wiperf_poller.watchdog'
bounce_file = '/tmp/wiperf_poller.bounce'
check_cfg_file = '/tmp/wiperf_poller.cfg'

# Enable debugs or create some dummy data for testing
DEBUG = 0
DUMMY_DATA = False # Speedtest data only

###################################
# File logger
###################################

# set up our error_log file & initialize
file_logger = FileLogger(log_file)
file_logger.info("*****************************************************")
file_logger.info(" Starting logging...")
file_logger.info("*****************************************************")

# Pull in our config.ini dict
(config_vars, config_obj) = read_local_config(config_file, file_logger)

# set logging to debug if debugging enabled
if DEBUG or (config_vars['debug'] == 'on'):
    file_logger.setLevel('DEBUG')
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

# exporter object
exporter_obj = ResultsExporter(file_logger, config_vars['platform'])

# adapter object
adapter_obj = ''
probe_mode = config_vars['probe_mode']
wlan_if = config_vars['wlan_if']
eth_if = config_vars['eth_if']
platform = config_vars['platform']

if probe_mode == "ethernet":
    adapter_obj = EthernetAdapter(eth_if, file_logger, platform=platform)
elif probe_mode == "wireless":
    adapter_obj = WirelessAdapter(wlan_if, file_logger, platform=platform)
else:
    file_logger.info("Unknown probe mode: {} (exiting)".format(probe_mode))

###############################################################################
# Main
###############################################################################
def main():

    global file_logger
    global config_vars
    global watchdog_file
    global config_file
    global check_cfg_file

    # if we have a config server specified, check to see if it's time
    # to pull the config
    file_logger.info("Checking if we use remote cfg file...")
    if config_vars['cfg_url']:
        
        # if able to get cfg file, re-read params in case updated
        if check_last_cfg_read(config_file, check_cfg_file, config_vars, file_logger):
            config_vars = read_local_config(config_file, file_logger)

    else:
        file_logger.info("No remote cfg file confgured...using current local ini file.")

    # create watchdog if doesn't exist
    watchdog_obj.create_watchdog()

    # check watchdog count...if higher than 3, time for a reboot
    watchdog_count = watchdog_obj.get_watchdog_count()
    if watchdog_count > 3:
        file_logger.error("Watchdog count exceeded...rebooting")
        bouncer_obj.reboot()

    ###################################
    # Check if script already running
    ###################################
    if lockf_obj.lock_file_exists():

        # read lock file contents & check how old timestamp is..
        file_logger.error("Existing lock file found...")
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

    # test issue flag - set if any tests hit major issues
    # to stall further testing
    config_vars['test_issue'] = False
    config_vars['test_issue_descr'] = ""

    # set up poll health obj
    poll_obj = PollStatus(config_vars, file_logger)
    poll_obj.probe_mode(probe_mode)
    poll_obj.mgt_if(config_vars['mgt_if'])
    
    #############################################
    # Run network checks
    #############################################
    # Note: test_issue flag not set by connection tests, as issues will result in process exit
    file_logger.info("########## Network connection checks ##########")
    connection_obj = ''

    status_file_obj.write_status_file("network check")

    if config_vars['probe_mode'] == 'ethernet':
        file_logger.info("Checking ethernet connection is good...(layer 1 &2)")
        connection_obj = EthernetConnectionTester(file_logger, eth_if, platform)
    else:
        file_logger.info("Checking wireless connection is good...(layer 1 &2)")
        connection_obj = WirelessConnectionTester(file_logger, wlan_if, platform)
    
    connection_obj.run_tests(watchdog_obj, lockf_obj, config_vars, exporter_obj)
    poll_obj.network('OK') 
    
    # update poll summary with IP
    poll_obj.ip(adapter_obj.get_adapter_ip())
 
    #############################################
    # Run speedtest (if enabled)
    #############################################                                                                                                                                                                                                                      

    file_logger.info("########## speedtest ##########")
    if config_vars['speedtest_enabled'] == 'yes':

        speedtest_obj = Speedtester(file_logger, platform)
        test_passed = speedtest_obj.run_tests(status_file_obj, check_correct_mode_interface, config_vars, exporter_obj, lockf_obj)

        if test_passed:
            poll_obj.speedtest('Completed')
        else:
            poll_obj.speedtest('Failure')
    else:
        file_logger.info("Speedtest not enabled in config file.")
        poll_obj.speedtest('Not enabled')

    #############################
    # Run ping test (if enabled)
    #############################
    file_logger.info("########## ping tests ##########")
    if config_vars['ping_enabled'] == 'yes' and config_vars['test_issue'] == False:

        # run ping test
        ping_obj = PingTester(file_logger, platform=platform)

        # run test
        tests_passed = ping_obj.run_tests(status_file_obj, config_vars, adapter_obj, check_correct_mode_interface, exporter_obj, watchdog_obj)

        if tests_passed:
            poll_obj.ping('Completed')
        else:
            poll_obj.ping('Failure')

    else:
        if config_vars['test_issue'] == True:
            file_logger.info("Previous test failed: {}".format(config_vars['test_issue_descr']))
            poll_obj.ping('Not run')
        else:
            file_logger.info("Ping test not enabled in config file, bypassing this test...")
            poll_obj.ping('Not enabled')

    ###################################
    # Run DNS lookup tests (if enabled)
    ###################################
    file_logger.info("########## dns tests ##########")
    if config_vars['dns_test_enabled'] == 'yes' and config_vars['test_issue'] == False:

        dns_obj = DnsTester(file_logger, platform=platform)
        tests_passed = dns_obj.run_tests(status_file_obj, config_vars, exporter_obj)

        if tests_passed:
            poll_obj.dns('Completed')
        else:
            poll_obj.dns('Failure')

    else:
        if config_vars['test_issue'] == True:
            file_logger.info("Previous test failed: {}".format(config_vars['test_issue_descr']))
            poll_obj.dns('Not run')
        else:
            file_logger.info("DNS test not enabled in config file, bypassing this test...")
            poll_obj.dns('Not enabled')

    #####################################
    # Run HTTP lookup tests (if enabled)
    #####################################
    file_logger.info("########## http tests ##########")
    if config_vars['http_test_enabled'] == 'yes' and config_vars['test_issue'] == False:

        http_obj = HttpTester(file_logger, platform=platform)
        tests_passed = http_obj.run_tests(status_file_obj, config_vars, exporter_obj, watchdog_obj, check_correct_mode_interface,)

        if tests_passed:
            poll_obj.http('Completed')
        else:
            poll_obj.http('Failure')

    else:
        if config_vars['test_issue'] == True:
            file_logger.info("Previous test failed: {}".format(config_vars['test_issue_descr']))
            poll_obj.http('Not run')
        else:
            file_logger.info("HTTP test not enabled in config file, bypassing this test...")
            poll_obj.http('Not enabled')
    
    ###################################
    # Run iperf3 tcp test (if enabled)
    ###################################
    file_logger.info("########## iperf3 tcp test ##########")
    if config_vars['iperf3_tcp_enabled'] == 'yes' and config_vars['test_issue'] == False:

        iperf3_tcp_obj = IperfTester(file_logger, platform)
        test_result = iperf3_tcp_obj.run_tcp_test(config_vars, status_file_obj, check_correct_mode_interface, exporter_obj)

        if test_result:
            poll_obj.iperf_tcp('Completed')
        else:
            poll_obj.iperf_tcp('Failed')

    else:
        if config_vars['test_issue'] == True:
            file_logger.info("Previous test failed: {}".format(config_vars['test_issue_descr']))
            poll_obj.iperf_tcp('Not run')
        else:
            file_logger.info("Iperf3 tcp test not enabled in config file, bypassing this test...")
            poll_obj.iperf_tcp('Not enabled')

    ###################################
    # Run iperf3 udp test (if enabled)
    ###################################
    file_logger.info("########## iperf3 udp test ##########")
    if config_vars['iperf3_udp_enabled'] == 'yes' and config_vars['test_issue'] == False:

        iperf3_udp_obj = IperfTester(file_logger, platform)
        test_result = iperf3_udp_obj.run_udp_test(config_vars, status_file_obj, check_correct_mode_interface, exporter_obj)

        if test_result:
            poll_obj.iperf_udp('Completed')
        else:
            poll_obj.iperf_udp('Failed')
    else:
        if config_vars['test_issue'] == True:
            file_logger.info("Previous test failed: {}".format(config_vars['test_issue_descr']))
            poll_obj.iperf_udp('Not run')
        else:
            file_logger.info("Iperf3 udp test not enabled in config file, bypassing this test...")
            poll_obj.iperf_udp('Not enabled')

    #####################################
    # Run DHCP renewal test (if enabled)
    #####################################
    file_logger.info("########## dhcp test ##########")
    if config_vars['dhcp_test_enabled'] == 'yes' and config_vars['test_issue'] == False:

        dhcp_obj = DhcpTester(file_logger, platform=platform)
        tests_passed = dhcp_obj.run_tests(status_file_obj, config_vars, exporter_obj)

        if tests_passed:
            poll_obj.dhcp('Completed')
        else:
            poll_obj.dhcp('Failure')

    else:
        if config_vars['test_issue'] == True:
            file_logger.info("Previous test failed: {}".format(config_vars['test_issue_descr']))
            poll_obj.dhcp('Not run')
        else:
            file_logger.info("DHCP test not enabled in config file, bypassing this test...")
            poll_obj.dhcp('Not enabled')

    #####################################
    # Tidy up before exit
    #####################################

    # get rid of log file
    status_file_obj.write_status_file("")
    lockf_obj.delete_lock_file()
    
    # dump poller status info
    poll_obj.dump()

    file_logger.info("########## end ##########")

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
