from __future__ import print_function, division

import multiprocessing as mp
import scheduler
import time
import os
import sys
import pyHook
import pythoncom
import threading
from message_window import MessageWindow
DEBUG = os.getenv('freezer_debug') == '1'
print("DEBUG=%s" % DEBUG)


class Hooker:
    def __init__(self, queue):
        # create a hook manager
        hm = pyHook.HookManager()
        # watch for all mouse events
        hm.KeyDown = self.OnKeyboardEvent
        # watch for all mouse events
        hm.MouseAll = self.OnMouseEvent
        self.hm = hm
        self.queue = queue

    def hook(self):
        self.hm.HookKeyboard()
        self.hm.HookMouse()

    def OnMouseEvent(self, event):
        if DEBUG:
            if tuple(event.Position) == (0, 0):
                sys.exit(0)
        self.queue.put(event)
        if DEBUG:
            return True
        else:
            return False

    def OnKeyboardEvent(self, event):
        key = event.Key
        print("Key:", key)
        self.queue.put(event)
        return False


def _freeze(queue, conn, fullscreen, topmost):
    '''Run hooking mouse and keyboard events.
    queue is used to to send keyboard and mouse events,
    conn is used to receive stop events'''
    print("freezer2: ITS FREEZING")

    def check_stop_signal():
        '''Check for stop signal from process connection '''
        if conn.poll():
            message = conn.recv()
            if message['action'] == 'stop':
                print("IMMEDIATELY EXITING _freeze BY STOP SIGNAL")
                sys.exit(0)

    mw = MessageWindow("Freezer 2", fullscreen=fullscreen, topmost=topmost)
    mw.show()

    hooker = Hooker(queue)
    hooker.hook()

    s = scheduler.Scheduler()
    s.with_interval(pythoncom.PumpWaitingMessages, 0.01)
    s.with_interval(mw.update, 0.1)
    s.with_interval(check_stop_signal, 0.1)

    while True:
        s.run_pending()


class Freezer:
    '''Freezer class containing enable and disable methods.
    When called enable() it will hook keyboard and mouse and shows
    a message text on screen.
    '''

    def __init__(self, max_events=100, text=None, topmost=False, fullscreen=False):
        '''Init
        Args:
            max_events: int: The maximum number of events stored (defaults to 100)
            text: str: Text message to display when frozen (defaults to "Frozen")
            fullscreen: bool: Show message window fullscreen
            topmost: bool: Show message window topmost
        '''
        self.fullscreen = fullscreen
        self.topmost = topmost
        self.max_events = max_events
        self.text = text or "Frozen"
        self._process = None
        self._queue = None
        self._events = []

    def is_running(self):
        '''Check if freezing process is running (formally .is_alive())'''
        if not self._process:
            return False
        return self._process.is_alive()

    def enable(self):
        '''Enable freezing. This will not do anything if freezing is not running. '''
        if not self.is_running():
            print("enabling freezer")
            conn1, conn2 = mp.Pipe()
            queue = mp.Queue()
            kwargs = {'queue': queue, 'conn': conn2,
                      'fullscreen': self.fullscreen, 'topmost': self.topmost}
            process = mp.Process(target=_freeze, kwargs=kwargs)
            process.start()

            self._events = []
            self._conn = conn1
            self._queue = queue
            self._process = process

    def disable(self):
        '''Disable freezing. This will not do anything if freezing is already running.'''
        if self.is_running():
            print("disabling freezer")
            # self._process.terminate()
            self._conn.send({'action': 'stop'})

    def get_events(self):
        '''Get a list of events. The list contains only the last "max_events" number 
        of events'''
        append = self._events.append
        while not self._queue.empty():
            append(self._queue.get_nowait())
        self._events = self._events[-self.max_events:]
        return self._events


if __name__ == '__main__':
    print('__name__ == __main__')
    freezer = Freezer()
    freezer.enable()
    while True:
        events = freezer.get_events()
        events = filter(lambda e: hasattr(e, 'Key'), events)
        text = ''.join(map(lambda e: str(e.Key), events))
        if text:
            print("text = %s" % text)
        if '123' in text:
            freezer.disable()
        time.sleep(1)
