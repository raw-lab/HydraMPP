# HydraMPP

## A massive parallel processing library for distributed processing in Python

## Requirements

HydraMPP is lightweight and requires little dependencies, and runs on Python >= 3.0.

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

## Status monitor

A script is included to monitor the status of HydraMPP while it is running.

```bash
hydra-status <address> <port>
```

This will query the status of HydraMPP and display some information on connected clients, available CPUs, and jobs in queue.  
It will immediately quit after displaying the status, for continuous monitoring use a tool like ```watch``` for this purpose.

```bash
watch -n1 hydra-status localhost
```

## SLURM

HydraMPP has a built in function to utilize a SLURM environment.  
  
All you need to do is add the flag ```--hydraMPP_slurm $SLURM_JOB_NODELIST``` when executing your python program and Hydra will take care of configuring the host/clients.  
  
make sure to call ```HydraMPP.init()``` once all required methods have been tagged with ```@HydraMPP.remote```  
  
i.e.

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

path/to/program.py --custom-args --hydraMPP_slurm $SLURM_JOB_NODELIST

```
