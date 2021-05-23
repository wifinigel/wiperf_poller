"""
IPV6 Routing in wiperf
======================

Routing of IP traffic can be problematic in some instances within a network probe. Once multiple
interfaces are enabled, it can be quite tricky for the IP stack to know which interface packets
should be sent over (as we are not using any routing protocols).

In the absence of any additional information, a probe will assign a number of interfaces
as default routes and then route packets out of the interface with the lowest metric. In the case of 
wiperf, when both the ethernet interface and wireless interface may have the same metric, it is not
clear which interface will be used as the default route for packets.

This not generally what we want to achieve - in many instances, we want to route all test traffic over 
the wireless interface, with management traffic being sent over the ethernet interface. 

This means that when several interaces are up, we may need to manipulate route metrics to achieve the 
desired flows and ensure traffic does not leak out of unintended interfaces. The case of IPv4, we 
may delete any routes that we do not wish to be used, but with IPv6, deleted routes are very quickly
re-learned. Therefore, we have to add static routes with low metrc values to ensure we use the required
routing. This is particularly important if the ethernet and wireless interfaces are on the same IP 
network, when test traffic could end up flowing out of the ethernet interface and not test the wireless
link at all.

In addition, we also need to verify that management traffic (i.e. test results data) can reach the
required management platform and has not been impacted by the changes to routing that have been
implemented to ensure the correct test traffic flows are achieved.

The interfaces to be used for testing are determined by the probe mode. There are currently two modes:
    1. Wireless mode
    2. Ethernet mode

In "wireless mode", all test traffic needs to flow over the wireless interface. Management traffic may 
flow over any nominated interface, which may include the wireless or ethernet interfaces. It is also
possible that other interfaces (e.g. a VPN interface (Zeortier for instance)) are used for 
management connectivity. The test traffic needs to flow towards the "WAN" direction, generally out to
the Internet to test remote resources. It is assumed that as we have selected wireless mode, the 
required test resources can be reached over the wireless Interface.

In "Ethernet mode", all test traffic needs to flow over the ethernet interface, rather than the 
wireless interface. 

Route Checking/Modification
---------------------------

The process for obtaining the correct traffic flows is as follows:

1. Check the interface that will be used to hit the test domain - this is done by looking up 
   the route to a nominated IPv6 destination out in the test domain (usually the Internet). 
   This can be achieved using the "ip" command - for instance:

   ip -6 route get 2a00:1450:4003:811::200e

   2a00:1450:4003:811::200e from :: via fe80::1 dev eth0 proto ra src 2001:818:e708:cf00:1:c2ff:fe8c:7ec4 metric 1024 hoplimit 64 pref medium

2. If route lookup indicates test traffic will hit the required interface, our route 
   is already set as we need it.

3. If the route lookup indicates that the incorrect interface is used as the default route, add a 
   default route that forces traffic across the test interface (assigning a metric of one). There may
   be several existing default routes as shown in the routing table below. 

    root@wlanpi:/home/wlanpi# ip -6 route
    ::1 dev lo proto kernel metric 256 pref medium
    2001:818:e708:cf00::/64 dev wlan0 proto kernel metric 1 pref medium
    2001:818:e708:cf00::/64 dev wlan0 proto kernel metric 256 expires 86344sec pref medium
    2001:818:e708:cf00::/64 dev eth0 proto kernel metric 256 expires 86344sec pref medium
    fe80::/64 dev eth0 proto kernel metric 256 pref medium
    fe80::/64 dev wlan0 proto kernel metric 256 pref medium
    fe80::/64 dev ztukutsbw2 proto kernel metric 256 pref medium
    default via fe80::1 dev eth0 proto ra metric 1024 expires 244sec hoplimit 64 pref medium
    default via fe80::1 dev wlan0 proto ra metric 1024 expires 244sec hoplimit 64 pref medium

   There is no point in trying to delete these routes, as they will re-appear a few seconds later 
   (I assume they are re-learned). The best approach is to add a static default route that has a
   lower metric and will be used in preference to any other already learned by the system. 
 
4. Perform a route lookup again to verify that test traffic will now hit the required interface:

   ip route get 2a00:1450:4003:811::200e

5. Another challenge is the possibility of two local interfaces being attached to the same
   subnet. This is a valid condition, but may make the choice of which interface to use for
   target test resources dubious as the interface to be used may be unpredictable.

   The answer to this is to add a static route for the same network and the test interface with a 
   metric of one. Note, this only needs to be done if the test interface is on the same subnet 
   as one of the other interfaces on the probe.

   Example: 

    2001:818:e708:cf00::/64 dev wlan0 proto kernel metric 1 pref medium <<<<<<<<<<<<<<<<
    2001:818:e708:cf00::/64 dev wlan0 proto kernel metric 256 expires 86344sec pref medium
    2001:818:e708:cf00::/64 dev eth0 proto kernel metric 256 expires 86344sec pref medium
   
   Again, there is in point simpy removing the local interface route entries, as they will 
   be automatically re-added a few moments later 

6. Finally, make sure that there is a viable route for management traffic, if IPv6 used for mgt
   traffic:

    a. Lookup the route to the IP of the mgt platform
    b. If the correct interface is not being used, inject a single host route to force mgt
       traffic over the correct interface. The interface must obviously have a viable onward 
       path to the mgt server once the mgt traffic is sent over that interface. 

"""

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
    """
    Generic field extraction from string based on pattern passed
    """
    re_result = re.search(pattern, cmd_output_text)

    if re_result is None:
        return None
    else:
        field_value = re_result.group(1)
        return field_value

  
def get_test_traffic_interface_ipv6(config_vars, file_logger):
    """
    Return the interface name used for testing traffic, based on the probe mode
    """
    probe_mode = config_vars['probe_mode']

    if probe_mode == "wireless": return config_vars['wlan_if'] 
    if probe_mode == "ethernet": return config_vars['eth_if'] 
        
    file_logger.error("  Unknown probe mode: {} (exiting)".format(probe_mode))
    sys.exit()

def get_routes_used_to_dest_ipv6(ip_address, file_logger):
    """
    Inpsect the routing table to determine the routes available 
    from the probe routing table for an IP address. 
    Uses the command:
    
        ip -6 route show to match <ipv6 address>
        
        typical output:
            root@wlanpi:/home/wlanpi# ip -6 route show to match 2a00:1450:4003:807::200e
            default via fe80::1 dev eth0 proto ra metric 1024 expires 281sec hoplimit 64 pref medium
            default via fe80::1 dev wlan0 proto ra metric 1024 expires 281sec hoplimit 64 pref medium
        
            (note: may return several routes if appropriate)

    Args:
        ip_address (str): target IP address
        file_logger (file_logger obj): file logger object
    """
    if not is_ipv6(ip_address):
        ip_address = resolve_name_ipv6(ip_address, file_logger)

    # get entries that match destination
    ip_route_cmd = "{} -6 route show to match {}".format(IP_CMD, ip_address) 

    try:
        route_list = subprocess.check_output(ip_route_cmd, stderr=subprocess.STDOUT, shell=True).decode().split("\n")
        file_logger.info("  Checked interface routes to : {}. Result: {}".format(ip_address, route_list))
        return route_list
    except subprocess.CalledProcessError as exc:
        output = exc.output.decode()
        file_logger.error("  Issue looking up routes (route cmd syntax?): {} (command used: {})".format(str(output), ip_route_cmd))
        return ''


def get_used_interface_to_dest_ipv6(ip_address, file_logger):
    """
    Inpsect the routing table to determine the interface to be used 
    from the probe routing table. Uses the command:
    
        ip -6 route get <ip address>
        
        typical output:
            root@wlanpi:/home/wlanpi# ip -6 route get 2a00:1450:4003:807::200e
            2a00:1450:4003:807::200e from :: via fe80::1 dev wlan0 proto ra src 2001:818:e909:cf00:8e88:2dff:fe00:237d metric 1 pref medium  

    Args:
        ip_address (str): target IP address
        file_logger (file_logger obj): file logger object
    """
    if not is_ipv6(ip_address):
        ip_address = resolve_name_ipv6(ip_address, file_logger)

    # get entries that match destination
    ip_route_cmd = "{} -6 route get {}".format(IP_CMD, ip_address) 

    try:
        cmd_output = subprocess.check_output(ip_route_cmd, stderr=subprocess.STDOUT, shell=True).decode().split("\n")
    except subprocess.CalledProcessError as exc:
        output = exc.output.decode()
        file_logger.error("  Issue looking up routes (route cmd syntax?): {} (command used: {})".format(str(output), ip_route_cmd))
        return ''
    
    interface_line = cmd_output[0]
    interface_used = _field_extractor(r'dev (\S+) ', interface_line)
    file_logger.info("  Checked interface used to : {}. Result: {}".format(ip_address, interface_used))

    return interface_used

# TODO: remove this function as no longer used?
def get_first_route_to_dest_ipv6(ip_address, file_logger):
    """
    Check the routes to a specific ip destination & return first entry
    """

    route_list = get_routes_used_to_dest_ipv6(ip_address, file_logger)

    if len(route_list) > 0:
        first_route = route_list[0]
        file_logger.info("  Checked interface route to : {}. Result: {}".format(ip_address, first_route))
        return first_route
    else:
        file_logger.warning("  Unable to determine first route to destination.")
        return False
        

def check_correct_mgt_interface_ipv6(mgt_host, mgt_interface, file_logger):
    """
    This function checks if the correct interface is being used for mgt traffic
    """
    file_logger.info("  Checking we will send mgt traffic over configured interface '{}' mode.".format(mgt_interface))

    # figure out mgt_ip (in case hostname passed)
    mgt_ip = resolve_name_ipv6(mgt_host, file_logger)

    #route_to_dest = get_first_route_to_dest_ipv6(mgt_ip, file_logger)
    interface_to_dest = get_used_interface_to_dest_ipv6(mgt_ip, file_logger)

    #if mgt_interface in route_to_dest:
    if mgt_interface == interface_to_dest:
        file_logger.info("  Mgt interface route looks good.")
        return True
    else:
        #file_logger.info("  Mgt interface will be routed over wrong interface: {}".format(route_to_dest))
        file_logger.error("  Mgt interface will be routed over wrong interface: {}".format(interface_to_dest))
        return False

def check_correct_mode_interface_ipv6(host, config_vars, file_logger):
    """
    Check that mgt traffic will go over correct interface for the selected mode
    """
    # this could be a hostname, try a name resolution just in case
    ip_address = resolve_name_ipv6(host, file_logger)

    # check test traffic will go via correct interface depending on mode
    test_traffic_interface= get_test_traffic_interface_ipv6(config_vars, file_logger)
   
    # get i/f name for route
    if not is_ipv6(ip_address):
        raise ValueError("IP address supplied is not IPv6 format: {}".format(ip_address))

    #route_to_dest = get_first_route_to_dest_ipv6(ip_address, file_logger)
    interface_to_dest = get_used_interface_to_dest_ipv6(ip_address, file_logger)

    #if test_traffic_interface in route_to_dest:
    if test_traffic_interface == interface_to_dest:
        file_logger.info("  Test traffic interface route looks good.")
        return True
    else:
        file_logger.error("  Test traffic will be routed over wrong interface: {}".format(interface_to_dest))
        return False

def inject_default_route_ipv6(ip_address, config_vars, file_logger):

    """
    This function will attempt to inject an IPv6 default route for the test
    traffic interface. All other detected default routes will be removed. The
    default route will also be modified to use a metric of 1 if existing, or
    added with a metric of 1 if it does not exist

    Scenario:

    This function is called as it has been determined that the route used for
    testing traffic is not the required interface. An attempt will be made to 
    fix the routing by adding a new default route that uses the interface required
    for testing, which will have a lower metrc and be used in preference to the
    original default route. All other default routes ill be removed. If an existing
    default can be used, it will be deleted and re-added with a metric of 1

    Process flow:
    
    1. Get routes to the destination IP address
    2. For each entry, if it is a "default" route:
         - check if it is tesing interface, if it is:
             re-add it with a metric of 1
         - if not:
            do nothing (no poin in removing as will re-appear)
    3. If no default route has been found, add a suitable
       default route with a metric of 1

    Note 1: If the interface nominated for test traffic is invalid as a route
        for carrying test traffic, connectivity will be lost and may only be
        restored via a reboot.
    """

    # get the default route to our ipv6 destination
    route_list = get_routes_used_to_dest_ipv6(ip_address, file_logger)

    file_logger.info('  [Default Route Injection (IPv6)] Checking if we can fix default routing to use correct test interface...')

    # figure out what our required interface is for testing traffic
    probe_mode = config_vars['probe_mode']
    file_logger.info("  [Default Route Injection (IPv6)] Checking probe mode: '{}' ".format(probe_mode))
    test_traffic_interface= get_test_traffic_interface_ipv6(config_vars, file_logger)
    file_logger.info("  [Default Route Injection (IPv6)] Testing interface: '{}' ".format(test_traffic_interface))

    # step through routes and remove each default route that does not match test interface
    test_interface_route_fixed = False

    file_logger.info("  [Default Route Injection (IPv6)] Checking routes...")

    for route_to_dest in route_list:

        # This fix relies on the retrieved route being a default route in the 
        # format: default dev eth0 metric 1024 onlink pref medium (or maybe:)
        #         fe80::1 dev eth0 proto ra src 200XXXXXXXXXXXXXXXXXfe5b:2005 metric 1024 hoplimit 64 pref medium

        # if an empty entry slips through, ignore
        if not route_to_dest:
            continue
        
        if not "default" in route_to_dest:
            # this isn't a default route, so we can't fix this
            file_logger.debug('  [Default Route Injection (IPv6)] Route is not a "default" route entry...unable to update this route: {}'.format(route_to_dest))
            continue
        
        # remove expiration fields (added by dhcp) in route to avoid route deletion issue
        if "expires" in route_to_dest:
            route_to_dest = route_to_dest.split("expires", 1)[0].strip()
              
        # if a match for test interface, modify metric & re-add as static route
        if test_traffic_interface in route_to_dest:
            route_to_dest =  re.sub(r"metric \d+", r"metric 1", route_to_dest)

            try:
                add_route_cmd = "{} -6 route add  {}".format(IP_CMD, route_to_dest)
                subprocess.run(add_route_cmd, shell=True)
                file_logger.info("  [Default Route Injection (IPv6)] Adding static route with modified metric: {}".format(route_to_dest))

                # signal that test traffic interface route updated
                if test_traffic_interface in route_to_dest:
                    test_interface_route_fixed = True
            except subprocess.CalledProcessError as proc_exc:
                file_logger.error('  [Default Route Injection (IPv6)] Route addition failed!')
                return False
        
    if not test_interface_route_fixed:

        # add default route via test interface
        route_to_dest = "default via fe80::1 dev {} metric 1".format(test_traffic_interface)

        try:
            add_route_cmd = "{} -6 route add  {}".format(IP_CMD, route_to_dest)
            subprocess.run(add_route_cmd, shell=True)
            file_logger.info("  [Default Route Injection (IPv6)] Adding static route with low metric: {}".format(route_to_dest))
            
            # signal that test traffic interface route updated
            if test_traffic_interface in route_to_dest:
                test_interface_route_fixed = True

        except subprocess.CalledProcessError as proc_exc:
            file_logger.error('  [Default Route Injection (IPv6)] Route addition failed!')
            return False
        
        file_logger.info("  [Default Route Injection (IPv6)] Route injection complete")
    
    return test_interface_route_fixed

def remove_duplicate_interface_route_ipv6(interface_ip, interface_name, file_logger):

   # Lookup the routing entry of the subnet that on which the testing interface resides, then find 
   # any duplicate routing table entries and add a static route with an metrc of 1 to be used instead
   # of the other route entries - this prevents test traffic leaking out of other local interfaces 
   # when 2 or more local interfaces are on same subnet:

   # get routes to the supplied interface address
    ip_route_cmd = "{} -6 route show to match ".format(IP_CMD) + interface_ip + " | grep '/'"
    file_logger.info("  [Check Interface Routes (IPv6)] Checking if we need to modify any duplicate interface routes...")

    try:
        routes = subprocess.check_output(ip_route_cmd, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
        file_logger.info("  [Check Interface Routes (IPv6)] Checked interface route to : {}. Result: {}".format(interface_ip, routes))
    except subprocess.CalledProcessError as exc:
        output = exc.output.decode()
        file_logger.error("  [Check Interface Routes (IPv6)] Issue looking up route (route cmd syntax?): {} (command used: {})".format(str(output), ip_route_cmd))
        return False
    
    if len(ip_route_cmd) > 1:

        # we have two or more local interface entries, so may have to fix issue (unless we
        # already previously fixed issue)
    
        # check each route entry and delete any that are not our interface of interest
        for route_entry in routes:

            # ignore link local addresses
            if route_entry.startswith("fe80"):
                continue

            if not (interface_name in route_entry):

                # do nothing, not a route entry of interest
                continue
            else:
                # remove expiration message (added by dhcp) in route
                if "expires" in route_entry:
                    route_entry = route_entry.split("expires", 1)[0].strip()
                
                # substitute the metric & change to 1
                new_route =  re.sub(r"metric \d+", r"metric 1", route_entry)

                # if it doesn't already exist in the route list, add static entry
                if not new_route in routes:

                    try:
                        add_route_cmd = "{} -6 route add  {}".format(IP_CMD, new_route)
                        subprocess.run(add_route_cmd, shell=True)
                        file_logger.info("  [Default Route Injection (IPv6)] Adding local interface route with modified metric: {}".format(new_route))
                    except subprocess.CalledProcessError as proc_exc:
                        file_logger.error('  [Default Route Injection (IPv6)] Route addition failed!')
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






