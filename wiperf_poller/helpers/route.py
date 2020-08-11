
from socket import gethostbyname
import subprocess
import re
import sys
from wiperf_poller.helpers.os_cmds import IP_CMD

def is_ipv4(ip_address):
    """
    Check if an address is in ivp4 format
    """
    return re.search(r'\d+.\d+.\d+.\d+', ip_address)


def is_ipv6(ip_address):
    """
    Check if an address is in ivp6 format
    """
    return re.search(r'[abcdf0123456789]+:', ip_address)


def resolve_name(hostname, file_logger):
    """
    if hostname passed, DNS lookup, otherwise, return unchanged IP address
    """
    if is_ipv4(hostname) or is_ipv6(hostname):
        return hostname

    try:
        ip_address = gethostbyname(hostname)
        file_logger.info("  DNS hostname lookup : {}. Result: {}".format(hostname, ip_address))
        return ip_address
    except Exception as ex:
        file_logger.error("  Issue looking up host {} (DNS Issue?): {}".format(hostname, ex))
        return False

  
def get_test_traffic_interface(config_vars, file_logger):
    """
    Return the interface name used for testing traffic, based on the probe mode
    """
    probe_mode = config_vars['probe_mode']

    if probe_mode == "wireless": return config_vars['wlan_if'] 
    if probe_mode == "ethernet": return config_vars['eth_if'] 
        
    file_logger.error("  Unknown probe mode: {} (exiting)".format(probe_mode))
    sys.exit()


def get_first_ipv4_route_to_dest(ip_address, file_logger, ip_ver=''):
    """
    Check the routes to a specific ip destination & return first entry
    """

    ip_address = resolve_name(ip_address, file_logger)

    # get specific route details of path that will be used by kernel (cannot be used to modify routing entry)
    ip_route_cmd = "{} {} route get ".format(IP_CMD, ip_ver) + ip_address + " | head -n 1"

    try:
        route_detail = subprocess.check_output(ip_route_cmd, stderr=subprocess.STDOUT, shell=True).decode()
        file_logger.info("  Checked interface route to : {}. Result: {}".format(ip_address, route_detail.strip()))
        return route_detail.strip()
    except subprocess.CalledProcessError as exc:
        output = exc.output.decode()
        file_logger.error("  Issue looking up route (route cmd syntax?): {} (command used: {})".format(str(output), ip_route_cmd))
        return ''
        
def get_first_ipv6_route_to_dest(ip_address, file_logger):
    """
    Check the routes to a specific ipv6 destination & return first entry
    """
    return get_first_ipv4_route_to_dest(ip_address, file_logger, '-6')


def get_route_used_to_dest(ip_address, file_logger):

    ip_address = resolve_name(ip_address, file_logger)

    # get first raw routing entry, otherwise show route that will actually be chosen by kernel
    ip_route_cmd = "{} route show to match ".format(IP_CMD) + ip_address + " | head -n 1"

    try:
        route_detail = subprocess.check_output(ip_route_cmd, stderr=subprocess.STDOUT, shell=True).decode()
        file_logger.info("  Checked interface route to : {}. Result: {}".format(ip_address, route_detail.strip()))
        return route_detail.strip()
    except subprocess.CalledProcessError as exc:
        output = exc.output.decode()
        file_logger.error("  Issue looking up route (route cmd syntax?): {} (command used: {})".format(str(output), ip_route_cmd))
        return ''


def check_correct_ipv4_mgt_interface(mgt_ip, mgt_interface, file_logger):
    """
    Check that the correct interface is being used for mgt traffic for a specific IP v4 target
    """
    file_logger.info("  Checking we will send mgt traffic over configured interface '{}' mode.".format(mgt_interface))
    route_to_dest = get_first_ipv4_route_to_dest(mgt_ip, file_logger)

    if mgt_interface in route_to_dest:
        file_logger.info("  Mgt interface route looks good.")
        return True
    else:
        file_logger.info("  Mgt interface will be routed over wrong interface: {}".format(route_to_dest))
        return False


def check_correct_ipv6_mgt_interface(mgt_ip, mgt_interface, file_logger):
    """
    Check that the correct interface is being used for mgt traffic for a specific IP v6 target
    """
    return check_correct_ipv4_mgt_interface(mgt_ip, mgt_interface, file_logger)


def check_correct_mgt_interface(mgt_host, mgt_interface, file_logger):
    """
    This function checks if the correct interface is being used for mgt traffic
    """

    # figure out mgt_ip (in case hostname passed)
    mgt_ip = resolve_name(mgt_host, file_logger)

    if is_ipv4(mgt_ip): return check_correct_ipv4_mgt_interface(mgt_ip, mgt_interface, file_logger)
    if is_ipv6(mgt_ip): return check_correct_ipv6_mgt_interface(mgt_ip, mgt_interface, file_logger)
    
    file_logger.error("  Unknown mgt IP address format '{}' mode.".format(mgt_ip))
    return False


def check_correct_mode_interface(ip_address, config_vars, file_logger):
    """
    This function checks whether we use the expected interface for testing traffic, 
    depending on which mode the probe is operating.

    Modes:
        ethernet : we expect to get to the Internet over the eth interface (usually eth0)
        wireless : we expect to get to the Internet over the WLAN interface (usually wlan0) 

    args:
        ip_address: IP address of target out on the test domain (usually the Internet)
        config_vars: dict of all config vars
        file_logger: file logger object so that we can log operations
    """

    # check test traffic will go via correct interface depending on mode
    test_traffic_interface= get_test_traffic_interface(config_vars, file_logger)
    
    # get i/f name for route
    route_to_dest = get_first_ipv4_route_to_dest(ip_address, file_logger)

    if test_traffic_interface in route_to_dest:
        return True
    else:
        return False


def inject_default_route(ip_address, config_vars, file_logger):

    """
    This function will attempt to inject a default route to attempt correct
    routing issues caused by path cost if the ethernet interface is up and
    is preferred to the WLAN interface.

    Scenario:

    This function is called as it has been determined that the route used for
    testing traffic is not the required interface. An attempt will be made to 
    fix the routing by increasing the metric of the exsiting default route and
    then adding a new deault route that uses the interface required for testing
    (which will have a lower metrc and be used in preference to the original
    default route)

    Process flow:
    
    1. Get route to the destination IP address
    2. If it's not a default route entry, we can't fix this, exit
    3. Delete the existing default route 
    4. Re-add the same default route with an metric increased to 500
    5. Figure out the interface over which testing traffic should be sent
    6. Add a new default route entry for that interface
    """

    # get the default route to our destination
    route_to_dest = get_route_used_to_dest(ip_address, file_logger)

    # This fix relies on the retrieved route being a default route in the 
    # format: default via 192.168.0.1 dev eth0

    if not "default" in route_to_dest:
        # this isn't a default route, so we can't fix this
        file_logger.error('  [Route Injection] Route is not a default route entry...cannot resove this routing issue: {}'.format(route_to_dest))
        return False
  
    # delete and re-add route with a new metric
    try:
        del_route_cmd = "{} route del ".format(IP_CMD) + route_to_dest
        subprocess.run(del_route_cmd, shell=True)
        file_logger.info("  [Route Injection] Deleting route: {}".format(route_to_dest))
    except subprocess.CalledProcessError as proc_exc:
        file_logger.error('  [Route Injection] Route deletion failed!: {}'.format(proc_exc))
        return False
    
    try:
        modified_route = route_to_dest + " metric 500"
        add_route_cmd = "{} route add  ".format(IP_CMD) + modified_route
        subprocess.run(add_route_cmd, shell=True)
        file_logger.info("  [Route Injection] Re-adding deleted route with new metric: {}".format(modified_route))
    except subprocess.CalledProcessError as proc_exc:
        file_logger.error('  [Route Injection] Route addition failed!')
        return False

    # figure out what our required interface is for testing traffic
    probe_mode = config_vars['probe_mode']
    file_logger.info("  [Route Injection] Checking probe mode: '{}' ".format(probe_mode))
    test_traffic_interface= get_test_traffic_interface(config_vars, file_logger)

    # inject a new route with the required interface
    try:
        new_route = "default dev {}".format(test_traffic_interface)
        add_route_cmd = "{} route add  ".format(IP_CMD) + new_route
        subprocess.run(add_route_cmd, shell=True)
        file_logger.info("  [Route Injection] Adding new route: {}".format(new_route))
    except subprocess.CalledProcessError as proc_exc:
        file_logger.error('  [Route Injection] Route addition failed!')
        return False

    file_logger.info("  [Route Injection] Route injection complete")
    return True


def _inject_static_route(ip_address, req_interface, traffic_type, file_logger, ip_ver=""):

    """
    This function will attempt to inject a static route to correct
    routing issues for specific targets that will not be reached via
    the intended interface without the addition of this route.

    A static route will be inserted in to the probe route table to send 
    matched traffic over a specific interface
    """

    file_logger.info("  [Route Injection] Attempting static route insertion to fix routing issue (note this may not take effect until the next test cycle)")
    try:
        new_route = "{} dev {}".format(ip_address, req_interface)
        add_route_cmd = "{} {} route add  ".format(IP_CMD, ip_ver) + new_route
        subprocess.run(add_route_cmd, shell=True)
        file_logger.info("  [Route Injection] Adding new {} traffic route: {}".format(traffic_type, new_route))
    except subprocess.CalledProcessError as proc_exc:
        output = proc_exc.output.decode()
        file_logger.error('  [Route Injection] Route addition ({})failed! ({})'.format(traffic_type, output))
        return False

    file_logger.info("  [Route Injection] Route injection ({})complete".format(traffic_type))
    return True


def _inject_ipv6_static_route(ip_address, req_interface, traffic_type, file_logger):
    # use ipv4 function, but pass in -6 version number
    # see https://www.tldp.org/HOWTO/Linux+IPv6-HOWTO/ch07s04.html
    return _inject_static_route(ip_address, req_interface, traffic_type, file_logger, "-6")


def inject_mgt_static_route(ip_address, config_vars, file_logger):
    """
    Inject a static route to correct routing issue for mgt traffic
    """
    mgt_interface = config_vars['mgt_if']

    if is_ipv6(ip_address): 
        return _inject_ipv6_static_route(ip_address, mgt_interface, "mgt", file_logger)
    
    return _inject_static_route(ip_address, mgt_interface, "mgt", file_logger)


def inject_test_traffic_static_route(ip_address, config_vars, file_logger):
    """
    Inject a static route to correct routing issue for specific test traffic 
    destination (e.g. iperf)
    """
    probe_mode = config_vars['probe_mode']
    file_logger.info("  [Route Injection] Checking probe mode: '{}' ".format(probe_mode))
    test_traffic_interface= get_test_traffic_interface(config_vars, file_logger)

    return _inject_static_route(ip_address, test_traffic_interface, "test traffic", file_logger)






