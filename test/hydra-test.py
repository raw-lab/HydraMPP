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
	for i in range(400):
		slow_func.remote(1)
	print("Waiting for jobs")
	ready,queue = hydraMPP.wait()
	while queue:
		if ready:
			print(hydraMPP.get(ready[0]))
		ready,queue = hydraMPP.wait()
	print(ready, queue)
	print(hydraMPP.get(ready[0]))
	return 0


if __name__ == "__main__":
	exit(main())
