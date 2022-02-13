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

from ngsim.process import xschem2spice


def path_setup(filename, cwd,  identifier):
    """ Generate names, filepaths etc. for regression test.

    Required inputs:
    ----------------
    filename (str):     .conf file holding simulation details.
    indentifier (str):  unique identifier for result file
    cwd (str):          current working directory


    Returns
    ----------------
    name (str):         overall name of the testsetup
    file_sch (str):     file location of the schematic
    file_conf (str):    file location of the test config
    file_res (str):     file location of the result file


    Description
    ----------------
    This function prepares all the variables required to run
    a regression test. It works based on the predefined structure
    that is assumed when building up regession tests.
    This structure likes like this:

    root/
        |--tb_name.sch
        |--tests/
                |--tb_name.conf
                |--results/
                          |--
                          |--

    """
    name = os.path.basename(filename).replace(".conf", "")
    name_sch  = name + ".sch"
    name_conf = name + ".conf"
    file_sch  = os.path.dirname(cwd) + "/" + name_sch
    file_conf = cwd + "/" + name_conf
    path_res  = cwd + "/" + "results"
    file_res  = "{}/{}_{}.csv".format(path_res, name, identifier)
    if not os.path.isdir(path_res):
        os.mkdir(path_res)
    return name, file_sch, file_conf, file_res


def create_netlist(file_sch, location, xschemrc):
    """ Create a spice netlist from xschem schematic.

    Required inputs:
    ----------------
    file_sch (str):     File location of xschem schematic.
    location (str):     Path where resulting netlist is placed.
    xschemrc (str):     location of xschemrc


    Returns
    ----------------
    file_net (str):     Location of the spice netlist
    """
    xschem2spice(file_sch, location, xschemrc)
    name_net = os.path.basename(file_sch).replace(".sch", ".spice")
    file_net = location + "/" + name_net
    return file_net


def latest_testresult(filename, location):
    """ Return the latest testresult

    Required inputs:
    ----------------
    filename (str): current file. typically __file__
    location (str): current working directory.


    Returns
    ----------------
    latest (str):       path to the latest result file.


    Description
    ----------------
    This is a helper function to the pytest setup.
    This should be called from a analysis script to get the
    latest result from a results location.
    This assumes a system, where the files are named with a
    timestamp, such that sorting them results in a orderly list.

    """
    path_results = os.path.abspath("{}/../results".format(location))
    name_file = os.path.basename(filename).replace(".py", "")
    files = sorted(os.listdir(path_results))
    matches = []
    for f in files:
        if re.match("^{}.*csv$".format(name_file), f):
            matches.append(f)
    try:
        latest = sorted(matches)[-1]
    except IndexError:
        raise Exception("No files match the current analysis")
    return path_results + "/" + latest
