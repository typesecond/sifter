"""Sifter desktop interface. Worker threads never manipulate Tk widgets."""
import math
from pathlib import Path
import queue
import threading
import time
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk

from .core import Pattern, export_keystore
from .miner import search

from .pixels import PixelHeader, pixel_font

BG = "#141627"
PANEL = "#1e2339"
LINE = "#46506d"
TEXT = "#edf0df"
MUTED = "#a2abc2"
ACCENT = "#b9ec78"


def duration(seconds):
    if not math.isfinite(seconds):
        return "—"
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    if seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:,.1f} days"


class App(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("dark")
        super().__init__(fg_color=BG)
        self.title("Sifter · Vanity address miner")
        self.geometry("760x640")
        self.minsize(720, 620)
        self.display_font = pixel_font()
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None
        self.export_worker = None
        self.result = None
        self.revealed = False
        self.closing = False
        self.started = 0
        self.animation_tick = 0
        self.prefix = ctk.StringVar(value="")
        self.suffix = ctk.StringVar(value="")
        self.engine = ctk.StringVar(value="Auto")
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=26, pady=(18, 8))
        self.pixel_header = PixelHeader(header)
        self.pixel_header.pack(side="left")
        self.label(header, "ETHEREUM\nADDRESS MINER", 12, MUTED, pixel=True).pack(side="right")

        form = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=0, border_width=2, border_color=LINE)
        form.grid(row=1, column=0, sticky="ew", padx=26)
        form.grid_columnconfigure((0, 1), weight=1)
        self.label(form, "STARTS WITH", 13, TEXT, pixel=True).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 4))
        self.label(form, "ENDS WITH", 13, TEXT, pixel=True).grid(row=0, column=1, sticky="w", padx=18, pady=(14, 4))
        self.prefix_entry = ctk.CTkEntry(form, textvariable=self.prefix, height=40, corner_radius=0, border_width=2, border_color=LINE, fg_color=BG, font=("Menlo", 18))
        self.prefix_entry.grid(row=1, column=0, sticky="ew", padx=(18, 8))
        self.suffix_entry = ctk.CTkEntry(form, textvariable=self.suffix, height=40, corner_radius=0, border_width=2, border_color=LINE, fg_color=BG, font=("Menlo", 18))
        self.suffix_entry.grid(row=1, column=1, sticky="ew", padx=(8, 18))
        self.difficulty = self.label(form, "Type a prefix, a suffix, or both. Use 0–9 and A–F.", 12, MUTED)
        self.difficulty.grid(row=2, column=0, columnspan=2, sticky="w", padx=18, pady=(7, 0))
        self.preview = self.label(form, "Example: abc … 123", 12, ACCENT, mono=True)
        self.preview.grid(row=3, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 12))
        self.engine_select = ctk.CTkOptionMenu(form, variable=self.engine, values=["Auto", "CPU", "GPU"], corner_radius=0, fg_color=LINE, button_color=LINE, button_hover_color="#5a6584", width=125, height=36, font=(self.display_font, 12))
        self.engine_select.grid(row=4, column=0, sticky="w", padx=18, pady=(0, 16))
        self.start_button = self.button(form, "FIND ADDRESS", self.start_search, primary=True, width=215, height=38)
        self.start_button.grid(row=4, column=1, sticky="e", padx=18, pady=(0, 16))
        self.bind("<Return>", lambda _event: self.start_search())

        session = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        session.grid(row=2, column=0, sticky="ew", padx=28, pady=(12, 10))
        session.grid_columnconfigure((0, 1, 2), weight=1)
        self.status = self.label(session, "Ready to search.", 13)
        self.status.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 3))
        self.rate = self.label(session, "— addr/s", 13, ACCENT, mono=True)
        self.rate.grid(row=1, column=0, sticky="w")
        self.elapsed = self.label(session, "0.0s elapsed", 12, MUTED)
        self.elapsed.grid(row=1, column=1)
        self.estimate = self.label(session, "50% estimate: —", 12, MUTED)
        self.estimate.grid(row=1, column=2, sticky="e")
        self.device = self.label(session, "Auto picks a search engine for you.", 11, MUTED)
        self.device.grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 1))

        result = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=0, border_width=2, border_color=LINE)
        result.grid(row=3, column=0, sticky="ew", padx=26)
        result.grid_columnconfigure(0, weight=1)
        self.label(result, "YOUR ADDRESS", 13, ACCENT, pixel=True).grid(row=0, column=0, sticky="w", padx=18, pady=(12, 5))
        self.address = self.label(result, "Your match will appear here.", 13, mono=True)
        self.address.grid(row=1, column=0, sticky="w", padx=18)
        self.secret = self.label(result, "Private key hidden", 10, MUTED, mono=True)
        self.secret.grid(row=2, column=0, sticky="w", padx=18, pady=(4, 9))
        actions = ctk.CTkFrame(result, fg_color="transparent", corner_radius=0)
        actions.grid(row=3, column=0, sticky="w", padx=18, pady=(0, 14))
        self.copy = self.button(actions, "COPY ADDRESS", self.copy_address, width=160)
        self.copy.pack(side="left", padx=(0, 8))
        self.reveal = self.button(actions, "SHOW KEY", self.toggle_key, width=125)
        self.reveal.pack(side="left", padx=(0, 8))
        self.export = self.button(actions, "SAVE WALLET", self.save_keystore, primary=True, width=170)
        self.export.pack(side="left")
        for button in (self.copy, self.reveal, self.export):
            button.configure(state="disabled")
        self.label(self, "LOCAL SEARCH  /  PASSWORD-ENCRYPTED WALLET EXPORT", 10, MUTED, pixel=True).grid(row=4, column=0, pady=(13, 10))
        self.prefix.trace_add("write", self.update_pattern)
        self.suffix.trace_add("write", self.update_pattern)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(75, self.poll)

    def label(self, parent, text, size, color=TEXT, pixel=False, mono=False):
        family = self.display_font if pixel else "Menlo" if mono else "Arial"
        return ctk.CTkLabel(parent, text=text, text_color=color, font=(family, size), anchor="w")

    def button(self, parent, text, command, primary=False, width=150, height=34):
        return ctk.CTkButton(parent, text=text, command=command, width=width, height=height,
                            corner_radius=0, border_width=2,
                            border_color=ACCENT if primary else LINE,
                            fg_color=ACCENT if primary else BG,
                            hover_color="#a6d367" if primary else LINE,
                            text_color=BG if primary else TEXT,
                            font=(self.display_font, 12))

    def update_pattern(self, *_):
        try:
            pattern = Pattern(self.prefix.get(), self.suffix.get())
            self.preview.configure(text="0x" + pattern.mask.lower().replace("x", "·"))
            self.difficulty.configure(text=f"{pattern.digits} matching characters  ·  {pattern.expected_attempts:,} attempts on average", text_color=MUTED)
        except ValueError as error:
            self.difficulty.configure(text=str(error), text_color="#f0ab8c")

    def start_search(self):
        if self.export_worker and self.export_worker.is_alive():
            self.status.configure(text="Finish the keystore export before starting another search.")
            return
        if self.worker and self.worker.is_alive():
            self.cancel.set()
            self.start_button.configure(text="STOPPING...", state="disabled")
            return
        try:
            pattern = Pattern(self.prefix.get(), self.suffix.get())
        except ValueError as error:
            self.status.configure(text=str(error))
            return
        if self.result and not messagebox.askyesno("Start another search?", "Starting again discards this result from the app. Have you saved the key or keystore?", parent=self):
            return
        self.result = None
        self.revealed = False
        self.secret.configure(text="Private key hidden")
        self.reveal.configure(text="SHOW KEY")
        self.address.configure(text="Sifting for your pattern…")
        for button in (self.copy, self.reveal, self.export):
            button.configure(state="disabled")
        self.cancel = threading.Event()
        self.started = time.monotonic()
        self.active_pattern = pattern
        self.rate.configure(text="— addr/s")
        self.estimate.configure(text="50% estimate: —")
        self.start_button.configure(text="STOP SEARCH", state="normal")
        self.prefix_entry.configure(state="disabled")
        self.suffix_entry.configure(state="disabled")
        self.engine_select.configure(state="disabled")
        engine = self.engine.get().lower()
        self.worker = threading.Thread(target=self.collect, args=(pattern, engine), daemon=True)
        self.worker.start()

    def collect(self, pattern, engine):
        try:
            for event in search(pattern, self.cancel, engine):
                self.events.put(event)
        except Exception:
            # Never render raw engine output or exception payloads with secrets.
            from .core import Event
            self.events.put(Event("error", "Search failed. Check the engine configuration and try again."))

    def poll(self):
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            if event.message:
                (self.device if event.kind == "device" else self.status).configure(text=event.message.split(",")[0] if event.kind == "device" else event.message)
            if event.rate:
                self.rate.configure(text=f"{event.rate:,.0f} addr/s")
                self.estimate.configure(text=f"50% estimate: {duration(self.active_pattern.seconds_for(.5, event.rate))}")
            if event.kind == "found":
                self.result = event.result
                self.address.configure(text=event.result.address)
                for button in (self.copy, self.reveal, self.export):
                    button.configure(state="normal")
        alive = self.worker and self.worker.is_alive()
        if alive:
            self.elapsed.configure(text=f"{duration(time.monotonic() - self.started)} elapsed")
        elif self.worker:
            self.worker = None
            self.start_button.configure(text="FIND ADDRESS", state="normal")
            self.prefix_entry.configure(state="normal")
            self.suffix_entry.configure(state="normal")
            self.engine_select.configure(state="normal")
        self.animation_tick += 1
        if self.animation_tick % 3 == 0:
            self.pixel_header.animate("mining" if alive else "found" if self.result else "idle")
        if self.closing:
            if not alive and not (self.export_worker and self.export_worker.is_alive()):
                self.destroy()
                return
        self.after(75, self.poll)

    def copy_address(self):
        if self.result:
            self.clipboard_clear()
            self.clipboard_append(self.result.address)
            self.status.configure(text="Address copied.")

    def toggle_key(self):
        if self.result:
            self.revealed = not self.revealed
            self.secret.configure(text="0x" + self.result.private_key.hex() if self.revealed else "Private key hidden")
            self.reveal.configure(text="HIDE KEY" if self.revealed else "SHOW KEY")

    def save_keystore(self):
        if not self.result:
            return
        destination = filedialog.asksaveasfilename(parent=self, title="Export encrypted keystore", initialfile=f"sifter-{self.result.address[:10]}.keystore.json", defaultextension=".json")
        if not destination:
            return
        password = simpledialog.askstring("Encrypt keystore", "Choose a password:", show="•", parent=self)
        if password is None:
            return
        confirmation = simpledialog.askstring("Encrypt keystore", "Confirm password:", show="•", parent=self)
        if not password or password != confirmation:
            messagebox.showerror("Export failed", "Passwords must be nonempty and match.", parent=self)
            return
        # scrypt runs outside Tk so the window remains responsive.
        self.export.configure(state="disabled", text="SAVING...")
        self.export_worker = threading.Thread(target=self.encrypt, args=(self.result, password, destination), daemon=True)
        self.export_worker.start()
        self.after(100, self.poll_export)

    def encrypt(self, result, password, destination):
        try:
            self.export_message = f"Encrypted keystore saved: {export_keystore(result, password, destination).name}"
        except FileExistsError:
            self.export_message = "Export skipped: that file already exists. Choose a new filename."
        except Exception:
            self.export_message = "Keystore export failed. Check the destination and try again."

    def poll_export(self):
        if self.export_worker.is_alive():
            self.after(100, self.poll_export)
        else:
            self.export.configure(state="normal", text="SAVE WALLET")
            self.status.configure(text=self.export_message)

    def on_close(self):
        if self.result and not messagebox.askyesno("Close Sifter?", "The result is held in memory. Close after saving your key or keystore?", parent=self):
            return
        self.closing = True
        self.cancel.set()


def run():
    App().mainloop()
