from logging import basicConfig, DEBUG, getLogger
import time

basicConfig(level=DEBUG)
getLogger('mktl').setLevel(DEBUG)

from lris2csu.remote import CSURemote
from lris2csu.slit import Slit, MaskConfig
from mktl.registry import DEFAULT_REGISTRY_PORT

stair_mask = MaskConfig(tuple(Slit(i, 130+i*10-6*10, 20) for i in range(12)))

c=CSURemote(registry_address=f'tcp://131.215.200.105:{DEFAULT_REGISTRY_PORT}')  #should be lris2csu but imss *sigh*

c.status()
time.sleep(1)
c.configure(stair_mask, speed=6500)
time.sleep(1)
c.stop()
