from __future__ import print_function, division
import tkinter as tk
import logging
logger = logging.getLogger('main')


class MessageWindow:
    '''A class for showing text message on window both fullscreen and topmost.
    Recommended to frequently call update() method to keep it responsive.
    '''
    _visible = False

    @property
    def visible(self):
        return self._visible

    def __init__(self, text, topmost=False, fullscreen=False):
        # add at least an new line for loading-dots
        self.text = text + '\n.'
        self.topmost = topmost
        self.fullscreen = fullscreen

    def show(self):
        '''Show the window'''
        if self.visible:
            return
        self._visible = True
        root = tk.Tk()
        self.label = tk.Label(root, 
                 text=self.text,
                 fg = "red",
                 font = "Verdana 32 bold"
                 )
        self.label.pack(fill='both', expand=True)
        root.lift()
        root.attributes('-fullscreen', self.fullscreen)
        root.attributes('-topmost', self.topmost)
        root.update()
        self.root = root

    def hide(self):
        '''Hide the window'''
        if not self.visible:
            return
        self._visible = False
        try: self.root.destroy()
        except: pass

    def update(self):
        '''Update the window'''
        if not self._visible:
            return

        try:
            line1, line2 = self.label['text'].splitlines()
            dots = len(line2)
            dots = 1 + (dots + 1) % 3
            line2 = '.' * dots
            self.label['text'] = line1 + '\n' + line2
            self.root.update()
        except Exception as e:
            logger.error("Error updating MessageWindow: %s", e)


if __name__ == '__main__':
    mw = MessageWindow('TEST', False, False)
    mw.show()
    mw.update()
    import time
    while True:
        mw.update()
        time.sleep(0.1)
