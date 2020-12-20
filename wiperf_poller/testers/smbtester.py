'''
A simple class to perform an network Smb copy and return a number of
result characteristics
'''

import time
import re
import subprocess
from sys import stderr
from wiperf_poller.helpers.os_cmds import SMB_CP,SMB_MOUNT,LS_CMD,UMOUNT_CMD
from wiperf_poller.helpers.route import inject_test_traffic_static_route

class SmbTester(object):
    '''
    A class to perform an SMB copy from a host - a basic wrapper around a CLI copy and mount command
    '''

    def __init__(self, file_logger, platform="rpi"):

        self.platform = platform
        self.file_logger = file_logger
        self.host = ''
        self.filename = ''
        self.username = ''
        self.password = ''
        self.path = ''
        self.test_time = ''
        self.time_to_transfer = ''
        self.mount_point = '/tmp/share'

    def smb_copy(self, host, filename, path, username, password,smb_timeout=1):
        '''
        This function will run mount a SMB volume and copy a file from it to the local 
        directory, time and transfer rate will be calculated 

        If the Smb fails, a False condition is returned with no further
        information. If the Smb succeeds, the following dictionary is returned:

        {   'host': self.host,
            'filename': self.filename,
            'path': self.path,
            'test_time': self.test_time,
        '''

        self.host = host
        self.filename=filename

        self.file_logger.debug("Smb mount: " + str(host) + " share " + str(path))

        # SMB mount the remote volume
        try:
            self.file_logger.info("Mounting remote volume...")
            #TODO: Need existing dir to mount to - /tmp/share does not exist by default
            cmd_string = "{} //{}{} {} -o user={},pass={}".format(SMB_MOUNT,host,path,self.mount_point,username,password)
            smb_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error = "Hit an error with SMB mount {} : {}".format(str(host), str(output))
            self.file_logger.error(error)

            # Things have gone bad - we just return a false status
            return False

        self.file_logger.debug("SMB command output:")
        self.file_logger.debug(smb_output)

        # Copy file to the SMB mounted volume
        self.file_logger.debug("SMB copy: " + str(filename)) 
        try:
            self.file_logger.info("Copying file to mounted volume...")
            cmd_string = "{} -f {}/{} ~/.".format(SMB_CP, self.mount_point, filename)

            # time the file transfer
            start_time= time.time()
            smb_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
            end_time=time.time()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error = "Hit an error with SMB copy {} : {}".format(str(host), str(output))
            self.file_logger.error(error)
        
        # Unmount the volume
        try:
            self.file_logger.info("Unmounting volume...")
            cmd_string = "{} {} ".format(UMOUNT_CMD, self.mount_point)
            smb_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error = "Hit an error when unmounting volume {} : {}".format(str(host), str(output))
            self.file_logger.error(error)
            stderr.write(str(error))
            # Things have gone bad - we just return a false status
            return False

        # Perform various calcs prior to returning results
        self.time_to_transfer = end_time-start_time

        cmd_string = "{} -l ~/{} ".format(LS_CMD,filename)
        smb_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
        byte=int(smb_output[0].split()[4])

        self.transfert_rate= ((byte*8)/self.time_to_transfer)/1024/1024

        self.file_logger.info('smb_host: {}, filename {} Time to transfert: {} rate in Mbps {}'.format(
            self.host, self.filename,self.time_to_transfer, self.transfert_rate))

        return {
            'host': self.host,
            'filename': self.filename,
            'Time to Transfer': self.time_to_transfer,
            'rate':self.transfert_rate}

    def run_tests(self, status_file_obj, config_vars, adapter, check_correct_mode_interface, exporter_obj, watchd):

        self.file_logger.info("Starting SMB test...")
        status_file_obj.write_status_file("SMB tests")

        username = config_vars['smb_user']
        password = config_vars['smb_password']

        # define column headers for CSV
        column_headers = ['time', 'smb_index', 'smb_host', 'filename','file_size', 'transfer_time', 'avg_mbps']
        
        tests_passed = True

        delete_file = True
        all_tests_fail = True
        results_dict = {}

        for smb_index in range(1,6):

            # bail if we have had previous test issues
            if config_vars['test_issue'] == True:
                self.file_logger.error("As we had previous issues, bypassing SMB tests.")
                break

            smb_host = config_vars['smb_host'+ str(smb_index)]
            server_hostname = smb_host

            if smb_host == '':
                continue

            filename = config_vars['smb_filename'+ str(smb_index)]
            path = config_vars['smb_path'+ str(smb_index)]

            # Check we have the correct route to the host under test
            if not check_correct_mode_interface(server_hostname, config_vars, self.file_logger):

                # if route looks wrong, try to fix it
                self.file_logger.warning("Unable to run SMB test to {} as route to destination not over correct interface...injecting static route".format(server_hostname))

                if not inject_test_traffic_static_route(server_hostname, config_vars, self.file_logger):

                    # route injection appears to have failed
                    self.file_logger.error("Unable to run SMB test to {} as route to destination not over correct interface...bypassing test".format(server_hostname))
                    config_vars['test_issue'] = True
                    config_vars['test_issue_descr'] = "SMB test failure (routing issue)"
                    tests_passed = False
                    break               

            smb_result=self.smb_copy(smb_host,filename,path,username,password, 1)
            
            # Send SMB results to exporter
            if smb_result:
                results_dict['time'] = int(time.time())
                results_dict['smb_index'] = smb_index
                results_dict['smb_host'] = smb_result['host']
                results_dict['filename'] = smb_result['filename']
                results_dict['smb_time'] = smb_result['Time to Transfer']
                results_dict['smb_Rate'] = smb_result['rate']
                # dump the results
                data_file = config_vars['smb_data_file']
                test_name = "SMB"
                if exporter_obj.send_results(config_vars, results_dict, column_headers, data_file, test_name, self.file_logger, delete_data_file=delete_file):
                    self.file_logger.info("SMB test ended.")
                else:
                    self.file_logger.error("Issue sending SMB results.")
                    tests_passed = False

                # Make sure we don't delete data file next time around
                delete_file = False

                self.file_logger.debug("Main: SMB test results:")
                self.file_logger.debug(smb_result)
                
                # signal that at least one test passed
                all_tests_fail = False

            else:
                self.file_logger.error("SMB test failed.")
                tests_passed = False
            
        # if all tests fail, and there are more than 2 tests, signal a possible issue
        if all_tests_fail and (smb_index > 1):
            self.file_logger.error("Looks like quite a few SMB tests failed, incrementing watchdog.")
            watchd.inc_watchdog_count()
        
        return tests_passed

    def get_host(self):
        ''' Get host name/address '''
        return self.host