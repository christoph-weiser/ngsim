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

from dataclasses import dataclass, field
from typing import List


@dataclass
class Simulation:
    cmd:        str
    prints:     List[str] = field(default_factory=lambda : [])
    outputs:    List[str] = field(default_factory=lambda : [])
    measure:    List[str] = field(default_factory=lambda : [])
    plots:      List[str] = field(default_factory=lambda : [])
    location:   str   = ""
    name:       str   = ""
    identifier: str   = None

    def __post_init__(self):
        for elem in ["prints", "outputs", "measure", "plots"]:
            attr = getattr(self, elem)
            if isinstance(attr, str):
                setattr(self, elem, [attr])
        self.identifier = self.cmd.split(" ")[0].upper()


def tran(tstop, tstep="1n", tstart=None, tmax=None, uic=None):
    """ Create a transient simulation.

    Required inputs:
    ----------------
    tstop (str):    Final simulation time.


    Optional inputs:
    ----------------
    tstep (str):    Output-sample/plotting step size.
    tstart (str):   Start time for collecting data.
    tmax (str):     Maximum step size.
    uic (bool):     Use initial conditions.


    Returns
    ----------------
    sim_str (str):      string with the ngspice compatible command.
    """
    if tstart:
        tstart = "tstart={}".format(tstart)
    else:
        tstart = ""
    if tmax:
        tmax = "tmax={}".format(tmax)
    else:
        tmax = ""
    if uic:
        uic = "uic={}".format(uic)
    else:
        uic = ""
    sim_str =  "tran {} {}   {}  {} {}".format(tstep, tstop, tstart, tmax, uic)
    sim_str = re.sub("\s{2,}", " ", sim_str)
    return sim_str


def dc(srcname, vstart, vstop, vincrement):
    """ Create a DC simulation.

    Required inputs:
    ----------------
    srcname (str):      name of the source to sweep.
    vstart (str):       start voltage of the sweep.
    vstop (str):        stop voltage of the sweep.
    vincrement (str):   step increment of the sweep.

    Returns
    ----------------
    sim_str (str):      string with the ngspice compatible command.
    """
    return "dc {} {} {} {}".format(srcname, vstart, vstop, vincrement)


def ac(fmin, fmax, pts, method="dec"):
    """ Create an AC simulation.

    Required inputs:
    ----------------
    fmin (str):         lower bandwith bound.
    fmax (str):         upper bandwith bound.
    pts (str, int):     points per specified method.


    Optional inputs:
    ----------------
    method (str):       can be ["dec", "oct", "lin"]


    Returns
    ----------------
    sim_str (str):      string with the ngspice compatible command.

    """
    return "ac {} {} {} {}".format(method, pts, fmin, fmax)


def tf(outvar, insrc):
    """ Create a TF simulation.

    Required inputs:
    ----------------
    outvar (str):    expression such as i(load), v(vout, vnet1) etc.
    insrc (str):     input source to the simulation.

    Returns
    ----------------
    sim_str (str):      string with the ngspice compatible command.
    """
    return "tf {} {}".format(outvar, insrc.lower())


def pz(vinp, vinn, voutp, voutn, stype="vol", otype="pz"):
    """ Create a PZ simulation.

    Required inputs:
    ----------------
    vinp (str):     positive input node reference.
    vinn (str):     negative input node reference.
    voutp (str):    positive output node reference.
    voutn (str):    negative output node reference.


    Optional inputs:
    ----------------
    stype (str):    signal type can be [vol]tage [cur]rent.
    otype (str):    output type can be pz, pol, zer.


    Returns
    ----------------
    sim_str (str):      string with the ngspice compatible command.
    """
    sim_str = "pz {} {} {} {} {} {}"
    return sim_str.format(vinp, vinn, voutp, voutn, stype, otype)


def noise(vout, src, pts, fstart, fstop, method="dec", pts_sum=1):
    """ Create a NOISE simulation.

    Required inputs:
    ----------------
    vout (str, tuple):  output node(s).
    src (str):          name of the noise source.
    pts (int):          number of points per "method"
    fstart (float):     sweep start frequency.
    fstop (float):      sweep end frequency.


    Optional inputs:
    ----------------
    method (str):       sweep method can be: dec, lin, oct.
    pts_sum (int):      number of points in the summary


    Returns
    ----------------
    sim_str (str):      string with the ngspice compatible command.
    """
    if isinstance(vout, str):
        return f"noise v({vout}) {src} {method} {pts} {fstart} {fstop} {pts_sum}"
    else:
        return f"noise v({vout[0]},{vout[1]}) {src} {method} {pts} {fstart} {fstop} {pts_sum}"

