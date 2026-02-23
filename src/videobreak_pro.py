
# VideoBreak Pro v3
# Fullscreen + Always On Top VLC
# Priority rotation playlist
# Stable NO-TRAY architecture

import os, json, time, threading, subprocess, ctypes
from pathlib import Path
from dataclasses import dataclass, asdict
import tkinter as tk
from tkinter import ttk, filedialog

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

@dataclass
class Config:
    interval:int = 40
    count:int = 1
    folder:str = str(appdata()/"videos")
    vlc:str = r"C:\Program Files\VideoLAN\VLC\vlc.exe"
    videos:dict = None

def load_cfg():
    if CFG.exists():
        d=json.loads(CFG.read_text())
        return Config(**d)
    return Config(videos={})

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
    if not order: return []
    i=state["idx"]
    batch=[order[(i+j)%len(order)] for j in range(cfg.count)]
    state["idx"]=(i+cfg.count)%len(order)
    save_state(state)
    return batch

def play(cfg):
    batch=next_batch(cfg,load_state())
    if not batch: return
    pl=appdata()/"playlist.m3u"
    pl.write_text("\n".join(str(p) for p in batch))
    p=subprocess.Popen([cfg.vlc,"--fullscreen","--video-on-top","--play-and-exit",str(pl)])
    for _ in range(10):
        force_topmost(p.pid)
        time.sleep(0.4)
    p.wait()

class Scheduler:
    def __init__(self,cfg,cb):
        self.cfg=cfg; self.cb=cb; self.stop=False; self.t=None
    def start(self):
        if self.t and self.t.is_alive(): return
        self.stop=False
        self.t=threading.Thread(target=self.loop,daemon=True)
        self.t.start()
    def loop(self):
        while not self.stop:
            self.cb("Attesa...")
            time.sleep(self.cfg.interval*60)
            self.cb("Riproduzione...")
            play(self.cfg)
    def halt(self):
        self.stop=True

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg=load_cfg()
        self.title(APP_NAME)
        self.geometry("720x440")
        self.scheduler=Scheduler(self.cfg,self.set_status)
        self.build()
    def build(self):
        f=ttk.Frame(self,padding=12); f.pack(fill="both",expand=True)
        ttk.Label(f,text="Intervallo (minuti)").grid(row=0,column=0)
        self.interval=tk.IntVar(value=self.cfg.interval)
        ttk.Spinbox(f,from_=1,to=1440,textvariable=self.interval,width=8).grid(row=0,column=1)
        ttk.Label(f,text="Video per ciclo").grid(row=0,column=2)
        self.count=tk.IntVar(value=self.cfg.count)
        ttk.Spinbox(f,from_=1,to=20,textvariable=self.count,width=6).grid(row=0,column=3)

        ttk.Label(f,text="Cartella video").grid(row=1,column=0,pady=10)
        self.folder=tk.StringVar(value=self.cfg.folder)
        ttk.Entry(f,textvariable=self.folder,width=45).grid(row=1,column=1,columnspan=2)
        ttk.Button(f,text="Sfoglia",command=self.pick_folder).grid(row=1,column=3)

        cols=("on","name","prio")
        self.tree=ttk.Treeview(f,columns=cols,show="headings",height=10)
        for c,t in zip(cols,["On","Video","Priorità"]):
            self.tree.heading(c,text=t)
        self.tree.grid(row=2,column=0,columnspan=4,sticky="nsew")

        ttk.Button(f,text="Avvia",command=self.start).grid(row=3,column=0,pady=10)
        ttk.Button(f,text="Stop",command=self.stop).grid(row=3,column=1)
        self.status=ttk.Label(f,text="Pronto")
        self.status.grid(row=3,column=2,columnspan=2)

        f.columnconfigure(2,weight=1)
        self.refresh_videos()

    def refresh_videos(self):
        self.tree.delete(*self.tree.get_children())
        Path(self.folder.get()).mkdir(exist_ok=True)
        self.cfg.videos = self.cfg.videos or {}
        for v in scan(self.folder.get()):
            meta=self.cfg.videos.get(v.name,{"on":True,"prio":1})
            self.tree.insert("", "end", values=(meta["on"],v.name,meta["prio"]))

    def pick_folder(self):
        d=filedialog.askdirectory()
        if d:
            self.folder.set(d)
            self.refresh_videos()

    def start(self):
        self.apply()
        self.scheduler.start()

    def stop(self):
        self.scheduler.halt()
        self.set_status("Fermato")

    def apply(self):
        self.cfg.interval=self.interval.get()
        self.cfg.count=self.count.get()
        self.cfg.folder=self.folder.get()
        save_cfg(self.cfg)

    def set_status(self,msg):
        self.status.config(text=msg)

if __name__=="__main__":
    App().mainloop()
