#!/usr/bin/env python3

import ngsim as ngs

netlist = "netlist/netlist.sp"

cir = ngs.CircuitSection(netlist)

filt = ("instance", "xr.*")

uids = cir.filter(filt)

for uid in uids:
    d = ngs.unpack_args(cir[uid]["args"])
    d["w"] = 2
    args = ngs.repack_args(d)
    cir[uid]["args"] = args 

print(cir)
