#!/usr/bin/env python3

import ngsim
import pytest
import logging
import os
from filelock import FileLock
import datatools as dt


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

CORNERS_PATH = os.getenv('CORNERS')
DESIGN_PATH  = os.getenv('DESIGN')
XSCHEMRC = os.getenv('XSCHEMRC')
SIM = os.getenv('SIM')
LOGDATE = os.getenv('LOGDATE')
CONFFILE = os.getenv('CONFFILE')
CWD = os.getenv('CWD')

#----------------------------------------------------------------------
# GENERAL NOTES
#----------------------------------------------------------------------
# - Test and config has always the same name as TB schematic.
# - To simulate PVT the supply source has to be named vdd.
# - Use a configuration template with this test as defined 
#   through my ngsim.parse_configuration parser.
#----------------------------------------------------------------------

filename = CONFFILE
cdir = CWD


log.info("filename", filename)
log.info("cwd", CWD)

name, file_sch, file_conf, file_res = ngsim.path_setup(filename, cdir, LOGDATE)
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


#----------------------------------------------------------------------
# TEST SETUP
#----------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def create_resultfile():
    with open(file_res, "w") as resfile:
        resfile.write("corner,vdd,temp,{},par,val,pass\n".format(var_name))


@pytest.mark.parametrize("temp",   CONF["temperature"])
@pytest.mark.parametrize("vdd",    CONF["supply"])
@pytest.mark.parametrize("corner", CONF["corners"])
@pytest.mark.parametrize("var",    var_value)
def test_Corners(corner, vdd, temp, var):
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
    for elem in CONF["evaluate"]:
        eval_str = "{} {} {}".format(res[elem[0]], elem[1], elem[2])
        if not eval(eval_str):
            overall_result = False
            failed.append(elem[0])
            log.warning("Failed Condition, \"{}\" = {}".format(elem[0], eval_str))

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
        log.info("{:<12} = {:<12}".format(k, dt.convert_sci_eng(res[k])))
    log.info("--------------------")
    if not overall_result:
        assert False
