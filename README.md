# BASOPRA_OpenBEERS
BASOPRA with EV/HP/Battery taking output from CitySim 
The software was tested in python 3.9, please use this version.

The python environment needed to run the program is in the file "environment.yml"

Once you have cloned the repository change the repertory to the subdirectory Core and run python3 Main_beers.py:



Please have in mind that you will need CPLEX (or gurobi, glpk...) to run the optimization. If you have problems with CPLEX or other optimization software but you are sure you have it, go to Core_LP.py and be sure that the executable path is the correct one for your system, it is in the line opt = SolverFactory('PATH_TO_YOUR_OPTIMIZATION_SOFTWARE')

---------------------------HOW TO USE---------------------

There are two folders: Core and Input.

Core contains the code in different scripts: main_beers.py (main script from which the code can be run), Core_LP.py (setting op the optimization), LP_EV.py (the optimization problem formulation), paper_classes.py (battery characteristics), and post_proc.py (post processing of model results)

Input contains the data input files, including generation and demand profiles for the PV installation, the household load, the electric vehicle, and heat pump and other technical specifications. Several files need to be unzipped before the program can run.

This is an ongoing project, and the interaction with [CitySim] (https://github.com/kaemco/CitySim-Solver/tree/master) is not yet fully included