# HydraMPP

## A massive parallel processing library for distributed processing in Python

HydraMPP is a library to make it easyer to create scalable distributed parallel processing applications.  
It will function seamlessly from a single computer to a computing cluster environment with multiple nodes.

## Requirements

HydraMPP is designed to be lightweight and requires little dependencies.  

Python >= 3.6

## Install

### pip

HydraMPP can be easily installed from PyPi through pip:

```bash
pip install hydraMPP
```

If you don't have administrative permission and get an error, try the --user flag to install HydraMPP in your home folder.

```bash
pip install --user hydraMPP
```

### Anaconda

HydraMPP is available through the conda-forge channel on Anaconda.

```bash
conda install -c conda-forge HydraMPP
```

## Usage

### Step 1: Import the library

The HydraMPP library can be imported in python using:

```python
import hydraMPP
```

### Step 2: Tag methods

Methods or functions that you would like to use with HydraMPP for parallel processing need to be tagged:

```python
@hydraMPP.remote
def my_slow_function():
    time.sleep(10)
    return
```

### Step 3: Initialize the connection(s)

HydraMPP can run in 3 modes:

1. local
2. host
3. client

### Step 4: Call your methods

Once HydraMPP has been initialized, just call the method you would like with the .remote tag and the library will queue and dispatch when enough CPUs are available either locally or on another node in your setup.

### Step 5: Get return values

Use ```hydraMPP.wait``` to check the status of running jobs.  
It will return two lists. The first is a list of job IDs for the jobs that have finished and the second a list of jobs in queue or still running.  
  
Once jobs have finished running, use ```hydraMPP.get``` to get the return value and some stats on the job.  
The return value of ```hydraMPP.get``` is a list with the following values:  
  
1. Boolean value stating if the job has finished
2. The method name
3. The return value
4. Number of CPUs used for the job
5. Time to run the job, in seconds
6. The hostname of the node that the job ran on

## Status monitor

A script is included to monitor the status of HydraMPP while it is running.

```bash
usage: hydra-status.py [-h] [address] [port]

positional arguments:
  address     Address of the HydraMPP server to get status from [127.0.0.1]
  port        Port to connect to [24515]

options:
  -h, --help  show this help message and exit
```

This will query the status of HydraMPP and display some information on connected clients, available CPUs, and jobs in queue.  
It will immediately quit after displaying the status, for continuous monitoring use a tool like ```watch``` for this purpose.

```bash
watch -n1 hydra-status.py localhost
```

## SLURM

HydraMPP has a built in function to utilize a SLURM environment.  
  
All you need to do is add the flag ```--hydraMPP-slurm $SLURM_JOB_NODELIST``` when executing your python program and Hydra will take care of configuring the host/clients.  
  
make sure to call ```HydraMPP.init()``` once all required methods have been tagged with ```@HydraMPP.remote```  
  
The ```hydraMPP-cpus``` can be used to set the number of CPUs for each node to use. If set to '0' or omitted then HydraMPP will try to guess the number of CPUs available on each node.

```bash
#SBATCH --job-name=My_Slurm_Job
#SBATCH --nodes=3
#SBATCH --tasks-per-node=1
#SBATCH --cpus-per-task=36
#SBATCH --mem=100G
#SBATCH --time=1-0
#SBATCH -o slurm-%x-%j.out

echo "====================================================="
echo "Start Time  : $(date)"
echo "Submit Dir  : $SLURM_SUBMIT_DIR"
echo "Job ID/Name : $SLURM_JOBID / $SLURM_JOB_NAME"
echo "Node List   : $SLURM_JOB_NODELIST"
echo "Num Tasks   : $SLURM_NTASKS total [$SLURM_NNODES nodes @ $SLURM_CPUS_ON_NODE CPUs/node]"
echo "======================================================"
echo ""

path/to/program.py --custom-args --hydraMPP_slurm $SLURM_JOB_NODELIST --hydraMPP-cpus $SLURM_CPUS_ON_NODE

```

## CONTACT

The informatics point-of-contact for this project is [Dr. Richard Allen White III](https://github.com/raw-lab).  
If you have any questions or feedback, please feel free to get in touch by email.  
[Dr. Richard Allen White III](mailto:rwhit101@uncc.edu)  
[Jose Luis Figueroa III](mailto:jlfiguer@uncc.edu)  
Or [open an issue](https://github.com/raw-lab/hydrampp/issues).  
