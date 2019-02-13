__version__ = 0.2

import time
import multiprocessing as mp
import queue
from configparser import ConfigParser
import pinger
import freezer
import tkinter_full
import traceback


class ProcessRunner:
    '''A class responsible for running or 
    not running a particular process.
    When called .run() method it runs target function in a process
     (and prevents multiple processes).
    When called .supress() method it stops the process if it is alive
    '''

    def __init__(self, target, kwargs=None, name=None, no_queue=False):
        self.target = target
        self.name = name
        self._process = None
        if not no_queue:
            self.queue = mp.Queue()
        else:
            self.queue = None
        self.kwargs = kwargs or {}

    def run(self):
        if self._process and self._process.is_alive():
            return False
        else:
            print(f"running process {self.name}")
            kwargs = self.kwargs
            if self.queue:
                kwargs['queue'] = self.queue
            self._process = mp.Process(target=self.target, kwargs=kwargs)
            self._process.start()

    def supress(self):
        if self._process and self._process.is_alive():
            print(f"stopping process {self.name}")
            self._process.terminate()


class CountdownTimer:
    '''A simple Countdown Timer class. '''

    def __init__(self, time):
        '''Time in seconds.'''
        self.time = time

    def start(self):
        self._start_time = time.time()

    def is_over(self):
        '''Check if time is over'''
        now = time.time()
        passed = now - self._start_time
        return passed >= self.time


# read config
config = ConfigParser()
config.read('config.ini')

# max number of ping failures before pc freezes
max_failures = config.getint('main', 'max_failures')

# timeout for ping in milliseconds
ping_timeout = config.getint('main', 'ping_timeout')

# the server to ping
server = config.get('main', 'server')

# a pinger instance
mypinger = pinger.Pinger(server, max_failures, timeout=ping_timeout)

# password for liberty
password = 'simsimopen'


def main():
    '''Function that runs the main loop.
    It checks for freeze flags from mypinger and 
    it calls for freezes and unfreezs accordingly.
    '''

    # process responsible for freezing keyboard and mouse
    freezer_proc = ProcessRunner(freezer.freeze, name="Freezer", kwargs={'password': password})

    # process responsible for showing a fullscreen message text
    tk_proc = ProcessRunner(tkinter_full.main, name="TkFullscreen", no_queue=True)

    # ping interval in seconds
    ping_interval = config.getfloat('main', 'ping_interval')

    # a liberty countdown timer, initially 5 seconds
    liberty_countdown = CountdownTimer(10)

    while True:
        # check liberty
        if liberty_countdown and not liberty_countdown.is_over():
            print("in liberty")
            freeze = False
        else:
            freeze = mypinger.get_freeze()
            print(f"freeze = {freeze}")

        # check for password events
        try:
            q = freezer_proc.queue.get_nowait()
            print(f"q = {q}")
            seconds = int(q['time']) * 60
            liberty_countdown = CountdownTimer(seconds)
            liberty_countdown.start()
            print("a liberty countdown started")
        except queue.Empty as e:
            print("Empty queue")
            pass

        if freeze:
            freezer_proc.run()
            tk_proc.run()
        else:
            freezer_proc.supress()
            tk_proc.supress()

        # sleeping zzZz
        if freeze:
            time.sleep(1)
        else:
            time.sleep(ping_interval)


if __name__ == '__main__':
    mp.freeze_support()
    try:
        main()
    except BaseException as e:
        tb = traceback.format_exc()
        print(tb)
        with open(time.strftime("%Y %d %b %H-%M-%S.log"), 'w') as f:
            f.write(tb)
