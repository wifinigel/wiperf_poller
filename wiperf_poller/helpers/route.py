
from socket import gethostbyname
import subprocess
import re
import sys

def get_route_to_dest(ip_address, file_logger):

    # If ip address is a hostname rather than an IP, do a lookup and substitute IP
    if re.search(r'[a-z]|[A-Z]', ip_address):
        hostname = ip_address
        # watch out for DNS Issues
        try:
            ip_address = gethostbyname(hostname)
            file_logger.info(
                "DNS hostname lookup : {}. Result: {}".format(hostname, ip_address))
        except Exception as ex:
            file_logger.error(
                "Issue looking up host {} (DNS Issue?): {}".format(hostname, ex))
            return False

    #ip_route_cmd = "/bin/ip route show to match " + ip_address + " | head -n 1 | awk '{print $5}'"
    ip_route_cmd = "/bin/ip route show to match " + ip_address + " | head -n 1"

    try:
        route_detail = subprocess.check_output(ip_route_cmd, stderr=subprocess.STDOUT, shell=True).decode()
        file_logger.info("Checked interface route to : {}. Result: {}".format(ip_address, route_detail.strip()))
        return route_detail.strip()
    except subprocess.CalledProcessError as exc:
        output = exc.output.decode()
        file_logger.error("Issue looking up route (route cmd syntax?): {} (command used: {})".format(str(output), ip_route_cmd))
        return ''

    
def check_correct_mode_interface(ip_address, config_vars, file_logger):

    """
    This function checks whether we use the expected interface to get to the Internet, 
    depending on which mode the probe is operating.

    Modes:
        ethernet : we expect to get to the Internet over the eth interface (usually eth0)
        wireless : we expect to get to the Internet over the WLAN interface (usually wlan0) 

    args:
        ip_address: IP address of target out on the Internet
        config_vars: dict of all config vars
        file_logger: file logger object so that we can log operations
    """

    # check test to Internet will go via correct interface depending on mode
    internet_interface = ''
    probe_mode = config_vars['probe_mode']

    file_logger.info("Checking we are going to Internet on correct interface as we are in '{}' mode.".format(probe_mode))
    
    if probe_mode == "wireless":
        internet_interface = config_vars['wlan_if']
    
    elif probe_mode == "ethernet":
        internet_interface = config_vars['eth_if']
    else:
        file_logger.error("Unknown probe mode: {} (exiting)".format(probe_mode))
        sys.exit()

    # get i/f name for route
    route_to_dest = get_route_to_dest(ip_address, file_logger)

    if internet_interface in route_to_dest:
        return True
    else:
        return False
    
def inject_default_route(ip_address, config_vars, file_logger):

    """
    This function will attempt to inject a default route to attempt correct
    routing issues caused by path cost if the ethernet interface is up and
    is preferred to the WLAN interface. It will also fix other scenarios
    I haven't thought of yet.

    (Note: this didn't work as expected - left here for possible future use.)
    """

    # get the default route to our destination
    route_to_dest = get_route_to_dest(ip_address, file_logger)
  
    # delete and re-add route with a new metric
    try:
        del_route_cmd = "/bin/ip route del " + route_to_dest
        subprocess.run(del_route_cmd, shell=True)
        file_logger.info("Deleting route: {}".format(route_to_dest))
    except subprocess.CalledProcessError as proc_exc:
        file_logger.error('Route deletion failed!: {}'.format(proc_exc))
        return False
    
    try:
        modified_route = route_to_dest + " metric 500"
        add_route_cmd = "/bin/ip route add  " + modified_route
        subprocess.run(add_route_cmd, shell=True)
        file_logger.info("Re-adding deleted route with new metric: {}".format(modified_route))
    except subprocess.CalledProcessError as proc_exc:
        file_logger.error('Route addition failed!')
        return False

    # figure out what our required interface is
    probe_mode = config_vars['probe_mode']
    file_logger.info("Checking probe mode: '{}' ".format(probe_mode))
    internet_interface = ''

    if probe_mode == "wireless":
        internet_interface = config_vars['wlan_if']
    
    elif probe_mode == "ethernet":
        internet_interface = config_vars['eth_if']
    else:
        file_logger.error("Unknown probe mode: {} (exiting)".format(probe_mode))
        sys.exit()


    # inject a new route with the required interface
    try:
        new_route = "default dev {}".format(internet_interface)
        add_route_cmd = "/bin/ip route add  " + new_route
        subprocess.run(add_route_cmd, shell=True)
        file_logger.info("Adding new route: {}".format(modified_route))
    except subprocess.CalledProcessError as proc_exc:
        file_logger.error('Route addition failed!')
        return False

    file_logger.info("Route injection complete")
    return True
