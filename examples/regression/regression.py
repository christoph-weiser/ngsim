#!/usr/bin/env python3

import os
import ngsim
import logging
import itertools
from filelock import FileLock
from multiprocessing import Pool, Manager

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


CORNERS_PATH = os.getenv('CORNERS')
DESIGN_PATH  = os.getenv('DESIGN')
XSCHEMRC = os.getenv('XSCHEMRC')
SIM = os.getenv('SIM')
LOGDATE = os.getenv('LOGDATE')
CONFFILE = os.getenv('CONFFILE')
CWD = os.getenv('CWD')
CORES= int(os.getenv('CORES'))

filename = CONFFILE
cdir = CWD
name, file_sch, file_conf, file_res = ngsim.path_setup(filename, cdir, LOGDATE)

log.info("name: {}".format(name))
log.info("file_sch: {}".format(file_sch))
log.info("file_conf: {}".format(file_conf))
log.info("file_res: {}".format(file_res))

file_net = ngsim.create_netlist(file_sch, SIM, XSCHEMRC)
netlist_in = ngsim.read_netlist(file_net)

cir = ngsim.CircuitSection(netlist_in, True)
ctl = ngsim.extract_control(netlist_in)

CONF = ngsim.parse_configuration(file_conf)

if not CONF["temperature"]:
    CONF["temperature"] = ["27"]

try:
    var_name = list(CONF["variable"].keys())[0]
    var_value = list(CONF["variable"].values())[0]
except:
    var_value = [None]
    var_name = "None"


def create_resultfile():
    with open(file_res, "w") as resfile:
        resfile.write("corner,vdd,temp,{},par,val,pass\n".format(var_name))

def test_corners(args):
    temp   = args[0]
    vdd    = args[1]
    corner = args[2]
    var    = args[3]

    log.info("--------------------")
    log.info("Starting Test")
    log.info("--------------------")
    log.info("corner:    {}".format(corner))
    log.info("vdd:       {}".format(vdd))
    log.info("temp:      {}".format(temp))
    log.info("var ({}):  {}".format(var_name, var))
    log.info("--------------------")

    cir = ngsim.CircuitSection(netlist_in, True)
    ctl = ngsim.extract_control(netlist_in)

    def alter_vdd(elem, vdd):
        elem["args"] = [str(vdd)]
        return elem

    def alter_temp(elem, temp):
        elem["args"] = [str(temp)]
        return elem

    def alter_var(elem, variable, name):
        sargs = elem["args"][0].split("=")
        if sargs[0] == name:
            elem["args"] = ["{}={}".format(sargs[0], variable)]
        return elem

    cir.apply(alter_vdd,  {"instance": "vdd",    "type": "vsource"},   vdd=vdd)
    cir.apply(alter_var,  {"instance": ".param", "type": "statement"}, variable=var, name=var_name)
    if cir.filter({"instance": ".temp",  "type": "statement"}):
        cir.apply(alter_temp, {"instance": ".temp",  "type": "statement"}, temp=temp)
    else:
        cir.append(".temp {}".format(temp))

    netlist = cir.netlist + ctl

    include = ".include {}/{}.spice\n".format(CORNERS_PATH, corner)
    simulation_netlist = include + netlist
    output = ngsim.run_simulation(simulation_netlist)
    res = ngsim.extract_output_data(output)
    overall_result = True
    failed = []
    log.info(res)

    for elem in CONF["evaluate"]:
        try:
            eval_str = "{} {} {}".format(res[elem[0]], elem[1], elem[2])
            if not eval(eval_str):
                overall_result = False
                failed.append(elem[0])
                log.warning("Failed Condition, \"{}\" = {}".format(elem[0], eval_str))
        except KeyError:
                overall_result = False
                failed.append(elem[0])
                log.warning("Failed Simulation")

    log.warning("Failed parameters: {}\n".format(failed))
    lockfile = file_res + ".lock"
    lock = FileLock(lockfile)
    with lock:
        with open(file_res, "a") as resfile:
            for k in res:
                if k in failed:
                    resfile.write("{},{},{},{},{},{},False\n".format(corner, vdd, temp, var, k, res[k]))
                else:
                    resfile.write("{},{},{},{},{},{},True\n".format(corner, vdd, temp, var, k, res[k]))

    log.info("--------------------")
    log.info("Results")
    log.info("--------------------")
    for k in res:
        log.info("{:<12} = {:<12}".format(k, res[k]))
    log.info("--------------------")


#----------------------------------------------------------------------
# TEST RUN
#----------------------------------------------------------------------

create_resultfile()

corners = list(itertools.product(CONF["temperature"], CONF["supply"], CONF["corners"], var_value))

with Pool(processes=CORES) as pool:
    pool.map(test_corners, corners)

