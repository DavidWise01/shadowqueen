
import argparse, json, time
from pathlib import Path
from .core import Event, Store, ShadowQueen

def load_events(path):
    text = Path(path).read_text(encoding="utf-8")
    if str(path).endswith(".jsonl"):
        for line in text.splitlines():
            if line.strip(): yield Event.from_dict(json.loads(line))
    else:
        data = json.loads(text)
        for item in (data if isinstance(data, list) else [data]):
            yield Event.from_dict(item)

def engine(store):
    return ShadowQueen(store.load_memory(), store.load_risk())

def cmd_scan(args):
    s = Store(args.db); q = engine(s)
    for e in load_events(args.input):
        d = q.classify(e); s.record(e,d); print(json.dumps(d, sort_keys=True))
    print("STATS", json.dumps(s.stats(), sort_keys=True))
    return 0

def cmd_demo(args):
    events = [
        Event("clean-1","agent_call",time.time(),phase="+1"),
        Event("shadow-1","agent_call",time.time(),phase="-1",parent_id="clean-1"),
        Event("peek-1","session",time.time(),layer="L5",features={"payload_read_attempt":True}),
        Event("bad-wiggle","io",time.time(),wiggle_sequence="++++"),
        Event("mem-1","memory",time.time(),features={"memory_import":True,"shadow_read_pass":False}),
        Event("child-shadow","agent_call",time.time(),parent_id="shadow-1",phase="0"),
    ]
    s=Store(args.db); q=engine(s)
    for e in events:
        d=q.classify(e); s.record(e,d); print(json.dumps(d, sort_keys=True))
    print("STATS", json.dumps(s.stats(), sort_keys=True))
    return 0

def cmd_collect(args):
    s=Store(args.db); q=engine(s)
    e=Event("local-host","host_snapshot",time.time(),phase="0",features={"collector":"basic"})
    d=q.classify(e); s.record(e,d); print(json.dumps(s.stats(), sort_keys=True)); return 0

def cmd_stats(args):
    print(json.dumps(Store(args.db).stats(), indent=2, sort_keys=True)); return 0

def main(argv=None):
    p=argparse.ArgumentParser(prog="shadowqueen")
    p.add_argument("--db", default="shadowqueen.db")
    sub=p.add_subparsers(dest="cmd", required=True)
    a=sub.add_parser("scan"); a.add_argument("input"); a.set_defaults(func=cmd_scan)
    sub.add_parser("demo").set_defaults(func=cmd_demo)
    sub.add_parser("collect").set_defaults(func=cmd_collect)
    sub.add_parser("stats").set_defaults(func=cmd_stats)
    args=p.parse_args(argv); return args.func(args)

if __name__=="__main__":
    raise SystemExit(main())
