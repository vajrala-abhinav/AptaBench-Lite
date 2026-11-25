"""Opt-in count/timing instrumentation. Never records function arguments or data.

Nested stage durations are inclusive and must not be summed as a total. Each
capture is context-local; unrelated Streamlit sessions do not share counters.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from time import perf_counter

_CURRENT = ContextVar('aptabench_performance_capture', default=None)


class Capture:
    def __init__(self):
        self.stages = {}

    def add(self, stage, elapsed):
        row = self.stages.setdefault(stage, {'calls': 0, 'seconds': 0.0})
        row['calls'] += 1
        row['seconds'] += elapsed

    @contextmanager
    def activate(self):
        token = _CURRENT.set(self)
        try:
            yield self
        finally:
            _CURRENT.reset(token)


@contextmanager
def measure(stage):
    recorder = _CURRENT.get()
    if recorder is None:
        yield
        return
    start = perf_counter()
    try:
        yield
    finally:
        recorder.add(stage, perf_counter()-start)


def timed(stage):
    def decorate(function):
        @wraps(function)
        def call(*args, **kwargs):
            if _CURRENT.get() is None:
                return function(*args, **kwargs)
            with measure(stage):
                return function(*args, **kwargs)
        return call
    return decorate


@contextmanager
def measured(stage):
    capture = _CURRENT.get()
    if capture is None:
        yield
        return
    start = perf_counter()
    try:
        yield
    finally:
        capture.add(stage, perf_counter() - start)


def timed(stage):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if _CURRENT.get() is None:
                return function(*args, **kwargs)
            with measured(stage):
                return function(*args, **kwargs)
        return wrapped
    return decorate
