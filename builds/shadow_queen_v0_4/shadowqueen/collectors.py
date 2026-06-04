
import json,time,socket,hashlib
from pathlib import Path
from .core import Event
def load_events(path):
    text=Path(path).read_text()
    data=[json.loads(x) for x in text.splitlines() if x.strip()] if str(path).endswith(".jsonl") else json.loads(text)
    for item in (data if isinstance(data,list) else [data]): yield Event.from_dict(item)
def process_snapshot(limit=128):
    out=[]; proc=Path("/proc"); now=time.time()
    if proc.exists():
        for p in list(proc.iterdir())[:limit]:
            if p.name.isdigit():
                try: name=(p/"comm").read_text(errors="ignore").strip()
                except Exception: name="unknown"
                out.append(Event(f"pid:{p.name}","process_snapshot",now,features={"pid":int(p.name),"process_name":name}))
    else: out.append(Event("host:local","process_snapshot",now))
    return out
def file_snapshot(path,recursive=False,limit=512):
    root=Path(path); now=time.time(); out=[]; it=root.rglob("*") if recursive and root.is_dir() else root.glob("*") if root.is_dir() else [root]
    for i,p in enumerate(it):
        if i>=limit: break
        try:
            st=p.stat(); h=""
            if p.is_file() and st.st_size<=1048576: h=hashlib.sha256(p.read_bytes()).hexdigest()
            out.append(Event(f"file:{p}","file_change",now,features={"path":str(p),"size":st.st_size,"mtime":st.st_mtime,"extension":p.suffix,"sha256":h}))
        except Exception as exc: out.append(Event(f"file:{p}","file_error",now,features={"error":str(exc)}))
    return out
def network_snapshot(limit=512):
    out=[]; now=time.time(); tcp=Path("/proc/net/tcp")
    def parse(a):
        h,p=a.split(":"); return socket.inet_ntoa(bytes.fromhex(h)[::-1]),int(p,16)
    if tcp.exists():
        for line in tcp.read_text().splitlines()[1:limit+1]:
            parts=line.split()
            try: lip,lp=parse(parts[1]); rip,rp=parse(parts[2])
            except Exception: continue
            out.append(Event(f"net:{lip}:{lp}->{rip}:{rp}","network_connection",now,features={"local_ip":lip,"local_port":lp,"remote_ip":rip,"remote_port":rp,"tcp_state":parts[3]}))
    else: out.append(Event("net:unavailable","network_snapshot",now,features={"available":False}))
    return out
