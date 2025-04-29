import importlib.resources
import yaml
import logging
import logging.config
import zmq
import os
import uuid



def setup_logging(name):
    ref = importlib.resources.files('lris2csu.config').joinpath('logging.yaml')
    with importlib.resources.as_file(ref) as path:
        if os.path.exists(path):
            with open(path, 'rt') as f:
                config = yaml.full_load(f.read())

    # postprocess loggers dict
    # keys are program names values are either
    #   1) a level for the log of the program
    #   2) a dict of log names and levels
    #   3) a dict of log names and dicts describing how to configure the corresponding Logger instance.
    #  See https://docs.python.org/3/library/logging.config.html#logging-config-dictschema
    # The configuring dict is searched for the following keys:
    #     level (optional). The level of the logger.
    #     propagate (optional). The propagation setting of the logger.
    #     filters (optional). A list of ids of the filters for this logger.
    #     handlers (optional). A list of ids of the handlers for this logger.
    cfg = config['loggers'][name]  # extract one we care about
    if isinstance(cfg, str):
        config['loggers'] = {name: {'level': cfg.upper()}}
    else:
        loggers = {}
        for k, v in cfg.items():
            loggers[k] = {'level': v.upper()} if isinstance(v, str) else v
        config['loggers'] = loggers

    logging.config.dictConfig(config)
    return logging.getLogger(name)


def load_default_config():
    ref = importlib.resources.files('lris2csu.config').joinpath('csu.yaml')
    with importlib.resources.as_file(ref) as path:
        if os.path.exists(path):
            with open(path, 'rt') as f:
                config = yaml.full_load(f)
    return config


class AbortedException(Exception):
    pass


def check_zmq_abort_pipe(pipe):
    try:
        abort = pipe.recv(zmq.NOBLOCK)
        raise AbortedException(abort)
    except zmq.ZMQError as e:
        if e.errno != zmq.EAGAIN:
            raise

def zpipe(ctx):
    """
    build an inproc pipe for talking to threads
    mimic pipe used in czmq zthread_fork.
    Returns a pair of PAIRs connected via inproc
    """
    a = ctx.socket(zmq.PAIR)
    b = ctx.socket(zmq.PAIR)
    a.linger = b.linger = 0
    a.hwm = b.hwm = 1
    iface = "inproc://%s" % uuid.uuid4().hex
    a.bind(iface)
    b.open(iface)
    return a, b
