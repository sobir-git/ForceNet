import sys
import tkinter as tk


class Fullscreen_Window:

    def __init__(self):
        self.tk = tk.Tk()
        tk.Label(self.tk, 
                 text="Connect the Network Cable",
                 fg = "red",
                 font = "Verdana 32 bold"
                 ).pack(fill='both', expand=True)
        self.tk.attributes("-fullscreen", True)


def main(**kwargs):
    w = Fullscreen_Window()
    w.tk.mainloop()

if __name__ == '__main__':
    p.start()
