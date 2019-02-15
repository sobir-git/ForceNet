import time
import os
import sys
import pyHook
import pythoncom
import threading
DEBUG = os.getenv('freezer_debug') == '1'
print(f"DEBUG={DEBUG}")


command = ''
QUEUE_LOCK = None
QUEUE = None
PASSWORD = None
HM = None


def OnMouseEvent(event):
    if DEBUG:
        if tuple(event.Position) == (0, 0):
            sys.exit(0)

    if DEBUG: return True
    else: return False


def OnKeyboardEvent(event):
    global command
    key = event.Key
    print("Key:", key)

    if key == 'Return':
        command = ''
    elif key == 'Back' and len(command) > 0:
        command = command[0:-1]
    else:
        command += key if (isinstance(key, str) and len(key) == 1) else ''

    if PASSWORD and command.lower().endswith(PASSWORD):
        size = len(PASSWORD)
        try:
            time = int(command[0:-size])
        except:
            time = 5

        time = min(time, 90 * 24 * 60)  # up to three monthes ;)

        if QUEUE_LOCK:
            print(f"getting FREE for {time} minutes")
            QUEUE_LOCK.acquire()
            QUEUE.append({"action": "liberty", "time": time})
            QUEUE_LOCK.release()
        stop()

    return False


def run(queue=None, password=None, queue_lock=None):
    '''Run hooking mouse and keyboard events.
    queue is used to send messages
    queue_lock is to be acquired befored setting queue
    '''
    global QUEUE, PASSWORD, QUEUE_LOCK, HM
    QUEUE = queue
    PASSWORD = password
    QUEUE_LOCK = queue_lock
    # create a hook manager
    HM = pyHook.HookManager()
    # watch for all mouse events
    HM.KeyDown = OnKeyboardEvent
    # watch for all mouse events
    HM.MouseAll = OnMouseEvent
    HM.HookKeyboard()
    HM.HookMouse()
    th = threading.current_thread()
    while True:
        pythoncom.PumpWaitingMessages()
        event = getattr(th, '_stop_event', None)
        if event and event.is_set():
            stop()
        # time.sleep(0)


def stop():
    print("Exiting freezer...")
    t0 = time.time()
    HM.UnhookKeyboard()
    HM.UnhookMouse()
    print(f"exit time = {time.time() - t0}")
    sys.exit(0)


if __name__ == '__main__':
    run(password='123')
