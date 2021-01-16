"""
spoolexporter.py

A class to spool results data in to a local folder during loss of
connectivity to mgt platform. Results will be uploaded once
connectivity is restored.

Implementation details:

1. Spooler files will be in jsonformat
2. Spooled files are stored under folder /var/spool/wiperf
3. One file will be created for each test performed (it will be date/timestamped)
5. The following config parameters will be specified in config .ini:
    a. Spooling enabled/disabled
    b. Retention period for files, in minutes (default = 60)
    c. Hidden parameter : 'spool_dir_root' which defaults to /var/spool/wiperf when not supplied
"""

import json
import os
import shutil
import sys
from datetime import datetime, timedelta
from wiperf_poller.helpers.timefunc import get_timestamp, time_synced

class SpoolExporter(object):
    """
    A class to spool results data in to a local folder during loss of
    connectivity to mgt platform. Results will be uploaded once
    connectivity is restored.
    """

    def __init__(self, config_vars, file_logger):

        self.file_logger = file_logger
        self.spool_enabled = config_vars['results_spool_enabled']
        self.spool_dir_root = config_vars['results_spool_dir']
        self.spool_max_age = int(config_vars['results_spool_max_age']) # time in minutes
        self.config_vars = config_vars

        self.spool_checks_completed = False
    
    def check_spool_dir_exists(self):
        """
        Check if root cache dir exists (by default /var/spool/wiperf)
        """
        if os.path.exists(self.spool_dir_root) and os.path.isdir(self.spool_dir_root):
            return True

        return False


    def _create_spool_dir(self):
        """
        Create spool root dir
        """

        try: 
            os.makedirs(self.spool_dir_root, exist_ok = True) 
            self.file_logger.debug("Created spooling root dir: {}".format(self.spool_dir_root))
        except OSError as e: 
            self.file_logger.error("Cannot create spooling root dir: {} ({})".format(self.spool_dir_root, e.strerror)) 
            return False
        return True
    
    def list_spool_files(self):

        # list files in spool dir (sorted by name a->z)
        spool_files = os.listdir(self.spool_dir_root)
        spool_files.sort()

        return spool_files

    
    def prune_old_files(self):
        """
        Remove files older than max_age policy
        """
     
        self.file_logger.info("Checking for files to prune.")

        if not self.check_spool_dir_exists():
            self.file_logger.info("Spool dir does not exist yet.")
            return True
        
        file_list = self.list_spool_files()

        if not file_list:
            self.file_logger.info("No files to prune.")
            return True

        # determine cut-off time for files as per max-age policy
        age_limit = datetime.now() - timedelta(minutes=self.spool_max_age)
        
        prune_count = 0
        for filename in file_list:

            full_file_name = "{}/{}".format(self.spool_dir_root, filename)

            if os.path.getctime(full_file_name) < age_limit.timestamp():
                os.remove(full_file_name)
                prune_count += 1
            else:
                # As soon as we hit a file within policy, exit
                break
        
        self.file_logger.info("Files pruned: {}".format(prune_count))
        
        return True


    def _dump_json_data(self, data_file, dict_data):
        """
        Dump the results data in timestamped json file
        """
        # write out the json data
        try:
            with open (data_file, 'w') as json_file:
                json.dump( [ dict_data ], json_file, indent=2)
        except IOError as err:
                self.file_logger.error("JSON I/O update error: {}".format(err))
                return False
        
        return True


    def spool_results(self, config_vars, data_file, dict_data, watchdog_obj, lockf_obj):
        """
        Dump the results data in to a timestamped file
        """

        #self.file_logger.debug("Result={}".format(dict_data))
        #self.file_logger.debug("Exporter={}".format(config_vars['exporter_type']))

        # if we get here and the exporter is not set to spooler, must have had
        # issue sending result to reporting server, try to spool it
        if config_vars['exporter_type'] != 'spooler':
        
            if self.spool_enabled == 'yes':
                self.file_logger.info("Spooling result as looks like an issue sending to reporting server.")
            else:
                self.file_logger.info("Unable to spool result as spooling disabled.")
                return False

        elif not self.spool_enabled == 'yes':
            # to get here, exporter must have been changed to spooler due to comms issue at start 
            # of poller checks. If spooling not enabled, increment watchdog, remove lock file & exit
            # as no point in continuing as no way of saving results.
            self.file_logger.error("Result spooling not enabled - Exiting.")
            watchdog_obj.inc_watchdog_count()
            lockf_obj.delete_lock_file()
            sys.exit()
        
        # Do not allow spooling if probe is not time sync'ed - historical
        # data timestamps will be meaningless
        if not time_synced():
            self.file_logger.warning("Result spooling not permitted as probe is not time-synced.")
            return False

        # perform spool checks, unless completed on previous iteration
        if not self.spool_checks_completed:

            self.file_logger.info("Spooling data as mgt platform not reachable.")

            # check we have a root dir spooling results
            if not self.check_spool_dir_exists():

                self.file_logger.info("Spool dir does not exist - creating: {}".format(self.spool_dir_root))

                # create it if required
                if not self._create_spool_dir():
                    self.file_logger.error("Unable to spool results data as spool root dir cannot be created: {}".format(self.spool_dir_root))
                    return False
            
            self.spool_checks_completed = True
        
        # add data source to results
        dict_data['data_source'] = data_file
        
        # derive spool filename in format YYYY-MM-DD-HHMMSSmmm-<data source>.json
        file_timestamp = datetime.today().strftime("%Y-%m-%d-%H%M%S.%f")[:-3]
        data_file = "{}/{}-{}.json".format(self.spool_dir_root, file_timestamp, data_file)

        # dump data in to json format file
        return self._dump_json_data(data_file, dict_data)





