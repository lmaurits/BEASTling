import logging

import beastling

_logger = None
_dependencies = set()


def get_logger():
    global _logger
    if _logger is None:
        _logger = logging.getLogger(beastling.__name__)
    return _logger


def _message(msg, model):
    if model:
        msg = '{0} {1}: {2}'.format(model.__class__.__name__, model.name, msg)
    return msg


def info(msg, model=None):
    get_logger().info(_message(msg, model))


def warning(msg, model=None):
    get_logger().warning(_message(msg, model))


def dependency(functionality, beast_package, model=None):
    global _dependencies
    if (functionality, beast_package) not in _dependencies:
        msg = '{0} is implemented in the BEAST package {1}.'.format(functionality, beast_package)
        get_logger().info('[DEPENDENCY] ' + _message(msg, model))
        _dependencies.add((functionality, beast_package))
