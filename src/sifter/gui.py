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

BG = "#111410"
PANEL = "#1b201a"
LINE = "#333d30"
TEXT = "#edf0e7"
MUTED = "#a3ad99"
ACCENT = "#c5f277"


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
        self.title("Sifter · Ethereum vanity studio")
        self.geometry("920x780")
        self.minsize(780, 720)
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None
        self.export_worker = None
        self.result = None
        self.revealed = False
        self.closing = False
        self.started = 0
        self.prefix = ctk.StringVar(value="")
        self.suffix = ctk.StringVar(value="")
        self.engine = ctk.StringVar(value="Auto")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        top = ctk.CTkFrame(self, fg_color=BG)
        top.grid(row=0, column=0, sticky="ew", padx=32, pady=(25, 12))
        self.label(top, "▦  SIFTER", 27, ACCENT).pack(side="left")
        self.label(top, "ETHEREUM  /  LOCAL WALLET STUDIO", 11, MUTED).pack(side="right")
        content = ctk.CTkScrollableFrame(self, fg_color=BG)
        content.grid(row=1, column=0, sticky="nsew", padx=20)
        content.grid_columnconfigure(0, weight=1)
        self.label(content, "An address with your signature.", 32).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))
        self.label(content, "Choose a pattern. Sift locally. Keep the keys.", 14, MUTED).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 23))
        config = ctk.CTkFrame(content, fg_color=PANEL, corner_radius=12)
        config.grid(row=2, column=0, sticky="ew", padx=10)
        config.grid_columnconfigure((0, 1), weight=1)
        self.label(config, "01   SET YOUR PATTERN", 11, ACCENT).grid(row=0, column=0, columnspan=2, sticky="w", padx=22, pady=(20, 14))
        self.label(config, "Starts with", 12, MUTED).grid(row=1, column=0, sticky="w", padx=22)
        self.label(config, "Ends with", 12, MUTED).grid(row=1, column=1, sticky="w", padx=22)
        self.prefix_entry = ctk.CTkEntry(config, textvariable=self.prefix, placeholder_text="c0ffee", height=42, border_color=LINE, fg_color=BG, font=("Menlo", 17))
        self.prefix_entry.grid(row=2, column=0, sticky="ew", padx=(22, 8), pady=(6, 12))
        self.suffix_entry = ctk.CTkEntry(config, textvariable=self.suffix, placeholder_text="beef", height=42, border_color=LINE, fg_color=BG, font=("Menlo", 17))
        self.suffix_entry.grid(row=2, column=1, sticky="ew", padx=(8, 22), pady=(6, 12))
        self.preview = self.label(config, "0x · · ·", 12, MUTED)
        self.preview.grid(row=3, column=0, columnspan=2, sticky="w", padx=22)
        self.difficulty = self.label(config, "Use 0–9 and A–F. Prefix, suffix, or both.", 12, MUTED)
        self.difficulty.grid(row=4, column=0, columnspan=2, sticky="w", padx=22, pady=(6, 18))
        self.engine_select = ctk.CTkOptionMenu(config, variable=self.engine, values=["Auto", "CPU", "GPU"], fg_color=LINE, button_color=LINE, button_hover_color="#46533f", width=125)
        self.engine_select.grid(row=5, column=0, sticky="w", padx=22, pady=(0, 20))
        self.start_button = ctk.CTkButton(config, text="Start sifting  →", command=self.start_search, height=40, fg_color=ACCENT, hover_color="#a9d360", text_color=BG, font=("Arial", 14, "bold"))
        self.start_button.grid(row=5, column=1, sticky="e", padx=22, pady=(0, 20))
        status = ctk.CTkFrame(content, fg_color=PANEL, corner_radius=12)
        status.grid(row=3, column=0, sticky="ew", padx=10, pady=14)
        status.grid_columnconfigure((0, 1, 2), weight=1)
        self.label(status, "02   SEARCH SESSION", 11, ACCENT).grid(row=0, column=0, columnspan=3, sticky="w", padx=22, pady=(18, 8))
        self.status = self.label(status, "Ready when you are.", 14)
        self.status.grid(row=1, column=0, columnspan=3, sticky="w", padx=22, pady=(0, 10))
        self.rate = self.label(status, "— addr/s", 20)
        self.rate.grid(row=2, column=0, sticky="w", padx=22)
        self.elapsed = self.label(status, "0.0s elapsed", 15, MUTED)
        self.elapsed.grid(row=2, column=1)
        self.estimate = self.label(status, "50% estimate: —", 12, MUTED)
        self.estimate.grid(row=2, column=2, sticky="e", padx=22)
        self.device = self.label(status, "Auto uses CPU for short patterns and an available GPU engine for longer ones.", 11, MUTED)
        self.device.grid(row=3, column=0, columnspan=3, sticky="w", padx=22, pady=(10, 18))
        result = ctk.CTkFrame(content, fg_color=PANEL, corner_radius=12)
        result.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 14))
        result.grid_columnconfigure(0, weight=1)
        self.label(result, "03   YOUR MATCH", 11, ACCENT).grid(row=0, column=0, sticky="w", padx=22, pady=(18, 10))
        self.address = self.label(result, "A verified address will appear here.", 14)
        self.address.grid(row=1, column=0, sticky="w", padx=22)
        self.secret = self.label(result, "Private key hidden", 11, MUTED)
        self.secret.grid(row=2, column=0, sticky="w", padx=22, pady=(8, 12))
        actions = ctk.CTkFrame(result, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="w", padx=22, pady=(0, 18))
        self.copy = ctk.CTkButton(actions, text="Copy address", width=120, command=self.copy_address, fg_color=LINE, hover_color="#46533f", state="disabled")
        self.copy.pack(side="left", padx=(0, 8))
        self.reveal = ctk.CTkButton(actions, text="Reveal key", width=110, command=self.toggle_key, fg_color=LINE, hover_color="#46533f", state="disabled")
        self.reveal.pack(side="left", padx=(0, 8))
        self.export = ctk.CTkButton(actions, text="Export encrypted keystore", width=190, command=self.save_keystore, fg_color=ACCENT, text_color=BG, hover_color="#a9d360", state="disabled")
        self.export.pack(side="left")
        self.label(self, "LOCAL BY DESIGN   /   SIFTER", 10, MUTED).grid(row=2, column=0, pady=(10, 16))
        self.prefix.trace_add("write", self.update_pattern)
        self.suffix.trace_add("write", self.update_pattern)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(75, self.poll)

    def label(self, parent, text, size, color=TEXT):
        return ctk.CTkLabel(parent, text=text, text_color=color, font=("Arial", size), anchor="w")

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
            self.start_button.configure(text="Stopping…", state="disabled")
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
        self.reveal.configure(text="Reveal key")
        self.address.configure(text="Sifting for your pattern…")
        for button in (self.copy, self.reveal, self.export):
            button.configure(state="disabled")
        self.cancel = threading.Event()
        self.started = time.monotonic()
        self.active_pattern = pattern
        self.rate.configure(text="— addr/s")
        self.estimate.configure(text="50% estimate: —")
        self.start_button.configure(text="Stop search", state="normal")
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
                (self.device if event.kind == "device" else self.status).configure(text=event.message)
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
            self.start_button.configure(text="Start sifting  →", state="normal")
            self.prefix_entry.configure(state="normal")
            self.suffix_entry.configure(state="normal")
            self.engine_select.configure(state="normal")
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
            self.reveal.configure(text="Hide key" if self.revealed else "Reveal key")

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
        self.export.configure(state="disabled", text="Encrypting…")
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
            self.export.configure(state="normal", text="Export encrypted keystore")
            self.status.configure(text=self.export_message)

    def on_close(self):
        if self.result and not messagebox.askyesno("Close Sifter?", "The result is held in memory. Close after saving your key or keystore?", parent=self):
            return
        self.closing = True
        self.cancel.set()


def run():
    App().mainloop()
