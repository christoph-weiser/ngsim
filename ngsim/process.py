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


import os
import re
import subprocess


def xschem2spice(schematic, outputdir, xschemrc):
    """ Convert xschem schematic to spice netlist

    Required inputs:
    ----------------
    schematic (str):        Path to schematic file.
    outputdir (str):        Path where output is generated.
    xschemrc  (str):        Path to xschemrc config file.

    Description
    ----------------
    This function will generate a spice netlist
    from a xschem schematic file.
    """
    pwd = os.getcwd()
    rc_location = "/".join(xschemrc.split("/")[:-1])
    os.chdir(rc_location)
    if outputdir == ".":
        outputdir = pwd
    p = subprocess.Popen(["xschem", "-x", "-n", "-q", schematic,
                          "-o", outputdir, "--tcl", "set cmdline_ignore true; set dummy_ignore true",
                          "--rcfile", xschemrc])
    (output, err) = p.communicate()
    p_status = p.wait()
    os.chdir(pwd)


def extract_circuit(netlist, as_str=True):
    """ Extract circuit from a xschem exported netlist.

    Required inputs:
    ----------------
    netlist (str, list):        Spice netlist from which to extract
                                the circuit information.

    Optional inputs:
    ----------------
    as_str (bool):              Return netlist as string or otherwise
                                as a list.

    Returns
    ----------------
    netlist_extract (list):     List of lines containing circuit elements.


    Description
    ----------------
    This function will extract all circuit related information
    from a spice netlist. It will discard simulator control
    sections by ignoring user architecture code.
    """
    if isinstance(netlist, str):
        netlist = netlist.split("\n")
    inside_user_code = False
    netlist_extract = []
    for line in netlist:
        if re.match("\*\*\*\* begin user architecture code", line):
            inside_user_code = True

        if not inside_user_code:
            netlist_extract.append(line)

        if re.match("\*\*\*\* end user architecture code", line):
            inside_user_code = False
    if as_str:
        netlist_extract = "\n".join(netlist_extract)
    return netlist_extract


def extract_control(netlist, skip_plots=True, as_str=True):
    """ Extract control section from a xschem exported netlist.

    Required inputs:
    ----------------
    netlist (str, list):    Spice netlist from which to extract
                            the circuit information.

    Optional inputs:
    ----------------
    skip_plots (bool):      Skip plot statements.
    as_str (bool):          Return netlist as string or otherwise
                            as a list.

    Returns
    ----------------
    netlist_extract (list): List of lines containing control section
                            elements.
    """
    if isinstance(netlist, str):
        netlist = netlist.split("\n")
    inside_control_code = False
    netlist_extract = []
    for line in netlist:
        if re.match("\.control", line):
            inside_control_code = True
        if inside_control_code:
            if skip_plots:
                if not re.match("^plot.*", line):
                    netlist_extract.append(line + "\n")
            else:
                netlist_extract.append(line + "\n")
        if re.match(".endc", line):
            inside_control_code = False
    if as_str:
        netlist_extract = "".join(netlist_extract)
    return netlist_extract


def extract_output_data(output):
    """ Extract results from ngspice output.

    Required inputs:
    ----------------
    output (list):      ngspice output

    Returns
    ----------------
    resutls (dict):     pairs of variable name and value
    """
    results = {}
    for line in output:
        if re.match(".* = .*", line):
            var = line.split("=")[0].strip()
            val = line.split("=")[-1].strip()
            results[var] = float(val)
    return results


def parse_configuration(filename):
    """ Parse custom configuration file format.

    Required inputs:
    ----------------
    filename (str):         path to the configuration file.

    Returns
    ----------------
    configuration (dict): Dictionary holding information
                          about the simulation runs evals etc.

    Description
    ----------------
    The custom format look like this:

        :corners
            tt
            ss
            ff
        :supply
            1.7
            1.8
            1.9
        :temperature
            -20
            27
            85
        :variable
            var 1 2 3
        :evaluate
            vm1#branch < 300e-9
            vm1#branch > 650e-9

    """
    with open(filename, "r") as infile:
        raw = infile.read()
        raw = raw.split("\n")
        data = []
        for line in raw:
            if not re.match("\s*#|^\s*$", line):
                data.append(line)
    corners = []; supply = []; temperature = []
    evaluate = []; variable = {}
    cpars = None
    for line in data:
        if line in [":corners", ":supply", ":temperature", ":evaluate", ":variable"]:
            cpars = line
        else:
            if cpars == ":corners":
                corners.append(line.strip())
            elif cpars == ":supply":
                supply.append(line.strip())
            elif cpars == ":temperature":
                temperature.append(line.strip())
            elif cpars == ":evaluate":
                line = line.lstrip()
                parts = line.split(" ")
                elements = []
                for elem in parts:
                    if not elem == '':
                        elements.append(elem)
                evaluate.append(elements)
            elif cpars == ":variable":
                line = line.lstrip()
                parts = line.split(" ")
                elements = []
                for elem in parts:
                    if not elem == '':
                        elements.append(elem)
                variable[elements[0]] = elements[1:]
    return {"corners": corners,   "supply": supply, "temperature": temperature,
            "evaluate": evaluate, "variable": variable}

