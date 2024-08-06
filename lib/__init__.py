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

__version__ = "0.0.4"


import sys
import os
import signal
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
#MANAGER = None
#NODES = None
#QUEUE = None

SLURM_CLIENTS = list()
RUNNING = False
SLURM = False
P = None
CURR_ID = 0
WORKERS = dict()


## REMOTE PROCS ###
def worker(func_name, id, NODES, QUEUE, args, kwargs):
	start = time.time()
	ret = None
	try:
		ret = WORKERS[func_name](*args, **kwargs)
	except Exception as e:
		printlog("ERROR REMOTE:", id, func_name)
		printlog(e)
	finally:
		NODES[0]['cpus'] += QUEUE[id][3]
		#QUEUE[id] = [True, func.__name__, ret, QUEUE[id][3], time.time()-start, NODES[0]['hostname']]
		QUEUE[id][2],QUEUE[id][4] = [ret, time.time()-start]
		QUEUE[id][0] = True
		#TODO: Save result to file for RAM conservation
		#with Path(NODES[0]['ObjectStoreSocketName'], f"{id}_{func.__name__}").open('wb') as f:
		#	pickle.dump(QUEUE[id], f)


def main_loop(NODES, QUEUE):
	RUNNING = True
	address = ("", 24515)
	sock_status = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
	sock_status.bind(address)	
	sock_status.setblocking(False)
	max_sent = 0

	print("Status server listening")
	while RUNNING:
		time.sleep(0.1)
		for i in range(1, len(NODES)):
			try: msg = recv_msg(NODES[i]['socket'])
			except: msg = None
			try:
				if msg:
					(id,(func_name,ret,duration)), = pickle.loads(msg).items()
					NODES[i]['cpus'] += QUEUE[id][3]
					QUEUE[id][2], QUEUE[id][4] = [ret, duration]
					QUEUE[id][0] = True
					#QUEUE[id] = [True, func_name, ret, QUEUE[id][3], duration, NODES[i]['hostname']]
			except Exception as e:
				printlog("ERROR: bad message from:", NODES[i]['hostname'])
				print(e)
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
	printlog("SERVER STOPPED LISTENING")
	RUNNING = False
	sock_status.close()
	return


def worker_listen(func_name, id, sock, args, kwargs):
	start = time.time()
	ret = None
	try:
		ret = WORKERS[func_name](*args, **kwargs)
	except Exception as e:
		printlog("CLIENT ERROR REMOTE:", id, func_name)
		printlog(e)
	finally:
		packet = {id:[func_name, ret, time.time()-start]}
		send_msg(sock, pickle.dumps(packet))
	return


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
		global MANAGER
		global NODES
		global QUEUE
		global CURR_ID

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
						mp.Process(target=worker, args=[self.func.__name__, id, NODES, QUEUE, args, kwargs]).start()
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
def init(address="local", num_cpus=None, timeout=10, port=24515, log_to_driver=False):
	def is_ip(a,p):
		return True #TODO: Actually check for valid ip address format
	global P
	global MANAGER
	global NODES
	global QUEUE
	global RUNNING
	global SLURM
	if SLURM == "Host":
		printlog("Host started through --hydraMPP options")
		return True
	elif SLURM:
		printlog("Client started through --hydraMPP options")
		address, port, num_cpus = SLURM
	if RUNNING:
		printlog("WARNING: HydraMPP Already running, skipping re-init. Shutdown first, and try again")
		return True
	RUNNING = True

	mp.freeze_support()
	mp.set_start_method("spawn")

	MANAGER = mp.Manager()
	NODES = MANAGER.list()
	QUEUE = MANAGER.dict()

	hostnames = set()
	if not num_cpus:
		num_cpus = psutil.cpu_count()
	hostnames.add(socket.gethostname())
	NODES += [MANAGER.dict(
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
		printlog(f"HOST INFO: waiting {timeout} seconds for clients")
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
			client_listen(sock)
		else:
			printlog("CLIENT: FAILED TO CONNECT")
		sys.exit(0)
	else:
		printlog("ERROR: address needs to be one of 'local', 'host', or an ip-address of a host to connect to.")
		return False

	atexit.register(shutdown, MANAGER, NODES, QUEUE)

	P = mp.Process(target=main_loop, args=[NODES, QUEUE])
	P.start()
	time.sleep(0.1)
	return True

def client_listen(sock:socket.socket):
	QUEUE = dict()

	# Listening Loop
	while is_connected(sock):
		msg = recv_msg(sock)
		if msg:
			(id,(func_name, args, kwargs, num_cpus)), = pickle.loads(msg).items()
			func = WORKERS[func_name]
			mp.Process(target=worker_listen, args=[func_name, id, sock, args, kwargs]).start()
		time.sleep(0.1)

	sock.close()

	printlog("INFO: Host disconnected")
	printlog("INFO: Terminating program")
	return

def nodes():
	global NODES
	return NODES

def get(id:int):
	global QUEUE
	if QUEUE[id][0]:
		return QUEUE.pop(id)
	else:
		return QUEUE[id]

def put(name:str, obj:tuple):
	global MANAGER
	global NODES
	global QUEUE
	global CURR_ID
	CURR_ID += 1
	QUEUE[CURR_ID] = MANAGER.list([True, name, obj, 0, 0, NODES[0]['hostname']])
	return CURR_ID

def wait(objects:list=None, timeout=0, max=1):
	global QUEUE
	ready = list()
	if not objects:
		objects = QUEUE.keys()
	objects = list(objects)
	start = time.time()
	while objects and len(ready) < max:
		time.sleep(0.01)
		for i in range(len(objects)):
			id = objects[i]
			if QUEUE[id][0]:
				ready += [objects.pop(i)]
				break
		if time.time() < start+timeout:
			break
	return ready, objects

def remote(func):
	global WORKERS
	worker = Worker(func)
	WORKERS[func.__name__] = func
	return worker

def shutdown(MANAGER, NODES, QUEUE):
	RUNNING = True
	if not RUNNING:
		return
	RUNNING = False
	printlog("HydraMPP: Shutdown")
	for node in NODES:
		if 'socket' in node:
			try:
				node['socket'].close()
			except: pass
	try:
		P.kill()
	except: pass
	MANAGER.shutdown()
	#if self.paccept:
	#	self.paccept.kill()
	for p in mp.active_children():
		try: p.kill()
		except: pass
		try: p.close()
		except: pass
		os.kill(p.ident, signal.SIGTERM)
	time.sleep(1)
	return


### Execute commands on loading HydraMPP ###

def slurm():
	global SLURM
	global SLURM_CLIENTS

	import argparse
	parser = argparse.ArgumentParser()
	s_parser = parser.add_mutually_exclusive_group()
	s_parser.add_argument('--hydraMPP-slurm', type=str, help=argparse.SUPPRESS)
	s_parser.add_argument('--hydraMPP-client', type=str, help=argparse.SUPPRESS)
	parser.add_argument('--hydraMPP-cpus', type=int, default=0, help=argparse.SUPPRESS)
	args,argv = parser.parse_known_args()

	# clear hydra flags from sys.argv
	sys.argv = [sys.argv[0]] + argv

	if args.hydraMPP_slurm:
		printlog("hydraMPP_slurm:", socket.gethostname())
		cmd = ["scontrol", "show", "hostnames", args.hydraMPP_slurm]
		node_list = subprocess.run(cmd, stdout=subprocess.PIPE, text=True).stdout.split()
		
		cmd = ["srun", "--nodes=1", "--ntasks=1", "-w", node_list[0], "hostname", "--ip-address"]
		head_ip = subprocess.run(cmd, stdout=subprocess.PIPE, text=True).stdout.strip()
		printlog("HOST IP:", head_ip)

		for i in range(1, len(node_list)):
			cmd = ["srun", "--nodes=1", "--ntasks=1", "-w", node_list[i]] + sys.argv + ["--hydraMPP-client", head_ip]
			SLURM_CLIENTS += [subprocess.Popen(cmd,
									  stdout=open(f"tmp-hydra/{node_list[i]}.stdout", 'w'),
									  stderr=open(f"tmp-hydra/{node_list[i]}.stderr", 'w')
									  )]
		init("host", timeout=5+len(SLURM_CLIENTS))
		SLURM = "Host"
	elif args.hydraMPP_client:
		printlog("Starting client node on slurm", socket.gethostname())
		time.sleep(1)
		SLURM = args.hydraMPP_client, 24515, args.hydraMPP_cpus
		#init(address=args.hydraMPP_client)
	return

if re.search(r'--hydraMPP-', ''.join(sys.argv)):
	slurm()

if __name__ == "__main__":
	mp.freeze_support()
	mp.set_start_method("spawn")
	global MANAGER
	global NODES
	global QUEUE
	MANAGER = mp.Manager()
	NODES = MANAGER.list()
	QUEUE = MANAGER.dict()
