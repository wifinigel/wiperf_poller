import socket
import subprocess
import re
import sys
from wiperf_poller.helpers.os_cmds import IP_CMD

def resolve_name_ipv6(hostname, file_logger):
    """
    if hostname passed, DNS lookup, otherwise, return unchanged IP address
    """
    if is_ipv6(hostname):
        return hostname  
    
    if is_ipv4(hostname):
        raise ValueError("IPv4 address passed to resolve_name_ipv6(), should be IPv6")

    try:
        ip_address = socket.getaddrinfo(hostname, 0, family=socket.AF_INET6)[0][4][0]
        file_logger.info("  DNS hostname lookup : {} / Result: {}".format(hostname, ip_address))
        return ip_address

    except Exception as ex:
        file_logger.error("  Issue looking up host {} (DNS or hostname Issue?): {}".format(hostname, ex))
        return False


def is_ipv4(ip_address):
    """
    Check if an address is in ivp4 format
    """     
    return re.search(r'\d+\.\d+\.\d+\.\d+', ip_address)


def is_ipv6(ip_address):
    """
    Check if an address is in ivp6 format
    """    
    return re.search(r'[abcdf0123456789]+:', ip_address)


def _field_extractor(pattern, cmd_output_text):

    re_result = re.search(pattern, cmd_output_text)

    if not re_result is None:
        field_value = re_result.group(1)
        return field_value
    else:
        return None

  
def get_test_traffic_interface_ipv6(config_vars, file_logger):
    """
    Return the interface name used for testing traffic, based on the probe mode
    """
    probe_mode = config_vars['probe_mode']

    if probe_mode == "wireless": return config_vars['wlan_if'] 
    if probe_mode == "ethernet": return config_vars['eth_if'] 
        
    file_logger.error("  Unknown probe mode: {} (exiting)".format(probe_mode))
    sys.exit()


def get_first_route_to_dest_ipv6(ip_address, file_logger):
    """
    Check the routes to a specific ip destination & return first entry
    """

    ip_address = resolve_name_ipv6(ip_address, file_logger)

    # get specific route details of path that will be used by kernel (cannot be used to modify routing entry)
    ip_route_cmd = "{} -6 route get ".format(IP_CMD) + ip_address + " | head -n 1"

    try:
        route_detail = subprocess.check_output(ip_route_cmd, stderr=subprocess.STDOUT, shell=True).decode()
        file_logger.info("  Checked interface route to : {}. Result: {}".format(ip_address, route_detail.strip()))
        return route_detail.strip()
    except subprocess.CalledProcessError as exc:
        output = exc.output.decode()
        file_logger.error("  Issue looking up route (route cmd syntax?): {} (command used: {})".format(str(output), ip_route_cmd))
        return ''
        
def get_route_used_to_dest_ipv6(ip_address, file_logger):

    ip_address = resolve_name_ipv6(ip_address, file_logger)

    # get first raw routing entry, otherwise show route that will actually be chosen by kernel
    ip_route_cmd = "{} -6 route show to match ".format(IP_CMD) + ip_address + " | head -n 1"

    try:
        route_detail = subprocess.check_output(ip_route_cmd, stderr=subprocess.STDOUT, shell=True).decode()
        file_logger.info("  Checked interface route to : {}. Result: {}".format(ip_address, route_detail.strip()))
        return route_detail.strip()
    except subprocess.CalledProcessError as exc:
        output = exc.output.decode()
        file_logger.error("  Issue looking up route (route cmd syntax?): {} (command used: {})".format(str(output), ip_route_cmd))
        return ''


def check_correct_mgt_interface_ipv6(mgt_host, mgt_interface, file_logger):
    """
    This function checks if the correct interface is being used for mgt traffic
    """
    file_logger.info("  Checking we will send mgt traffic over configured interface '{}' mode.".format(mgt_interface))

    # figure out mgt_ip (in case hostname passed)
    mgt_ip = resolve_name_ipv6(mgt_host, file_logger)

    route_to_dest = get_first_route_to_dest_ipv6(mgt_ip, file_logger)

    if mgt_interface in route_to_dest:
        file_logger.info("  Mgt interface route looks good.")
        return True
    else:
        file_logger.info("  Mgt interface will be routed over wrong interface: {}".format(route_to_dest))
        return False

def check_correct_mode_interface_ipv6(ip_address, config_vars, file_logger):
    """
    Check that mgt traffic will go over correct interface for the selected mode
    """
    # check test traffic will go via correct interface depending on mode
    test_traffic_interface= get_test_traffic_interface_ipv6(config_vars, file_logger)
    
    # get i/f name for route
    if not is_ipv6(ip_address):
        raise ValueError("IP address supplied is not IPv4 format")

    route_to_dest = get_first_route_to_dest_ipv6(ip_address, file_logger)

    if test_traffic_interface in route_to_dest:
        return True
    else:
        return False


def inject_default_route_ipv6(ip_address, config_vars, file_logger):

    """
    This function will attempt to inject an IPv6 default route to attempt
    correct routing issues caused by path cost if the ethernet interface
    is up and is preferred to the WLAN interface.

    Scenario:

    This function is called as it has been determined that the route used for
    testing traffic is not the required interface. An attempt will be made to 
    fix the routing by adding a new default route that uses the interface required
    for testing, which will have a lower metrc and be used in preference to the
    original default route

    Process flow:
    
    1. Get route to the destination IP address
    2. If it's not a default route entry, we can't fix this, exit
    3. Get the existing default route & extract its metric 
    4. Add a default route for the interface used for testing, with a lower metric
    """

    # get the default route to our ipv6 destination
    route_to_dest = get_route_used_to_dest_ipv6(ip_address, file_logger)

    # This fix relies on the retrieved route being a default route in the 
    # format: default dev eth0 metric 1024 onlink pref medium

    if not "default" in route_to_dest:
        # this isn't a default route, so we can't fix this
        file_logger.error('  [Route Injection (ipv6)] Route is not a default route entry...cannot resolve this routing issue: {}'.format(route_to_dest))
        return False
  
    # delete and re-add route with a new metric
    try:
        del_route_cmd = "{} route del ".format(IP_CMD) + route_to_dest
        subprocess.run(del_route_cmd, shell=True)
        file_logger.info("  [Route Injection (ipv6)] Deleting route: {}".format(route_to_dest))
    except subprocess.CalledProcessError as proc_exc:
        file_logger.error('  [Route Injection (ipv6)] Route deletion failed!: {}'.format(proc_exc))
        return False
    
    try:
        modified_route = re.sub(r"metric (\d+)", "metric 1024", route_to_dest)
        add_route_cmd = "{} route add  ".format(IP_CMD) + modified_route
        subprocess.run(add_route_cmd, shell=True)
        file_logger.info("  [Route Injection (ipv6)] Re-adding deleted route with new metric: {}".format(modified_route))
    except subprocess.CalledProcessError as proc_exc:
        file_logger.error('  [Route Injection (ipv6)] Route addition failed!')
        return False

    # figure out what our required interface is for testing traffic
    probe_mode = config_vars['probe_mode']
    file_logger.info("  [Route Injection (ipv6)] Checking probe mode: '{}' ".format(probe_mode))
    test_traffic_interface= get_test_traffic_interface_ipv6(config_vars, file_logger)

    # inject a new route with the required interface
    try:
        new_route = "default dev {} metric 1023".format(test_traffic_interface)
        add_route_cmd = "{} route add  ".format(IP_CMD) + new_route
        subprocess.run(add_route_cmd, shell=True)
        file_logger.info("  [Route Injection (ipv6)] Adding new route: {}".format(new_route))
    except subprocess.CalledProcessError as proc_exc:
        file_logger.error('  [Route Injection (ipv6)] Route addition failed!')
        return False

    file_logger.info("  [Route Injection (ipv6)] Route injection complete")
    return True

def _inject_static_route_ipv6(ip_address, req_interface, traffic_type, file_logger):
    """
    This function will attempt to inject an IPv6 static route to correct
    routing issues for specific targets that will not be reached via
    the intended interface without the addition of this route.

    A static route will be inserted in to the probe route table to send 
    matched traffic over a specific interface

    Ref: see https://www.tldp.org/HOWTO/Linux+IPv6-HOWTO/ch07s04.html
    """

    file_logger.info("  [Route Injection] Attempting {} static route insertion to fix routing issue".format(traffic_type))
    try:
        new_route = "{} dev {}".format(ip_address, req_interface)
        add_route_cmd = "{} -6 route add  ".format(IP_CMD) + new_route
        subprocess.run(add_route_cmd, shell=True)
        file_logger.info("  [Route Injection] Adding new {} traffic route: {}".format(traffic_type, new_route))
    except subprocess.CalledProcessError as proc_exc:
        output = proc_exc.output.decode()
        file_logger.error('  [Route Injection] Route addition ({})failed! ({})'.format(traffic_type, output))
        return False

    file_logger.info("  [Route Injection] Route injection ({})complete".format(traffic_type))
    return True

def inject_mgt_static_route_ipv6(ip_address, config_vars, file_logger):
    """
    Inject a static route (ipv6) to correct routing issue for mgt traffic
    """
    mgt_interface = config_vars['mgt_if']

    if not is_ipv6(ip_address): 
        raise ValueError("Supplied IP address for static route is not IPv6 format")
    
    return _inject_static_route_ipv6(ip_address, mgt_interface, "mgt", file_logger)


def inject_test_traffic_static_route_ipv6(host, config_vars, file_logger):
    """
    Inject a static route to correct routing issue for specific test traffic 
    destination (e.g. iperf)
    """
    probe_mode = config_vars['probe_mode']
    file_logger.info("  [Route Injection] Checking probe mode: '{}' ".format(probe_mode))
    test_traffic_interface= get_test_traffic_interface_ipv6(config_vars, file_logger)

    # figure out ip (in case hostname passed)
    ip_address = resolve_name_ipv6(host, file_logger)

    # if route injection works, check that route is now over correct interface
    if _inject_static_route_ipv6(ip_address, test_traffic_interface, "test traffic", file_logger):

       if check_correct_mode_interface_ipv6(ip_address, config_vars, file_logger):

           return True
    
    # Something went wrong...
    return False






