from __future__ import print_function, division

__version__ = "0.3.0"


import os
import time
import queue
from ConfigParser import ConfigParser
import pinger
import traceback
import threading
import scheduler
import freezer
import logging
import multiprocessing
import sys


logger = None


def init():
    '''Set up application working directory and logging'''

    global logger
    join = os.path.join
    homepath = os.path.expanduser("~")
    forcedir = join(homepath, 'ForceNet')
    logdir = join(forcedir, 'logs')
    if not os.path.exists(forcedir):
        os.mkdir(forcedir)
    if not os.path.exists(logdir):
        os.mkdir(logdir)
    logfile = join(logdir, time.strftime("%Y %d %b %H-%M-%S.log"))

    # determine if application is a script file or frozen exe
    if getattr(sys, 'frozen', False):
        # redirect all output to file
        sys.stderr = open(join(logdir, time.strftime(
            "%Y %d %b %H-%M-%S-stderr.txt")), 'w')
        application_path = os.path.dirname(sys.executable)
        # Note: The service executable which will run this app must also be in the same directory
        # as in this case sys.executable will be the path to service executable
    elif __file__:
        application_path = os.path.dirname(__file__)

    # work in application path
    os.chdir(application_path)

    logging.basicConfig(
        filename=logfile,
        level=logging.DEBUG,
        format='[%(asctime)s] {%(name)-8s:%(lineno)-4d} %(levelname)-8s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # set up logging to console
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    # add the handler to the root logger
    logger = logging.getLogger('main')
    logger.debug("Logger created")
    logger.addHandler(console)
    logger.debug("Logger added console handler")
    logger.debug("Working directory: %s", os.getcwd())
    logger.debug("sys.executable = %s", sys.executable)


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

    def __init__(self):
        # password for liberty
        self.password = 'simsimopen'

        # read config
        config = ConfigParser()
        config.read('config.ini')
        self.config = config
        # get config values
        # interval between pings in seconds
        ping_interval = config.getfloat('main', 'ping_interval')
        # the server to ping
        server = config.get('main', 'server')
        # fullscreen message window
        fullscreen = config.getboolean('main', 'fullscreen')
        # topmost message window
        topmost = config.getboolean('main', 'topmost')
        # max number of ping failures before freeze
        max_failures = config.getint('main', 'max_failures')

        # create pinger thread
        args = [server, max_failures, ping_interval]
        pinger_thread = threading.Thread(
            target=pingping, name="Pinger", args=args)
        pinger_thread.freeze_event = threading.Event()
        pinger_thread.stop_event = threading.Event()
        self.pinger_thread = pinger_thread

        # scheduler for this class
        self.s = scheduler.Scheduler()

        # a liberty boolean
        self._liberty = False

        # freezer object
        self.freezer = freezer.Freezer(
            topmost=topmost,
            fullscreen=fullscreen,
            text='CONNECT THE NETWORK CABLE')

    def get_liberty(self):
        return self._liberty

    def remove_liberty(self):
        logger.info("ForceNet: remove liberty")
        self._liberty = False

    def start_liberty(self, seconds):
        '''Start a liberty period.'''
        logger.info("ForceNet: start liberty fo %ss.", seconds)
        self._liberty = True
        self.s.only_once(self.remove_liberty, seconds)

    def check_events(self):
        '''Check for other thread events '''
        # check for password events
        logger.debug("check events")
        freezer = self.freezer
        if not freezer.is_running():
            return
        events = freezer.get_events()
        chars = []
        append = chars.append
        pop = chars.pop
        for e in events:
            key = getattr(e, 'Key', None)
            if key == 'Return':
                del chars[:]
            elif key == 'Back' and chars:
                pop()
            elif isinstance(key, str) and len(key) == 1:
                append(key)

        text = ''.join(chars).lower()
        if text.endswith(self.password):
            logger.info("ForceNet: detected password")
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
            logger.info("ForceNet: will freeze")
            self.freezer.enable()

    def unfreeze(self):
        if self.freezer.is_running():
            logger.info("ForceNet: will unfreeze")
            self.freezer.disable()

    def run(self):
        '''Function that runs inits and runs the main loop.
        It checks for freeze flags from mypinger and 
        it calls for freezes and unfreezs accordingly.
        '''
        logger.info("In ForceNet.run()")
        self.pinger_thread.start()
        logger.info("pinger_thread started")

        s = self.s
        s.with_interval(self.loop, 0.1)
        s.with_interval(self.check_events, 0.1)
        logger.debug("added scheduler")
        try:
            while True:
                s.run_pending()
                time.sleep(0.01)
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt...")
            self.unfreeze()
            self.pinger_thread.stop_event.set()

    def loop(self):
        '''Main loop'''
        if self.get_liberty():
            self.unfreeze()
            return

        freeze = self.pinger_thread.freeze_event.is_set()

        if freeze:
            self.freeze()
        else:
            self.unfreeze()


if __name__ == '__main__':
    try:
        init()
        logger.debug("Adding freeze support")
        multiprocessing.freeze_support()
        logger.info("Initialization")
        fn = ForceNet()
        try:
            fn.run()
        except BaseException as e:
            logger.error("Exception occured on ForceNet.run()")
            tb = traceback.format_exc()
            logger.error(tb)
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(tb)
