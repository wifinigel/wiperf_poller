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
        
def get_routes_used_to_dest_ipv6(ip_address, file_logger):

    ip_address = resolve_name_ipv6(ip_address, file_logger)

    # get entries that match destination
    ip_route_cmd = "{} -6 route show to match {}".format(IP_CMD, ip_address) 

    try:
        route_list = subprocess.check_output(ip_route_cmd, stderr=subprocess.STDOUT, shell=True).decode().strip("\n")
        file_logger.info("  Checked interface routes to : {}. Result: {}".format(ip_address, route_list))
        return route_list
    except subprocess.CalledProcessError as exc:
        output = exc.output.decode()
        file_logger.error("  Issue looking up routes (route cmd syntax?): {} (command used: {})".format(str(output), ip_route_cmd))
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
    # this could be a hostname, try a name resolution just in case
    ip_address = resolve_name_ipv6(ip_address, file_logger)

    # check test traffic will go via correct interface depending on mode
    test_traffic_interface= get_test_traffic_interface_ipv6(config_vars, file_logger)
   
    # get i/f name for route
    if not is_ipv6(ip_address):
        raise ValueError("IP address supplied is not IPv6 format: {}".format(ip_address))

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
    
    1. Get routes to the destination IP address
    2. For each entry, if it is a "default" route:
         - check if it is tesing interface, if it is:
            delete it and re-add it with a metric of 1
         - if not:
            delete it and re-add it with a metric of 1024

    (Note the interface that provides the new default route must be bounced to
    update the probe routing table correctly)
    """

    # get the default route to our ipv6 destination
    route_list = get_routes_used_to_dest_ipv6(ip_address, file_logger)

    file_logger.info('  [Default Route Injection (IPv6)] Checking if we can fix default routing to use correct test interface...')

    # figure out what our required interface is for testing traffic
    probe_mode = config_vars['probe_mode']
    file_logger.info("  [Default Route Injection (IPv6)] Checking probe mode: '{}' ".format(probe_mode))

    test_traffic_interface= get_test_traffic_interface_ipv6(config_vars, file_logger)
    file_logger.info("  [Default Route Injection (IPv6)] Testing interface: '{}' ".format(test_traffic_interface))

    test_interface_route_fixed = False

    file_logger.info("  [Default Route Injection (IPv6)] Checking routes...")
    for route_to_dest in route_list:

        # This fix relies on the retrieved route being a default route in the 
        # format: default dev eth0 metric 1024 onlink pref medium (or maybe:)
        #         fe80::1 dev eth0 proto ra src 200XXXXXXXXXXXXXXXXXfe5b:2005 metric 1024 hoplimit 64 pref medium

        if not "default" in route_to_dest:
            # this isn't a default route, so we can't fix this
            file_logger.error('  [Default Route Injection (IPv6)] Route is not a "default" route entry...unable to update this route: {}'.format(route_to_dest))
            continue
        
        # remove expiration fields (added by dhcp) in route to avoid route deletion issue
        if "expires" in route_to_dest:
            route_to_dest = route_to_dest.split("expires", 1)[0].strip()
        
        # delete default route
        try:
            del_route_cmd = "{} -6 route del ".format(IP_CMD) + route_to_dest
            subprocess.run(del_route_cmd, shell=True)
            file_logger.info("  [Default Route Injection (IPv6)] Deleting route: {}".format(route_to_dest))
        except subprocess.CalledProcessError as proc_exc:
            file_logger.error('  [Default Route Injection (IPv6)] Route deletion failed!: {}'.format(proc_exc))
            return False
        
        # if we match test interface, re-add route with metric of 1
        if test_traffic_interface in route_to_dest:
            route_to_dest =  re.sub(r"metric \d+", r"metric 1", route_to_dest)
        else:
            route_to_dest =  re.sub(r"metric \d+", r"metric 1024", route_to_dest)
        
        # update the default route with a modified metric
        try:
            add_route_cmd = "{} -6 route add  ".format(IP_CMD) + route_to_dest
            subprocess.run(add_route_cmd, shell=True)
            file_logger.info("  [Default Route Injection (IPv6)] Re-adding deleted route with modified metric: {}".format(route_to_dest))
            # signal that test traffic interface route updated
            if test_traffic_interface in route_to_dest:
                test_interface_route_fixed = True
        except subprocess.CalledProcessError as proc_exc:
            file_logger.error('  [Default Route Injection (IPv6)] Route addition failed!')
            return False
      
    file_logger.info("  [Default Route Injection (IPv6)] Route injection complete")
    
    return test_interface_route_fixed

def remove_duplicate_interface_route_ipv6(interface_ip, interface_name, file_logger):

   # Lookup the routing entry of the subnet that on which the testing interface resides, then find & 
   # remove any duplicate routing table entries - this prevents test traffic leaking out of other local
   # interfaces when 2 local interfaces are on same subnet:

   # get routes to the supplied interface address
    ip_route_cmd = "{} -6 route show to match ".format(IP_CMD) + interface_ip + " | grep '/'"
    file_logger.info("  [Check Interface Routes (IPv6)] Checking if we need to remove any interface routes...")

    try:
        routes = subprocess.check_output(ip_route_cmd, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
        file_logger.info("  [Check Interface Routes (IPv6)] Checked interface route to : {}. Result: {}".format(interface_ip, routes))
    except subprocess.CalledProcessError as exc:
        output = exc.output.decode()
        file_logger.error("  [Check Interface Routes (IPv6)] Issue looking up route (route cmd syntax?): {} (command used: {})".format(str(output), ip_route_cmd))
        return False
    
    # check each route entry and delete any that are not our interface of interest
    for route_entry in routes:

        # ignore link local addresses
        if route_entry.startswith("fe80"):
            continue

        if not (interface_name in route_entry):

            # remove expiration message (added by dhcp) in route to avoid route deletion issue
            if "expires" in route_entry:
                route_entry = route_entry.split("expires", 1)[0].strip()
            
            # delete the route entry
            try:
                del_route_cmd = "{} -6 route del ".format(IP_CMD) + route_entry
                subprocess.run(del_route_cmd, shell=True)
                file_logger.info("  [Check Interface Routes (IPv6)] Deleting route: {}".format(route_entry))
            except subprocess.CalledProcessError as proc_exc:
                file_logger.error('  [Check Interface Routes (IPv6)] Route deletion failed!: {}'.format(proc_exc))
                return False
    
    file_logger.info("  [Check Interface Routes (IPv6)] Checks/operations complete.")
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

    file_logger.info("  [Host Route Injection (IPv6)] Attempting {} static route insertion to fix routing issue".format(traffic_type))
    try:
        new_route = "{} dev {}".format(ip_address, req_interface)
        add_route_cmd = "{} -6 route add  ".format(IP_CMD) + new_route
        subprocess.run(add_route_cmd, shell=True)
        file_logger.info("  [Host Route Injection (IPv6)] Adding new {} traffic route: {}".format(traffic_type, new_route))
    except subprocess.CalledProcessError as proc_exc:
        output = proc_exc.output.decode()
        file_logger.error('  [Host Route Injection (IPv6)] Route addition ({})failed! ({})'.format(traffic_type, output))
        return False

    file_logger.info("  [Host Route Injection (IPv6)] Route injection ({})complete".format(traffic_type))
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
    file_logger.info("  [Host Route Injection (IPv6)] Checking probe mode: '{}' ".format(probe_mode))
    test_traffic_interface= get_test_traffic_interface_ipv6(config_vars, file_logger)

    # figure out ip (in case hostname passed)
    ip_address = resolve_name_ipv6(host, file_logger)

    # if route injection works, check that route is now over correct interface
    if _inject_static_route_ipv6(ip_address, test_traffic_interface, "test traffic", file_logger):

       if check_correct_mode_interface_ipv6(ip_address, config_vars, file_logger):

           return True
    
    # Something went wrong...
    return False






