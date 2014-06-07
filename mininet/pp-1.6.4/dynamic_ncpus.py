"""
dynamic_ncpus.py
Open Mobile Hub

Runs a benchmark computation on given Parallel Python workers
Based on Vitalii Vanovschi's dynamic_ncpus.py
Edited by Gareth Johnson
"""

import math
import sys
import time
import pp

def part_sum(start, end):
    """Calculates partial sum"""
    sum = 0
    for x in xrange(start, end):
        if x % 2 == 0:
            sum -= 1.0 / x
        else:
            sum += 1.0 / x
    return sum

def print_usage():
	print "Usage: python dynamic_ncpus.py NUM_HOSTS HOST_IPS"
	print "where NUM_HOSTS is the number of remote broadcasting nodes to use"
	print "and HOST_IPS is the series of IP addresses for those hosts"
	print
	sys.exit()

# Check command-line usage
if len(sys.argv) < 2: print_usage()
	
print

num_hosts = int(sys.argv[1])
if len(sys.argv) != num_hosts + 2: print_usage()

ppservers = tuple()
for host in sys.argv[2:]:
	ppservers += (host,)

start = 1
end = 2000000

# Divide the task into 64 subtasks
parts = 64
step = (end - start) / parts + 1

# Create jobserver and discover the nodes that are broadcasting
job_server = pp.Server(ppservers=ppservers)
print "Looking for hosts..."
num_hosts_found = 0
hosts_found = set(['local'])
while num_hosts_found != num_hosts:
	active_nodes = set(job_server.get_active_nodes())
	hosts_found = hosts_found.union(active_nodes)
	new_num_hosts_found = len(hosts_found) - 1 # minus one for 'local'
	# If new hosts are found, then print total
	if new_num_hosts_found != num_hosts_found:
		num_hosts_found = new_num_hosts_found
		print "", num_hosts_found, "host(s) found:",
		for name in iter(hosts_found):
			if name != 'local':
				print name, " ",
		print
print "Done looking."
print
job_server.destroy()

hosts_found.remove('local') # 'local' is added by default; we don't want to add it again
ppservers = ()

# Execute the same task with different amount of remote servers and measure the time
for num_servers in range(1, num_hosts_found+1):
	if num_servers != 0:
		ppservers = ppservers + (hosts_found.pop(), )
	job_server = pp.Server(ppservers=ppservers, ncpus=0) # 0 cpus for jobserver
	jobs = []
	print "Connecting..."
	time.sleep(3) # a hack: wait for 3 seconds while ther server connects
	start_time = time.time()
	print "Using", num_servers, "remote host servers"
	for index in xrange(parts):
		starti = start+index*step
		endi = min(start+(index+1)*step, end)
        # Submit a job which will calculate partial sum
        # part_sum - the function
        # (starti, endi) - tuple with arguments for part_sum
        # () - tuple with functions on which function part_sum depends
        # () - tuple with module names which must be
        #      imported before part_sum execution
		jobs.append(job_server.submit(part_sum, (starti, endi)))
	print "Active nodes:", job_server.get_active_nodes()
	part_sum1 = sum([job() for job in jobs])
	print "Partial sum is", part_sum1, "| diff =", math.log(2) - part_sum1
	print "Time elapsed: ", time.time() - start_time, "s"
	print
	job_server.print_stats()
	job_server.destroy()
