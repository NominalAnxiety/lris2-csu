from logging import getLogger
import threading
import argparse
import yaml
import functools

from cooethercat.helpers import StatuswordStates, HomingMethods
from cooethercat import EPOS4Bus

from lris2csu.slit import MaskConfig
from lris2csu.util import setup_logging
from lris2csu.hardware import BarMotor, BrakeMotor, CSUHardwareConfig
from mktl.mktlcoms import MKTLComs


class CSUHardware:
    def __init__(self, config:CSUHardwareConfig|str='csu.yaml', connect=False):

        if not isinstance(config, CSUHardwareConfig):
            # Load and parse the configuration YAML file
            try:
                with open(config, 'r') as f:
                    config: dict = yaml.full_load(config)['hardware']
            except Exception as e:
                raise ValueError(f"Failed to load configuration file '{config}': {e}")

        self.configuration :CSUHardwareConfig = config

        # self.left_brake = BrakeMotor(self.configuration.left_brake)
        # self.left_brake = BrakeMotor(self.configuration.right_brake)

        # TODO I'm not thrilled with implementing this via functools partial as it does require a better understanding
        #  of python. Its probably clear enough that it can serve as a teaching moment if necessary
        self.slave_types = {id: functools.partial(BarMotor, kwargs={'use_ssi_encoder':cfg.use_ssi})
                            for id, cfg in self.configuration.bar_configs.items()}

        # Create the bus
        self.bus = EPOS4Bus(self.configuration.ethercat_device)
        if connect:
            self.reset_bus()

    def reset_bus(self):
        self.bus.initialize(self.slave_types)

    def calibrate(self):
        self.bus.disable_pdo()
        for s in self.bus.slaves:
            if self.configuration.bar_by_dev_id(s.node).reversed:
                method = HomingMethods.CURRENT_THRESHOLD_POS_SPEED_AND_INDEX
            else:
                method = HomingMethods.CURRENT_THRESHOLD_NEG_SPEED_AND_INDEX
            s.home_via_method(method, current_threshold=350, monitor=None, timeout=30, setup_only=True)
        self.bus.enable_pdo()
        self.bus.execute_homing()

    def configure(self, mask_config:MaskConfig, speed=8000):
        bar_pos = self.configuration.compute_bar_count_positions(mask_config.to_dict())
        self.bus.enable_pdo()
        self.bus.move_to(bar_pos, blocking=True, speed=speed)
        self.bus.disable_pdo()

    def halt(self):
        self.bus.disable_pdo()
        for s in self.bus.slaves:
            s.halt()

    def status(self):
        return {id: (self.bus.slaves[bp.left.bus_id].debug_info_sdo,
                     self.bus.slaves[bp.right.bus_id].debug_info_sdo)
                for id, bp in self.configuration.bar_pairs.items()}

    def terminate_control(self):
        self.bus.disable_pdo()
        self.bus.close()



class CSUServer:
    def __init__(self, config='csu.yaml', start=True):

        # Load and parse the configuration YAML file
        try:
            with open(config, 'r') as f:
                self.configuration: dict = yaml.full_load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration file '{config}': {e}")

        self.csu = CSUHardware(self.configuration['hardware'])

        name = self.configuration['daemon']['name']
        CSU_COMMANDS = {
            f'{name}.configure': self.csu.configure,
            f'{name}.reset': self.csu.reset_bus,
            f'{name}.calibrate': self.csu.calibrate,
            f'{name}.status': self.csu.status,

            f'{name}.abort': self.csu.halt,
            f'{name}.halt': self.csu.halt,
            f'{name}.stop': self.csu.halt,
        }

        self.comms = MKTLComs(identity=name, authoritative_keys=CSU_COMMANDS,
                              registry_addr=self.configuration['daemon']['mktl']['registry'],
                              shutdown_callback=self.shutdown)
        cmd_port = self.configuration['daemon']['mktl']['cmd_port']
        pub_port = self.configuration['daemon']['mktl']['pub_port']
        self.comms.bind(f'tcp://0.0.0.0:{cmd_port}')
        self.comms.bind_pub(f'tcp://0.0.0.0:{pub_port}')
        if start:
            self.comms.start()

    def shutdown(self):
        getLogger(__name__).info('Shutting down')
        self.csu.terminate_control()
        self.comms.stop()
        exit(0)


def parse_cl():
    parser = argparse.ArgumentParser(description='LRIS2 CSU Server', add_help=True)
    parser.add_argument('-p', '--port', dest='port', action='store', required=False, type=int,
                        help='Server port', default='8888')
    parser.add_argument('--status_port', dest='status_port', action='store', required=False, type=int,
                        help='Status Port', default='8890')
    parser.add_argument('--eth', dest='ethernet_device', action='store', required=True, type=str,
                        help='Ethercat device (e.g. eth0)', default='eth0')
    parser.add_argument('--cfg', dest='config_yaml', action='store', required=False, type=str,
                        help='Configuration YAML', default='')
    return parser.parse_args()


if __name__ == '__main__':

    import os, time
    os.environ['TZ'] = 'right/UTC'
    time.tzset()
    args = parse_cl()
    setup_logging('csuserver')

    app = CSUServer(config=args.config_yaml, start=True)
    print("CSU Server running on tcp://*:5570")
    while True:
        threading.Event().wait(60)