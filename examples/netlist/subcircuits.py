#!/usr/bin/env python3

import ngsim as ngs

circuitfile = "netlist/netlist.sp"

cir = ngs.CircuitSection(circuitfile)

for uid in cir.circuit:
    print(cir.circuit[uid]["instance"], (cir.circuit[uid]["location"]))
