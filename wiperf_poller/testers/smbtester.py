'''
A simple class to perform an network Smb copy and return a number of
result characteristics
'''

import time
import re
import subprocess
from sys import stderr
from wiperf_poller.helpers.os_cmds import SMB_CP,SMB_MOUNT,LS_CMD,UMOUNT_CMD

class SmbTester(object):
    '''
    A class to perform a smb copy from a host - a basic wrapper around a CLI cp and mount command
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

    def Smb_copy(self, host, filename, path, username, password,Smb_timeout=1):
        '''
        This function will run mount a Smb volume and copy a file from it to the local directory, time and transfer rate will be calculated 

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

        # Execute the Smb mount
        try:
            cmd_string = "{} //{}{} /mnt/shares/share1 -o user={},pass=\'{}\'".format(SMB_MOUNT,host,path,username,password)
            print ("commande ",cmd_string)
            Smb_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error = "Hit an error when Smb mount {} : {}".format(str(host), str(output))
            self.file_logger.error(error)
            stderr.write(str(error))

            # Things have gone bad - we just return a false status
            return False

        self.file_logger.debug("Smb command output:")
        self.file_logger.debug(Smb_output)
        # Execute the cp mount
        self.file_logger.debug("Smb cp: " + str(filename)) 
        try:
            cmd_string = "{} -f /mnt/shares/share1/{} ~/.".format(SMB_CP,filename)
            print ("commande ",cmd_string)
            start_time= time.time()
            Smb_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
            end_time=time.time()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error = "Hit an error when Smb cp {} : {}".format(str(host), str(output))
            self.file_logger.error(error)
            stderr.write(str(error))
        try:
            cmd_string = "{} /mnt/shares/share1 ".format(UMOUNT_CMD)
            Smb_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            error = "Hit an error when Smb mount {} : {}".format(str(host), str(output))
            self.file_logger.error(error)
            stderr.write(str(error))
            # Things have gone bad - we just return a false status
            return False
        self.time_to_transfer = end_time-start_time
        cmd_string = "{} -l ~/{} ".format(LS_CMD,filename)
        print ("commande ",cmd_string)
        Smb_output = subprocess.check_output(cmd_string, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
        byte=int(Smb_output[0].split()[4])
        self.transfert_rate= ((byte*8)/self.time_to_transfer)/1024/1024
        self.file_logger.info('Smb_host: {}, filename {} Time to transfert: {} rate in Mbps {}'.format(
            self.host, self.filename,self.time_to_transfer, self.transfert_rate))
        return {
            'host': self.host,
            'filename': self.filename,
            'Time to Transfer': self.time_to_transfer,
            'rate':self.transfert_rate}

    def run_tests(self, status_file_obj, config_vars, adapter, check_correct_mode_interface, exporter_obj, watchd):

        self.file_logger.info("Starting Smb test...")
        status_file_obj.write_status_file("Smb tests")



        username = config_vars['SMB_user']
        password = config_vars['SMB_password']

        Smb_hosts={}
        Smb_filename={}
        Smb_path={}

        Smb_hosts[1] = config_vars['smb_host1']
        Smb_filename[1]=config_vars['smb_filename1']
        Smb_path[1]=config_vars['smb_path1']

        Smb_hosts[2] = config_vars['smb_host2']
        Smb_filename[2]=config_vars['smb_filename2']
        Smb_path[2]=config_vars['smb_path2']

        Smb_hosts[3] = config_vars['smb_host3']
        Smb_filename[3]=config_vars['smb_filename3']
        Smb_path[3]=config_vars['smb_path3']

        Smb_hosts[4] = config_vars['smb_host4']
        Smb_filename[4]=config_vars['smb_filename4']
        Smb_path[4]=config_vars['smb_path4']

        Smb_hosts[5] = config_vars['smb_host5']
        Smb_filename[5]=config_vars['smb_filename5']
        Smb_path[5]=config_vars['smb_path5']



        # define colum headers for CSV
        column_headers = ['time', 'Smb_index', 'Smb_host', 'File Name','File Size', 'Time to transfer',
                            'Avg Mbps']
        
        tests_passed = True

        Smb_index = 0
        delete_file = True
        all_tests_fail = True
        results_dict = {}

        Smb_index=0
        while Smb_index < 5:
            # bail if we have had DNS issues
            if config_vars['test_issue'] == True:
                self.file_logger.error("As we had previous issues, bypassing Smb tests.")
                break

            Smb_index += 1
            Smb_host=Smb_hosts[Smb_index]
            if Smb_host == '':
                continue
            else:
                filename=Smb_filename[Smb_index]
                path=Smb_path[Smb_index]
                # check tests will go over correct interface
                if check_correct_mode_interface(Smb_host, config_vars, self.file_logger):
                    Smb_result=self.Smb_copy(Smb_host,filename,path,username,password, 1)
                else:
                    self.file_logger.error(
                        "Unable to download file {} from {}".format(Smb_host,filename))
                    # we will break here if we have an issue as something bad has happened...don't want to run more tests
                    config_vars['test_issue'] = True
                    tests_passed = False
                    break

            # Smb results
            if Smb_result:
                results_dict['time'] = int(time.time())
                results_dict['Smb_index'] = Smb_index
                results_dict['Smb_host'] = Smb_result['host']
                results_dict['filename'] = Smb_result['filename']
                results_dict['Smb_time'] = Smb_result['Time to Transfer']
                results_dict['Smb_Rate'] = Smb_result['rate']
                # dump the results
                data_file = config_vars['SMB_data_file']
                test_name = "Smb"
                if exporter_obj.send_results(config_vars, results_dict, column_headers, data_file, test_name, self.file_logger, delete_data_file=delete_file):
                    self.file_logger.info("Smb test ended.")
                else:
                    self.file_logger.error("Issue sending Smb results.")
                    tests_passed = False

                # Make sure we don't delete data file next time around
                delete_file = False

                self.file_logger.debug("Main: Smb test results:")
                self.file_logger.debug(Smb_result)
                
                # signal that at least one test passed
                all_tests_fail = False

            else:
                self.file_logger.error("Smb test failed.")
                tests_passed = False
            
        # if all tests fail, and there are more than 2 tests, signal a possible issue
        if all_tests_fail and (Smb_index > 1):
            self.file_logger.error("Looks like quite a few Smbs failed, incrementing watchdog.")
            watchd.inc_watchdog_count()
        
        return tests_passed

    def get_host(self):
        ''' Get host name/address '''
        return self.host