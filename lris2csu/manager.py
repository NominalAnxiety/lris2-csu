from logging import getLogger
import threading
import argparse
from typing import Callable

import yaml
import functools

from lris2csu.util import setup_logging
from lris2csu.hardware import CSUHardware
from lris2csu.slit import MaskConfig, Slit

from mktl.mktlcoms import MKTLComs, MKTLMessage
from mktl.registry import DEFAULT_REGISTRY_PORT


class CSUDummyHardware:
    def __init__(self, cfg):
        getLogger(__name__).info(f"CSU Dummy Hardware initialized with config: {cfg}")
        self.cfg = cfg

    def reset_bus(self):
        pass

    def calibrate(self, one_at_a_time=False):
        pass

    def configure(self, mask_config:MaskConfig, speed=8000):
        pass

    def halt(self):
        pass

    def status(self, verbose:bool=False)->dict:
        d = {'node': '',
                 'position': '',
                 'target_position':  '',
                 'error_reg': '',
                 'error_code': '',}
        if verbose:
            d.update({
                 'network_state': '',
                 'mode_of_operation': '',
                 'velocity_demand' : '',
                 'velocity_actual': '',
                 'velocity_profile': '',
                 'velocity_target': '',
                 'torque_actual' : '',
                 'controlword': '',
                 'statusword': '',
                 'temperatue': '',
                 })
        status = {id: [d,d] for id in range(11)}

        ret = {'status': status,
               'mask': MaskConfig(tuple(Slit(i, 3*130/2-(i%2)*120, 20) for i in range(12))).to_dict(),
               }
        return ret

    def clear_faults(self):
        pass

    def terminate_control(self):
        pass


class CSUServer:

    def __init__(self, config='csu.yaml', start=True, dummynode=False, cmd_port=None, registry_addr=None):

        self.csu = None
        self.comms: MKTLComs | None = None
        self.CSU_COMMANDS: dict[str, Callable] = {}

        # Load the configuration file
        self.configuration = self._load_config(config)

        # Set up hardware
        hardware = CSUDummyHardware if dummynode else CSUHardware
        self.csu = hardware(self.configuration['hardware'])

        # Set up CSU command handlers
        self._set_up_commands()

        # Set up communication
        cmd_port = cmd_port or self.configuration['daemon']['mktl']['cmd_port']
        ip = self.configuration['daemon']['mktl']['daemon_ip']
        self.comms = MKTLComs(identity=self.configuration['daemon']['name'], authoritative_keys=self.CSU_COMMANDS,
                              registry_addr=registry_addr or self.configuration['daemon']['mktl']['registry'],
                              shutdown_callback=self.shutdown, bind_addr=f'tcp://{ip}:{cmd_port}', start=False)

        # If start is True, start communication and reset hardware
        if start:
            self.comms.start()
            self.csu.reset_bus()

    @staticmethod
    def _load_config(config):
        """Load the configuration file."""
        try:
            with open(config, 'r') as f:
                return yaml.full_load(f)
        except FileNotFoundError:
            raise RuntimeError(f"Configuration file '{config}' not found.")
        except yaml.YAMLError as e:
            raise RuntimeError(f"YAML parsing error in '{config}': {e}")

    def _set_up_commands(self):
        """Set up CSU command handlers."""
        name = self.configuration['daemon']['name']
        self.CSU_COMMANDS = {
            f'{name}.configure': self.handler,
            f'{name}.reset': self.handler,
            f'{name}.calibrate': self.handler,
            f'{name}.status': self.handler,

            f'{name}.abort': self.handler,
            f'{name}.halt': self.handler,
            f'{name}.stop': self.handler,
            f'{name}.clear_faults': self.handler,
        }

    def shutdown(self):
        """Shutdown the server."""
        getLogger(__name__).info('Shutting down')
        self.csu.terminate_control()
        self.comms.stop()
        exit(0)

    def handler(self, m:MKTLMessage):
        """
        Handle a command message.

        TODO: This is gross and my fault -JIB, will clean up with better integrations with mktlcoms."""
        method = m.msg_type
        context = m.json_data
        key = m.key
        m.ack()

        if method =='get' and key.split('.')[1] not in ('status',):
            m.fail('get unsupported')

        if method =='set' and key.split('.')[1] not in ('configure', 'reset', 'calibrate', 'abort', 'halt', 'stop', 'clear_faults'):
            m.fail('set unsupported')

        args = context.get('args', [])
        kwargs = context.get('kwargs', {})
        resp = 'OK'
        try:
            if 'configure' in key:
                mask = MaskConfig.from_dict(args[0])
                self.csu.configure(mask, **kwargs)
            if 'reset' in key:
                self.csu.reset_bus()
            if 'calibrate' in key:
                self.csu.calibrate(**kwargs)
            if 'status' in key:
                resp = self.csu.status(**kwargs)
            if 'abort' in key or 'halt' in key or 'stop' in key:
                self.csu.halt()
            if 'clear_faults' in key:
                self.csu.clear_faults()
        except Exception as e:
            getLogger(__name__).exception(f"Exception in {key}: {e}", exc_info=True)
            m.fail(str(e))
        m.respond(resp)


def parse_cl():
    parser = argparse.ArgumentParser(description='LRIS2 CSU Server', add_help=True)
    parser.add_argument('-p', '--port', dest='port', action='store', required=False, type=int,
                        help='Server port', default=None)
    parser.add_argument('--registry', dest='registry', action='store', required=False, type=str,
                        help='Registry Address', default='')
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

    app = CSUServer(config=args.config_yaml, start=True, dummynode=args.dummy_mode,
                    cmd_port=args.port, registry_addr=args.registry)
    while True:
        threading.Event().wait(60)