from wiperf_poller._02_ipv4_tests import run_ipv4_tests

def run_ipv6_tests(config_vars, file_logger, poll_obj, status_file_obj, exporter_obj, lockf_obj, adapter_obj, watchdog_obj):

    # remove ipv4 test values (if exist)
    ipv4_keys = config_vars['ipv4'].keys()

    for key in config_vars['ipv4'].keys():
        if key in ipv4_keys:
            del config_vars[key]
    
    config_vars['ipv4'] = {}

    # copy ipv6 test configuration in to main config_vars dict from sub-key
    for key, value in config_vars['ipv6'].items():
        config_vars[key] = value

    # run tests
    run_ipv4_tests(config_vars, file_logger, poll_obj, status_file_obj, exporter_obj, lockf_obj, adapter_obj, watchdog_obj, ip_ver="IPv6")