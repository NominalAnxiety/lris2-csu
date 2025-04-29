from typing import Any

from lris2csu.slit import MaskConfig, Slit
from mktl.mktlcoms import MKTLComs


class CSURemote:
    def __init__(self, csu_address:str=None, start_comms=True, dummy_mode=False):
        """
        Initializes a CSU Remote Control with either a specific address or an mKTL registry
        address, optionally starting mKTL communications.

        If specified, the `csu_address` will take precedence over the `registry_address`
        and is required if no registry is provided.

        Args:
            csu_address (str, optional): The address of the CSU to establish a connection.
            start_comms (bool, optional): Indicates whether the communication system should start immediately. Default is True.
            dummy_mode (bool, optional): Indicates whether the manager is running in dummy mode. Default is False.
        """

        self.csu_address = csu_address
        self.dummy_mode = dummy_mode
        self.coms = MKTLComs()

        if start_comms:
            self.coms.start()

    def configure(self, mask_config:MaskConfig, speed=8000):
        return self.coms.set('lris2csu.configure', dict(args=(mask_config.to_dict(),), kwargs={'speed':speed}),
                      destination=self.csu_address).json_data

    def reset(self):
        return self.coms.set('lris2csu.reset', dict(args=tuple()), destination=self.csu_address).json_data

    def calibrate(self, one_at_a_time=True):
        return self.coms.set('lris2csu.calibrate', dict(args=tuple(), kwargs={'one_at_a_time':one_at_a_time}),
                      destination=self.csu_address).json_data

    def shutdown(self):
        return self.coms.set('lris2csu.mktl_control', dict(args=tuple()), destination=self.csu_address).json_data

    def status(self, verbose=False) -> tuple[dict[Any, Any], MaskConfig]:
        if self.dummy_mode:
            # In dummy mode, return mock status and a simple dummy MaskConfig
            mock_status = {'status': 'dummy_value'}
            # Create a mock MaskConfig
            mock_mask = MaskConfig(tuple(Slit(i, 130, 30) for i in range(12)))
            return mock_status, mock_mask

        else:
            # In hardware mode, perform the usual status query
            x = self.coms.get('lris2csu.status', dict(args=tuple(), kwargs={'verbose': verbose})).json_data
            return x['status'], MaskConfig.from_dict(x['mask'])

    def stop(self):
        return self.coms.set('lris2csu.stop', dict(args=tuple()), destination=self.csu_address).json_data

    def clear_faults(self):
        return self.coms.set('lris2csu.clear_faults', dict(args=tuple()), destination=self.csu_address).json_data