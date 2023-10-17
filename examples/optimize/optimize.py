#!/usr/bin/env python3

import ngsim as ngs

filename = "netlist.spice"

ctl = ngs.ControlSection(filename)
cir = ngs.CircuitSection(filename)

def costfunc(result, pars):
    vdc         = result["op_vdc"] 
    fmeas       = result["ac_fmeas"] 
    vdc_norm    = ngs.lim_bound(vdc, 0.75, 0.751)
    fmeas_norm  = ngs.lim_bound(fmeas, 1e6, 1.01e6)
    cost        = vdc_norm**2 + fmeas_norm**2
    return cost

# Define the bounds that will be assigned to variables.
bound_lut = {"rres":  (100, 10e3 ),
             "ccap":  (1e-12, 1e-6) }

# Define the parameters of the optimization procedure.
params = [ {"type": "value", "bound": "rres", "instances": ["rsh"]},
           {"type": "value", "bound": "ccap", "instances": ["csh"]}] 

# Example replacing a particular argument of a component.        
# {"type": "arg", "arg": "tc", "bound": "rtc", "instances": ["rsh"]}] 


# Create optimization ready bounds.
bounds = ngs.create_bounds(params, bound_lut)

# Create the optimizer instance.
optimizer = ngs.Optimizer(costfunc, bounds, cir, ctl, params)

# Run a particular optization strategy for the problem. 
res = optimizer.opt_de(cores=1, maxiter=100)

# Print the resulting pararametes and the 
# corresponding result.
print(res.x)
print(optimizer.eval(res.x))
