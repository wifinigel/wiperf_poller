import speedtest
import sys
import time
import subprocess
import json
from wiperf_poller.helpers.os_cmds import LIBRESPEED_CMD
from wiperf_poller.helpers.timefunc import get_timestamp
from wiperf_poller.helpers.viabilitychecker import TestViabilityChecker

class Speedtester():
    """
    Class to implement speedtest server tests for wiperf
    """

    def __init__(self, file_logger, config_vars, resolve_name, adapter_obj):

        self.file_logger = file_logger
        self.config_vars = config_vars
        self.test_name = "Speedtest"
        self.speedtest_data_file = config_vars['speedtest_data_file']
        self.http_proxy = config_vars['http_proxy']
        self.https_proxy = config_vars['https_proxy']
        self.no_proxy = config_vars['no_proxy']
        
        self.resolve_name = resolve_name
        self.adapter_obj = adapter_obj

        # ipv4
        self.adapter_ip_ipv4 = self.adapter_obj.get_adapter_ipv4_ip()
        self.wan_target_ipv4 = config_vars['connectivity_lookup']

        # ipv6
        self.adapter_ip_ipv6 = self.adapter_obj.get_adapter_ipv6_ip()
        self.wan_target_ipv6 = config_vars['connectivity_lookup_ipv6']
           

    def librespeed_run(self, target_index, target_name, server_id='', args='', ip_ver="ipv4", DEBUG=False):
        """
        This function runs the librespeed speedtest and returns the result
        as a dictionary: 
            {   time = test_time (int)
                target_num = target_num (int)
                target_name = target_name (str)
                download_rate_mbps = download_rate_mbps (float)
                upload_rate_mbps = upload_rate_mbps (float)
                ping_time = ping_time (int)
                server_name = server_name (str)
                mbytes_sent = mbytes_sent (float)
                mbytes_received = mbytes_received (float)
                latency_ms = latency_ms (same as ping_time value - float)
                jitter_ms = jitter (int)
                client_ip = client_ip_add (str)
                provider = provider_name (str - always Librespeed)
            }

        Speedtest result format (Librespeed):
            {   
                "timestamp":"2020-12-29T05:48:10.143697357Z",
                "server":{
                    "name":"Frankfurt, Germany (Clouvider)",
                    "url":"http://fra.speedtest.clouvider.net/backend"
                },
                "client":{
                    "ip":"81.111.152.68",
                    "hostname":"cpc82729-staf9-2-0-cust67.3-1.cable.virginm.net",
                    "city":"Stoke-on-Trent",
                    "region":"England",
                    "country":"GB",
                    "loc":"53.0042,-2.1854",
                    "org":"AS5089 Virgin Media Limited",
                    "postal":"ST4",
                    "timezone":"Europe/London"
                },
                "bytes_sent":21037056,
                "bytes_received":58813742,
                "ping":33.72727272727273,
                "jitter":2.51,
                "upload":10.79,
                "download":30.16,
                "share":""
            }

        """
        # check command exists
        if not LIBRESPEED_CMD:
            self.file_logger.error("Librespeed-cli command does not appear to be installed, unable to perform test.")
            return False
        
        # define ipv4/v6 test choice
        librespeed_ip_ver = '--ipv4'
        if ip_ver == 'ipv6': librespeed_ip_ver = '--ipv6'

        # define command to run
        cmd = "{} {} --json".format(LIBRESPEED_CMD, librespeed_ip_ver)

        if server_id:
            cmd += " --server {}".format(server_id)
        
        if args:
            cmd += " {}".format(args)

        self.file_logger.debug("Librespeed command: {}".format(cmd))
        
        # run librespeed command
        try:
            speedtest_info = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True).decode()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error_descr = "Issue running librespeed speedtest command: {}".format(output)

            self.file_logger.error("{}".format(error_descr))
            return False

        self.file_logger.debug("Librespeed returned info: {}".format(speedtest_info))

        # extract data from JSON string
        results_dict = {}
        if speedtest_info:
            results_dict = json.loads(speedtest_info)
        else:
            self.file_logger.error("No data returned by Librespeed speedtest - returning error")
            return False

        if not results_dict:
            self.file_logger.error("JSON decode of librespeed results failed - returning error")
            return False
        
        test_time = get_timestamp(self.config_vars)
        target_index = int(target_index)
        download_rate_mbps = round(float(results_dict['download']), 2)
        upload_rate_mbps = round(float(results_dict['upload']), 2)
        ping_time = int(results_dict['ping'])
        server_name = str(results_dict['server']['name'])
        mbytes_sent = round(int(results_dict['bytes_sent'])/1024000, 2)
        mbytes_received = round(int(results_dict['bytes_received'])/1024000, 2)
        latency_ms = int(results_dict['ping'])
        jitter_ms = int(results_dict['jitter'])
        client_ip = str(results_dict['client']['ip'])
        provider = 'Librespeed'

        results_dict = {'time': test_time, 'target_index': target_index, 'target_name': target_name, 'ping_time': ping_time, 'download_rate_mbps': download_rate_mbps, 'upload_rate_mbps': upload_rate_mbps, 
            'server_name': server_name, 'mbytes_sent': mbytes_sent, 'mbytes_received': mbytes_received, 'latency_ms': latency_ms, 
            'jitter_ms': jitter_ms, 'client_ip': client_ip, 'provider': provider}

        self.file_logger.info(results_dict)

        return results_dict

    def ooklaspeedtest(self, target_index, target_name, server_id='', ip_ver="ipv4", DEBUG=False):
        '''
        This function runs the ookla speedtest and returns the result
        as a dictionary: 
            {   time = timestamp (int)
                target_name = target_name (str)
                download_rate_mbps = download_rate_mbps (float)
                upload_rate_mbps = upload_rate_mbps (float)
                ping_time = ping_time (int)
                server_name = server_name (str)
                mbytes_sent = mbytes_sent (float)
                mbytes_received = mbytes_received (float)
                latency_ms = latency_ms (same as ping_time value - float)
                jitter_ms = jitter (int)
                client_ip = client_ip_add (str)
                provider = provider_name (str - always Ookla)
            }
        
        Speedtest results format (Ookla):
        {
            'download': 29471546.96131429, 
            'upload': 10066173.96792112, 
            'ping': 34.035, 
            'server': {
                'url': 'http://speedtest-net5.rapidswitch.co.uk:8080/speedtest/upload.php', 
                'lat': '52.6369', 
                'lon': '-1.1398', 
                'name': 'Leicester', 
                'country': 'United Kingdom', 
                'cc': 'GB', 
                'sponsor': 'Iomart', 
                'id': '29080', 
                'host': 'speedtest-net5.rapidswitch.co.uk:8080', 
                'd': 68.38417645961746, 
                'latency': 34.035
            }, 
            'timestamp': '2020-12-29T06:45:22.334398Z', 
            'bytes_sent': 13393920, 
            'bytes_received': 37314032, 
            'share': None, 
            'client': {
                'ip': '81.111.152.68', 
                'lat': '52.8052', 
                'lon': '-2.1164', 
                'isp': 'Virgin Media', 
                'isprating': '3.7', 
                'rating': '0', 
                'ispdlavg': '0', 
                'ispulavg': '0', 
                'loggedin': '0', 
                'country': 'GB'
            }
        }

        Speedtest server list format (dict):
        19079.416816052293: [{'cc': 'NZ',
                        'country': 'New Zealand',
                        'd': 19079.416816052293,
                        'host': 'speed3.snap.net.nz:8080',
                        'id': '6056',
                        'lat': '-45.8667',
                        'lon': '170.5000',
                        'name': 'Dunedin',
                        'sponsor': '2degrees',
                        'url': 'http://speed3.snap.net.nz/speedtest/upload.php',
                        'url2': 'http://speed-dud.snap.net.nz/speedtest/upload.php'},
                        {'cc': 'NZ',
                        'country': 'New Zealand',
                        'd': 19079.416816052293,
                        'host': 'speedtest.wic.co.nz:8080',
                        'id': '5482',
                        'lat': '-45.8667',
                        'lon': '170.5000',
                        'name': 'Dunedin',
                        'sponsor': 'WIC NZ Ltd',
                        'url': 'http://speedtest.wic.co.nz/speedtest/upload.php',
                        'url2': 'http://speedtest.wickednetworks.co.nz/speedtest/upload.php'},
                        {'cc': 'NZ',
                        'country': 'New Zealand',
                        'd': 19079.416816052293,
                        'host': 'speedtest.unifone.net.nz:8080',
                        'id': '12037',
                        'lat': '-45.8667',
                        'lon': '170.5000',
                        'name': 'Dunedin',
                        'sponsor': 'Unifone NZ LTD',
                        'url': 'http://speedtest.unifone.net.nz/speedtest/upload.php'}]
        '''

        # bind interface to ensure chosen ipv4/v6 test performed
        if ip_ver == 'ipv6': 
            adapter_ip = self.adapter_obj.get_adapter_ipv6_ip()
        elif ip_ver == 'ipv4': 
            adapter_ip = self.adapter_obj.get_adapter_ipv4_ip()
        else:
            raise ValueError("Unknown version type in speedtest ver choice: {}".format(ip_ver))

        # perform Speedtest
        try:
            st = speedtest.Speedtest(source_address=adapter_ip)
            #st = speedtest.Speedtest()
        except Exception as error:
            self.file_logger.error("Speedtest error: {}".format(error))
            return False
        # check if we have specific target server
        if server_id:
            self.file_logger.info("Speedtest info: specific server ID provided for test: {}".format(str(server_id)))
            try:
                st.get_servers(servers=[server_id])
            except Exception as error:
                self.file_logger.error("Speedtest error: unable to get details of specified server: {}, reason: {}".format(
                    str(server_id), error))
                return False
        else:
            # get best server (try 3 times in case of comms issue)
            get_server_error = False
            for c in range(1, 4):
                try:
                    st.get_best_server()
                    get_server_error = False
                    break
                except Exception as error:
                    self.file_logger.error("Speedtest issue: get best server attempt #{}".format(c))
                    get_server_error = "Speedtest error: unable to get best server, reason: {}".format(error)
            
            if get_server_error:
                self.file_logger.error(get_server_error)
                return False

        # run download test
        try:
            st.download()
        except Exception as error:
            self.file_logger.error("Download test error: {}".format(error))
            return False

        try:
            st.upload(pre_allocate=False)
        except Exception as error:
            self.file_logger.error("Upload test error: {}".format(error))
            return False

        results_dict = st.results.dict()

        test_time = get_timestamp(self.config_vars)
        target_index = int(target_index)
        download_rate_mbps = round(float(results_dict['download'])/1024000, 2)
        upload_rate_mbps = round(float(results_dict['upload'])/1024000, 2)
        ping_time = int(results_dict['ping'])
        server_name = str(results_dict['server']['host'])
        mbytes_sent = round(int(results_dict['bytes_sent'])/1024000, 2)
        mbytes_received = round(int(results_dict['bytes_received'])/1024000, 2)
        latency_ms = int(results_dict['ping'])
        jitter_ms = None
        client_ip = str(results_dict['client']['ip'])
        provider = 'Ookla'

        results_dict = {'time': test_time, 'target_index': target_index, 'target_name': target_name, 'ping_time': ping_time, 'download_rate_mbps': download_rate_mbps, 'upload_rate_mbps': upload_rate_mbps, 'server_name': server_name, 
            'mbytes_sent': mbytes_sent, 'mbytes_received': mbytes_received, 'latency_ms': latency_ms, 'jitter_ms': jitter_ms, 'client_ip': client_ip,
            'provider': provider}

        self.file_logger.info(results_dict)

        return results_dict


    def run_tests(self, status_file_obj, check_correct_mode_interface, config_vars, exporter_obj, lockf_obj):

        self.file_logger.info("Starting speedtest(s)...")
        status_file_obj.write_status_file("speedtest")

        num_st_targets = int(config_vars['speedtest_targets_count']) + 1

        for target_num in range(1, num_st_targets):
            target_name = config_vars['st_name_{}'.format(target_num)]
            target_ip_ver = config_vars['st_ip_ver_{}'.format(target_num)]
            target_provider = config_vars['st_provider_{}'.format(target_num)]
            target_server_id = config_vars['st_server_id_{}'.format(target_num)]
            target_librespeed_args = config_vars['st_librespeed_args_{}'.format(target_num)]

            wan_target = self.wan_target_ipv4
            if target_ip_ver == "ipv6":
                wan_target = self.wan_target_ipv6
            
            # check we can hit the WAN
            wan_target = self.resolve_name(wan_target, self.file_logger)
            if not wan_target:
                self.file_logger.error("  Unable to resolve WAN target IP, will not be run ({})".format(wan_target))
                continue

             # check if test to host is viable (based on probe ipv4/v6 support)
            checker = TestViabilityChecker(config_vars, self.file_logger)
            if not checker.check_test_host_viable(wan_target, target_ip_ver):
                self.file_logger.error("  Speedtest not viable, will not be run (WAN target: {})".format(wan_target))
                continue

            if not check_correct_mode_interface(wan_target, config_vars, self.file_logger):
                self.file_logger.error("Unable to run Speedtest(s) as route to Internet not correct interface for more - we have a routing issue of some type.")
                config_vars['test_issue'] += 1
                config_vars['test_issue_descr'] = "Speedtest test failure - no route to WAN({})".format(target_name)
                continue

            # get adapter ip addr
            adapter_ip = self.adapter_ip_ipv4
            if target_ip_ver == "ipv6":
                adapter_ip = self.adapter_ip_ipv6
            
            if not adapter_ip:
                self.file_logger.error("Unable to run Speedtest test interface has no valid IP address")
                config_vars['test_issue'] += 1
                config_vars['test_issue_descr'] = "Speedtest test failure - no interface IP address ({})".format(target_name)
                continue

            self.file_logger.info("!!! Speedtest #{} of {} in progress....please wait.".format(target_num, num_st_targets - 1))

            # speedtest returns false if there are any issues
            speedtest_results = {}

            if target_provider == 'ookla':
                self.file_logger.debug("Running Ookla speedtest.")
                speedtest_results = self.ooklaspeedtest(target_num, target_name, target_server_id)
                
            elif target_provider == 'librespeed':
                self.file_logger.debug("Running Librespeed speedtest.")
                speedtest_results = self.librespeed_run(target_num, target_name, server_id=target_server_id, args=target_librespeed_args)

            else:
                self.file_logger.error("Unknown speedtest provider: {}".format(target_provider))
                continue

            if speedtest_results:

                self.file_logger.debug("Main: Speedtest results:")
                self.file_logger.debug(speedtest_results)

                # define column headers
                column_headers = list(speedtest_results.keys())

                self.file_logger.info("Speedtest ended.\n")

                # dump the results
                if exporter_obj.send_results(config_vars, speedtest_results, column_headers, self.speedtest_data_file, self.test_name, self.file_logger):
                    self.file_logger.info("Speedtest results sent OK.")
                    continue
                else:
                    #TODO: graceful failure?
                    self.file_logger.error("Error sending speedtest results. Exiting")
                    lockf_obj.delete_lock_file()
                    sys.exit()
            else:
                self.file_logger.error("Error running speedtest #{} - check logs for info.".format(target_num))
                continue
        
        return True

            
