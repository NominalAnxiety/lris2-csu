from logging import getLogger
import pysoem
from cooethercat.epos4 import *
import cooethercat
from cooethercat.epos4 import StatuswordStates
from lris2csu.util import  setup_logging, load_default_config
from lris2csu.manager import CSUHardware

setup_logging('csuserver')
cfg = load_default_config()
csu = CSUHardware(cfg['hardware'])



csu.reset_bus()

bus = csu.bus
slaves = csu.bus.slaves
pmaster = csu.bus._bus.pysoem_master
pslaves = pmaster.slaves


csu.calibrate()

i=8
sign = -1 if csu.configuration.bar_by_dev_id(i).reversed else 1
csu.bus.slaves[i].profile_position_move_sdo(30e5*sign,4000)

i=8
method = HomingMethods.CURRENT_THRESHOLD_POS_SPEED_AND_INDEX if csu.configuration.bar_by_dev_id(i).reversed else HomingMethods.CURRENT_THRESHOLD_NEG_SPEED_AND_INDEX
csu.bus.slaves[i].home_via_method(method, current_threshold=300, monitor=EPOS4Registers.CURRENT_ACTUAL_VALUE_INSTANT, timeout=30)



open_pos = 0
central_slit = {i:(130, 30) for i in range(12)}
stair_slit = {i:(130+i*10-6*10, 20) for i in range(12)}
nstair_slit = {i:(130-i*10+6*10, 20) for i in range(12)}
window_slits = {i:(130/2+(i%2)*120, 20) for i in range(12)}
nwindow_slits = {i:(3*130/2-(i%2)*120, 20) for i in range(12)}

central_pos = csu.configuration.compute_bar_count_positions(central_slit)
stair_pos = csu.configuration.compute_bar_count_positions(stair_slit)
nstair_pos = csu.configuration.compute_bar_count_positions(nstair_slit)
window_pos = csu.configuration.compute_bar_count_positions(window_slits)
nwindow_pos = csu.configuration.compute_bar_count_positions(nwindow_slits)

csu.bus.move_to(central_pos)
