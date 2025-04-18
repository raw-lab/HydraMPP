# HydraMPP

## Version 0.0.5

### v0.0.5 New Features

- More efficient in process spawning

### v0.0.5 Bug Fixes

- Fixed port issue with status monitor

## Version 0.0.4

### v0.0.4 Bug Fixes

- Fixed compatibility with OSX and conda-forge
- Fixed a couple of race condition issues

## Version 0.0.3

### v0.0.3 New Features

- Utility to check the status of HydraMPP
  - hydra-status.py
- SLURM helper

### v0.0.3 Enhancements

- better output
- host initialization improvement

### v0.0.3 Bug Fixes

- Works with multiple nodes

### v0.0.3 Known issues

- Does not check for crashed clients or bad return value

### v0.0.3 Future plan

- password
  - encryption
- compression?
- error checking
  - if more CPUs are requested than available
- suppress worker node stdout/stderr, redirect

## Version 0.0.2

### v0.0.2 New Features

- sockets (network)
- Distributed Processing
- pickle objects

### v0.0.2 Enhancements

- cleaner code

### v0.0.2 Bug Fixes

- multiprocessing sync error

### v0.0.2 Known issues

- Might not work with more than 2 nodes

### v0.0.2 Future plan

- password
  - encryption
- compression?
- error checking
  - if more CPUs are requested than available
- suppress worker node stdout/stderr, redirect

## Version 0.0.1

### v0.0.1 New Features

- local MPP
  - Functions as a quick replacement for Ray (minimal options only)

### v0.0.1 Bug Fixes

### v0.0.1 Future plan

- sockets (network)
- Distributed Processing
- pickle objects
- password
- error reporting
- compression?
- encryption
- Error checking
  - if more CPUs are requested than available
