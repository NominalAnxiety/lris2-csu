#Stub placeholder for pyzmq, mKTL, redis pubsub, python socket, etc ad nauseam communication wrapper
from dataclasses import dataclass
from logging import getLogger
from typing import Callable

import zmq
import threading
import json
import time


#TODO consider using a zmq inproc pipe for thread signaling

class ZMQComms:
    """
    Manages ZeroMQ Pub/Sub for sending and receiving JSON messages.
    """
    def __init__(self, domain_string, pub_address="tcp://*:5556", sub_address="tcp://localhost:5556"):
        context = zmq.Context()
        self.domain_string = domain_string
        self.publisher = context.socket(zmq.PUB)
        self.publisher.bind(pub_address)

        self.subscriber = context.socket(zmq.SUB)
        self.subscriber.connect(sub_address)
        # By default, subscribe to everything; you might refine with a topic filter
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, self.domain_string)

        # A separate thread for receiving messages
        self._stop_event = threading.Event()
        self._sub_thread = threading.Thread(target=self._listen_loop, daemon=True)

        self.message_callback = None  # Assign a callback from CSUManager if desired

    def start(self):
        self._sub_thread.start()

    def _listen_loop(self):
        while not self._stop_event.is_set():
            try:
                message = self.subscriber.recv_string(flags=zmq.NOBLOCK)
                topic, msg_json = message.split(" ", 1)
                data = json.loads(msg_json)
                if self.message_callback:
                    self.message_callback(topic, data)
            except zmq.Again:
                # No message ready
                time.sleep(0.01)  #play nice

    def stop(self):
        self._stop_event.set()
        self._sub_thread.join()

    def publish(self, topic: str, data: dict):
        """
        Publish a JSON-serialized dict under a topic.
        """
        msg_json = json.dumps(data)
        self.publisher.send_string(f"{self.domain_string}.{topic} {msg_json}")


@dataclass
class MKTLMessage:
    command_key: str
    command: Callable
    args: tuple
    kwargs: dict
    respond: Callable = None

    def __post_init__(self):
        if self.respond is None:
            self.respond = lambda x: getLogger(__name__).info(f'NOOP Response: {x}')


class ZMQComms:
    def __init__(self, config: dict, connect=True):
        self.configuration = config

        context = zmq.Context.instance(io_threads=2)

        self.status_relay = None
        self.socket = context.socket(zmq.REP)
        self.socket.bind(self.configuration['address'])
        self.socket.linger = 1
        self.socket.hwm = 1000000000
        self.socket.setsockopt(zmq.SNDTIMEO, 1000)
        self.socket.setsockopt(zmq.RCVTIMEO, 1000)
        if connect:
            pass

    @property
    def command_address(self):
        return self.configuration['address']

    def listen(self):
        for message in self.socket.recv_pyobj():
            yield message

    def start_snm_status_relay(self, stat_addr):
        from zmq.devices import ThreadDevice

        stat_addr_internal = 'inproc://status.xsub'
        self.status_relay = std = ThreadDevice(zmq.QUEUE, zmq.XSUB, zmq.XPUB)
        std.setsockopt_in(zmq.LINGER, 0)
        std.setsockopt_out(zmq.LINGER, 0)
        std.bind_in(stat_addr_internal)
        std.bind_out(stat_addr)
        std.daemon = True
        std.start()
        getLogger(__name__).info(f'Publishing status information to {stat_addr} from relay @ {stat_addr_internal}')


class MKTLComms(ZMQComms):
    def __init__(self, config: dict, suppoted_commands=None):
        super().__init__(config)
        self.supported_commands = suppoted_commands or []

    def send(self, data, error=False):
        self.socket.send_pyobj(data)

    def listen(self):
        for message in super().listen():
            try:
                message = json.loads(message)
            except json.JSONDecodeError as e:
                getLogger(__name__).error(f'Caught {e}, malformed command: {message}')
                self.socket.send_pyobj('ERROR: Malformed command')
            except Exception as e:
                getLogger(__name__).error(f'Caught {e}, malformed command: {message}')
                self.socket.send_pyobj('ERROR: Malformed command')

            if message not in self.supported_commands:
                getLogger(__name__).error(f'Caught {e}, malformed command: {message}')
                self.socket.send_pyobj('ERROR: Unsupported Command')
            yield MKTLMessage(message['key'], self.supported_commands(message['key']), message['args'],
                              message['kwargs'],
                              self.send)


def CommsFactory(coms_config, suppoted_commands=None):
    try:
        return MKTLComms(coms_config['mktl'], suppoted_commands=suppoted_commands)
    except KeyError:
        return ZMQComms(coms_config['zmq'])
