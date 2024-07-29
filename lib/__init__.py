# -*- coding: utf-8 -*-

"""hydraMPP: Module for Distributed Parallel Processing

Hydra MPP is a Python library for Distributed Parallel Processing.
DPP utilizes multiple nodes/computers to distribute workloads for
faster processing.

Currently this module is compatible as a basic stand in for Ray.
Not all features are fully implemented yet.

Data Structure formats:

NODES: list
NODES[i]: dict
  socket: socket.socket
  address: address
  hostname: str (unique)
  num_cpus: int
  cpus: int

QUEUE: dict
key = id:int
value = list(
0	finished:bool
1	func.name:str
2	ret:obj
3	num_cpus:int
4	time_to_run:float
5	hostname:str )

packet (to client): list
0	id:int
1	func.name:str
2	args:list
3	kwargs:dict

"""

__version__ = "0.0.2"


import sys
import socket
import atexit
import multiprocessing as mp
import socket
import pickle
import psutil
import time
from pathlib import Path
import re
import subprocess

from .log import *
from .net import *
from .client import *


## GLOBAL VARIABLES ##
MANAGER = mp.Manager()
NODES = MANAGER.list()
QUEUE = MANAGER.dict()

SLURM_CLIENTS = list()
RUNNING = False
SLURM = False
P = None
CURR_ID = 0
WORKERS = dict()


## CLASS ##
class Worker:
	def __init__(self, func):
		self.func = func
		self.reset()
		return
	
	def reset(self):
		self.num_cpus = 1
		return

	def options(self, num_cpus=1):
		self.num_cpus = num_cpus
		return self

	def remote(self, *args, **kwargs):
		global NODES
		global CURR_ID
		def __worker(func, id, args, kwargs):
			global NODES
			global CURR_ID
			start = time.time()
			ret = None
			try:
				ret = func(*args, **kwargs)
			except Exception as e:
				printlog("ERROR REMOTE:", id, func)
				printlog(e)
			finally:
				NODES[0]['cpus'] += QUEUE[id][3]
				#QUEUE[id] = [True, func.__name__, ret, QUEUE[id][3], time.time()-start, NODES[0]['hostname']]
				QUEUE[id][0],QUEUE[id][2],QUEUE[id][4] = [True, ret, time.time()-start]
				#TODO: Save result to file for RAM conservation
				#with Path(NODES[0]['ObjectStoreSocketName'], f"{id}_{func.__name__}").open('wb') as f:
				#	pickle.dump(QUEUE[id], f)

		CURR_ID += 1
		id = CURR_ID
		QUEUE[id] = MANAGER.list([False, self.func.__name__, None, self.num_cpus, 0, ""])
		while True:
			time.sleep(0.1)
			for i in range(0, len(NODES)):
				#cpus_ready = sum([])
				if NODES[i]['cpus'] >= self.num_cpus:
					NODES[i]['cpus'] -= self.num_cpus
					QUEUE[id][5] = NODES[i]['hostname']
					if i == 0:
						mp.Process(target=__worker, args=[self.func, id, args, kwargs]).start()
					else:
						packet = pickle.dumps({id:[self.func.__name__, args, kwargs, self.num_cpus]})
						send_msg(NODES[i]['socket'], packet)
					break
			else:
				# Finished loop without finding available node, retry
				continue
			break
		self.reset()
		return id

## METHODS ##
def init(address="local", num_cpus=None, timeout=5, port=24515, log_to_driver=False):
	def is_ip(a,p):
		return True #TODO: Actually check for valid ip address format
	global P
	global NODES
	global RUNNING
	global SLURM
	if SLURM:
		printlog("Started with slurm options")
		return True
	if RUNNING:
		printlog("WARNING: HydraMPP Already running, skipping re-init. Shutdown first, and try again")
		return True
	RUNNING = True

	hostnames = set()
	if not num_cpus:
		num_cpus = psutil.cpu_count()
	hostnames.add(socket.gethostname())
	NODES = [MANAGER.dict(
		hostname = socket.gethostname(),
		num_cpus = num_cpus,
		cpus = num_cpus,
		temp = Path("tmp-hydra"),
		ObjectStoreSocketName = Path("tmp-hydra", "objects"))]
	NODES[0]['ObjectStoreSocketName'].mkdir(parents=True, exist_ok=True)
	printlog("Starting HydraMPP (Massive Parallel Processing)", __version__)

	# Network connection
	printlog("Connecting to:", address)
	if address == "local":
		NODES[0]['address'] = "local"
		#NODES[0]['socket'] = Path("tmp-hydra", 'socket.txt').open('w')
	elif address == "host":
		NODES[0]['address'] = "host"
		h_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		h_socket.settimeout(0.5)
		h_socket.bind(("", port))
		h_socket.listen(5)
		NODES[0]['socket'] = h_socket
		start = time.time()
		printlog("HOST INFO: waiting for clients")
		while time.time() < start+timeout:
			try:
				(sock, (addr, port)) = h_socket.accept()
				sock.settimeout(0)
				printlog("HOST Accepted connection from:", addr)
				msg = sock.recv(1024).decode("utf-8")
				match = re.search(r'cpus:(\d+),hostname:(.+)', msg)
				if match:
					cpus = int(match.group(1))
					hostname = match.group(2)
				else:
					printlog("HOST ERROR: bad handshake from client")
					break
				re_add = re.compile(r'\((\d+)\)$')
				while hostname in hostnames:
					match = re_add.search(hostname)
					if match:
						d = int(match.group(1)) + 1
						hostname = re_add.sub(f"({d})", hostname)
					else:
						hostname += "(1)"
				hostnames.add(hostname)
				NODES += [MANAGER.dict(
					hostname = hostname,
					address = addr,
					socket = sock,
					cpus = cpus,
					num_cpus = cpus
				)]
			except socket.timeout:
				pass
			except Exception as e:
				printlog("HOST ERROR: Socket error")
				printlog(e)
	elif is_ip(address, port):
		sock = client_init(address, port, num_cpus)
		if sock:
			client_listen(sock, WORKERS)
		else:
			printlog("CLIENT: FAILED TO CONNECT")
		sys.exit(0)
	else:
		printlog("ERROR: address needs to be one of 'local', 'host', or an ip-address of a host to connect to.")
		return False

	P = mp.Process(target=main_loop)
	P.start()
	return True


def main_loop():
	address = ("", 24515)
	sock_status = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
	sock_status.bind(address)	
	sock_status.setblocking(False)
	max_sent = 0

	print("UDP server up and listening")
	start = time.time()
	while RUNNING:
		time.sleep(0.1)
		for i in range(1, len(NODES)):
			try: msg = recv_msg(NODES[i]['socket'])
			except: msg = None
			if msg:
				(id,(func_name,ret,duration)), = pickle.loads(msg).items()
				NODES[i]['cpus'] += QUEUE[id][3]
				QUEUE[id][0], QUEUE[id][2], QUEUE[id][4] = [True, ret, duration]
				#QUEUE[id] = [True, func_name, ret, QUEUE[id][3], duration, NODES[i]['hostname']]

		# Listen for status request
		try:
			msg,addr = sock_status.recvfrom(1024)
			if msg:
				now = time.localtime()
				nodes = list()
				for node in NODES:
					nodes += [dict(
						address = node['address'],
						hostname = node['hostname'],
						num_cpus = node['num_cpus'],
						cpus = node['cpus'],
						)]
				queue = dict()
				for k,v in QUEUE.items():
					queue[k] = dict(
						finished = v[0],
						func_name = v[1],
						#ret = v[2],
						num_cpus = v[3],
						runtime = v[4],
						hostname = v[5]
					)
				data = pickle.dumps((now, nodes, queue))
				if len(data) > max_sent:
					max_sent = len(data)
				sock_status.sendto(data, addr)
				#sendto_msg(sock_status, data, addr)
		except socket.error: pass
		except Exception as e:
			printlog("RECV ERROR:")
			printlog(e)

		continue
		if time.time() > start+1:
			start = time.time()
			with open(NODES[0]["temp"]/"status.log", 'w') as writer:
				now = time.localtime()
				print(f"{now[3]}:{now[4]}:{now[5]}", file=writer)
				print(f"\nNODES: {sum(([n['cpus'] for n in NODES]))} / {sum([n['num_cpus'] for n in NODES])}", file=writer)
				for node in NODES:
					print(node['hostname'], f"{node['cpus']} / {node['num_cpus']}", sep='\t', file=writer)
				print(f"QUEUE:", len(QUEUE), file=writer)
				for k,v in QUEUE.items():
					try:
						print(f"{k}:{v[5]}\t{v[0]}:{v[1]} {v[3]}", file=writer)
					except Exception as e:
						printlog("MAIN LOOP QUEUE ERROR:", k)
						printlog(e)
						pass
				writer.flush()
	sock_status.close()
	return

def nodes():
	return NODES

def get(id:int):
	if QUEUE[id][0]:
		return QUEUE.pop(id)
	else:
		return QUEUE[id]

def put(name:str, obj:tuple):
	global CURR_ID
	CURR_ID += 1
	QUEUE[CURR_ID] = MANAGER.list([True, name, obj, 0, 0, NODES[0]['hostname']])
	return CURR_ID

def wait(objects:list, timeout=0, max=1):
	ready = list()
	objects = list(objects)
	start = time.time()
	while objects and len(ready) < max:
		time.sleep(0.1)
		for i in range(len(objects)):
			id = objects[i]
			if QUEUE[id][0]:
				ready += [objects.pop(i)]
				break
		if time.time() < start+timeout:
			break
	return ready, objects

def remote(func):
	worker = Worker(func)
	WORKERS[func.__name__] = func
	return worker

def shutdown():
	global RUNNING
	if not RUNNING:
		return
	RUNNING = False
	printlog("Hydra DMPP: Shutdown")
	for node in NODES:
		if 'socket' in node:
			node['socket'].close()
	try:
		P.kill()
		P.join()
	except: pass
	MANAGER.shutdown()
	#if self.paccept:
	#	self.paccept.kill()
	for p in mp.active_children():
		p.kill()
	#for id,p in self.procs.items():
	#	p.kill()
	#printlog(self.curr_id)
	time.sleep(1)
	return


### Execute commands on loading HydraMPP ###

atexit.register(shutdown)

if re.search(r'--hydra-', ''.join(sys.argv)):
	import argparse
	parser = argparse.ArgumentParser()
	s_parser = parser.add_mutually_exclusive_group()
	s_parser.add_argument('--hydra-slurm', type=str, help=argparse.SUPPRESS)
	s_parser.add_argument('--hydra-client', type=str, help=argparse.SUPPRESS)
	args,argv = parser.parse_known_args()

	# clear hydra flags from sys.argv
	sys.argv = [sys.argv[0]] + argv

	if "hydra_slurm" in args:
		cmd = ["scontrol", "show", "hostnames", args.hydra_slurm]
		nodes = subprocess.run(cmd, stdout=subprocess.PIPE, text=True).stdout.split()
		printlog("Starting HydraMPP on slurm nodes:", nodes)
		
		cmd = ["srun", "--nodes=1", "--ntasks=1", "-w", nodes[0], "hostname", "--ip-address"]
		head_ip = subprocess.run(cmd, stdout=subprocess.PIPE, text=True).stdout
		printlog("HEAD IP:", head_ip)

		p = mp.Process(target=init, args=["host"])
		p.start()
		time.sleep(1)

		for i in range(1, len(nodes)):
			cmd = sys.argv + ["--hydra-client", head_ip]
			printlog("CMD:", cmd)
			SLURM_CLIENTS += [subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)]
		p.join()
	elif "hydra_client" in args:
		init(args.hydra_client)

	SLURM = True
	sys.exit(0)
#   nodes=$(scontrol show hostnames "$SLURM_JOB_NODELIST")
#   nodes_array=($nodes)
#   
#   head_node=${nodes_array[0]}
#   head_node_ip=$(srun --nodes=1 --ntasks=1 -w "$head_node" hostname --ip-address)
#   
#   #  export head_node_ip
#   >&2 echo "IP Head: $head_node_ip"
#   
#   >&2 echo "Starting HOST at $head_node"
#   srun --nodes=1 --ntasks=1 -w "$head_node" \
#     command time metacerberus.py --address host $args &
#   
#   sleep 1
#   
#   
#   # number of nodes other than the head node
#   worker_num=$((SLURM_JOB_NUM_NODES - 1))
#   
#   for ((i = 1; i <= worker_num; i++)); do
#     node_i=${nodes_array[$i]}
#     >&2 echo "Starting WORKER $i at $node_i"
#     srun --nodes=1 --ntasks=1 -w "$node_i" \
#       command time metacerberus.py --address $head_node_ip $args &>$node_i.log &
#   done