
import os
import json
import time
import threading
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Tray support (optional but included in requirements)
try:
    import pystray
    from PIL import Image
except Exception:
    pystray = None
    Image = None

APP_NAME = "VideoBreak Pro"
ORG_FOLDER = "VideoBreakPro"
VIDEO_EXTS = (".mp4", ".mkv", ".avi", ".mov", ".wmv", ".m4v")

def appdata_dir() -> Path:
    appdata = os.environ.get("APPDATA") or str(Path.home())
    p = Path(appdata) / ORG_FOLDER
    p.mkdir(parents=True, exist_ok=True)
    return p

CONFIG_PATH = appdata_dir() / "config.json"
LOG_PATH = appdata_dir() / "run.log"

@dataclass
class Config:
    interval_minutes: int = 40
    video_folder: str = str(appdata_dir() / "videos")
    vlc_path: str = r"C:\Program Files\VideoLAN\VLC\\vlc.exe"
    start_with_windows: bool = False
    start_minimized: bool = True

def load_config() -> Config:
    try:
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            merged = {**asdict(Config()), **data}
            return Config(**merged)
    except Exception:
        pass
    return Config()

def save_config(cfg: Config) -> None:
    CONFIG_PATH.write_text(json.dumps(asdict(cfg), indent=4), encoding="utf-8")

def ensure_video_folder(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)

def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)

def list_videos(folder: str):
    p = Path(folder)
    if not p.exists():
        return []
    files = []
    for x in sorted(p.iterdir()):
        if x.is_file() and x.suffix.lower() in VIDEO_EXTS:
            files.append(str(x))
    return files

def write_playlist(files, playlist_path: Path):
    playlist_path.write_text("\n".join(files) + "\n", encoding="utf-8")

def run_vlc(vlc_path: str, playlist_path: str):
    args = [vlc_path, "--fullscreen", "--play-and-exit", playlist_path]
    log("Starting VLC")
    subprocess.run(args, check=False)
    log("VLC finished")

def set_startup(enable: bool):
    try:
        import winreg, sys
        run_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                target = sys.executable if getattr(sys, "frozen", False) else str(Path(__file__).resolve())
                winreg.SetValueEx(key, "VideoBreakPro", 0, winreg.REG_SZ, f"\"{target}\"")
            else:
                try:
                    winreg.DeleteValue(key, "VideoBreakPro")
                except FileNotFoundError:
                    pass
    except Exception as e:
        log(f"Startup registry error: {e}")
        raise

class Scheduler:
    def __init__(self, cfg: Config, notify):
        self.cfg = cfg
        self.notify = notify
        self._stop = threading.Event()
        self._thread = None
        self.next_run_ts = None

    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.notify()

    def stop(self):
        self._stop.set()
        self.next_run_ts = None
        self.notify()

    def play_now(self):
        threading.Thread(target=self._play_once, daemon=True).start()

    def _loop(self):
        while not self._stop.is_set():
            interval = max(1, int(self.cfg.interval_minutes) * 60)
            self.next_run_ts = time.time() + interval
            self.notify()
            while not self._stop.is_set() and time.time() < self.next_run_ts:
                time.sleep(0.5)
            if self._stop.is_set():
                break
            self._play_once()

    def _play_once(self):
        try:
            ensure_video_folder(self.cfg.video_folder)
            files = list_videos(self.cfg.video_folder)
            if not files:
                log("No videos found. Skipping playback.")
                return
            playlist = appdata_dir() / "playlist.m3u"
            write_playlist(files, playlist)
            run_vlc(self.cfg.vlc_path, str(playlist))
        except Exception as e:
            log(f"Playback error: {e}")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        ensure_video_folder(self.cfg.video_folder)

        self.title(APP_NAME)
        self.geometry("620x380")
        self.minsize(620, 380)

        self.scheduler = Scheduler(self.cfg, self._refresh_ui)
        self.tray = None

        self.protocol("WM_DELETE_WINDOW", self._on_close_clicked)

        self._build_ui()
        self._init_tray()

        self.after(500, self._tick)

        if self.cfg.start_minimized:
            self.after(200, self._minimize_to_tray)

    def _build_ui(self):
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)

        title = ttk.Label(root, text="VideoBreak Pro", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 12))

        ttk.Label(root, text="Intervallo (minuti)").grid(row=1, column=0, sticky="w")
        self.interval = tk.IntVar(value=int(self.cfg.interval_minutes))
        ttk.Spinbox(root, from_=1, to=1440, textvariable=self.interval, width=8).grid(row=1, column=1, sticky="w")

        ttk.Label(root, text="Cartella Video").grid(row=2, column=0, sticky="w", pady=(10,0))
        self.folder = tk.StringVar(value=self.cfg.video_folder)
        ttk.Entry(root, textvariable=self.folder, width=54).grid(row=2, column=1, columnspan=2, sticky="we", pady=(10,0))
        ttk.Button(root, text="Sfoglia", command=self._pick_folder).grid(row=2, column=3, sticky="e", pady=(10,0))

        ttk.Label(root, text="Percorso VLC (vlc.exe)").grid(row=3, column=0, sticky="w", pady=(10,0))
        self.vlc = tk.StringVar(value=self.cfg.vlc_path)
        ttk.Entry(root, textvariable=self.vlc, width=54).grid(row=3, column=1, columnspan=2, sticky="we", pady=(10,0))
        ttk.Button(root, text="Sfoglia", command=self._pick_vlc).grid(row=3, column=3, sticky="e", pady=(10,0))

        self.startup = tk.BooleanVar(value=self.cfg.start_with_windows)
        ttk.Checkbutton(root, text="Avvia con Windows", variable=self.startup).grid(row=4, column=0, sticky="w", pady=(10,0))

        self.minimize = tk.BooleanVar(value=self.cfg.start_minimized)
        ttk.Checkbutton(root, text="Avvia minimizzato (tray)", variable=self.minimize).grid(row=4, column=1, sticky="w", pady=(10,0))

        ttk.Separator(root).grid(row=5, column=0, columnspan=4, sticky="we", pady=14)

        btnbar = ttk.Frame(root)
        btnbar.grid(row=6, column=0, columnspan=4, sticky="we")

        self.btn_start = ttk.Button(btnbar, text="Avvia", command=self._start)
        self.btn_stop = ttk.Button(btnbar, text="Stop", command=self._stop)
        self.btn_now = ttk.Button(btnbar, text="Riproduci ora", command=self._play_now)
        self.btn_save = ttk.Button(btnbar, text="Salva", command=self._save)

        self.btn_start.pack(side="left", padx=6)
        self.btn_stop.pack(side="left", padx=6)
        self.btn_now.pack(side="left", padx=6)
        self.btn_save.pack(side="right", padx=6)

        self.status = tk.StringVar(value="Pronto.")
        ttk.Label(root, textvariable=self.status).grid(row=7, column=0, columnspan=4, sticky="w", pady=(10,0))

        self.countdown = tk.StringVar(value="")
        ttk.Label(root, textvariable=self.countdown, font=("Segoe UI", 10)).grid(row=8, column=0, columnspan=4, sticky="w", pady=(6,0))

        note = "Nota: i video vengono letti dalla cartella scelta. VLC si chiude automaticamente a fine playlist."
        ttk.Label(root, text=note, wraplength=560, foreground="#444").grid(row=9, column=0, columnspan=4, sticky="w", pady=(16,0))

        root.columnconfigure(2, weight=1)
        self._refresh_ui()

    def _init_tray(self):
        if pystray is None or Image is None:
            return
        try:
            icon_path = Path(__file__).resolve().parent / "assets" / "icon.png"
            image = Image.open(icon_path)
            menu = pystray.Menu(
                pystray.MenuItem("Apri", lambda: self.after(0, self._restore_from_tray)),
                pystray.MenuItem("Riproduci ora", lambda: self.after(0, self._play_now)),
                pystray.MenuItem("Avvia/Stop", lambda: self.after(0, (self._stop if self.scheduler.running() else self._start))),
                pystray.MenuItem("Esci", lambda: self.after(0, self._exit_app)),
            )
            self.tray = pystray.Icon("VideoBreakPro", image, APP_NAME, menu)
            threading.Thread(target=self.tray.run, daemon=True).start()
        except Exception as e:
            log(f"Tray error: {e}")
            self.tray = None

    def _validate(self):
        if self.interval.get() < 1:
            messagebox.showerror(APP_NAME, "Intervallo non valido.")
            return False
        if not self.folder.get().strip():
            messagebox.showerror(APP_NAME, "Cartella video non valida.")
            return False
        vlc = self.vlc.get().strip()
        if not vlc or not Path(vlc).exists():
            messagebox.showerror(APP_NAME, "Percorso VLC non valido. Seleziona vlc.exe.")
            return False
        return True

    def _apply_cfg(self):
        self.cfg.interval_minutes = int(self.interval.get())
        self.cfg.video_folder = self.folder.get().strip()
        self.cfg.vlc_path = self.vlc.get().strip()
        self.cfg.start_with_windows = bool(self.startup.get())
        self.cfg.start_minimized = bool(self.minimize.get())

    def _save(self):
        if not self._validate():
            return
        self._apply_cfg()
        ensure_video_folder(self.cfg.video_folder)
        save_config(self.cfg)
        try:
            set_startup(self.cfg.start_with_windows)
        except Exception as e:
            messagebox.showwarning(APP_NAME, f"Non sono riuscito a impostare l'avvio automatico.\n{e}")
        self.status.set("Configurazione salvata.")
        log("Config saved")

    def _start(self):
        if not self._validate():
            return
        self._apply_cfg()
        save_config(self.cfg)
        self.scheduler.cfg = self.cfg
        self.scheduler.start()
        self.status.set("Scheduler attivo.")
        log("Scheduler started")
        self._refresh_ui()

    def _stop(self):
        self.scheduler.stop()
        self.status.set("Scheduler fermo.")
        log("Scheduler stopped")
        self._refresh_ui()

    def _play_now(self):
        if not self._validate():
            return
        self._apply_cfg()
        save_config(self.cfg)
        self.scheduler.cfg = self.cfg
        self.status.set("Riproduzione in corso...")
        log("Play now")
        self.scheduler.play_now()

    def _refresh_ui(self):
        running = self.scheduler.running()
        if running:
            self.btn_start.state(["disabled"])
            self.btn_stop.state(["!disabled"])
        else:
            self.btn_start.state(["!disabled"])
            self.btn_stop.state(["disabled"])

    def _tick(self):
        if self.scheduler.running() and self.scheduler.next_run_ts:
            remaining = max(0, int(self.scheduler.next_run_ts - time.time()))
            mm, ss = divmod(remaining, 60)
            self.countdown.set(f"Prossima riproduzione tra {mm:02d}:{ss:02d} (mm:ss)")
        else:
            self.countdown.set("")
        self.after(500, self._tick)

    def _pick_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder.get() or os.getcwd())
        if folder:
            self.folder.set(folder)

    def _pick_vlc(self):
        file = filedialog.askopenfilename(title="Seleziona vlc.exe", filetypes=[("VLC", "vlc.exe")])
        if file:
            self.vlc.set(file)

    def _minimize_to_tray(self):
        if self.tray is None:
            return
        self.withdraw()
        self.status.set("Minimizzato in tray.")

    def _restore_from_tray(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_close_clicked(self):
        # Professional UX: close -> minimize to tray
        if self.tray is not None:
            self._minimize_to_tray()
        else:
            self._exit_app()

    def _exit_app(self):
        try:
            self.scheduler.stop()
        except Exception:
            pass
        try:
            if self.tray is not None:
                self.tray.stop()
        except Exception:
            pass
        self.destroy()

def main():
    cfg = load_config()
    ensure_video_folder(cfg.video_folder)
    hint = Path(cfg.video_folder) / "_metti_i_video_qui.txt"
    if not hint.exists():
        hint.write_text("Metti qui i video (.mp4, .mkv, .avi, ...)\n", encoding="utf-8")
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
