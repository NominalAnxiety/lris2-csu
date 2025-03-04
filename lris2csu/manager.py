import pickle
from logging import getLogger
import zmq
import threading
import argparse
import yaml

from cooethercat.epos4 import EPOS4Bus

from .slit import BarPair, MaskConfig, Slit, SlitBar
from .util import zpipe, setup_logging


class CSUManager:
    def __init__(self, config='csu.yaml', ethercat_device=None, connect=True):

        # Load and parse the configuration YAML file
        try:
            with open(config, 'r') as f:
                self.configuration: dict = yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration file '{config}': {e}")

        self.bus = EPOS4Bus(ethercat_device)
        if connect:
            self.bus.openNetworkInterface()
            self.bus.initializeSlaves()

        self._bar_pairs : list[BarPair] = []
        for bar_name, epos_id_pair in self.configuration['bar_pairs']:
            id1, id2 = epos_id_pair
            self._bar_pairs.append(BarPair(self.bus.slaves[id1], self.bus.slaves[id2]))

        self._cap_pipe, self._cap_pipe_thread = None, None
        self._control_thread = None


    def begin_slit_control(self, start=True, daemon=False, context: zmq.Context = None):
        if self._control_thread is not None:
            raise RuntimeError('Slit control mut be terminated and joined join')

        self._cap_pipe, self._cap_pipe_thread = zpipe(context or zmq.Context.instance())
        self._control_thread = threading.Thread(name='CSU Slit Control Thread',
                                                target=self._slit_controller, args=(self._cap_pipe_thread,),
                                                kwargs={'context': context}, daemon=daemon)
        if start:
            self._control_thread.start()

        return self._control_thread

    def terminate_slit_control(self, join: float|bool =True):
        if self._control_thread is None:
            return

        if not self._control_thread.is_alive():
            self._control_thread=None
            try:
                self._cap_pipe.close()
            except:
                pass
            return

        if self._cap_pipe:
            self._cap_pipe.send_pyobj(('exit', None))
            self._cap_pipe.close()

        if join:
            self._control_thread.join(timeout=None if isinstance(join, bool) else join)
            if self._control_thread.is_alive():
                raise RuntimeError(f'{self._control_thread.name} did not terminate within {join}')

            self._control_thread = None

    def __del__(self):
        try:
            self.terminate_slit_control(join=True)
            self._cap_pipe_thread.close()  #should have been closed by the other thread
        except:
            pass

    def _abort(self, join=False, reason='None given', raise_zmqerror=True):
        pass

    def _configure(self, mask: MaskConfig):
        """Configure the system based on the provided MaskConfig."""
        for slit in mask.slits:
            for bar_center, (x, width) in slit.get_bar_positions().items():
                self._bar_pairs[bar_center].set_position(x, width)

        self._requested_mask = mask  # Update internal configuration

    def _slit_controller(self, pipe: zmq.Socket, context: zmq.Context = None):
        """
        Args:
            pipe: a pipe for receiving commands
            context: zmq.Context

        Returns: None

        """
        context = context or zmq.Context().instance()

        getLogger(__name__).info('CSU control thread started')
        while True:

            cmd, data = '', ''
            try:
                cmd, data = pipe.recv_pyobj(zmq.NOBLOCK)
            except zmq.ZMQError as e:
                if e.errno != zmq.EAGAIN:
                    self._abort(reason='End of command pipe')
                    if e.errno == zmq.ETERM:
                        break
                    else:
                        raise e  # real error

            match cmd:
                case 'exit':
                    self._abort(reason='Exit command', join=True)
                    break
                case 'abort':
                    self._abort(reason='Abort command')
                case 'configure':
                    # Build Slit() out of the required slit bars and configure the system
                    self._configure(data)
                case _:
                    getLogger(__name__).error(f'Received invalid command "{cmd}", ignoring')

        getLogger(__name__).info('CSU control thread exiting')

    def status(self):
        """ Returns: Dictionary of status information """
        #this is playing fast and loos with the ethercat buss across threads
        status = {
            'mask': MaskConfig([Slit(*(bp.get_position() + (SlitBar.SLIT_BAR_HEIGHT,))) for bp in self._bar_pairs]),
            'bars': {bp.y: (bp.bar1.engineering_status(), bp.bar2.engineering_status()) for bp in self._bar_pairs},
            'config': self.configuration}

        return status

    def abort(self):
        if self._cap_pipe:
            self._cap_pipe.send_pyobj(('abort', id))
        else:
            raise RuntimeError('No pipe to worker')

    def configure(self, mask_config: MaskConfig):
        if self._cap_pipe:
            self._cap_pipe.send_pyobj(('configure', mask_config))
        else:
            raise RuntimeError('No pipe to worker')


def parse_cl():
    parser = argparse.ArgumentParser(description='LRIS2 CSU Server', add_help=True)
    parser.add_argument('-p', '--port', dest='port', action='store', required=False, type=int,
                        help='Server port', default='8888')
    parser.add_argument('--status_port', dest='status_port', action='store', required=False, type=int,
                        help='Status Port', default='8890')
    parser.add_argument('--eth', dest='ethernet_device', action='store', required=True, type=str,
                        help='Ethercat device (e.g. eth0)', default='eth0')
    parser.add_argument('--cfg', dest='config', action='store', required=False, type=str,
                        help='Configuration YAML', default='')
    return parser.parse_args()


def start_zmq_devices(stat_addr):
    from zmq.devices import ThreadDevice

    stat_addr_internal = 'inproc://cap_stat.xsub'
    std = ThreadDevice(zmq.QUEUE, zmq.XSUB, zmq.XPUB)
    std.setsockopt_in(zmq.LINGER, 0)
    std.setsockopt_out(zmq.LINGER, 0)
    std.bind_in(stat_addr_internal)
    std.bind_out(stat_addr)
    std.daemon = True
    std.start()
    getLogger(__name__).info(f'Publishing status information to {stat_addr} from relay @ {stat_addr_internal}')

    return std


if __name__ == '__main__':

    import os, time
    os.environ['TZ'] = 'right/UTC'
    time.tzset()
    setup_logging('csuserver')

    # if check_active_jupyter_notebook():
    #     raise RuntimeError('Jupyter notebooks are running, shut them down first.')

    args = parse_cl()

    context = zmq.Context.instance(io_threads=2)
    context.linger = 1

    # Set up proxies for routing all the status data
    stat_addr = f'tcp://*:{args.status_port}'
    start_zmq_devices(stat_addr)

    # Set up a command port
    command_port = args.port
    cmd_addr = f"tcp://*:{command_port}"
    socket = context.socket(zmq.REP)
    socket.bind(cmd_addr)

    # Start up CSU manager
    csu = CSUManager(args.ethernet_device)
    csu.begin_slit_control(context=context, start=True, daemon=False)

    getLogger(__name__).info(f'Accepting commands on {cmd_addr}')

    while True:
        try:
            cmd, arg = socket.recv_pyobj()
        except zmq.ZMQError as e:
            getLogger(__name__).error(f'Caught {e}, aborting and shutting down')
            csu.terminate_slit_control()
            break
        except KeyboardInterrupt:
            getLogger(__name__).error(f'Keyboard Interrupt, aborting and shutting down')
            csu.terminate_slit_control()
            break
        except pickle.UnpicklingError:
            socket.send_pyobj('ERROR: Ignoring unpicklable command')
            getLogger(__name__).error(f'Ignoring unpicklable command')
            continue
        else:
            if not csu.is_alive():
                getLogger(__name__).critical(f'CSU is not alive (died prematurely). Exiting.')
                socket.send_pyobj('ERROR: CSU controller died')
                break

        getLogger(__name__).debug(f'Received command "{cmd}" with args {arg}')

        if cmd == 'reset':
            socket.send_pyobj('OK')
            csu.terminate_slit_control(join=True)
            csu.begin_slit_control(context=context, start=True, daemon=False)

        elif cmd == 'status':
            try:
                status = csu.status()  # this might take a while and fail
            except Exception as e:
                status = {'hardware': str(e)}
            status['id'] = f'CSUServer {args.ethernet_device} @ {args.port}/{args.status_port}'
            socket.send_pyobj(status)

        elif cmd == 'configure':
            csu.configure(arg)
            socket.send_pyobj({'resp': 'OK', 'code': 0})

        elif cmd == 'abort':
            csu.abort(arg)
            socket.send_pyobj({'resp': 'OK', 'code': 0})

        else:
            socket.send_pyobj({'resp': 'ERROR', 'code': 0})

    csu.terminate_slit_control(join=True)
    socket.close()
    context.term()
