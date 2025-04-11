from lris2csu.slit import MaskConfig
from mktl.mktlcoms import MKTLComs


class CSURemote:
    def __init__(self, csu_address:str=None, registry_address:str=None, start_comms=True):
        """
        Initializes a CSU Remote Control with either a specific address, or an mKTL registry address,
        optionally start mKTL communications.

        If specified the csu_address will take precedence over the registry_address and is required if no registry
        is provided.

        :param csu_address: The address of the CSU to establish a connection.
        :type csu_address: str, optional
        :param registry_address: The address of the registry used by the communication system.
        :type registry_address: str, optional
        :param start_comms: Indicates whether the communication system should start immediately or not.
        :type start_comms: bool, default is True
        """
        self.csu_address = csu_address
        if not self.csu_address and not registry_address:
            raise ValueError("Either csu_address or registry_address must be specified.")
        self.coms = MKTLComs(registry_addr=registry_address)

        if start_comms:
            self.coms.start()

    def configure(self, mask_config:MaskConfig, speed=8000):
        self.coms.set('lris2csu.configure', dict(args=(mask_config.to_dict(),), kwargs={'speed':speed}),
                      destination=self.csu_address)

    def reset(self):
        self.coms.set('lris2csu.reset', dict(args=tuple()), destination=self.csu_address)

    def calibrate(self, one_at_a_time=False):
        self.coms.set('lris2csu.calibrate', dict(args=tuple(), kwargs={'one_at_a_time':one_at_a_time}),
                      destination=self.csu_address)

    def shutdown(self):
        self.coms.set('lris2csu.mktl_control', dict(args=tuple()), destination=self.csu_address)

    def status(self, verbose=False):
        return self.coms.get('lris2csu.status', dict(args=tuple(), kwargs={'verbose':verbose}))

    def stop(self):
        self.coms.set('lris2csu.stop', dict(args=tuple()), destination=self.csu_address)

    def clear_faults(self):
        self.coms.set('lris2csu.clear_faults', dict(args=tuple()), destination=self.csu_address)