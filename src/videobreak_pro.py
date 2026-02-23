
# VideoBreak Pro v4
# Fullscreen + Always On Top VLC
# Audio mute all except VLC (pycaw)
# Working countdown timer + proper restart

import os, json, time, threading, subprocess, ctypes
from pathlib import Path
from dataclasses import dataclass, asdict
import tkinter as tk
from tkinter import ttk, filedialog
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume

APP_NAME = "VideoBreak Pro"
ORG = "VideoBreakPro"
VIDEO_EXTS = (".mp4",".mkv",".avi",".mov",".wmv",".m4v")

def appdata():
    p = Path(os.environ["APPDATA"]) / ORG
    p.mkdir(parents=True, exist_ok=True)
    return p

CFG = appdata()/"config.json"
STATE = appdata()/"state.json"

user32 = ctypes.windll.user32
HWND_TOPMOST = -1
SWP = 0x1 | 0x2 | 0x40

def force_topmost(pid):
    def enum(hwnd, _):
        p = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(hwnd):
            user32.SetWindowPos(hwnd, HWND_TOPMOST,0,0,0,0,SWP)
        return True
    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_int,ctypes.c_int)(enum),0)

def mute_all_except(vlc_pid):
    sessions = AudioUtilities.GetAllSessions()
    state = {}
    for s in sessions:
        if not s.Process:
            continue
        vol = s._ctl.QueryInterface(ISimpleAudioVolume)
        state[s.Process.pid] = vol.GetMute()
        if s.Process.pid != vlc_pid:
            vol.SetMute(1, None)
    return state

def restore_audio(state):
    sessions = AudioUtilities.GetAllSessions()
    for s in sessions:
        if not s.Process:
            continue
        pid = s.Process.pid
        if pid in state:
            vol = s._ctl.QueryInterface(ISimpleAudioVolume)
            vol.SetMute(state[pid], None)

@dataclass
class Config:
    interval:int = 40
    count:int = 1
    folder:str = str(appdata()/"videos")
    vlc:str = r"C:\Program Files\VideoLAN\VLC\vlc.exe"
    videos:dict = None

def load_cfg():
    default = Config(videos={})
    if not CFG.exists():
        return default
    try:
        d = json.loads(CFG.read_text())
        if "interval_minutes" in d:
            d["interval"] = d.pop("interval_minutes")
        if "count_per_run" in d:
            d["count"] = d.pop("count_per_run")
        if "video_folder" in d:
            d["folder"] = d.pop("video_folder")
        if "vlc_path" in d:
            d["vlc"] = d.pop("vlc_path")
        if d.get("videos") is None:
            d["videos"] = {}
        return Config(**{**asdict(default), **d})
    except:
        return default

def save_cfg(c):
    CFG.write_text(json.dumps(asdict(c),indent=4))

def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"idx":0}

def save_state(s):
    STATE.write_text(json.dumps(s))

def scan(folder):
    return sorted([f for f in Path(folder).iterdir() if f.suffix.lower() in VIDEO_EXTS])

def build_order(cfg):
    items=[]
    for f in scan(cfg.folder):
        meta=cfg.videos.get(f.name,{"on":True,"prio":1})
        if meta["on"]:
            items.append((meta["prio"],f))
    return [x[1] for x in sorted(items,key=lambda x:(x[0],x[1].name))]

def next_batch(cfg,state):
    order=build_order(cfg)
    if not order:
        return []
    i=state["idx"]
    batch=[order[(i+j)%len(order)] for j in range(cfg.count)]
    state["idx"]=(i+cfg.count)%len(order)
    save_state(state)
    return batch

def play(cfg, status_cb):
    batch=next_batch(cfg,load_state())
    if not batch:
        return
    status_cb("Riproduzione in corso…")
    pl=appdata()/"playlist.m3u"
    pl.write_text("\n".join(str(p) for p in batch))
    p=subprocess.Popen([cfg.vlc,"--fullscreen","--video-on-top","--play-and-exit",str(pl)])
    for _ in range(8):
        force_topmost(p.pid)
        time.sleep(0.3)
    audio_state = mute_all_except(p.pid)
    p.wait()
    restore_audio(audio_state)
    status_cb("Attesa…")

class Scheduler:
    def __init__(self,cfg,ui):
        self.cfg=cfg
        self.ui=ui
        self.running=False
        self.next_run=None
        self.thread=None

    def start(self):
        self.running=True
        self.next_run=time.time()+self.cfg.interval*60
        if not self.thread or not self.thread.is_alive():
            self.thread=threading.Thread(target=self.loop,daemon=True)
            self.thread.start()

    def stop(self):
        self.running=False
        self.next_run=None

    def loop(self):
        while self.running:
            if time.time()>=self.next_run:
                play(self.cfg,self.ui.set_status)
                self.next_run=time.time()+self.cfg.interval*60
            time.sleep(0.5)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg=load_cfg()
        self.title(APP_NAME)
        self.geometry("760x480")
        self.scheduler=Scheduler(self.cfg,self)
        self.build()
        self.after(500,self.update_timer)

    def build(self):
        f=ttk.Frame(self,padding=12); f.pack(fill="both",expand=True)
        self.timer_lbl=ttk.Label(f,text="--:--",font=("Segoe UI",20))
        self.timer_lbl.grid(row=0,column=0,columnspan=4,pady=6)

        ttk.Label(f,text="Intervallo (min)").grid(row=1,column=0)
        self.interval=tk.IntVar(value=self.cfg.interval)
        ttk.Spinbox(f,from_=1,to=1440,textvariable=self.interval,width=8).grid(row=1,column=1)

        ttk.Label(f,text="Video per ciclo").grid(row=1,column=2)
        self.count=tk.IntVar(value=self.cfg.count)
        ttk.Spinbox(f,from_=1,to=20,textvariable=self.count,width=6).grid(row=1,column=3)

        ttk.Label(f,text="Cartella video").grid(row=2,column=0,pady=10)
        self.folder=tk.StringVar(value=self.cfg.folder)
        ttk.Entry(f,textvariable=self.folder,width=45).grid(row=2,column=1,columnspan=2)
        ttk.Button(f,text="Sfoglia",command=self.pick_folder).grid(row=2,column=3)

        self.status=ttk.Label(f,text="Pronto",foreground="green")
        self.status.grid(row=3,column=0,columnspan=4)

        ttk.Button(f,text="Avvia / Riavvia",command=self.start).grid(row=4,column=0,pady=10)
        ttk.Button(f,text="Stop",command=self.stop).grid(row=4,column=1)

    def set_status(self,msg):
        self.status.config(text=msg)

    def update_timer(self):
        if self.scheduler.running and self.scheduler.next_run:
            rem=int(self.scheduler.next_run-time.time())
            if rem<0: rem=0
            self.timer_lbl.config(text=f"{rem//60:02d}:{rem%60:02d}")
        else:
            self.timer_lbl.config(text="--:--")
        self.after(500,self.update_timer)

    def start(self):
        self.cfg.interval=self.interval.get()
        self.cfg.count=self.count.get()
        self.cfg.folder=self.folder.get()
        save_cfg(self.cfg)
        self.scheduler.start()
        self.set_status("Attesa…")

    def stop(self):
        self.scheduler.stop()
        self.set_status("Fermato")

    def pick_folder(self):
        d=filedialog.askdirectory()
        if d:
            self.folder.set(d)

if __name__=="__main__":
    App().mainloop()
