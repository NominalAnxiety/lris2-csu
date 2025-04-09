from logging import basicConfig, DEBUG, getLogger

basicConfig(level=DEBUG)
getLogger('mktl').setLevel(DEBUG)

from lris2csu.remote import CSURemote
c=CSURemote(registry_address='tcd://localhost:5570')