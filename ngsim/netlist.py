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


class ControlSection:
    """ Ngspice control section.  """

    def __init__(self):
        self._nelist = ""

    def __str__(self):
        return self._netlist

    def __add__(self, other):
        return self.netlist + str(other)


class ControlSectionExternal(ControlSection):
    """ Ngspice control section from file or string.  """
    def __init__(self, netlist, from_file=True):

        if from_file:
            self._netlist = read_netlist(netlist)
        else:
            self._netlist = clean_netlist(netlist)

    @property
    def netlist(self):
        """ Simulation ready circuit netlist """
        return self._netlist


class ControlSectionLogical(ControlSection):
    """ Logical representation of the ngspice control section.

    Required inputs:
    ----------------
    simulations (list, Simulation):  Simulation Object or list of such.


    Optional inputs:
    ----------------
    includes (list, str):       Str or list of such containing includes.
    sweep_num (int):            Identifier of the current sweep.
    sim_options (list, str):    General simulation options can be a string or tuple
                                where the setting is a key value pair.
    ng_options (list, str):     Ngspice specific options can be a string or tuple
                                where the setting is a key value pair.
    save (list, str):           Which signals to save. Default is all.
    outputfile (str):           If data is saved to file it is saved with the name
                                of outputfile. If this is part of a sweep the
                                sweep_num is appeded to outputfile.
    outputdir (str):            Directory where data is saved. Default is pwd.
    filetype= (str):            Specifies the filetype format can be ascii or binary.
    wr_singlescale (bool):      Ngspice wr_singlescale option.  default is true.
    wr_vecnames (bool):         Ngspice wr_vecnames option.  default is true.
    exit_post_run (bool):       Exit after run is complete or stay open. default  True.


    Description
    ----------------
    The ControlSection object allows to create a high-level object containing all
    information about the execution of a simulation including all options and
    execution parameters.
    A control section is independent from the netlist and represents the ngspice
    control section plus any includes.

    """
    def __init__(self,
                 simulations,
                 includes=None,
                 sweep_num=None,
                 sim_options = [],
                 ng_options = [],
                 save = "all",
                 outputfile="output.csv",
                 outputdir=".",
                 filetype="ascii",
                 wr_singlescale=True,
                 wr_vecnames=True,
                 exit_post_run=True):

        self.sim_options = sim_options
        self.ng_options = ng_options
        self.filetype = filetype
        self.wr_singlescale = wr_singlescale
        self.wr_vecnames = wr_vecnames
        self.outputdir=outputdir
        self._netlist = ""
        self.exit_post_run = exit_post_run

        if isinstance(save, list):
            self.save = save
        else:
            self.save = [save]
        if isinstance(includes, list):
            self.includes = includes
        elif includes == None:
            self.includes = None
        else:
            self.includes = [includes]
        if isinstance(simulations, list):
            self.simulations = simulations
        else:
            self.simulations = [simulations]
        self.outputfile = outputfile
        if sweep_num:
            self.sweep_num = sweep_num
        else:
            self.sweep_num = ""
        self.assemble()


    @property
    def netlist(self):
        """ Simulation ready circuit netlist """
        self.assemble()
        return self._netlist


    def assemble(self):
        """ Assemble a netlist from object details.

        Description
        ----------------
        Based on the parameters of the instance
        a complete control section netlist will be assembled.
        that can be used to run a ngspice simulation.

        """
        section = [ "", "* Control section", "", ".control" ]
        app = section.append
        # ascii or raw output
        app("set filetype={}".format(self.filetype))
        # data nr. columns
        if self.wr_singlescale:
            app("set wr_singlescale".format(self.filetype))
        # naming of the vector columns.
        if self.wr_vecnames:
            app("set wr_vecnames")
        # add ngspice options
        for opt in self.ng_options:
            if isinstance(opt, str):
                app("set {}".format(opt))
            else:
                app("set {}={}".format(opt[0], opt[1]))
        # hspice compatibility mode.
        app("set ngbehavior=hsa")
        # save signals
        for sig in self.save:
            app("save {}".format(sig))
        for sim in self.simulations:
            # simulation commmand line.
            app("{}".format(sim.cmd))
            app("echo --- start {} ---".format(sim.identifier))
            # handle print statements
            for p in sim.prints:
                app("print {}".format(p))
            for pl in sim.plots:
                app("plot {}".format(pl))
            # handle output statements
            if sim.location == "":
                outloc = self.outputdir
            if sim.name == "":
                outname = self.outputfile
            if sim.outputs:
                if self.sweep_num:
                    app("wrdata {}/{}_{}_{} {}".format(outloc,
                                                       sim.identifier.lower(),
                                                       self.sweep_num,
                                                       outname, " ".join(sim.outputs)))
                else:
                    app("wrdata {}/{}_{} {}".format(outloc, sim.identifier.lower(),
                                                    outname, " ".join(sim.outputs)))
            # handle meas statements
            for m in sim.measure:
                app("{}".format(m))
            app("echo --- end {} ---".format(sim.identifier))
        if self.exit_post_run:
            app("exit")
        app(".endc")
        # add simulation options
        for opt in self.sim_options:
            if isinstance(opt, str):
                section.append(".option {}".format(opt))
            else:
                section.append(".option {}={}".format(opt[0], opt[1]))
        # add includes
        if self.includes:
            for lib in self.includes:
                app(".include \"{}\"".format(lib))
        # end of control netlist.
        app(".end")
        # update the object netlist
        section = [ "{}\n".format(line) for line in section ]
        self._netlist = "".join(section)


class CircuitSection():
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

    emap = {"*":  ["comment",                        ()],
            ".":  ["statement",                      ()],
            "A":  ["xspice",                         ()],
            "B":  ["behavioral source",              ("n+", "n-")],
            "C":  ["capacitor",                      ("n+", "n-")],
            "D":  ["diode",                          ("n+", "n-")],
            "E":  ["vcvs",                           ("n+", "n-", "nc+", "nc-")],
            "F":  ["cccs",                           ("n+", "n-")],
            "G":  ["vccs",                           ("n+", "n-", "nc+", "nc-")],
            "H":  ["ccvs",                           ("n+", "n-")],
            "I":  ["isource",                        ("n+", "n-")],
            "J":  ["jfet",                           ("n1", "n2", "n3")],
            "K":  ["coupled inductor",               ()],
            "L":  ["inductor",                       ("n+", "n-")],
            "M":  ["mosfet",                         ("n1", "n2", "n3", "n4")],
            "N":  ["numerical device gss",           ()],
            "O":  ["lossy transmission line",        ("n1", "n2", "n3", "n4")],
            "P":  ["coupled multiconductor line",    ()],
            "Q":  ["bjt",                            ("n1", "n2", "n3", "n4")],
            "R":  ["resistor",                       ("n+", "n-")],
            "S":  ["vcsw",                           ("n+", "n-", "nc+", "nc-")],
            "T":  ["lossless transmission line",     ("n1", "n2", "n3", "n4")],
            "U":  ["uniformely distributed rc line", ("n1", "n2", "n3")],
            "V":  ["vsource",                        ("n+", "n-")],
            "W":  ["icsw",                           ("n+", "n-")],
            "X":  ["subcircuit",                     ()],
            "XC": ["capacitor",                      ("n1", "n2")],
            "XM": ["mosfet",                         ("n1", "n2", "n3", "n4")],
            "Y":  ["single lossy transmission line", ("n1", "n2", "n3", "n4")],
            "Z":  ["mesfet",                         ("n1", "n2", "n3")]}


    def __init__(self, netlist, is_netlist=False):
        if is_netlist:
            self.filename = "Netlist"
            self._netlist = netlist
        else:
            self.filename = netlist
            self._netlist = read_netlist(self.filename)

        self.parsed_circuit = self.parse(self._netlist)
        self.circuit = copy.deepcopy(self.parsed_circuit)
        self.synthesize()


    def __str__(self):
        return self.netlist


    def __add__(self, other):
        return self.netlist + str(other)


    def __setitem__(self, key, item):
        self.circuit[key] = item


    def __getitem__(self, key):
        return self.circuit[key]


    @property
    def netlist(self):
        """ Simulation ready circuit netlist """
        self.synthesize()
        return "".join(self._netlist)


    def reset(self):
        """ Reset the circuit to the first parsed circuit. """
        self.circuit = copy.deepcopy(self.parsed_circuit)


    def append(self, line):
        """ Append a element to the circuit dict.

        Required inputs:
        ----------------
        line (str):     spice netlist line

        """
        count = 0
        while True:
            uid = (hashlib.md5((str(count)+line).encode())).hexdigest()
            count = count + 1
            if uid not in self.circuit.keys():
                break
        params = self.parse(line)
        uid = list(params.keys())[0]
        params = params[uid]
        self.circuit[uid] = params


    def identify_linetype(self, line):
        """ Identify the type of line.

        Required inputs:
        ----------------
        line (str):     spice netlist line

        """
        line = line.lstrip()
        letter_1 = line[0].upper()
        letter_2 = line[1].upper()
        if (letter_1 == "X" and letter_2 in ["M", "C"]):
            elemtype = letter_1 + letter_2
        else:
            elemtype = letter_1
        if not elemtype in self.emap.keys():
            raise Exception("Linetype not understood by parser")
        else:
            return elemtype


    def resolve_ports(self, line, elemtype):
        """ Extract the ports of the linetype.

        Required inputs:
        ----------------
        line (str):     Spice netlist line
        elemtype(str):  A spice netlist element type like V, R, C, E, etc.
                        check the emap dict for all available types.

        """
        port_list = self.emap[elemtype][1]
        elems = line.split(" ")
        if port_list:
            return {p:v for p,v in zip(port_list, elems[1:len(port_list)+1])}
        else:
            return {}



    def parse(self, netlist):
        """ Parse the string netlist into a circuit representation.

        Required inputs:
        ----------------
        netlist (str, list):    Spice netlist


        Returns
        ----------------
        elements (dict):        dict of circuit elements. Where
                                the key is the uid.


        Description
        ----------------
        This function takes the netlist and interprets each line by which
        type of element it sees and splits the line into i

        "instance":     identifier of the circuit element
        "type":         The type of circuit i.e. resistor vcvs etc.
        "ports":        The ports that the circuit element has if any.
        "args":         The arguments of the circuit element if any.

        It return a list where each element is a dict with these four keys.
        """
        elements = dict()
        if isinstance(netlist, str):
            netlist = netlist.split("\n")
        inside_ctl_section=False
        hierarchy = collections.deque()
        hierarchy.append("root")
        for i,line in enumerate(netlist):
            line = line.strip()
            if not re.match("^$|^\.end$|^\s*\*", line):
                if re.match("^.subckt*", line):
                    hierarchy.append(line.split(" ")[1])
                if re.match("^.control", line) or inside_ctl_section:
                    inside_ctl_section = True
                    if re.match("^.endc", line):
                        inside_ctl_section = False
                else:
                    elemtype = self.identify_linetype(line)
                    ports = self.resolve_ports(line, elemtype)
                    nports = len(ports)
                    itype = self.emap[elemtype][0]
                    elems = line.split(" ")
                    args = elems[nports+1:]
                    instance = elems[0]
                    location = "/".join(hierarchy)
                    uid = (hashlib.md5((str(i)+line).encode())).hexdigest()
                    if uid not in elements.keys():
                        elements[uid] = {"instance" : instance,
                                         "type"     : itype,
                                         "ports"    : ports,
                                         "location" : location,
                                         "args"     : args}
                    else:
                        raise Exception("uid not unique. Aborting.")
                if re.match("^.ends.*", line):
                    hierarchy.pop()
        return elements


    def synthesize(self):
        """ Create a netlist from a circuit.

        Description
        ----------------
        Reverse of parse(). It generates a netlist from a list from
        the circuit object.
        Synthesize will update the object internal netlist when called.

        """
        netlist = [ "* {}\n\n".format(self.filename) ]
        for uid in self.circuit:
            s = ""
            if self.circuit[uid]["instance"] == ".ends":
                is_ends = True
            else:
                is_ends = False
            for k in self.circuit[uid]:
                if k == "instance":
                    s += self.circuit[uid][k] + " "
                elif k == "ports":
                    sp = " ".join(self.circuit[uid][k].values())
                    if sp:
                        s += sp + " "
                elif k == "args":
                    sa = " ".join(self.circuit[uid][k])
                    if sa:
                        s += sa
            netlist.append(s+"\n")
            if is_ends:
                netlist.append("\n")
        self._netlist = netlist


    def write(self, filename):
        """ Write the netlist to file

        Optional inputs:
        ----------------
        filename (str):     name of the output file
        """
        write_netlist(self.netlist, filename)


    def match(self, key, val):
        """ Match a circuit element key by regex.

        Required inputs:
        ----------------
        key (str):      Dictionary key.
        val (str):      Regular expression to match.


        Returns
        ----------------
        matches (list): A list with all the lines in
                        self.circuit where the key matches
                        the regular expression.
        """
        matches = []
        for uid in self.circuit:
            if re.match(val, self.circuit[uid][key]):
                matches.append(uid)
        return matches


    def filter(self, filt):
        """ Filter circuit elements by regex.

        Required inputs:
        ----------------
        filt (tuple, list , dict):  Pairs of key to circuit element
                                    dict and regex to match in that key.

        Returns
        ----------------
        matches (list):             List of uid's that matches the
                                    criteria.

        Description
        ----------------
        The filt argument can be a:

            tuple: ("instance", "xr.*")
            list : [("instance", "xr.*"), ("type", "subc*")]
            dict : {"instance": "xr.*", "type": "subc*"}

        The filter matches the filt input in order.

        """
        if isinstance(filt, tuple):
            key = filt[0]
            val = filt[1]
            return self.match(key, val)
        if isinstance(filt, list):
            key = filt[0][0]
            val = filt[0][1]
            matches = self.match(key, val)
            for elem in filt[1:]:
                key = elem[0]
                val = elem[1]
                nmatch = self.match(key, val)
                mmatch = []
                for elem in nmatch:
                    if elem in matches:
                        mmatch.append(elem)
                matches = mmatch
            return matches
        elif isinstance(filt, dict):
            key = list(filt.keys())[0]
            val = filt[key]
            matches = self.match(key, val)
            for k in list(filt.keys())[1:]:
                nmatch = self.match(k, filt[k])
                mmatch = []
                for elem in nmatch:
                    if elem in matches:
                        mmatch.append(elem)
                matches = mmatch
            return matches


    def apply(self, func, filt, **kwargs):
        """ Apply function to matching circuit elements.

        Required inputs:
        ----------------
        func (func):                function to apply to matching elements.
        filt (tuple, list , dict):  pairs of key to circuit element dict
                                    and regex to match in that key.
                                    See also self.filter for more info.

        Returns
        ----------------
        n (int):                    number of modified circuit elements


        Description
        ----------------
        Filter the circuit representation for matching elements.
        Then apply func to all those elements.
        If func modifies the the object it will alter the internal
        circuit representation also!
        kwargs are passed along to func.
        """
        matches = self.filter(filt)
        if matches:
            for uid in matches:
                element = self.circuit[uid]
                self.circuit[uid] = func(element, **kwargs)
        return len(matches)


def unpack_args(args):
    """ Unpack circuit element arguments.

    Required inputs:
    ----------------
    args (list):        Circuit element arguments

    Returns
    ----------------
    unpacked (dict):    Circuit element arguments as dictionary.
                        if there is no assigment (=) then the value
                        is simply None.
    """
    unpacked = dict()
    for elem in args:
        s = elem.split("=",1)
        if len(s) == 1:
            unpacked[s[0]] = None
        else:
            unpacked[s[0]] = s[1]
    return unpacked


def repack_args(args):
    """ Repackage circuit element arguments.

    Required inputs:
    ----------------
    args (dict):        Circuit element arguments as dict

    Returns
    ----------------
    repacked (list):    Circuit element arguments as list
    """
    repacked = []
    for k in args:
        if args[k]:
            repacked.append("{}={}".format(k, args[k]))
        else:
            repacked.append("{}".format(k))
    return repacked


def replace_argument(uid, cir, key, val):
    """ Replace an argument of a circuit element.

    Required inputs:
    ----------------
    uid (str):              Unique identfier of the circuit
                            element.
    cir (CircuitSection):   circuit section in which to replace
                            the argument.
    key (str):              key to identify the argument that is
                            to be replaced.
    val (str):              The value that is inserted as a
                            replacement for the key.

    Returns
    ----------------
    cir (CircuitSection):   circuit section where the argument
                            has been replaced.
    """
    args = unpack_args(cir[uid]["args"])
    if args[key]:
        args[key] = val
    else:
        replacement = {key: val}
        for k, v in list(args.items()):
            args[replacement.get(k, k)] = args.pop(k)
            tmp = dict()
            for k in args:
                if k == key:
                    tmp[k.upper()] = args[k]
                else:
                    tmp[k] = args[k]
            args = tmp
    args = repack_args(args)
    cir[uid]["args"] = args
    return cir


def read_netlist(filename):
    """ Read a netlist from file.

    Required inputs:
    ----------------
    filename (str):         Name/path of the netlist file.

    Returns
    ----------------
    clean_netlist (str):    Netlist that has been made uniform
                            through the input cleanup process.
    """
    with open(filename, "r") as ifile:
        netlist = ifile.read()
    return clean_netlist(netlist)


def write_netlist(netlist, filename):
    """ Write a netlist to file.

    Required inputs:
    ----------------
    netlist (list):     line by line ne
    filename (str):     Name/path for the netlist file
    """
    with open(filename, "w") as ofile:
        ofile.write("* Netlist written: {}\n".format(datetime.datetime.now()))
        if isinstance(netlist, list):
            ofile.write("\n".join(netlist))
        elif isinstance(netlist, str):
            ofile.write(netlist)
        elif isinstance(netlist, CircuitSection):
            ofile.write(netlist.netlist)
        elif isinstance(netlist, ControlSection):
            ofile.write(netlist.netlist)
        else:
            raise Exception("Write netlist cannot operate with {}".format(type(netlist)))


def write_sim_netlist(cir, ctl, directory=".", filename="netlist.cir"):
    """ Assemble a simulation ready netlist.

    Required inputs:
    ----------------
    cir (CircuitSection):   CircuitSection object
    ctl (ControlSection):   ControlSection object


    Optional inputs:
    ----------------
    directory (str):        Output directory.
    filename (str):         Netlist name.
    """
    if isinstance(cir, CircuitSection):
        cir = cir.netlist
    if isinstance(ctl, ControlSection):
        ctl = ctl.netlist

    net = cir + ctl
    output = "{}/{}".format(directory, filename)
    write_netlist(net, output)


def clean_netlist(netlist):
    """ Cleanup a netlist.

    Required inputs:
    ----------------
    netlist (str, list):    Netlist as a single string or list of lines.


    Returns
    ----------------
    netlist (str):          The cleaned netlist


    Description
    ----------------
    This function will cleanup a netlist and unify it such that
    i can be processed in a reliable manner.

    The order of the individual steps matters! Be careful
    when changing something that the order is preserved and
    makes sense.
    """

    if isinstance(netlist, str):
        netlist = netlist.split("\n")

    netlist = [line.lstrip() for line in netlist]

    # Remove emtpy continued (+) lines, emtpy lines
    # and comments.
    netlist_a0 = []
    for line in netlist:
        if not re.match("^\+\s*$|^\s{,}$|^\*.*$",line):
            netlist_a0.append(line)

    # Remove end of line comments
    netlist_a = [re.sub("\$.*", "", line) for line in netlist_a0]

    # Combine split lines back to one
    netlist_b = []
    for line in netlist_a:
        if re.match("^\+",line):
            netlist_b[-1] = netlist_b[-1] + re.sub("^\+\s{,}", " ", line)
        else:
            netlist_b.append(line)

    # Unify Whitespace
    netlist_c = [re.sub("\t| {1,}", " ", line) for line in netlist_b]

    # Remove whitespace inside expression
    netlist_d = [remove_enclosed_space(line) for line in netlist_c]

    # Remove space around assignments
    netlist_e = [re.sub(" {1,}= {1,}", "=", line) for line in netlist_d]

    # Lowercase all letters unless .include statement
    netlist_f = []
    for line in netlist_e:
        if re.match("^.include.*", line):
            netlist_f.append(line)
        else:
            netlist_f.append(line.lower())

    netlist = "\n".join(netlist_f)
    return netlist


def remove_enclosed_space(string):
    """ Remove whitespace enclosed in single quotes

    Required inputs:
    ----------------
    string (str):   A string from which the whitespace is to be removed.


    Returns
    ----------------
    string (str):   String with whitespace between single quotes removed.

    """
    state = False
    parsed = []
    for c in string:
        if c == "'":
            if state:
                state = False
            else:
                state = True
            parsed.append(c)
        else:
            if state:
                if c == " ":
                    pass
                else:
                    parsed.append(c)
            else:
                parsed.append(c)
    return "".join(parsed)
