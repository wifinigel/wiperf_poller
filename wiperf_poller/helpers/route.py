"""
Routing in wiperf
=================

Routing of IP traffic can be problematic in some instances within a network probe. Once multiple
interfaces are enabled, it can be quite tricky for the IP stack to know which interface packets
should be sent over (as we are not using any routing protocols).

In the absence of any additional information, a probe will typically assign a number of interfaces
as default routes and then route packets out of the lowest cost interface. In the case of wiperf,
this often means that if we have the Ethernet interface connected and a wireless connection established,
the ethernet interface will generally be preferred over the wireless interface. This not generally 
what we want to achieve - in many instances, we want to route all test traffic over the wireless
interface, with management traffic being sent over the ethernet interface. This means that when several
interaces are up, we may need to manipulate route metrics and maybe add or remove some routes to 
gain the desired traffic flow. This is particularly important if the ethernet and wireless interfaces
are on the same interface, when test traffic may end up flowing out of the ethernet interface and not
test the wireless link at all.

In addition, we also need to verify that management traffic (i.e. test results data) can reach the
required management platform and has not been impacted by the changes to routing that have been
implemented to ensure the correct test traffic flows are achieved.

The interfaces to be used for testing are determined by the probe mode. There are currently two modes:
    1. Wireless mode
    2. Ethernet mode

In wireless mode, all test traffic needs to flow over the wireless interface. Management traffic may 
flow over any nominated interface, which may include the wireless or ethernet interfaces. It is also
possible that other interfaces (e.g. a VPN interface (Zeortier for instance)) that are used for 
management connectivity. The test traffic needs to flow towards the "WAN" direction, generally out to
the Internet to test remote resources. It is assumed that as we have selected wireless mode, the 
required test resources can be reached over the wireless Interface.

In Ethernet mode, all test traffic needs to flow over the ethernet interface, rather than the 
wireless interface. This is generally easier to achieve, as ethernet interfaces have lower 
metrics that wireless interfaces and are selected as the natual default gateway (but, we can't 
make this assumption globally...there may be future changes with high speed wireless connections)

Route Checking/Modification
---------------------------

The process for obtaining the correct traffic flows is as follows:

1. Check the route that will be used to hit the test domain - this is done by looking up 
   the route to nominated IP destination out in the test domain (usually the Internet). This
   can be achieved using the "ip" command - for instance:

   ip route show to match 8.8.8.8

2. If route lookup indicates test traffic will hit the required interface, our default route 
   is already set a we need it.

3. If the route lookup indicates that the incorrect interface is used as the default route, add
   a default route that selects the desired interface. Then, replace the previously observered
   default route with a the same default route entry, but with a high metric (to discourage its
   use compared to the new default route we added). 
   
   Add a new default route that goes via the correct interface (with no metric...i.e. zero)

   Finally, bounce the interface that has just had the default route added, to ensure the probe 
   routing table reflects the desired routing table sequence and that the new default route 
   obtains a gateway setting (I forgot this final step which caused me 2 days of angst...):
   
   ip route del default via 192.168.0.1 dev eth0
   ip route add default via 192.168.0.1 dev eth0 metric 500
   ip route add default dev wlan0
   ifdown wlan0; ifup wlan0
   
4. Perform a route lookup again to verify that test traffic will now hit the required interface:

   ip route show to match 8.8.8.8

5. The steps above are shown for IPv4 networks. This also needs to be repeated for IPV6 networks 
   if IPv6 is enabled

6. Finally, make sure that there is a viable route for management traffic:

    a. Lookup the route to the IP of the mgt platform
    b. If the correct interface is not being used, inject a single host route to force mgt
       traffic over the correct interface. The interface must obviously have a viable onward 
       path to the mgt server once the mgt traffic is sent over that interface. (Note: this 
       may be an IPv4 or IPv6 address)

"""
import socket
import subprocess
import re
import sys, os
from wiperf_poller.helpers.os_cmds import IP_CMD

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

def lookup(hostname, ip_ver, file_logger):
    """
    Perform a name lookup using the specfied IP family version specified (i.e. IPv4 or IPv6)
    """

    if ip_ver == "ipv4": family=socket.AF_INET
    elif ip_ver == "ipv6": family=socket.AF_INET6
    else: raise ValueError("Supplied ip_ver should be ipv4 or ipv6")

    try:
        ip_address = socket.getaddrinfo(hostname, 0, family=family)[0][4][0]
        file_logger.info("  DNS hostname lookup : {} / Result: {}".format(hostname, ip_address))
        return ip_address
    except Exception as ex:
        file_logger.error("  Issue looking up host {} (DNS or hostname Issue?): {}".format(hostname, ex))
        return False

def resolve_name_ipv4(hostname, file_logger, strict=True):
    """
    if hostname passed, DNS lookup & only return IPv4 result, otherwise, return unchanged IP address
    """
    if is_ipv4(hostname): return hostname  
    
    if is_ipv6(hostname) and strict == True:
        raise ValueError("IPv6 address passed to resolve_name_ipv4(), should be IPv4: {}".format(hostname))

    return lookup(hostname, "ipv4", file_logger)

def resolve_name_ipv6(hostname, file_logger, strict=True):
    """
    if hostname passed, DNS lookup & only return IPv6 result, otherwise, return unchanged IP address
    """
    if is_ipv6(hostname): return hostname  
    
    if is_ipv4(hostname) and strict == True:
        raise ValueError("IPv4 address passed to resolve_name_ipv4(), should be IPv6: {}".format(hostname))

    return lookup(hostname, "ipv6", file_logger)

def resolve_name(hostname, file_logger, config_vars):
    """
    Generic name lookup (IPv4/IPv6) - if hostname passed, DNS lookup, otherwise, return unchanged IP address
    """

    if is_ipv6(hostname): return hostname 
    if is_ipv4(hostname): return hostname 

    # lets try an IPv4 lookup on this hostname
    if config_vars['ipv4_enabled'] == 'yes':
        ip_address = resolve_name_ipv4(hostname, file_logger, strict=False)
        if ip_address: return ip_address
    
    # Let's try an IPv6 lookup on this hostname
    if config_vars['ipv6_enabled'] == 'yes':
        ip_address = resolve_name_ipv6(hostname, file_logger, strict=False)
        if ip_address: return ip_address

    file_logger.error("  All name lookup combinations failed for this host: {}".format(hostname))
    return False

def _field_extractor(pattern, cmd_output_text):
    """
    Generic field extraction from string based on pattern passed
    """
    re_result = re.search(pattern, cmd_output_text)

    if not re_result is None:
        field_value = re_result.group(1)
        return field_value
    else:
        return None
  
def get_test_traffic_interface(config_vars, file_logger):
    """
    Return the interface name used for testing traffic, based on the probe mode
    """
    probe_mode = config_vars['probe_mode']

    if probe_mode == "wireless": return config_vars['wlan_if'] 
    if probe_mode == "ethernet": return config_vars['eth_if'] 
        
    file_logger.error("  Unknown probe mode: {} (exiting)".format(probe_mode))
    sys.exit()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# IPv4 Utils
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def get_routes_used_to_dest_ipv4(ip_address, file_logger):

    ip_address = resolve_name_ipv4(ip_address, file_logger)

    # get entries that match destination
    ip_route_cmd = "{} route show to match {}".format(IP_CMD, ip_address) 

    try:
        route_list = subprocess.check_output(ip_route_cmd, stderr=subprocess.STDOUT, shell=True).decode().split("\n")
        file_logger.info("  Checked interface routes to : {}. Result: {}".format(ip_address, route_list))
        return route_list
    except subprocess.CalledProcessError as exc:
        output = exc.output.decode()
        file_logger.error("  Issue looking up routes (route cmd syntax?): {} (command used: {})".format(str(output), ip_route_cmd))
        return ''

def get_first_route_to_dest_ipv4(ip_address, file_logger):
    """
    Check the routes to a specific ip destination & return first entry
    """

    route_list = get_routes_used_to_dest_ipv4(ip_address, file_logger)

    if len(route_list) > 0:
        first_route = route_list[0]
        file_logger.info("  Checked interface route to : {}. Result: {}".format(ip_address, first_route))
        return first_route
    else:
        file_logger.warning("  Unable to determine first route to destination.")
        return False

def check_correct_mgt_interface_ipv4(mgt_host, mgt_interface, file_logger):
    """
    This function checks if the correct interface is being used for mgt traffic
    """
    file_logger.info("  Checking we will send mgt traffic over configured interface '{}' mode.".format(mgt_interface))

    # figure out mgt_ip (in case hostname passed)
    mgt_ip = resolve_name_ipv4(mgt_host, file_logger)

    route_to_dest = get_first_route_to_dest_ipv4(mgt_ip, file_logger)

    if mgt_interface in route_to_dest:
        file_logger.info("  Mgt interface route looks good.")
        return True
    else:
        file_logger.info("  Mgt interface will be routed over wrong interface: {}".format(route_to_dest))
        return False

def check_correct_mode_interface_ipv4(host, config_vars, file_logger):
    """
    Check that mgt traffic will go over correct interface for the selected mode
    """
    # this could be a hostname, try a name resolution just in case
    ip_address = resolve_name_ipv4(host, file_logger)

    # check test traffic will go via correct interface depending on mode
    test_traffic_interface= get_test_traffic_interface(config_vars, file_logger)
    
    # get i/f name for route
    if not is_ipv4(ip_address):
        raise ValueError("IP address supplied is not IPv4 format")

    route_to_dest = get_first_route_to_dest_ipv4(ip_address, file_logger)

    if test_traffic_interface in route_to_dest:
        return True
    else:
        return False

def inject_default_route_ipv4(ip_address, config_vars, file_logger):

    """
    This function will attempt to inject an IPv4 default route for the test
    traffic interface. All other detected default routes will be removed. The
    default route will also be modified to use a metric of 0 if existing, or
    added with a metric of 0 if it does not exist

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
            delete it and re-add it with a metric of 0
         - if not:
            delete it
    3. If no default route has been found, add a suitable
       default route with a metric of 0

    (Note the interface that provides the new default route *must* be bounced to
    update the probe routing table correctly)
    """

    # get the default route to our ipv6 destination
    route_list = get_routes_used_to_dest_ipv4(ip_address, file_logger) 
    
    file_logger.info('  [Default Route Injection (IPv4)] Checking if we can fix default routing to use correct test interface...')

    # figure out what our required interface is for testing traffic
    probe_mode = config_vars['probe_mode']
    file_logger.info("  [Default Route Injection (IPv4)] Checking probe mode: '{}' ".format(probe_mode))
    test_traffic_interface= get_test_traffic_interface(config_vars, file_logger)
    file_logger.info("  [Default Route Injection (IPv4)] Testing interface: '{}' ".format(test_traffic_interface))

    # step through routes and remove each default route that does not match test interface
    test_interface_route_fixed = False

    file_logger.info("  [Default Route Injection (IPv4)] Checking routes...")
    
    for route_to_dest in route_list:

        # This fix relies on the retrieved route being a default route in the 
        # format: default via 192.168.0.1 dev eth0

        # if an empty entry slips through, ignore
        if not route_to_dest:
            continue
        
        if not "default" in route_to_dest:
            # this isn't a default route, so we can't fix this
            file_logger.debug('  [Default Route Injection (IPv4)] Route is not a "default" route entry...unable to update this route: {}'.format(route_to_dest))
            continue
              
        # delete default route
        try:
            del_route_cmd = "{} route del ".format(IP_CMD) + route_to_dest
            subprocess.run(del_route_cmd, shell=True)
            file_logger.info("  [Default Route Injection (IPv4)] Deleting route: {}".format(route_to_dest))
        except subprocess.CalledProcessError as proc_exc:
            file_logger.error('  [Default Route Injection (IPv4)] Route deletion failed!: {}'.format(proc_exc))
            return False
        
        # if a match for test interface, modify metric & re-add
        if test_traffic_interface in route_to_dest:

            if "metric" in route_to_dest:
                route_to_dest =  re.sub(r"metric \d+", r"metric 0", route_to_dest)
            else:
                route_to_dest += " metric 0"

            try:
                add_route_cmd = "{} route add  ".format(IP_CMD) + route_to_dest
                subprocess.run(add_route_cmd, shell=True)
                file_logger.info("  [Default Route Injection (IPv4)] Re-adding deleted route with modified metric: {}".format(route_to_dest))
            except subprocess.CalledProcessError as proc_exc:
                file_logger.error('  [Default Route Injection (IPv4)] Route addition failed!')
                return False
            
            # signal that test traffic interface route updated
            if test_traffic_interface in route_to_dest:
                test_interface_route_fixed = True
        
    if not test_interface_route_fixed:

        # We didn't manage to fix our routing issue (most likely as there was another interface
        # being used for the default route), so lets try adding a default route for the interface
        # we're testing over.
        #
        # We need to add a route in the format:
        #   ip route add default dev wlan0 via 192.168.1.1 metric 0 
        #
        # Process: pull out last "lease { }" entry for interface and extract "option routers"
        #          to use as def gw for routing table
        #          file: /var/lib/dhcp/dhclient.eth0.leases
        #          format: option routers 192.168.1.1;

        lease_file_name = "/var/lib/dhcp/dhclient.{}.leases".format(test_traffic_interface)
        leases_file_content = ''

        if os.path.exists(lease_file_name):
            try:
                with open(lease_file_name, 'r') as f:
                    leases_file_content = f.read()
            except Exception as ex:
                file_logger.error("  [Default Route Injection (IPv4)] Issue reading lease file: {}. Route addition failed!".format(ex))
                return False
        else:
            file_logger.error('  [Default Route Injection (IPv4)] Unable to find required lease file for {}. Route addition failed!'.format(test_traffic_interface))
            return False
        
        # find all instances of the "option routers" configuration line
        option_routers_list = re.findall("option routers .*?\;", leases_file_content)

        if len(option_routers_list) < 1:
            file_logger.error('  [Default Route Injection (IPv4)] Unable to determine def gw for route addition. Route addition failed!')
            return False
        
        # pull out the IP address from the last instance of the "option routers" line 
        option_router_line = option_routers_list[-1]
        def_gw = _field_extractor('\d+\.\d+\.\d+\.\d+', option_router_line)
    
        if not def_gw:
            file_logger.error('  [Default Route Injection (IPv4)] Unable to determine def gw from leases file. Route addition failed!')
            return False

        # add default route via test interface
        route_to_dest = "default dev {} via {} metric 0".format(test_traffic_interface, def_gw)

        try:
            add_route_cmd = "{} route add  {}".format(IP_CMD, route_to_dest)
            subprocess.run(add_route_cmd, shell=True)
            file_logger.info("  [Default Route Injection (IPv4)] Adding test interface route: {}".format(route_to_dest))
        except subprocess.CalledProcessError as proc_exc:
            file_logger.error('  [Default Route Injection (IPv4)] Route addition failed!')
            return False
        
        # signal that test traffic interface route updated
        if test_traffic_interface in route_to_dest:
            test_interface_route_fixed = True
        
    file_logger.info("  [Default Route Injection (IPv4)] Route injection operation complete")
    
    return test_interface_route_fixed

def remove_duplicate_interface_route_ipv4(interface_ip, interface_name, file_logger):

   # Lookup the routing entry of the subnet that on which the testing interface resides, then find & 
   # remove any duplicate routing table entries - this prevents test traffic leaking out of other local
   # interfaces when 2 local interfaces are on same subnet:

   # get routes to the supplied interface address
    ip_route_cmd = "{} route show to match ".format(IP_CMD) + interface_ip + " | grep '/'"
    file_logger.info("  [Check Interface Routes (IPv4)] Checking if we need to remove any interface routes...")

    try:
        routes = subprocess.check_output(ip_route_cmd, stderr=subprocess.STDOUT, shell=True).decode().splitlines()
        file_logger.info("  [Check Interface Routes (IPv4)] Checked interface route to : {}. Result: {}".format(interface_ip, routes))
    except subprocess.CalledProcessError as exc:
        output = exc.output.decode()
        file_logger.error("  [Check Interface Routes (IPv4)] Issue looking up route (route cmd syntax?): {} (command used: {})".format(str(output), ip_route_cmd))
        return False
    
    # check each route entry and delete any that are not our interface of interest
    for route_entry in routes:
        if not (interface_name in route_entry):
            # delete the route entry
            try:
                del_route_cmd = "{} route del ".format(IP_CMD) + route_entry
                subprocess.run(del_route_cmd, shell=True)
                file_logger.info("  [Check Interface Routes (IPv4)] Deleting route: {}".format(route_entry))
            except subprocess.CalledProcessError as proc_exc:
                file_logger.error('  [Check Interface Routes (IPv4)] Route deletion failed!: {}'.format(proc_exc))
                return False
    
    file_logger.info("  [Check Interface Routes (IPv4)] Checks/operations complete.")
    return True


def _inject_static_route_ipv4(ip_address, req_interface, traffic_type, file_logger, ip_ver=""):

    """
    This function will attempt to inject an IPv4 static route to correct
    routing issues for specific targets that will not be reached via
    the intended interface without the addition of this route.

    A static route will be inserted in to the probe route table to send 
    matched traffic over a specific interface
    """

    file_logger.info("  [Host Route Injection (IPv4)] Attempting {} static route insertion to fix routing issue".format(traffic_type))
    try:
        new_route = "{} dev {}".format(ip_address, req_interface)
        add_route_cmd = "{} {} route add  ".format(IP_CMD, ip_ver) + new_route
        subprocess.run(add_route_cmd, shell=True)
        file_logger.info("  [Host Route Injection (IPv4)] Adding new {} traffic route: {}".format(traffic_type, new_route))
    except subprocess.CalledProcessError as proc_exc:
        output = proc_exc.output.decode()
        file_logger.error('  [Host Route Injection (IPv4)] Route addition ({})failed! ({})'.format(traffic_type, output))
        return False

    file_logger.info("  [Host Route Injection (IPv4)] Route injection ({})complete".format(traffic_type))
    return True


def inject_mgt_static_route_ipv4(ip_address, config_vars, file_logger):
    """
    Inject a static route (ipv4) to correct routing issue for mgt traffic
    """
    mgt_interface = config_vars['mgt_if']

    if not is_ipv4(ip_address): 
        raise ValueError("Supplied IP address for static route is not IPv4 format")
    
    return _inject_static_route_ipv4(ip_address, mgt_interface, "mgt", file_logger)

#TODO: remove?
def inject_test_traffic_static_route_ipv4(host, config_vars, file_logger):
    """
    Inject a static route to correct routing issue for specific test traffic 
    destination (e.g. iperf)
    """
    probe_mode = config_vars['probe_mode']
    file_logger.info("  [Host Route Injection (IPv4)] Checking probe mode: '{}' ".format(probe_mode))
    test_traffic_interface= get_test_traffic_interface(config_vars, file_logger)

    # figure out ip (in case hostname passed)
    ip_address = resolve_name_ipv4(host, file_logger)

    # if route injection works, check that route is now over correct interface
    if _inject_static_route_ipv4(ip_address, test_traffic_interface, "test traffic", file_logger):

       if check_correct_mode_interface_ipv4(ip_address, config_vars, file_logger):

           return True
    
    # Something went wrong...
    return False






