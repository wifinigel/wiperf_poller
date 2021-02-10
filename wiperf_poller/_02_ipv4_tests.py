

def run_ipv4_tests(config_vars, file_logger, poll_obj, status_file_obj, exporter_obj, lockf_obj, adapter_obj, watchdog_obj, ip_ver="IPv4"):

    if ip_ver == "IPv4":
        from wiperf_poller.testers.dhcptester import DhcpTester
        from wiperf_poller.testers.dnstester import DnsTesterIpv4 as DnsTester
        from wiperf_poller.testers.httptester import HttpTesterIpv4 as HttpTester
        from wiperf_poller.testers.iperf3tester import IperfTesterIpv4  as IperfTester
        from wiperf_poller.testers.pingtester import PingTesterIpv4 as PingTester
        from wiperf_poller.testers.speedtester import SpeedtesterIpv4 as Speedtester
        from wiperf_poller.testers.smbtester import SmbTesterIpv4 as SmbTester
        from wiperf_poller.helpers.route import check_correct_mode_interface_ipv4 as check_correct_mode_interface
        from wiperf_poller.helpers.route import resolve_name_ipv4 as resolve_name
    else:
        from wiperf_poller.testers.ipv6.dhcptester_ipv6 import DhcpTester
        from wiperf_poller.testers.ipv6.dnstester_ipv6 import DnsTesterIpv6 as DnsTester
        from wiperf_poller.testers.ipv6.httptester_ipv6 import HttpTesterIpv6 as HttpTester
        from wiperf_poller.testers.ipv6.iperf3tester_ipv6 import IperfTesterIpv6  as IperfTester
        from wiperf_poller.testers.ipv6.pingtester_ipv6 import PingTesterIpv6 as PingTester
        from wiperf_poller.testers.ipv6.speedtester_ipv6 import SpeedtesterIpv6 as Speedtester
        from wiperf_poller.testers.ipv6.smbtester_ipv6 import SmbTesterIpv6 as SmbTester
        from wiperf_poller.helpers.ipv6.route_ipv6 import check_correct_mode_interface_ipv6 as check_correct_mode_interface
        from wiperf_poller.helpers.ipv6.route_ipv6 import resolve_name_ipv6 as resolve_name

    # copy ipv4 test configuration in to main config_vars dict from sub-key
    for key, value in config_vars['ipv4'].items():
        config_vars[key] = value


    #############################################
    # Run speedtest (if enabled)
    #############################################                                                                                                                                                                                                                      

    file_logger.info("########## speedtest ({}) ##########".format(ip_ver))
    if config_vars['speedtest_enabled'] == 'yes':

        speedtest_obj = Speedtester(file_logger, config_vars, resolve_name)
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
    file_logger.info("########## ping tests ({}) ##########".format(ip_ver))
    if config_vars['ping_enabled'] == 'yes' and config_vars['test_issue'] == False:

        # run ping test
        ping_obj = PingTester(file_logger)

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
    file_logger.info("########## dns tests ({}) ##########".format(ip_ver))
    if config_vars['dns_test_enabled'] == 'yes' and config_vars['test_issue'] == False:

        dns_obj = DnsTester(file_logger, config_vars)
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
    file_logger.info("########## http tests ({}) ##########".format(ip_ver))
    if config_vars['http_test_enabled'] == 'yes' and config_vars['test_issue'] == False:

        http_obj = HttpTester(file_logger)
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
    file_logger.info("########## iperf3 tcp test ({}) ##########".format(ip_ver))
    if config_vars['iperf3_tcp_enabled'] == 'yes' and config_vars['test_issue'] == False:

        iperf3_tcp_obj = IperfTester(file_logger)
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
    file_logger.info("########## iperf3 udp test ({}) ##########".format(ip_ver))
    if config_vars['iperf3_udp_enabled'] == 'yes' and config_vars['test_issue'] == False:

        iperf3_udp_obj = IperfTester(file_logger)
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
    file_logger.info("########## dhcp test ({}) ##########".format(ip_ver))
    if config_vars['dhcp_test_enabled'] == 'yes' and config_vars['test_issue'] == False:

        dhcp_obj = DhcpTester(file_logger, lockf_obj)
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
    # Run SMB renewal test (if enabled)
    #####################################
    file_logger.info("########## SMB test ({}) ##########".format(ip_ver))
    if config_vars['smb_enabled'] == 'yes' and config_vars['test_issue'] == False:

        smb_obj = SmbTester(file_logger)
        tests_passed = smb_obj.run_tests(status_file_obj, config_vars, adapter_obj, check_correct_mode_interface, exporter_obj, watchdog_obj)
        if tests_passed:
            poll_obj.smb('Completed')
        else:
            poll_obj.smb('Failure')

    else:
        if config_vars['test_issue'] == True:
            file_logger.info("Previous test failed: {}".format(config_vars['test_issue_descr']))
            poll_obj.smb('Not run')
        else:
            file_logger.info("smb test not enabled in config file, bypassing this test...")
            poll_obj.smb('Not enabled')
