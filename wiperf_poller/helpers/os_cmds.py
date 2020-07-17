"""
Centralised file for all OS commands used by the wiperf probe
"""

import pathlib
import shutil

def _find_cmd(cmd):
    """
    This function checks if an OS command is available.

    Returns: filename (if exists/found) or False if not found
    """
    path = pathlib.Path(cmd)

    if not path.is_file():
        # as we can't find it, lets hunt through the path
        command_name = cmd.split('/')[-1]
        found_cmd = shutil.which(command_name)

        if not found_cmd:     
            return False
        else:
            # re-write cmd path
            return found_cmd
    
    return cmd

# define OS commands (attempt to find in path if not in hardcoded path)
OS_CMDS = {
    'DHCLIENT_CMD': _find_cmd('/sbin/dhclient'),
    'IF_CONFIG_CMD': _find_cmd('/sbin/ifconfig'),
    'IF_DOWN_CMD': _find_cmd('/sbin/ifdown'),
    'IF_UP_CMD': _find_cmd('/sbin/ifup'),
    'IP_CMD': _find_cmd('/sbin/ip'),
    'IWCONFIG_CMD': _find_cmd('/sbin/iwconfig'),
    'IW_CMD': _find_cmd('/sbin/iw'),
    'NC_CMD': _find_cmd('/bin/nc'),
    'PING_CMD': _find_cmd('/bin/ping'),
    'REBOOT_CMD': _find_cmd('/sbin/reboot'),
    'ROUTE_CMD': _find_cmd('/sbin/route'),
}

# define exportable vars
DHCLIENT_CMD = OS_CMDS['DHCLIENT_CMD']
IF_CONFIG_CMD = OS_CMDS['IF_CONFIG_CMD']
IF_DOWN_CMD = OS_CMDS['IF_DOWN_CMD']
IF_UP_CMD = OS_CMDS['IF_UP_CMD']
IP_CMD = OS_CMDS['IP_CMD']
IWCONFIG_CMD = OS_CMDS['IWCONFIG_CMD']
IW_CMD = OS_CMDS['IW_CMD']
NC_CMD = OS_CMDS['NC_CMD']
PING_CMD = OS_CMDS['PING_CMD']
REBOOT_CMD = OS_CMDS['REBOOT_CMD']
ROUTE_CMD = OS_CMDS['ROUTE_CMD']


def check_os_cmds(file_logger):
    """
    This function checks is all expected OS commands are avaiable.
    """
    for cmd_name in OS_CMDS.keys():

        if not OS_CMDS[cmd_name]:     
            file_logger.error("Unable to find required OS command: {}".format(cmd_name))
            return False
    
    return True

