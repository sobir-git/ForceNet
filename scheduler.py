'''
This module contains classes to schedule functions.

Example:
>>> s = Schedule()
>>> f = lambda name: print('Hello %s!' % name)
>>> s.with_interval(f, 1, args=['John']) # in intervals of 1 second
>>> while True:
...     s.run_pending()
Hello John!

If your function returns scheduler.CancelJob it will not get called again.

'''
from __future__ import print_function, division


import traceback
import time


class CancelJob:
    pass


class Job:
    def __init__(self, function, args=None, kwargs=None, name=None, interval=None):
        self.name = name
        self.function = function
        self.args = args or []
        self.kwargs = kwargs or {}
        self.interval = interval
        self._last_call = None

    @property
    def last_call(self):
        return self._last_call

    def do(self):
        # print("JOB: %s" % self.function.__name__)
        self._last_call = time.time()
        try:
            result = self.function(*self.args, **self.kwargs)
        except Exception as e:
            print("Exception on calling a job")
            traceback.print_exc()
            result = e
        return result


class Scheduler:
    '''A scheduler class for scheduling function calss.'''
    def __init__(self):
        self._queue = []

    def with_interval(self, function, interval, args=None, kwargs=None, name=None):
        '''Schedule function with interval '''
        job = Job(function, args=args, kwargs=kwargs, name=name, interval=interval)
        on = time.time() + interval
        self._queue.append((on, job))

    def only_once(self, function, delay, args=None, kwargs=None, name=None):
        '''Schedule function only once'''
        job = Job(function, args=args, kwargs=kwargs, name=name)
        on = time.time() + delay
        self._queue.append((on, job))

    def run_pending(self):
        '''Run pending jobs'''
        self._queue.sort(reverse=True, key=lambda x: x[0])
        add_later = []
        now = time.time()
        while self._queue:
            on, job = self._queue[-1]
            if on > now:
                break
            self._queue.pop()
            result = job.do()
            if job.interval and result is not CancelJob:
                add_later.append((on + job.interval, job))

        self._queue = add_later + self._queue


def test_only_once():
    s = Scheduler()
    f = lambda x: print('hello %s!' % x)
    s.only_once(f, 3, args=['world'])
    while True:
        s.run_pending()

def test_interval():
    s = Scheduler()
    f1 = lambda x: print('f1: hello %s!' % x)
    f2 = lambda x: print('f2: hello %s!' % x)
    s.with_interval(f1, 1, args=['world'])
    s.with_interval(f2, 2, args=['world'])
    while True:
        s.run_pending()

def test_multiple():
    s1 = Scheduler()
    s2 = Scheduler()
    f1 = lambda x: print('f1: hello %s!' % x)
    f2 = lambda x: print('f2: hello %s!' % x)
    s1.with_interval(f1, 1, args=['world'])
    s2.with_interval(f2, 2, args=['world'])
    while True:
        s1.run_pending()
        s2.run_pending()

if __name__ == '__main__':
    test_multiple()
