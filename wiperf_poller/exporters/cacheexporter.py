"""
cacheexporter.py

A class to dump cached results data in to a local folder for inspection/retrieval
by alternative methods (user defined methods)

Implementation details:

1. Cache files may be in json or CSV format
2. Cache files are stored under folder /var/cache/wiperf
3. One folder to conatin cache files will be created for each day
4. One file will be created for each test type per day (e.g. one for http, one for ping etc.)
5. The following config parameters will be specified in config .ini:
    a. Caching enabled/disabled
    b. Retention period for files, in days (default = 3)
    c. Cache file format (json or csv)
    d. Hidden parameter : cache_dir which defaults to /var/cache/wiperf when not supplied
"""

import csv
import json
import os
import shutil
from datetime import datetime

class CacheExporter(object):
    """
    A class to dump cached results data in to a local folder for inspection/retrieval
    by alternative methods (user defined methods)
    """

    def __init__(self, file_logger, platform="rpi"):

        self.platform = platform
        self.file_logger = file_logger
        self.cache_root = ''
        self.retention_period = 0
        self.data_format = ''
        self.day_dir_name = ''

        self.cache_checks_completed = False
    
    
    def _check_cache_day_dir_exists(self):
        """
        Check if today's dir exists
        """
        # Check if day dir already defined
        if not self.day_dir_name:

            # derive day directory name in format YYYY--MM-DD
            self.day_dir_name = self.cache_root + "/" + datetime.today().strftime('%Y-%m-%d')

        if os.path.exists(self.day_dir_name) and os.path.isdir(self.day_dir_name):
            return True

        return False


    def _create_cache_day_dir(self):
        """
        Create today's cache dir
        """

        try: 
            os.makedirs(self.day_dir_name, exist_ok = True) 
            self.file_logger.debug("Created cache file for day: {}".format(self.day_dir_name))
        except OSError as e: 
            self.file_logger.error("Cannot create day dir for today's cache files: {} ({})".format(self.day_dir_name, e.strerror)) 
            return False
        return True


    def _prune_cache_dirs(self):
        """
        Remove dirs that are older than the configured policy
        """

        # get a list of cache dirs
        cache_dir_list = sorted(os.listdir(self.cache_root))

        # get rid of oldest dir(s)
        if len(cache_dir_list) > self.retention_period:

            slice_size = len(cache_dir_list) - self.retention_period

            for n in range(slice_size):
                dir_name = cache_dir_list[n]
                full_dir_name = self.cache_root + "/" + dir_name

                try:
                    shutil.rmtree(full_dir_name)
                except OSError as e:
                    self.file_logger.error("Unable to remove cache directory tree: {} ({})".format(full_dir_name, e.strerror))
                    return False
        
        return True


    def _dump_json_data(self, data_file, dict_data):
        """
        Dump the results data in today's json file
        """

        file_data = []

        # if json file exists, read it in and update data dict
        if os.path.exists(data_file):

            try:
                with open(data_file) as json_file:
                    file_data = json.load(json_file)
            except IOError as err:
                self.file_logger.error("JSON I/O file read error: {}".format(err))
                return False
            
            file_data.append(dict_data)
        else:
            # no file, so prepare to write initial data
            file_data = [ dict_data ]

        # write out the json data
        try:
            with open (data_file, 'w') as json_file:
                json.dump(file_data, json_file, indent=2)
        except IOError as err:
                self.file_logger.error("JSON I/O update error: {}".format(err))
                return False
        
        return True

    
    def _dump_csv_data(self, data_file, dict_data, column_headers):
        """
        Dump the results data in today's csv file
        """

        try:
            # if False:
            if os.path.exists(data_file):
                with open(data_file, 'a') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=column_headers)
                    writer.writerow(dict_data)
            else:
                with open(data_file, 'w') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=column_headers)
                    writer.writeheader()
                    writer.writerow(dict_data)
        except IOError as err:
            self.file_logger.error("CSV I/O error: {}".format(err))
            return False
        
        return True


    def dump_cache_results(self, config_vars, data_file, dict_data, column_headers, data_filter=''):
        """
        Dump the results data in today's file
        """

        self.cache_root = config_vars['cache_root']
        self.retention_period = int(config_vars['cache_retention_period'])
        self.data_format = config_vars['cache_data_format']

        # check if we want to limit cache dumping to specific data sources
        if data_filter:
            if data_file in data_filter:
                self.file_logger.debug("Data source filtered {}, not dumped in cache".format(data_file))
                return True

        # check cache checks, unless completed on previous iteration
        if not self.cache_checks_completed:

            # check cache dir for today exists
            if not self._check_cache_day_dir_exists():

                # create it if required
                if not self._create_cache_day_dir():
                    return False
            
            # prune old cache dirs if required (exceeded retention policy)
            if not self._prune_cache_dirs():
                return False

            self.cache_checks_completed = True
        
        # dump data in configured format
        if self.data_format == 'json':
            data_file = self.day_dir_name + "/" + data_file + ".json"
            self._dump_json_data(data_file, dict_data)

        elif self.data_format == 'csv':
            data_file = self.day_dir_name + "/" + data_file + ".csv"
            self._dump_csv_data(data_file, dict_data, column_headers)
        
        else:
            self.file_logger.error("Unknown data format parameter supplied: {}".format(self.data_format))




