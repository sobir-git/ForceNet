import os
import sys
import pyHook
import pythoncom
import threading
DEBUG = os.getenv('freezer_debug') == '1'
print(f"DEBUG={DEBUG}")


command = ''
QUEUE = None
PASSWORD = None

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

    if command.lower().endswith(PASSWORD):
        size = len(PASSWORD)
        try:
            time = int(command[0:-size])
        except:
            time = 5

        time = min(time, 90 * 24 * 60)  # up to three monthes ;)

        print(f"getting FREE for {time} minutes")
        QUEUE.put({"time": time})
        print("done putting")

    return False


def freeze(queue=None, password=None):
    global QUEUE, PASSWORD
    PASSWORD = password
    QUEUE = queue
    # create a hook manager
    hm = pyHook.HookManager()
    # watch for all mouse events
    hm.KeyDown = OnKeyboardEvent
    # watch for all mouse events
    hm.MouseAll = OnMouseEvent
    hm.HookKeyboard()
    hm.HookMouse()
    pythoncom.PumpMessages()
