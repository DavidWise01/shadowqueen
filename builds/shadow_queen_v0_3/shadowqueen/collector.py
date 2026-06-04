
import json,time,os
from pathlib import Path
from .core import Event

def load_events(path):
    text=Path(path).read_text()
    if str(path).endswith(".jsonl"):
        for line in text.splitlines():
            if line.strip():
                yield Event.from_dict(json.loads(line))
    else:
        data=json.loads(text)
        for item in (data if isinstance(data,list) else [data]):
            yield Event.from_dict(item)

def follow_existing_jsonl(path):
    """Read currently available JSONL lines; useful for tests and batch stream catch-up."""
    yield from load_events(path)

def follow_live_jsonl(path,poll=0.25,stop_after=None):
    """Follow appended JSONL lines until stop_after seconds elapse."""
    p=Path(path); p.touch(exist_ok=True)
    start=time.time()
    with p.open("r") as f:
        f.seek(0,os.SEEK_END)
        while True:
            line=f.readline()
            if line:
                yield Event.from_dict(json.loads(line))
            else:
                if stop_after is not None and time.time()-start>=stop_after:
                    break
                time.sleep(poll)

def collect_basic_snapshot():
    return [Event("local-host","host_snapshot",time.time(),features={"collector":"basic"})]
