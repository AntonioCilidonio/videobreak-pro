
import os
import json
import time
import threading
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog

APP_NAME = "VideoBreak Pro"
ORG_FOLDER = "VideoBreakPro"
VIDEO_EXTS = (".mp4", ".mkv", ".avi", ".mov", ".wmv", ".m4v")

def appdata_dir():
    p = Path(os.environ.get("APPDATA", Path.home())) / ORG_FOLDER
    p.mkdir(parents=True, exist_ok=True)
    return p

CONFIG_PATH = appdata_dir() / "config.json"

@dataclass
class Config:
    interval_minutes: int = 40
    video_folder: str = str(appdata_dir() / "videos")
    vlc_path: str = r"C:\Program Files\VideoLAN\VLC\vlc.exe"

def load_config():
    if CONFIG_PATH.exists():
        try:
            return Config(**json.loads(CONFIG_PATH.read_text()))
        except:
            pass
    return Config()

def save_config(cfg):
    CONFIG_PATH.write_text(json.dumps(asdict(cfg), indent=4))

def list_videos(folder):
    p = Path(folder)
    return [str(f) for f in p.iterdir() if f.suffix.lower() in VIDEO_EXTS] if p.exists() else []

def run_vlc(vlc, playlist):
    subprocess.run([vlc, "--fullscreen", "--play-and-exit", str(playlist)])

class Scheduler:
    def __init__(self, cfg, cb):
        self.cfg = cfg
        self.cb = cb
        self.stop_event = threading.Event()
        self.thread = None
        self.next_run = None

    def start(self):
        if self.thread and self.thread.is_alive(): return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()
        self.cb()

    def stop(self):
        self.stop_event.set()
        self.next_run = None
        self.cb()

    def play_now(self):
        threading.Thread(target=self.play, daemon=True).start()

    def loop(self):
        while not self.stop_event.is_set():
            self.next_run = time.time() + self.cfg.interval_minutes * 60
            while time.time() < self.next_run and not self.stop_event.is_set():
                time.sleep(0.5)
            if self.stop_event.is_set(): break
            self.play()

    def play(self):
        vids = list_videos(self.cfg.video_folder)
        if not vids: return
        playlist = appdata_dir() / "playlist.m3u"
        playlist.write_text("\n".join(vids))
        run_vlc(self.cfg.vlc_path, playlist)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.title(APP_NAME)
        self.geometry("520x300")
        self.scheduler = Scheduler(self.cfg, self.refresh)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.build_ui()
        self.after(500, self.refresh)

    def build_ui(self):
        f = ttk.Frame(self, padding=12)
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="Intervallo (minuti)").grid(row=0, column=0, sticky="w")
        self.interval = tk.IntVar(value=self.cfg.interval_minutes)
        ttk.Spinbox(f, from_=1, to=1440, textvariable=self.interval).grid(row=0, column=1)

        ttk.Label(f, text="Cartella video").grid(row=1, column=0, pady=10, sticky="w")
        self.folder = tk.StringVar(value=self.cfg.video_folder)
        ttk.Entry(f, textvariable=self.folder, width=40).grid(row=1, column=1)
        ttk.Button(f, text="Sfoglia", command=self.pick_folder).grid(row=1, column=2)

        ttk.Label(f, text="Percorso VLC").grid(row=2, column=0, pady=10, sticky="w")
        self.vlc = tk.StringVar(value=self.cfg.vlc_path)
        ttk.Entry(f, textvariable=self.vlc, width=40).grid(row=2, column=1)
        ttk.Button(f, text="Sfoglia", command=self.pick_vlc).grid(row=2, column=2)

        b = ttk.Frame(f)
        b.grid(row=3, column=0, columnspan=3, pady=16)
        ttk.Button(b, text="Avvia", command=self.start).pack(side="left", padx=6)
        ttk.Button(b, text="Stop", command=self.stop).pack(side="left", padx=6)
        ttk.Button(b, text="Riproduci ora", command=self.play_now).pack(side="left", padx=6)

        self.status = tk.StringVar(value="Pronto.")
        ttk.Label(f, textvariable=self.status).grid(row=4, column=0, columnspan=3, sticky="w")

        f.columnconfigure(1, weight=1)

    def refresh(self):
        if self.scheduler.next_run:
            r = int(self.scheduler.next_run - time.time())
            self.status.set(f"Prossima riproduzione tra {r//60:02d}:{r%60:02d}")
        else:
            self.status.set("Scheduler fermo.")
        self.after(500, self.refresh)

    def start(self):
        self.apply()
        self.scheduler.start()

    def stop(self):
        self.scheduler.stop()

    def play_now(self):
        self.apply()
        self.scheduler.play_now()

    def apply(self):
        self.cfg.interval_minutes = self.interval.get()
        self.cfg.video_folder = self.folder.get()
        self.cfg.vlc_path = self.vlc.get()
        save_config(self.cfg)

    def pick_folder(self):
        d = filedialog.askdirectory()
        if d: self.folder.set(d)

    def pick_vlc(self):
        f = filedialog.askopenfilename(filetypes=[("VLC","vlc.exe")])
        if f: self.vlc.set(f)

if __name__ == "__main__":
    App().mainloop()
