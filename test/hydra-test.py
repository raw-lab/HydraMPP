#!/usr/bin/env python

import time
import hydraMPP


@hydraMPP.remote
def slow_func(seconds=1):
	time.sleep(seconds)
	return seconds


def main():
	print("Running test program for HydraMPP")
	hydraMPP.init()
	print("Starting jobs")
	for i in range(20):
		slow_func.remote(1)
	for i in range(10):
		slow_func.options(num_cpus=4).remote(1)
	print("Waiting for jobs")
	ready,queue = hydraMPP.wait()
	while queue:
		if ready:
			print(hydraMPP.get(ready[0]))
		ready,queue = hydraMPP.wait(queue)
	print(ready, queue)
	print(hydraMPP.get(ready[0]))

	print("TEST COMPLETE")
	print("exit in 3")
	time.sleep(1)
	print("exit in 2")
	time.sleep(1)
	print("exit in 1")
	time.sleep(1)
	return 0


if __name__ == "__main__":
	exit(main())
