import json
import pickle
from dataclasses import dataclass
from logging import getLogger
from typing import Callable
import zmq
import threading
import argparse
import yaml

from cooethercat.helpers import StatuswordStates, HomingMethods
from cooethercat import EPOS4Bus

from lris2csu.slit import MaskConfig, Slit
from lris2csu.util import zpipe, setup_logging
from lris2csu.hardware import BarMotor, BrakeMotor, CSUHardwareConfig
from collections import defaultdict
from lris2csu.comms import CommsFactory


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

        self.slave_types = defaultdict(lambda: BarMotor)

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
    def __init__(self, config='csu.yaml', connect=True):

        # Load and parse the configuration YAML file
        try:
            with open(config, 'r') as f:
                self.configuration: dict = yaml.full_load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration file '{config}': {e}")

        self.csu = CSUHardware(self.configuration['hardware'])

        CSU_COMMANDS = {
            'csu.configure': self.csu.configure,
            'csu.abort': self.csu.halt,
            'csu.reset': self.csu.reset_bus,
            'csu.calibrate': self.csu.calibrate,
            'csu.halt': self.csu.halt,
            'csu.status': self.csu.status,
        }

        SERVER_COMMANDS = {'csu.exit': self.shutdown}

        self.comms = CommsFactory(self.configuration, suppoted_commands=SERVER_COMMANDS+CSU_COMMANDS)

        # if check_active_jupyter_notebook():
        #     raise RuntimeError('Jupyter notebooks are running, shut them down first.')

    def shutdown(self):
        getLogger(__name__).info('Shutting down')
        self.csu.terminate_control()
        self.comms.shutdown()
        exit(0)

    def run(self):

        getLogger(__name__).info(f'Accepting commands on {self.comms.command_address}')

        try:
            for message in self.comms.listen():

                getLogger(__name__).debug(f'Received: {message}')
                try:
                    message.respond(message.command(*message.args, **message.kwargs))
                except Exception as e:
                    message.respond(e, error=True)
        except zmq.ZMQError as e:
            getLogger(__name__).error(f'Caught {e}, aborting and shutting down')
        except KeyboardInterrupt:
            getLogger(__name__).error(f'Keyboard Interrupt, aborting and shutting down')

        self.csu.terminate_control()
        self.comms.shutdown()


    # def begin_slit_control(self, start=True, daemon=False, context: zmq.Context = None):
    #     if self._control_thread is not None:
    #         raise RuntimeError('Slit control mut be terminated and joined join')
    #
    #     self._cap_pipe, self._cap_pipe_thread = zpipe(context or zmq.Context.instance())
    #     self._control_thread = threading.Thread(name='CSU Slit Control Thread',
    #                                             target=self._slit_controller, args=(self._cap_pipe_thread,),
    #                                             kwargs={'context': context}, daemon=daemon)
    #     if start:
    #         self._control_thread.start()
    #
    #     return self._control_thread
    #
    # def terminate_slit_control(self, join: float|bool =True):
    #     if self._control_thread is None:
    #         return
    #
    #     if not self._control_thread.is_alive():
    #         self._control_thread=None
    #         try:
    #             self._cap_pipe.close()
    #         except:
    #             pass
    #         return
    #
    #     if self._cap_pipe:
    #         self._cap_pipe.send_pyobj(('exit', None))
    #         self._cap_pipe.close()
    #
    #     if join:
    #         self._control_thread.join(timeout=None if isinstance(join, bool) else join)
    #         if self._control_thread.is_alive():
    #             raise RuntimeError(f'{self._control_thread.name} did not terminate within {join}')
    #
    #         self._control_thread = None
    #
    # def __del__(self):
    #     try:
    #         self.terminate_slit_control(join=True)
    #         self._cap_pipe_thread.close()  #should have been closed by the other thread
    #     except:
    #         pass
    #
    #
    # def _slit_controller(self, pipe: zmq.Socket, context: zmq.Context = None):
    #     """
    #     Args:
    #         pipe: a pipe for receiving commands
    #         context: zmq.Context
    #
    #     Returns: None
    #
    #     """
    #     context = context or zmq.Context().instance()
    #     self.reset_bus()
    #
    #     getLogger(__name__).info('CSU control thread started')
    #     while True:
    #
    #         cmd, data = '', ''
    #         try:
    #             cmd, data = pipe.recv_pyobj(zmq.NOBLOCK)
    #         except zmq.ZMQError as e:
    #             if e.errno != zmq.EAGAIN:
    #                 self._abort(reason='End of command pipe')
    #                 if e.errno == zmq.ETERM:
    #                     break
    #                 else:
    #                     raise e  # real error
    #
    #         match cmd:
    #             case 'exit':
    #                 self._abort(reason='Exit command', join=True)
    #                 break
    #             case 'abort':
    #                 self._abort(reason='Abort command')
    #             case 'configure':
    #                 # Build Slit() out of the required slit bars and configure the system
    #                 self._configure(data)
    #             case _:
    #                 getLogger(__name__).error(f'Received invalid command "{cmd}", ignoring')
    #
    #     getLogger(__name__).info('CSU control thread exiting')
    #
    # def abort(self):
    #     if self._cap_pipe:
    #         self._cap_pipe.send_pyobj(('abort', id))
    #     else:
    #         raise RuntimeError('No pipe to worker')
    #
    # def configure(self, mask_config: MaskConfig):
    #     if self._cap_pipe:
    #         self._cap_pipe.send_pyobj(('configure', mask_config))
    #     else:
    #         raise RuntimeError('No pipe to worker')


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

    # if check_active_jupyter_notebook():
    #     raise RuntimeError('Jupyter notebooks are running, shut them down first.')

    args = parse_cl()

    CSUServer(config=args.config_yaml).run()
