#!/usr/bin/env python3

import ngsim as ngs

netlist = "netlist/netlist.sp"
control = "netlist/control.sp"

cir = ngs.CircuitSection(netlist)
ctl = ngs.ControlSectionExternal(control)

filt = {"instance": "vdd", "type": "vsource"}

def alter_vdd(elem, vdd):
    elem["args"] = [str(vdd)]
    return elem

vdd_vec = [1.7, 1.8, 1.9]

for vdd in vdd_vec:
    cir.apply(alter_vdd, filt, vdd=vdd)
    sim_netlist = cir + ctl
    ngs.run_simulation(sim_netlist)
