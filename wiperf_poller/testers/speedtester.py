import speedtest
import sys
import time

class Speedtester(object):
    """
    Class to implement speedtest server tests for wiperf
    """

    def __init__(self, file_logger, platform):

        self.platform = platform
        self.file_logger = file_logger


    def ooklaspeedtest(self, server_id='', DEBUG=False):
        '''
        This function runs the actual speedtest and returns the result
        as a dictionary: 
            { 'ping_time':  ping_time,
            'download_rate': download_rate,
            'upload_rate': upload_rate,
            'server_name': server_name
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

        download_rate_mbps = round(float(results_dict['download'])/1024000, 2)
        upload_rate_mbps = round(float(results_dict['upload'])/1024000, 2)
        ping_time = int(results_dict['ping'])
        server_name = str(results_dict['server']['host'])
        mbytes_sent = round(int(results_dict['bytes_sent'])/1024000, 2)
        mbytes_received = round(int(results_dict['bytes_received'])/1024000, 2)
        latency_ms = int(results_dict['ping'])
        jitter_ms = None

        self.file_logger.info('ping_time: {}, download_rate_mbps: {}, upload_rate_mbps: {}, server_name: {}, mbytes_sent: {}, mbytes_received: {}, latency_ms: {}, jitter_ms: {}'.format(
            ping_time, download_rate_mbps, upload_rate_mbps, server_name, mbytes_sent, mbytes_received, latency_ms, jitter_ms))

        return {'ping_time': ping_time, 'download_rate_mbps': download_rate_mbps, 'upload_rate_mbps': upload_rate_mbps, 'server_name': server_name, 
            'mbytes_sent': mbytes_sent, 'mbytes_received': mbytes_received, 'latency_ms': latency_ms, 'jitter_ms': jitter_ms}


    def run_tests(self, status_file_obj, check_correct_mode_interface, config_vars, exporter_obj, lockf_obj):

        column_headers = [ 'time', 'server_name', 'ping_time', 'download_rate_mbps', 'upload_rate_mbps', 
            'mbytes_sent', 'mbytes_received', 'latency_ms', 'jitter_ms' ]

        self.file_logger.info("Starting speedtest...")
        status_file_obj.write_status_file("speedtest")

        if check_correct_mode_interface('8.8.8.8', config_vars, self.file_logger):

            self.file_logger.info("Speedtest in progress....please wait.")

            # speedtest returns false if there are any issues
            speedtest_results = self.ooklaspeedtest(config_vars['server_id'])

            if not speedtest_results == False:

                self.file_logger.debug("Main: Speedtest results:")
                self.file_logger.debug(speedtest_results)

                # speedtest results - add timestamp
                speedtest_results['time'] = int(time.time())

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
