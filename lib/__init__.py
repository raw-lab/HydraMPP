# -*- coding: utf-8 -*-

"""hydraMPP: Module for Distributed Parallel Processing

Hydra MPP is a Python library for Distributed Parallel Processing.
DPP utilizes multiple nodes/computers to distribute workloads for
faster processing.

Currently this module is compatible as a basic stand in for Ray.
Not all features are fully implemented yet.

Implemented:
local MPP

Not implemented;
DPP
  sockets
  password
  error reporting
  pickle objects
  compression?
  encryption
Error checking
  if more CPUs are requested than available
"""

__version__ = "0.1.2"


import atexit
import multiprocessing as mp
import psutil
import time
from pathlib import Path


## GLOBAL VARIABLES ##
RUNNING = False
manager = mp.Manager()
P = None
CURR_ID = 0
NODES = list()
QUEUE = manager.dict()


## CLASS ##
class Worker:
	def __init__(self, func):
		self.func = func
		self.num_cpus = 1
		return
	
	def options(self, num_cpus=1):
		self.num_cpus = num_cpus
		return self

	def remote(self, *args, **kwargs):
		def __worker(func, id, args, kwargs):
			try: QUEUE[id] = [func(*args, **kwargs), True, 0]
			except: print("MPP ERROR", func, id, args, kwargs)
		global CURR_ID
		CURR_ID += 1
		QUEUE[CURR_ID] = [args, False, self.num_cpus]
		p = mp.Process(target=__worker, args=[self.func, CURR_ID, args, kwargs])
		cpus = sum([x[2] for x in QUEUE.values() if not x[1]])
		while NODES[0]['num_cpus'] < cpus:
			time.sleep(0.001)
			cpus = sum([x[2] for x in QUEUE.values() if not x[1]])
		p.start()
		self.num_cpus = 1
		return CURR_ID


## METHODS ##
def init(address="local", num_cpus=None, log_to_driver=False):
	global P
	global NODES
	global RUNNING
	if not num_cpus:
		num_cpus = psutil.cpu_count()
	NODES = [dict(
		address = "local",
		num_cpus = num_cpus,
		temp = Path("tmp-hydra"),
		ObjectStoreSocketName = Path("tmp-hydra", "current", "objects"))]
	NODES[0]['temp'].mkdir(parents=True, exist_ok=True)
	print("Starting Hydra DPP (Distributed Parallel Processing)")
	print("CPUS:", NODES[0]['num_cpus'])
	P = mp.Process(target=main_loop)
	RUNNING = True
	P.start()
	return

def main_loop():
	start = time.time()
	while RUNNING:
		time.sleep(0.001)
		if time.time() > start+1:
			with open(NODES[0]["temp"]/"queue.log", 'w') as writer:
				print("QUEUE:", NODES[0]['num_cpus'], file=writer)
				for k,v in QUEUE.items():
					try:
						now = time.localtime()
						print(f"{now[3]}:{now[4]}:{now[5]}", file=writer)
						if v[1]:
							print(f"{k}|{v[2]}\t", file=writer)
						else:
							print(f"{k}|{v[2]}\t{v[0][0].__name__}", file=writer)
						print(f"\t{v[0][1]}", file=writer)
					except Exception as e:
						#print("QUEUE ERROR:", k, v)
						#print(e)
						pass
				start = time.time()
	return

def nodes():
	return NODES

def get(id:int):
	return QUEUE.pop(id)[0]

def put(obj):
	global CURR_ID
	CURR_ID += 1
	QUEUE[CURR_ID] = [obj, True, 0]
	return CURR_ID

def wait(objects:list, timeout=0, max=1):
	ready = list()
	for i in range(len(objects)):
		id = objects[i]
		if QUEUE[id][1]:
			ready += [objects.pop(i)]
			break
	start = time.time()
	while objects and len(ready) < max and time.time() < start+timeout:
		time.sleep(0.001)
		for i in range(len(objects)):
			id = objects[i]
			if QUEUE[id][1]:
				ready += [objects.pop(i)]
				break

	return ready, objects

def remote(func):
	return Worker(func)

def shutdown():
	global RUNNING
	if not RUNNING:
		return
	RUNNING = False
	print("Hydra DMPP: Shutdown")
	P.kill()
	P.join()
	manager.shutdown()
	#if self.paccept:
	#	self.paccept.kill()
	for p in mp.active_children():
		p.kill()
	#for id,p in self.procs.items():
	#	p.kill()
	#print(self.curr_id)
	time.sleep(1)
	return

atexit.register(shutdown)
