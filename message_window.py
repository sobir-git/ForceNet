import tkinter as tk


class MessageWindow:
    '''A class for showing message on window both fullscreen and topmost.
    Recommended to frequently call update() method to keep it responsive.
    '''
    _visible = False

    @property
    def visible(self):
        return self._visible

    def __init__(self, message, topmost=False, fullscreen=False):
        self.message = message
        self.topmost = topmost
        self.fullscreen = fullscreen

    def show(self):
        '''Show the window'''
        if self.visible:
            return
        self._visible = True
        root = tk.Tk()
        tk.Label(root, 
                 text=self.message,
                 fg = "red",
                 font = "Verdana 32 bold"
                 ).pack(fill='both', expand=True)
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
        try: self.root.update()
        except: pass


if __name__ == '__main__':
    mw = MessageWindow('TEST', True, True)
    mw.show()
    mw.update()
    import time
    time.sleep(1)
