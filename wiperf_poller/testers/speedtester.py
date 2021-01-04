import speedtest
import sys
import time
import subprocess
import json
from wiperf_poller.helpers.os_cmds import LIBRESPEED_CMD
from wiperf_poller.helpers.timefunc import get_timestamp

class Speedtester(object):
    """
    Class to implement speedtest server tests for wiperf
    """

    def __init__(self, file_logger, config_vars, platform):

        self.platform = platform
        self.file_logger = file_logger
        self.config_vars = config_vars

    def librespeed(self, server_id='', args='', DEBUG=False):
        """
        This function runs the ookla speedtest and returns the result
        as a dictionary: 
            {   download_rate_mbps = download_rate_mbps (float)
                upload_rate_mbps = upload_rate_mbps (float)
                ping_time = ping_time (int)
                server_name = server_name (str)
                mbytes_sent = mbytes_sent (float)
                mbytes_received = mbytes_received (float)
                latency_ms = latency_ms (same as ping_time value - float)
                jitter_ms = jitter (int)
            }

        Speedtest result format:
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
        
        # define command to run
        cmd = "{} --json".format(LIBRESPEED_CMD)

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

        self.file_logger.info('time: {}, ping_time: {}, download_rate_mbps: {}, upload_rate_mbps: {}, server_name: {}, mbytes_sent: {},  \
mbytes_received: {}, latency_ms: {}, jitter_ms: {}, client_ip: {}, provider: {}'.format(
            test_time, ping_time, download_rate_mbps, upload_rate_mbps, server_name, mbytes_sent, mbytes_received, latency_ms, jitter_ms, client_ip, provider))

        return {'time': test_time, 'ping_time': ping_time, 'download_rate_mbps': download_rate_mbps, 'upload_rate_mbps': upload_rate_mbps, 
            'server_name': server_name, 'mbytes_sent': mbytes_sent, 'mbytes_received': mbytes_received, 'latency_ms': latency_ms, 
            'jitter_ms': jitter_ms, 'client_ip': client_ip, 'provider': provider}

    def ooklaspeedtest(self, server_id='', DEBUG=False):
        '''
        This function runs the ookla speedtest and returns the result
        as a dictionary: 
            {   download_rate_mbps = download_rate_mbps (float)
                upload_rate_mbps = upload_rate_mbps (float)
                ping_time = ping_time (int)
                server_name = server_name (str)
                mbytes_sent = mbytes_sent (float)
                mbytes_received = mbytes_received (float)
                latency_ms = latency_ms (same as ping_time value - float)
                jitter_ms = jitter (int)
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

        # perform Speedtest
        try:
            st = speedtest.Speedtest()
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
            try:
                st.get_best_server()
            except Exception as error:
                self.file_logger.error("Speedtest error: unable to get best server, reason: {}".format(error))
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

        self.file_logger.info( 'time: {}, ping_time: {}, download_rate_mbps: {}, upload_rate_mbps: {}, server_name: {}, mbytes_sent: {},  \
mbytes_received: {}, latency_ms: {}, jitter_ms: {}, client_ip: {}, provider: {}'.format(
            test_time, ping_time, download_rate_mbps, upload_rate_mbps, server_name, mbytes_sent, mbytes_received, latency_ms, jitter_ms, client_ip, provider))

        return {'time': test_time, 'ping_time': ping_time, 'download_rate_mbps': download_rate_mbps, 'upload_rate_mbps': upload_rate_mbps, 'server_name': server_name, 
            'mbytes_sent': mbytes_sent, 'mbytes_received': mbytes_received, 'latency_ms': latency_ms, 'jitter_ms': jitter_ms, 'client_ip': client_ip,
            'provider': provider}


    def run_tests(self, status_file_obj, check_correct_mode_interface, config_vars, exporter_obj, lockf_obj):

        self.file_logger.info("Starting speedtest ({})...".format(config_vars['provider']))
        status_file_obj.write_status_file("speedtest")

        if check_correct_mode_interface('8.8.8.8', config_vars, self.file_logger):

            self.file_logger.info("Speedtest in progress....please wait.")

            # speedtest returns false if there are any issues
            speedtest_results = {}

            if config_vars['provider'] == 'ookla':
                self.file_logger.debug("Running Ookla speedtest.")
                speedtest_results = self.ooklaspeedtest(config_vars['server_id'])
                
            elif config_vars['provider'] == 'librespeed':
                self.file_logger.debug("Running Librespeed speedtest.")
                speedtest_results = self.librespeed(server_id=config_vars['server_id'], args=config_vars['librespeed_args'])

            else:
                self.file_logger.error("Unknown speedtest provider: {}".format(config_vars['provider']))
                return False

            if not speedtest_results == False:

                self.file_logger.debug("Main: Speedtest results:")
                self.file_logger.debug(speedtest_results)

                # define column headers for CSV
                column_headers = list(speedtest_results.keys())

                self.file_logger.info("Speedtest ended.")

                # dump the results
                data_file = config_vars['speedtest_data_file']
                test_name = "Speedtest"
                if exporter_obj.send_results(config_vars, speedtest_results, column_headers, data_file, test_name, self.file_logger):
                    self.file_logger.info("Speedtest results sent OK.")
                    return True
                else:
                    self.file_logger.error("Error sending speedtest results. Exiting")
                    lockf_obj.delete_lock_file()
                    sys.exit()
            else:
                self.file_logger.error("Error running speedtest - check logs for info.")
                return False
        else:
            self.file_logger.error("Unable to run Speedtest as route to Internet not correct interface for more - we have a routing issue of some type.")
            config_vars['test_issue'] = True
            config_vars['test_issue_descr'] = "Speedtest test failure"
            return False
