"""
A runtime patch to Logbook to enable greenlet-based stack management.

Usage:

    >>> import logbook_gevent
    >>> logbook_gevent.monkey_patch()
"""

from itertools import count

import gevent.coros
import gevent.local
import greenlet

import logbook.base
import logbook._fallback
import logbook.handlers
try:
    import logbook._speedups as speedups
except ImportError:
    import logbook._fallback as speedups


def current_greenlet():
    return id(greenlet.getcurrent())

_missing = object()
_MAX_CONTEXT_OBJECT_CACHE = 256


class StackedObject(logbook.base.StackedObject):

    def push_greenlet(self):
        """Pushes the stacked object to the greenlet stack."""
        raise NotImplementedError()

    def pop_greenlet(self):
        """Pops the stacked object from the greenlet stack."""
        raise NotImplementedError()

    def __enter__(self):
        self.push_greenlet()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.pop_greenlet()

    def greenletbound(self, _cls=speedups._StackBound):
        return _cls(self, self.push_greenlet, self.pop_greenlet)


class ContextObject(StackedObject, logbook.base.ContextObject):

    def push_greenlet(self):
        self.stack_manager.push_greenlet(self)

    def pop_greenlet(self):
        popped = self.stack_manager.pop_greenlet()
        assert popped is self, 'popped unexpected object'


class NestedSetup(StackedObject, logbook.base.NestedSetup):

    def push_greenlet(self):
        for obj in self.objects:
            obj.push_greenlet()

    def pop_greenlet(self):
        for obj in reversed(self.objects):
            obj.pop_greenlet()


class GreenletContextStackManager(logbook._fallback.ContextStackManager):

    # The contents of this class are copied almost verbatim from
    # logbook._fallback.ContextStackManager, only threading constructs have
    # been replaced with greenlet/gevent-based ones.

    def __init__(self):
        self._global = []
        self._context_lock = gevent.coros.RLock()
        self._context = gevent.local.local()
        self._cache = {}
        self._stackop = count().next

    def iter_context_objects(self):
        """Returns an iterator over all objects for the combined
        application and context cache.
        """
        tid = current_greenlet()
        objects = self._cache.get(tid)
        if objects is None:
            if len(self._cache) > _MAX_CONTEXT_OBJECT_CACHE:
                self._cache.clear()
            objects = self._global[:]
            objects.extend(getattr(self._context, 'stack', ()))
            objects.sort(reverse=True)
            objects = [x[1] for x in objects]
            self._cache[tid] = objects
        return iter(objects)

    def push_greenlet(self, obj):
        self._context_lock.acquire()
        try:
            self._cache.pop(current_greenlet(), None)
            item = (self._stackop(), obj)
            stack = getattr(self._context, 'stack', None)
            if stack is None:
                self._context.stack = [item]
            else:
                stack.append(item)
        finally:
            self._context_lock.release()

    def pop_greenlet(self):
        self._context_lock.acquire()
        try:
            self._cache.pop(current_greenlet(), None)
            stack = getattr(self._context, 'stack', None)
            assert stack, 'no objects on stack'
            return stack.pop()[1]
        finally:
            self._context_lock.release()


def monkey_patch():
    """Monkey-patch Logbook to enable `greenletbound()`."""
    logbook.base.Processor.__bases__ = (ContextObject,)
    logbook.base.Processor.stack_manager = GreenletContextStackManager()
    logbook.base.Flags.__bases__ = (ContextObject,)
    logbook.base.Flags.stack_manager = GreenletContextStackManager()
    logbook.handlers.Handler.__bases__ = (ContextObject,)
    logbook.handlers.Handler.stack_manager = GreenletContextStackManager()
