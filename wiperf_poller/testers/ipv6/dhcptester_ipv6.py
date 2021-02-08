from wiperf_poller.testers.dhcptester import DhcpTester

class DhcpTesterIpv6(DhcpTester):
    """
    An IPv6 class to perform a DHCP release & renew and return the renewal time

    Bare bones class extension to provide an IPv6 library - provides
    possible future flexibility for addition of IPv6 related features
    """

    def __init__(self):

        super().__init__()

    
