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
import copy
import datetime
import hashlib
import collections
import spatk

from ngsim.process import extract_control
from spatk.helpers import read_netlist, clean_netlist


class ControlSection():
    """ Ngspice control section from file or string. """
    def __init__(self, netlist, is_filename=True):
        if is_filename:
            with open(netlist, "r") as ifile:
                self._netlist = ifile.read()
        else:
            self._netlist = netlist
        self._netlist = extract_control(self._netlist, as_str=False)

    def __str__(self):
        return self.netlist

    def __add__(self, other):
        return self.netlist + str(other)

    @property
    def lines(self):
        """ Lines of control section netlist """
        return self._netlist

    @lines.setter
    def lines(self, arg):
        if isinstance(arg, str):
            self._netlist = arg.split("\n")
        elif isinstance(arg, list): 
            self._netlist = arg
        else:
            raise Exception("control list must be str or list")

    @property
    def netlist(self):
        """ Simulation ready circuit netlist """
        return "\n".join(self._netlist)

    def write(self, filename):
        """ Write the control netlist to file

        Required inputs:
        ----------------
        filename (str):     Name of the output file.
        """
        with open(filename, "w") as ofile:
            ofile.write("* Netlist written: {}\n".format(datetime.datetime.now()))
            ofile.write(self.netlist)


class CircuitSection(spatk.Circuit):
    """ CircuitSection represents a spice netlist.

    Required inputs:
    ----------------
    netlist  (str):     spice netlist or path to a spice netlist.


    Optional inputs:
    ----------------
    is_netlist (bool):  Indicator if netlist is a filepath or actual netlist.
                        Default assumes a path.

    Description
    ----------------
    The Circuit section is a high-level object of any ordinary spice netlist.
    The object allows however to filter the netlist elements by their type
    arguments and ports.

        filename:       When read from file filename, otherwise this can be
                        used a identfier and will be writen to the first line
                        of the netlist object.

        parsed_circuit: This variable holds a string with the original netlist
                        even before variable subsitution.


        circuit:        A list of all the netlist elements in a dict fashion
                        with "instance", "type",  "ports",  "args" keys.

        netlist:        A spice netlist generated from the "circuit" list/dict.
    """

    def __init__(self, *args):
        super(CircuitSection, self).__init__(*args)
