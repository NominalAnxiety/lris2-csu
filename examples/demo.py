from logging import getLogger
import pysoem
from cooethercat.epos4 import *
from lris2csu.util import  setup_logging, load_default_config
from lris2csu.manager import CSUHardware
from lris2csu.slit import Slit, MaskConfig

setup_logging('csuserver')
cfg = load_default_config()
csu = CSUHardware(cfg['hardware'])

csu.reset_bus()

# csu.calibrate()


stair_mask = MaskConfig(tuple(Slit(i, 130+i*10-6*10, 20) for i in range(12)))
nstair_mask = MaskConfig(tuple(Slit(i, 130-i*10+6*10, 20) for i in range(12)))
central_mask = MaskConfig(tuple(Slit(i, 130, 30) for i in range(12)))
window_mask = MaskConfig(tuple(Slit(i, 130/2+(i%2)*120, 20) for i in range(12)))
nwindow_mask = MaskConfig(tuple(Slit(i, 3*130/2-(i%2)*120, 20) for i in range(12)))

csu.configure(window_mask)

bus = csu.bus
slaves = csu.bus.slaves
pmaster = csu.bus._bus.pysoem_master
pslaves = pmaster.slaves
# i=8
# sign = -1 if csu.configuration.bar_by_dev_id(i).reversed else 1
# csu.bus.slaves[i].profile_position_move_sdo(30e5*sign,4000)
#
# i=8
# method = HomingMethods.CURRENT_THRESHOLD_POS_SPEED_AND_INDEX if csu.configuration.bar_by_dev_id(i).reversed else HomingMethods.CURRENT_THRESHOLD_NEG_SPEED_AND_INDEX
# csu.bus.slaves[i].home_via_method(method, current_threshold=300, monitor=EPOS4Registers.CURRENT_ACTUAL_VALUE_INSTANT, timeout=30)
#
open_pos = 0
central_pos = csu.configuration.compute_bar_count_positions({i:(130, 30) for i in range(12)})
csu.bus.enable_pdo()
csu.bus.move_to(open_pos)
time.sleep(30)
csu.bus.disable_pdo()
csu.bus.set_device_states(StatuswordStates.READY_TO_SWITCH_ON)