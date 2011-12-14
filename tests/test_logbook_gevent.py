"""Run this file to test greenlet-based context stack management."""

import gevent
import logbook
import logbook_gevent; logbook_gevent.monkey_patch()


def inject(**params):

    """
    A Logbook processor to inject arbitrary information into log records.

    Simply pass in keyword arguments and use as a context manager:

        >>> with inject(identifier=str(uuid.uuid4())).applicationbound():
        ...     logger.debug('Something happened')
    """

    def callback(log_record):
        log_record.extra.update(params)
    return logbook.Processor(callback)


logger = logbook.Logger("contextname")

def log_one():
    with inject(abc=123).greenletbound():
        gevent.sleep(0)
        logger.info("ABC = 123")

def log_two():
    with inject(abc=456).greenletbound():
        gevent.sleep(0)
        logger.info("ABC = 456")


gl1 = gevent.spawn(log_one)
gl2 = gevent.spawn(log_two)
with logbook.handlers.TestHandler().applicationbound() as h:
    gevent.joinall([gl1, gl2])

r1, r2 = h.records
assert r1.message == 'ABC = %d' % r1.extra['abc']
assert r2.message == 'ABC = %d' % r2.extra['abc']
assert set((r1.extra['abc'], r2.extra['abc'])) == set((123, 456))
