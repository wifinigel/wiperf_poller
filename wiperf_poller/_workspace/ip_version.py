
#from ipv4_module import Ipv4 as Printer
#from ipv6_module import Ipv6 as Printer

import importlib

class IpVersionPrinter():

    def __init__(self, version="ipv4"):

        #super().__init__()

        if version=="ipv4":
            #from ipv4_module import Ipv4 as Printer
            module = importlib.import_module("ipv4_module")
        elif version=="ipv6":
            #from ipv6_module import Ipv6 as Printer
            module = importlib.import_module("ipv6_module")
        else:
            raise ValueError("Unknown version")

        self.printer = module.Printer()
