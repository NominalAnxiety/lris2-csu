from logging import getLogger
import threading
import argparse
import yaml
import functools

from lris2csu.util import setup_logging
from lris2csu.hardware import CSUHardware

from mktl.mktlcoms import MKTLComs, MKTLMessage


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
            f'{name}.configure': self.handler,
            f'{name}.reset': self.handler,
            f'{name}.calibrate': self.handler,
            f'{name}.status': self.handler,

            f'{name}.abort': self.handler,
            f'{name}.halt': self.handler,
            f'{name}.stop': self.handler,
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

    def handler(self, m:MKTLMessage):
        method = m.msg_type
        context = m.json_data
        key = m.key

        if method =='get' and key.split('.')[1] in ('status',):
            m.fail('set unsupported')

        if method =='set' and key.split('.')[1] in ('configure', 'reset', 'calibrate', 'abort', 'halt', 'stop'):
            m.fail('set unsupported')

        args = context.get('args', [])
        kwargs = context.get('kwargs', {})
        resp = 'OK'
        try:
            if 'configure' in key:
                self.csu.configure(*args, **kwargs)
            if 'reset' in key:
                self.csu.reset_bus()
            if 'calibrate' in key:
                self.csu.calibrate()
            if 'status' in key:
                resp = self.csu.status()
            if 'abort' in key or 'halt' in key or 'stop' in key:
                self.csu.halt()
        except Exception as e:
            m.fail(str(e))
        m.respond(resp)


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