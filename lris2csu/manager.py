from logging import getLogger
import threading
import argparse
import yaml
import functools

from lris2csu.util import setup_logging
from lris2csu.hardware import CSUHardware

from mktl.mktlcoms import MKTLComs


class CSUDummyHardware:
    def __init__(self, cfg):
        getLogger(__name__).info(f"CSU Dummy Hardware initialized with config: {cfg}")
        self.cfg = cfg

    def __getattr__(self, item):
        def func(*args, **kwargs):
            getLogger(__name__).info(f"Dummy CSUDummyHardware.{item} called with args={args} and kwargs={kwargs}")
            return 'Boo!'
        return func


class CSUServer:
    def __init__(self, config='csu.yaml', start=True, dummynode=False):

        # Load and parse the configuration YAML file
        try:
            with open(config, 'r') as f:
                self.configuration: dict = yaml.full_load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration file '{config}': {e}")

        if dummynode:
            self.csu = CSUDummyHardware(self.configuration['hardware'])
        else:
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
    parser.add_argument('--no-hardware', dest='dummy_mode', action='store_true', required=False,
                        help='Do not instantiate the CSUHardware', default=False)
    return parser.parse_args()


if __name__ == '__main__':

    import os, time
    os.environ['TZ'] = 'right/UTC'
    time.tzset()
    args = parse_cl()
    setup_logging('csuserver')

    app = CSUServer(config=args.config_yaml, start=True, dummynode=args.dummy_mode)
    print("CSU Server running on tcp://*:5570")
    while True:
        threading.Event().wait(60)