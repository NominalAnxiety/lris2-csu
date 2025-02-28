#Stub placeholder for pyzmq, mKTL, redis pubsub, python socket, etc ad nauseum communication wrapper


class Communicator:
    def send(self, who, what):
        pass

    def listen(self, who: str | List[str], filter=None):
        yield None

    def receive(self, who: str | List[str], filter=None):
        pass