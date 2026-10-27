"""Small, code-drawn pixel graphics and a process-local display font."""
import ctypes
from pathlib import Path
import sys
import tkinter as tk

BG = "#141627"
EDGE = "#596080"
LIGHT = "#dcf1c0"
LIME = "#b9ec78"
GOLD = "#f1c777"

GLYPHS = {
    "S": ("11111", "10000", "10000", "11111", "00001", "00001", "11111"),
    "I": ("111", "010", "010", "010", "010", "010", "111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
}


def pixel_font():
    """Register the bundled font for this app process, without installing it."""
    path = Path(__file__).parent / "assets/Silkscreen-Regular.ttf"
    try:
        if sys.platform == "darwin":
            cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
            ct = ctypes.CDLL("/System/Library/Frameworks/CoreText.framework/CoreText")
            cf.CFURLCreateFromFileSystemRepresentation.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_bool]
            cf.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
            cf.CFRelease.argtypes = [ctypes.c_void_p]
            ct.CTFontManagerRegisterFontsForURL.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p]
            ct.CTFontManagerRegisterFontsForURL.restype = ctypes.c_bool
            raw = str(path).encode()
            url = cf.CFURLCreateFromFileSystemRepresentation(None, raw, len(raw), False)
            if url:
                ct.CTFontManagerRegisterFontsForURL(url, 1, None)
                cf.CFRelease(url)
            return "Silkscreen"
        if sys.platform == "win32":
            from customtkinter import FontManager
            if FontManager.load_font(str(path)):
                return "Silkscreen"
    except (OSError, AttributeError):
        pass
    return "Courier"


class PixelHeader(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, width=290, height=66, bg=BG, highlightthickness=0, bd=0)
        self.phase = 0
        self.state = "idle"
        self.draw()

    def block(self, x, y, w, h, color):
        self.create_rectangle(x, y, x + w, y + h, fill=color, outline="", tags="art")

    def draw(self):
        self.delete("art")
        # A tiny sieve sorts the falling ore into a bright pixel gem.
        self.block(4, 22, 49, 4, EDGE)
        self.block(8, 26, 4, 13, EDGE)
        self.block(45, 26, 4, 13, EDGE)
        self.block(12, 35, 33, 4, GOLD)
        for x in range(16, 42, 8):
            self.block(x, 29, 4, 6, GOLD)
        for index, x in enumerate((15, 27, 39)):
            y = 5 + ((self.phase * 4 + index * 8) % 22 if self.state == "mining" else index * 4)
            self.block(x, y, 4, 4, GOLD if index != 1 else LIME)
        self.block(23, 46, 12, 4, LIME)
        self.block(19, 50, 20, 4, LIGHT if self.state == "found" else LIME)
        self.block(23, 54, 12, 4, LIME)
        self.block(27, 58, 4, 4, LIME)
        x = 72
        for letter in "SIFTER":
            rows = GLYPHS[letter]
            for row, line in enumerate(rows):
                for col, value in enumerate(line):
                    if value == "1":
                        self.block(x + col * 5, 12 + row * 5, 5, 5, LIGHT)
            x += (len(rows[0]) + 1) * 5

    def animate(self, state):
        self.state = state
        if state == "mining":
            self.phase = (self.phase + 1) % 20
        self.draw()
