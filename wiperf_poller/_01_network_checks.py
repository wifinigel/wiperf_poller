from wiperf_poller.testers.networkconnectiontester import NetworkConnectionTester
from wiperf_poller.testers.mgtconnectiontester import MgtConnectionTester

def run_network_checks(file_logger, status_file_obj, config_vars, poll_obj, 
    watchdog_obj, lockf_obj, exporter_obj):

    #############################################
    # Run network checks
    #############################################
    # Note: test_issue flag not set by connection tests, as issues will result in process exit
    file_logger.info("####### Network testing path connection checks #######")

    status_file_obj.write_status_file("network check")

    wlan_if = config_vars['wlan_if']
    eth_if = config_vars['eth_if']
    mgt_if = config_vars['mgt_if']

    if config_vars['probe_mode'] == 'wireless':
        network_if = wlan_if
    else:
        network_if = eth_if
    
    file_logger.info("Checking {} connection is good...(layer 1/2 & routing for test traffic)".format(config_vars['probe_mode']))
    network_connection_obj = NetworkConnectionTester(file_logger, network_if, config_vars['probe_mode'])  
    network_connection_obj.run_tests(watchdog_obj, lockf_obj, config_vars, exporter_obj)

    file_logger.info("####### Network mgt path connection checks #######")

    file_logger.info("Checking mgt connection is good via interface {}...".format(mgt_if))
    mgt_connection_obj = MgtConnectionTester(config_vars, file_logger)
    mgt_connection_obj.check_mgt_connection(lockf_obj, watchdog_obj)

    return 'OK'
