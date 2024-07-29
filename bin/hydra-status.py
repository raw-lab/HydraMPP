#!/usr/bin/env python


import argparse
import pickle
import socket

from hydraMPP.log import *


parser = argparse.ArgumentParser()
parser.add_argument("address", nargs='?', type=str, default="127.0.0.1", help="Address of the HydraMPP server to get status from [127.0.0.1]")
parser.add_argument("port", nargs='?', type=int, default=24515, help="Port to connect to [24515]")
args = parser.parse_args()

sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
sock.settimeout(1)

try:
	sock.sendto("Status".encode(), (args.address, args.port))
	#msg,_ = sock.recvfrom(1024)
	data,addr = sock.recvfrom(65536)

	now,nodes,queue = pickle.loads(data)

	print(f"{now[3]}:{now[4]}:{now[5]}")

	print(f"\nNODES: {sum([n['cpus'] for n in nodes])} / {sum([n['num_cpus'] for n in nodes])}")

	for node in nodes:
		print(f"{node['hostname']:<15}{node['cpus']:>4} / {node['num_cpus']}")

	print(f"QUEUE:", len(queue))
	for k,v in queue.items():
		try:
			print(f"{k:<4}{v['hostname']:<15}\t{v['finished']}: {v['num_cpus']} | {v['func_name']}")
		except Exception as e:
			printlog("ERROR:", k)
			printlog(e)

except socket.timeout:
	pass
exit(0)
