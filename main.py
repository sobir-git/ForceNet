__version__ = "0.2.4"
import os
import sys
import time
import queue
from configparser import ConfigParser
import pinger
import traceback
import threading
import scheduler
import freezer2


class ThreadRunner:
    '''A class responsible for running or not running a particular thread.
    When called .run() method it runs target function in a thread (and 
    prevents multiple copies).
    When called .supress() method it sets the stop_event of the thread
    '''
    def __init__(self, target, kwargs=None, name=None):
        self.target = target
        self.kwargs = kwargs or {}
        self._thread = None
        self.name = name

    def run(self):
        if self._thread: # and self._thread.is_alive():
            return False
        print(f"running thread {self.name}")
        self._thread = threading.Thread(target=self.target, kwargs=self.kwargs)
        stop_event = threading.Event()
        self._thread._stop_event = stop_event
        self._thread.start()

    def supress(self):
        if self._thread: # and self._thread.is_alive():
            print(f"stopping thread {self.name}")
            self._thread._stop_event.set()
            self._thread = None
            return True
        return False


def pingping(server, max_failures, ping_interval):
    '''A function that continuously pings the server and updates thread's 
    freeze_event. It will freeze if max_failures of pings happens successively.
    Ideally this should run in its own thread.
    '''
    # a pinger instance
    th = threading.current_thread()
    mypinger = pinger.Pinger(server, max_failures)

    def update_freeze():
        freeze = mypinger.get_freeze()
        if freeze:
            th.freeze_event.set()
        else:
            th.freeze_event.clear()

    def check_stop_event():
        if th.stop_event.is_set():
            sys.exit(0)

    s = scheduler.Scheduler()
    s.with_interval(update_freeze, ping_interval)
    s.with_interval(check_stop_event, 0.1)
    while True:
        s.run_pending()
        time.sleep(0.1)


class ForceNet:

    # read config
    config = ConfigParser()
    config.read('config.ini')

    # password for liberty
    password = 'simsimopen'

    # max number of ping failures before pc freezes
    max_failures = config.getint('main', 'max_failures')

    # the server to ping
    server = config.get('main', 'server')

    # ping interval in seconds
    ping_interval = config.getfloat('main', 'ping_interval')

    # run pinger in a different thread
    pinger_thread = threading.Thread(target=pingping, name="Pinger", args=[server, max_failures, ping_interval])
    pinger_thread.freeze_event = threading.Event()
    pinger_thread.stop_event = threading.Event()

    # # process responsible for freezing keyboard and mouse
    # freezer_queue = []
    # freezer_queue_lock = threading.Lock()
    # freezer_proc = ThreadRunner(freezer.run, name="Freezer", 
    #     kwargs={'password': password, 'queue': freezer_queue,
    #     'queue_lock': freezer_queue_lock})

    # freezer2_queue = mp.Queue()
    # freezer2_proc = mp.Process(target=freezer2.run, kwargs={'queue': freezer2_queue, 'password': password})

    freezer = freezer2.Freezer()

    # a liberty countdown timer, initially 5 seconds
    _liberty = False

    # scheduler for this class
    s = scheduler.Scheduler()

    def get_liberty(self):
         return self._liberty

    def remove_liberty(self):
        self._liberty = False

    def start_liberty(self, seconds):
        '''Start a liberty period.'''
        print(f"STARED LIBERTY FOR {seconds}s.")
        self._liberty = True
        self.s.only_once(self.remove_liberty, seconds)

    def check_events(self):
        '''Check for other thread events '''
        # check for password events
        freezer = self.freezer
        if not freezer.is_running():
            return
        events = freezer.get_events()
        chars = []
        append = chars.append
        pop = chars.pop
        for e in events:
            try:
                key = e.Key
                if key == 'Return':
                    chars.clear()
                elif key == 'Back' and chars:
                    pop()
                elif isinstance(key, str) and len(key) == 1:
                    append(key)
            except:
                pass

        text = ''.join(chars).lower()
        print(f"text={text}")
        if text.endswith(self.password):
            # get time if typed
            try:
                timestr = text[:-len(self.password)]
                identifier = 'm'  # time identifier
                if timestr[-1] in ['m', 'd', 'h', 's']:
                    timestr = timestr[:-1]
                    identifier = timestr[-1]
                num = int(timestr)
                # convert time to seconds
                if identifier == 'm':
                    seconds = num * 60
                elif identifier == 'h':
                    seconds = num * 60 * 60
                elif identifier == 'd':
                    seconds = num * 60 * 60 * 24
                else:
                    seconds = num
            except:
                seconds = 300  # 5 minutes
            self.start_liberty(seconds)

    def freeze(self):
        if not self.freezer.is_running():
            print("\t\t\t\tFREEZE!")
            self.freezer.enable()

    def unfreeze(self):
        if self.freezer.is_running():
            print("\t\t\t\tUN FREEZE!")
            self.freezer.disable()

    def run(self):
        '''Function that runs inits and runs the main loop.
        It checks for freeze flags from mypinger and 
        it calls for freezes and unfreezs accordingly.
        '''
        self.pinger_thread.start()
        s = self.s
        s.with_interval(self.loop, 0.1)
        s.with_interval(self.check_events, 1)
        try:
            while True:
                s.run_pending()
                time.sleep(0.01)
        except KeyboardInterrupt:
            print("KeyboardInterrupt...")
            self.unfreeze()
            self.pinger_thread.stop_event.set()

    def loop(self):
        '''Main loop'''
        if self.get_liberty():
            # print("in liberty")
            self.unfreeze()
            return

        freeze = self.pinger_thread.freeze_event.is_set()
        # print(f"freeze = {freeze}")

        if freeze:
            self.freeze()
        else:
            self.unfreeze()


if __name__ == '__main__':
    fn = ForceNet()
    try:
        fn.run()
    except BaseException as e:
        tb = traceback.format_exc()
        print(tb)
        join = os.path.join
        homepath = os.getenv('homepath')
        forcedir = join(homepath, 'ForceNet')
        logdir = join(forcedir, 'logs')
        if not os.path.exists(forcedir):
            os.mkdir(forcedir)
        if not os.path.exists(logdir):
            os.mkdir(logdir)
        with open(join(logdir, time.strftime("%Y %d %b %H-%M-%S.log")), 'w') as f:
            f.write(tb)
