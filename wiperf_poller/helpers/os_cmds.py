"""
Centralised file for all OS commands used by the wiperf probe
"""

DHCLIENT_CMD = '/sbin/dhclient'
IF_CONFIG_CMD = '/sbin/ifconfig'
IF_DOWN_CMD = '/sbin/ifdown'
IF_UP_CMD = '/sbin/ifup'
IP_CMD = '/sbin/ip'
IWCONFIG_CMD = '/sbin/iwconfig'
IW_CMD = '/sbin/iw'
NC_CMD = '/bin/nc'
PING_CMD = '/bin/ping'
REBOOT_CMD = '/sbin/reboot'
ROUTE_CMD = '/sbin/route'

CMDS = [
    DHCLIENT_CMD,
    IF_CONFIG_CMD,
    IF_DOWN_CMD,
    IF_UP_CMD,
    IP_CMD,
    IWCONFIG_CMD,
    IW_CMD,
    NC_CMD,
    PING_CMD,
    REBOOT_CMD,
    ROUTE_CMD
]