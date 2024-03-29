# Ngsim - A ngspice simulation interface using python
# Copyright (C) 2022 Christoph Weiser
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
import os
import subprocess

import numpy as np
import pandas as pd

from multiprocessing import Pool, Manager
from scipy.optimize import differential_evolution, shgo, dual_annealing, brute

from ngsim.invoke  import run_simulation
from spatk.helpers import replace_argument, read_netlist


class Optimizer():
    """ Optimizer class for solving circuit optimization
    problems using ngspice.

    Required inputs:
    ----------------
    costfunc (callable):   Cost function to minimize.
    bounds (tuple):        Bounds for the cost function inputs.
    cir (CircuitSection):  Circuit representation.
    ctl: (ControlSection): Control representation.
    params: (list):        list of dict with the following format:
                           [{"variable": "var2", 
                            "bound": "r", 
                            "instances": ["r2", "r11", "r20", "r29"]}, 
                            {...}, {...}, {...}]
                         


    Optional inputs:
    ----------------
    constraints (tuple):   Constraint defined using scipy constraints.

    """
    def __init__(self, costfunc, bounds, cir, ctl, params, constraints=(), bound_conditions={}):
        self.costfunc = costfunc
        self.bounds = bounds
        self.cir = cir
        self.ctl = ctl
        self.params = params
        self.df = pd.DataFrame()
        self.constraints = constraints
        self.bound_conditions = bound_conditions


    def opt_brute(self, cores=1, **kwargs):
        """ Brute force an optimal solution.

        Optional inputs:
        ----------------
        cores (int): Number of cores to use for evalution.
                     -1 uses all cores available.
        kwargs (dict):  optional arguments passed to the
                        brute function.

        Returns
        ----------------
        opt (OptimizeResult): Result of Optimization
        """
        if cores == -1:
            cores = os.cpu_count()
        manager = Manager()
        self.reslist = manager.list()
        Ns = kwargs.pop("Ns", 5)
        with Pool(processes=cores) as pool:
            opt = brute(self.run,
                        self.bounds,
                        Ns=Ns,
                        workers=pool.map,
                        **kwargs)
        self._update_database(self.reslist)
        self._write_database()
        return opt


    def opt_de(self, cores=1, **kwargs):
        """ optimize using differential evolution algorithm.

        Optional inputs:
        ----------------
        cores (int):    number of cores to use for evalution.
                        -1 uses all cores available.
        kwargs (dict):  optional arguments passed to the
                        differential_evolution function.

        Returns
        ----------------
        opt (OptimizeResult): Result of Optimization


        Notes
        ----------------
        useful ressource: https://cutt.ly/zjroOyn

        """
        if cores == -1:
            cores = os.cpu_count()
        manager = Manager()
        self.reslist = manager.list()
        maxiter         = kwargs.pop("maxiter", 1)
        polish          = kwargs.pop("polish", False)
        mutation        = kwargs.pop("mutation", 0.5)
        recombination   = kwargs.pop("recombination", 0.7)
        with Pool(processes=cores) as pool:
            opt = differential_evolution(self.run,
                                         self.bounds,
                                         constraints=self.constraints,
                                         maxiter=maxiter,
                                         workers=pool.map,
                                         polish=polish,
                                         mutation=mutation,
                                         recombination=recombination,
                                         **kwargs)
        self._update_database(self.reslist)
        self._write_database()
        return opt


    def opt_shgo(self, **kwargs):
        """ Simplicial homology global optimization.

        Optional inputs:
        ----------------
        kwargs (dict):  optional arguments passed to the
                        shgo function.

        Returns
        ----------------
        opt (OptimizeResult):  Result of Optimization


        Notes
        ----------------
        Useful ressource: https://stefan-endres.github.io/shgo/

        """
        self.reslist = list()
        sampling_method = kwargs.pop("sampling_method", "sobol")
        opt = shgo(self.run,
                   self.bounds,
                   constraints=self.constraints,
                   sampling_method=sampling_method,
                    **kwargs)
        self._update_database(self.reslist)
        self._write_database()
        return opt


    def opt_da(self, **kwargs):
        """ Optimization using Dual Annealing.

        Optional inputs:
        ----------------
        kwargs (dict):  optional arguments passed to the
                        dual_annealing function.

        Returns
        ----------------
        opt (OptimizeResult): Result of Optimization


        Description
        ----------------
        Dual annealing combines global heuristic search
        with local gradient search.
        """
        self.reslist = list()
        maxiter       = kwargs.pop("maxiter", 50)
        initial_temp  = kwargs.pop("initial_temp", 5230.)
        opt = dual_annealing(self.run,
                             self.bounds,
                             maxiter=maxiter,
                             initial_temp=initial_temp,
                             no_local_search=False)
        self._update_database(self.reslist)
        self._write_database()
        return opt


    def _update_database(self,reslist):
        """ update internal result database.

        Required inputs:
        ----------------
        reslist (list): simulation results, including
                        parameters and cost function result.

        Description
        ----------------
        Updates the internal pandas result database
        with all runs carried out by the optimization routine.
        """
        cols = {}
        for res in reslist:
            for k in res[0]:
                cols[k] = res[0][k]
            for k in res[1]:
                cols[k] = res[1][k]
            cols["cost"] = res[2]
            self.df = pd.concat([self.df, pd.DataFrame([cols])], ignore_index=True)


    def _write_database(self, filename="optimize_output.csv"):
        """ Write the internal pandas dataframe to file.

        Optional inputs:
        ----------------
        filename (str): filename of the output file.

        """
        self.df.to_csv(filename)


    def run(self, x):
        """ Core function to launch simulation.

        Required inputs:
        ----------------
        x (np.array): itteration input vector

        Returns
        ----------------
        cost (float): result of costfunction evaluation.
        """
        netlist, params = self.precondition(x)
        output = run_simulation(netlist)
        result = self.handle_output(output)
        cost = self.costfunc(result, params)
        self.reslist.append((params, result, cost))
        return cost


    def eval(self, x):
        """ Evaluate itteration input vector and
        obtain simulation results.

        Required inputs:
        ----------------
        x (np.array): itteration input vector

        Returns
        ----------------
        result (dict): Result of simulation run.
        """
        netlist, params = self.precondition(x)
        output = run_simulation(netlist)
        return self.handle_output(output)


    def precondition(self, x):
        """ Condition netlist with current optimization parameters.

        Required inputs:
        ----------------
        x (numpy.array):    the current itteration of optimization
                            parameters.

        Returns
        ----------------
        netlist (str):      Simulation netlist with current optimization
                            parameters subsituted.
        associated (dict):  association between current optimization
                            parameters list and names of these parameters.
        """

        associated = {}
        for p,v in zip(self.params, x): 
            for inst in p["instances"]: 
                if p["type"] == "value":
                    associated[(inst, "value" )] = v
                elif p["type"] == "arg":
                    associated[(inst, p["arg"])] = v
                else:
                    raise Exception("Provided unexpected param 'type' field")
        self.cir.reset()
        for k in associated:
            inst = k[0]
            par = k[1]
            value = associated[k]
            uid = self.cir.filter("instance", inst)[0]
            if par == "value":
                self.cir[uid].value = str(value)
            else:
                self.cir = replace_argument(uid, self.cir, par, value)
        netlist = self.cir.netlist + self.ctl.netlist
        return netlist, associated

    
    def handle_output(self, output):
        result = {}
        for line in output:
            if re.match("^\S* =", line):
                var, val = line.split(" = ")
                result[var] = float(val)
        return result


    def _order_pz_output(self,res):
        """ Helper function to create a more useful
        result container for the pz output.

        Required inputs:
        ----------------
        res (str): section of result string containing
                   results for pz analysis.

        Return
        ----------------
        result (dict): dict holding list of poles and zeros.

        """
        poles = []
        zeros = []
        for k in res:
            rtype = k.split("(")[0]
            if rtype == "pole":
                poles.append( 1*res[k][0] + 1j*res[k][1])
            elif rtype == "zero":
                zeros.append( 1*res[k][0] + 1j*res[k][1])
        poles.reverse()
        zeros.reverse()
        return {"poles": poles, "zeros": zeros }


#----------------------------------------------------------------------
# Helper Functions
#----------------------------------------------------------------------

def discretize_param(par, disc):
    """ Convert par to the closest value in disc.

    Required inputs:
    ----------------
    par (float):        parameter to discretize.
    disc (list):        list of discrete values to attain.

    Return
    ----------------
    solution (float):   closed value that par matched in disc.
    """
    minimum  = abs(par - disc[0])
    solution = disc[0]
    for d in disc[1:]:
        if abs(d - par) < minimum:
            minimum = abs(d - par)
            solution = d
    return solution


def range_discretize_param(par, disc):
    """ find closed match for par in ranges.

    Required inputs:
    ----------------
    par (float):        parameter to discretize.
    disc (list):        list of range tuples.

    Return
    ----------------
    solution (float):   if par is in any range solution=par
                        otherwise the closest value that is
                        in disc.
    """
    solution = None
    for d in disc:
        if  (d[0] <= par) and (par <= d[1]):
            solution = par
    if solution:
        return solution
    else:
        disc = [x[0] for x in disc] + [x[1] for x in disc]
        return discretize_param(par, disc)


#----------------------------------------------------------------------
# Utilities to create cost functions, bounds etc.
#----------------------------------------------------------------------
#
# Helper functions that make it easier to create a
# cost (objective) function for the global optimization
# procedure.
#
#----------------------------------------------------------------------


def lim_upper(val, lim):
    """ Cost function helper

    Required inputs:
    ----------------
    val (float):    value that was given by simulation
    lim (float):    limit that shall not exceeded

    Return
    ----------------
    cost (float):   cost calculated based on limit


    Description
    ----------------
    Evaluate if the value exceeds an upper limit
    and return a normalized cost for this.
    """
    res = (lim - val)/lim
    if res > 0:
        return 0
    else:
        return abs(res)


def lim_lower(val, lim):
    """ Cost function helper

    Required inputs:
    ----------------
    val (float):    value that was given by simulation
    lim (float):    limit below which the value shall not drop.

    Return
    ----------------
    cost (float):   cost calculated based on limit


    Description
    ----------------
    Evaluate if the value drops below an lower limit
    and return a normalized cost for this.

    """
    res = (lim - val)/lim
    if res < 0:
        return 0
    else:
        return abs(res)


def lim_bound(val, limlow, limhigh):
    """ Cost function helper

    Required inputs:
    ----------------
    val (float):     Value that was given by simulation.
    limlow (float):  Lower limit beyond which the value should not
                     drop.
    limhigh (float): Lower limit beyond which the value should not
                     drop.

    Returns
    ----------------
    cost (float):    Cost calculated based on limits


    Description
    ----------------
    Evaluate if the value drops below or exceeds a set limit
    and return a normalized cost for this.
    """
    reslow  = (val - limlow)/limlow
    reshigh = (limhigh - val)/limhigh
    if (reslow < 0):
        return abs(reslow)
    elif (reshigh < 0):
        return abs(reshigh)
    else:
        return 0


def create_bounds(params, lut):
    """ helper function to create bounds for opt routines.

    Required inputs:
    ----------------
    params (dict):  dict with "bound" key indicating bound
                    name and instances key, that are to 
                    be applied with this bound. example:
                    {"variable": "var1", 
                     "bound": "r", 
                     "instances": ["r1", "r2"]}
    lut (dict):     lookup table with bound for parameters.
                    example:  {"r":  (1e3, 100e3)}

    Returns
    ----------------
    bounds (list):  List with the bounds for all parameters.
    """
    return [lut[elem["bound"]] for elem in params]
