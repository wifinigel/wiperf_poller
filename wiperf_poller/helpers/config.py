"""
Read in config.ini file and return in a dictionary 

Returns:
    dict -- All wiperf config params
"""
import configparser
import os
import sys

def read_local_config(config_file, file_logger):
    '''
    Read in and return all config file variables. 
    '''
    config_vars = {}

    #check config file exists
    if not os.path.exists(config_file):
        file_logger.error("Cannot find config file: {} (exiting)".format(config_file))
        sys.exit()

    # create parser
    config = configparser.ConfigParser()
    config.read(config_file)   

    # TODO: add checking logic for values in config.ini file

    # Get general config params
    gen_sect = config['General']
    # Testing mode
    config_vars['probe_mode'] = gen_sect.get('probe_mode', 'wireless')
    # Eth interface name
    config_vars['eth_if'] = gen_sect.get('eth_if', 'eth0')
    # WLAN interface name
    config_vars['wlan_if'] = gen_sect.get('wlan_if', 'wlan0')
    # Interface name to send mgt traffic over (default wlan0)
    config_vars['mgt_if'] = gen_sect.get('mgt_if', 'wlan0')
    # Get platform architecture (derived automatically, not read from cfg file)
    config_vars['platform'] = 'rpi'
    if os.path.exists("/etc/wlanpi-state"):
        config_vars['platform'] = 'wlanpi'
    
    # data exporter type for results
    config_vars['exporter_type'] = gen_sect.get('exporter_type', 'splunk')
    config_vars['time_format'] = gen_sect.get('exporter_type', 'splunk')

    # report poller results after each cycle?
    config_vars['poller_reporting_enabled'] = gen_sect.get('poller_reporting_enabled', 'yes')

    # Results spooling enabled?
    config_vars['results_spool_enabled'] = gen_sect.get('results_spool_enabled', 'yes')
    # Max age of spooled results data (in minutes)
    config_vars['results_spool_max_age'] = gen_sect.get('results_spool_max_age', 30)
    # Dir for spool files
    config_vars['results_spool_dir'] = gen_sect.get('results_spool_dir', '/var/spool/wiperf')

    # local results caching enabled/disabled
    config_vars['cache_enabled'] = gen_sect.get('cache_enabled', 'no')
    # format of cache output data (csv/json)
    config_vars['cache_data_format'] = gen_sect.get('cache_data_format', 'csv')
    # root directory where cache data dumped
    config_vars['cache_root'] = gen_sect.get('cache_root', "/var/cache/wiperf")
    # retention period of cache files (in days)
    config_vars['cache_retention_period'] = gen_sect.get('cache_retention_period', 3)

    # log error polling error messages to mgt platform
    config_vars['error_messages_enabled'] = gen_sect.get('error_messages_enabled', 'yes')
    # max number of messages per poll
    config_vars['error_messages_limit'] = gen_sect.get('error_messages_limit', 5)
    

    ####### Splunk config ########
    # data transport
    config_vars['data_transport'] = gen_sect.get('data_transport', 'hec')
    # host where to send logs
    config_vars['splunk_host'] = gen_sect.get('splunk_host')
    # host port
    config_vars['splunk_port'] = gen_sect.get('splunk_port', '8088')
    # Splunk HEC token
    config_vars['splunk_token'] = gen_sect.get('splunk_token')
    ##############################

    ####### Influx1 config ########
    config_vars['influx_host'] = gen_sect.get('influx_host')
    config_vars['influx_port'] = gen_sect.get('influx_port', '8086')
    config_vars['influx_ssl'] = gen_sect.getboolean('influx_ssl', True)
    config_vars['influx_username'] = gen_sect.get('influx_username', 'admin')
    config_vars['influx_password'] = gen_sect.get('influx_password', 'admin')
    config_vars['influx_database'] = gen_sect.get('influx_database', 'wiperf')
    ##############################

    ####### Influx2 config ########
    config_vars['influx2_host'] = gen_sect.get('influx2_host')
    config_vars['influx2_port'] = gen_sect.get('influx2_port', '8086')
    config_vars['influx2_ssl'] = gen_sect.getboolean('influx2_ssl', True)
    config_vars['influx2_token'] = gen_sect.get('influx2_token', '')
    config_vars['influx2_bucket'] = gen_sect.get('influx2_bucket', '')
    config_vars['influx2_org'] = gen_sect.get('influx2_org', '')
    ##############################

    # convert host & port in to std global var
    if config_vars['exporter_type'] == 'splunk':
        config_vars['data_host'] = config_vars['splunk_host']
        config_vars['data_port'] = config_vars['splunk_port']
    elif config_vars['exporter_type'] == 'influxdb':
        config_vars['data_host'] = config_vars['influx_host']
        config_vars['data_port'] = config_vars['influx_port']
    elif config_vars['exporter_type'] == 'influxdb2':
        config_vars['data_host'] = config_vars['influx2_host']
        config_vars['data_port'] = config_vars['influx2_port']
    else:
        print("Unknown exporter type: {}".format(config_vars['exporter_type']))
        sys.exit()

    # test cycle timing parameters
    config_vars['test_interval'] = gen_sect.get('test_interval', '5')
    config_vars['test_offset'] = gen_sect.get('test_offset', '0')

    # connectivity DNS lookup - site used for initial DNS lookup when assessing if DNS working OK
    config_vars['connectivity_lookup'] = gen_sect.get('connectivity_lookup', 'google.com')


    # unit bouncer - hours at which we'd like to bounce unit (e.g. 00, 04, 08, 12, 16, 20)
    config_vars['unit_bouncer'] = gen_sect.get('unit_bouncer', False)

    # location
    config_vars['location'] = gen_sect.get('location', '')

    # debugging on/off for enhanced logging messages
    config_vars['debug'] = gen_sect.get('debug', 'off')

    # config server details (if supplied)
    config_vars['cfg_filename'] = gen_sect.get('cfg_filename', '')
    config_vars['cfg_url'] = gen_sect.get('cfg_url', '')
    config_vars['cfg_username'] = gen_sect.get('cfg_username', '')
    config_vars['cfg_password'] = gen_sect.get('cfg_password', '')
    config_vars['cfg_token'] = gen_sect.get('cfg_token', '')
    config_vars['cfg_refresh_interval'] = gen_sect.get('cfg_refresh_interval', 1800)

    # TODO: tidy this up
    # do some basic checks that mandatory fields are present
    """
    for field in ['data_host', 'splunk_token']:

        if config_vars[field] == '':
            err_msg = "No value in config.ini for field value: {} - exiting...".format(
                field)
            file_logger.error(err_msg)
            print(err_msg)
            sys.exit()
    """
    
    # Get network test config params
    network_sect = config['Network_Test']
    config_vars['network_data_file'] = network_sect.get('networkd', 'wiperf-network')

    # Get Speedtest config params
    speed_sect = config['Speedtest']
    config_vars['speedtest_enabled'] = speed_sect.get('enabled', 'no')
    config_vars['provider'] = speed_sect.get('provider', 'ookla')
    config_vars['server_id'] = speed_sect.get('server_id', '')
    config_vars['librespeed_args'] = speed_sect.get('librespeed_args', '')
    config_vars['speedtest_data_file'] = speed_sect.get('speedtest_data_file', 'wiperf-speedtest')
    config_vars['http_proxy'] = speed_sect.get('http_proxy', '')
    config_vars['https_proxy'] = speed_sect.get('https_proxy', '')
    config_vars['no_proxy'] = speed_sect.get('no_proxy', '')
    # set env vars if they are specified in the config file
    for proxy_var in ['http_proxy', 'https_proxy', 'no_proxy']:

        if config_vars[proxy_var]:
            os.environ[proxy_var] = config_vars[proxy_var]

    # Get Ping config params
    ping_sect = config['Ping_Test']
    config_vars['ping_enabled'] = ping_sect.get('enabled', 'no')
    config_vars['ping_targets_count'] = ping_sect.get('ping_targets_count', 5)
    config_vars['ping_data_file'] = ping_sect.get('ping_data_file', 'wiperf-ping')

    # get specifed number of targets (format: 'ping_host1')
    num_ping_targets = int(config_vars['ping_targets_count']) + 1

    for target_num in range(1, num_ping_targets):
        target_name = 'ping_host{}'.format(target_num)
        # format: config_vars["ping_host1"]
        config_vars[target_name] = ping_sect.get(target_name, '')

    config_vars['ping_count'] = ping_sect.get('ping_count', 10)
    config_vars['ping_timeout'] = ping_sect.get('ping_timeout', 1)
    config_vars['ping_interval'] = ping_sect.get('ping_interval', 0.2)

    # Get iperf3 tcp test params
    iperft_sect = config['Iperf3_tcp_test']
    config_vars['iperf3_tcp_enabled'] = iperft_sect.get('enabled', 'no')
    config_vars['iperf3_tcp_data_file'] = iperft_sect.get('iperf3_tcp_data_file', 'wiperf-iperf3-tcp')
    config_vars['iperf3_tcp_server_hostname'] = iperft_sect.get('server_hostname', '')
    config_vars['iperf3_tcp_port'] = iperft_sect.get('port', '')
    config_vars['iperf3_tcp_duration'] = iperft_sect.get('duration', '')

    # Get iperf3 udp test params
    iperfu_sect = config['Iperf3_udp_test']
    config_vars['iperf3_udp_enabled'] = iperfu_sect.get('enabled', 'no')
    config_vars['iperf3_udp_data_file'] = iperfu_sect.get('iperf3_udp_data_file', 'wiperf-iperf3-udp')
    config_vars['iperf3_udp_server_hostname'] = iperfu_sect.get('server_hostname', '')
    config_vars['iperf3_udp_port'] = iperfu_sect.get('port', '')
    config_vars['iperf3_udp_duration'] = iperfu_sect.get('duration', '')
    config_vars['iperf3_udp_bandwidth'] = iperfu_sect.get('bandwidth', '')

    # Get DNS test params
    dns_sect = config['DNS_test']
    config_vars['dns_test_enabled'] = dns_sect.get('enabled', 'no')
    config_vars['dns_targets_count'] = dns_sect.get('dns_targets_count', 5)
    config_vars['dns_data_file'] = dns_sect.get('dns_data_file', 'wiperf-dns')

    # get specifed number of targets (format: 'dns_target1')
    num_dns_targets = int(config_vars['dns_targets_count']) + 1

    for target_num in range(1, num_dns_targets):
        target_name = 'dns_target{}'.format(target_num)
        # format: config_vars["dns_target1"]
        config_vars[target_name] = dns_sect.get(target_name, '')

    # Get http test params
    http_sect = config['HTTP_test']
    config_vars['http_test_enabled'] = http_sect.get('enabled', 'no')
    config_vars['http_targets_count'] = http_sect.get('http_targets_count', 5)
    config_vars['http_data_file'] = http_sect.get('http_data_file', 'wiperf-http')

    # get specifed number of targets (format: 'http_target1')
    num_http_targets = int(config_vars['http_targets_count']) + 1

    for target_num in range(1, num_http_targets):
        target_name = 'http_target{}'.format(target_num)
        # format: config_vars["http_target1"]
        config_vars[target_name] = http_sect.get(target_name, '')

    # Get DHCP test params
    dhcp_sect = config['DHCP_test']
    config_vars['dhcp_test_enabled'] = dhcp_sect.get('enabled', 'no')
    config_vars['dhcp_test_mode'] = dhcp_sect.get('mode', 'passive')
    config_vars['dhcp_data_file'] = dhcp_sect.get('dhcp_data_file', 'wiperf-dhcp')

    # Get SMB test config params
    smb_sect = config['SMB_test']
    config_vars['smb_enabled'] = smb_sect.get('enabled', 'no')
    config_vars['smb_data_file'] = smb_sect.get('smb_data_file', 'wiperf-smb')
    config_vars['smb_targets_count'] = smb_sect.get('smb_targets_count', 5)

    config_vars['smb_global_username'] = smb_sect.get('smb_global_username', ' ')
    config_vars['smb_global_password'] = smb_sect.get('smb_global_password', ' ')

    # get specifed number of targets 
    # format: 
    #   config_vars['smb_host1'] = smb_sect.get('smb_host1', '')
    #   config_vars['smb_username1'] = smb_sect.get('smb_username1', ' ')
    #   config_vars['smb_password1'] = smb_sect.get('smb_password1', ' ')
    #   config_vars['smb_path1'] = smb_sect.get('smb_path1', '')
    #   config_vars['smb_filename1'] = smb_sect.get('smb_filename1','')
    
    num_smb_targets = int(config_vars['smb_targets_count']) + 1

    for target_num in range(1, num_smb_targets):

        host = 'smb_host{}'.format(target_num)
        # format: config_vars['smb_host1']
        config_vars[host] = smb_sect.get(host, '')

        username = 'smb_username{}'.format(target_num)
        # format: config_vars['smb_username1']
        config_vars[username] = smb_sect.get(username, '')

        password = 'smb_password{}'.format(target_num)
        # format: config_vars['smb_password1']
        config_vars[password] = smb_sect.get(password, '')

        path = 'smb_path{}'.format(target_num)
        # format: config_vars['smb_path1']
        config_vars[path] = smb_sect.get(path, '')

        filename = 'smb_filename{}'.format(target_num)
        # format: config_vars['smb_filename1']
        config_vars[filename] = smb_sect.get(filename, '')


    # Get Authentication test config params
    #auth_sect = config['Auth_test']
    #config_vars['auth_enabled'] = auth_sect.get('enabled', 'no')
    #config_vars['auth_data_file'] = auth_sect.get('auth_data_file', 'wiperf-auth')

    return config_vars