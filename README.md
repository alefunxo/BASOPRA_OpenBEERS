# BASOPRA_OpenBEERS
BASOPRA with EV/HP/Battery taking output from CitySim 
The software was tested in python 3.9 and 3.12. Due to 3.9 soon being deprecated please use a higher version.

A base python environment file is provided under `linux_environment.yml`. An alternative file with windows libraries is provided as well under `environment.yml`.

The current version of the code requires Gurobi.

---------------------------HOW TO USE---------------------

The main files and directories to know are the following:
- Core/run.py : Main file used to start the entire process
- Core/main_beers.py : Creation and Lauch of building simulation processes
- Core/Core.py : Gurobi simulation logic
- openbeers_api/ : modules retrieving all necessary data from OpenBEERS platform
- heat_pump/pump_sizer.py : Logic used to dimension heat_pumps
- config/config.yaml : Main configuration file

Outputs of the simulations are saved in the `basopra_output` directory.

This is an ongoing project, and the interaction with [CitySim] (https://github.com/kaemco/CitySim-Solver/tree/master) is not yet fully included

# Setup
To get this to work, you should create a conda environment using the `environment.yml` file (or linux_environment.yml if linux based).
```bash
conda env create -f linux_environment.yml  # creates the basopra_clean environment
```
or update an environment with the following
```bash
conda env update -n basopra_clean -f linux_environment.yml
```

Once your conda environment is setup access it and install the openbeers library from the gitlab repository (registration on the gitlab needed to get username and password)
```bash
conda activate basopra_clean
pip install git+https://gitlab.idiap.ch/energy/openbeers/openbeers-py.git
```
Alternatively, it was found to work better in some cases to clone the repository and install from repository
```bash
git clone git+https://gitlab.idiap.ch/energy/openbeers/openbeers-py.git`
cd openbeers-py
pip install -e .
```

Also make sure you have the Gurobi solver installed

# Run
You can modify settings before running in `config/config.yaml`
You can run the program from the top level with
```bash
python Core/run.py
```
