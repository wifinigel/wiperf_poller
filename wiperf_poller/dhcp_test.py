import time
import subprocess
import os

interface = 'eth0'

start = time.time()
#try:
#    subprocess.check_output("{} -v {} -pf /tmp/dhclient.pid".format(DHCLIENT_CMD, self.interface), shell=True)
#except subprocess.CalledProcessError as exc:
#    output = exc.output.decode()
#    self.file_logger.error("Issue renewing IP on interface: {}, issue {}".format(self.interface, output))
#    self.bounce_interface(self.interface, self.file_logger)
cmd = "{} -v {} -pf /tmp/dhclient.pid".format('/sbin/dhclient', interface)
p = subprocess.Popen(['dhclient', '-v', 'eth0'], stderr=subprocess.PIPE) # add stderr=subprocess.PIPE) to merge output & error
while True:
    line = p.stderr.readline()
    print("test:", line.rstrip())
    if b'DHCPACK' in line:
        break
    if not line:
        break
    
end = time.time()

duration = int(round((end - start) * 1000))
print("Duration = {}".format(duration))