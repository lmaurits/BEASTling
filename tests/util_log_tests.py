import logging

import beastling
from beastling.util import log


def test_log_message(caplog):
    class Model:
        name = 'mname'

    with caplog.at_level(logging.INFO, logger=beastling.__name__):
        log.info('text', model=Model())
        assert caplog.records[0].message.startswith('Model mname:')


def test_dependency_only_logged_once(caplog):
    with caplog.at_level(logging.INFO, logger=beastling.__name__):
        log._dependencies = set()
        log.dependency('f', 'p')
        assert len(caplog.records) == 1
        log.dependency('f', 'p')
        assert len(caplog.records) == 1


def test_info_logged_multiple_times(caplog):
    with caplog.at_level(logging.INFO, logger=beastling.__name__):
        log.info('f')
        assert len(caplog.records) == 1
        log.info('f')
        assert len(caplog.records) == 2
