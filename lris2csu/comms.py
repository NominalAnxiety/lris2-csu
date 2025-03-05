#Stub placeholder for pyzmq, mKTL, redis pubsub, python socket, etc ad nauseam communication wrapper
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
