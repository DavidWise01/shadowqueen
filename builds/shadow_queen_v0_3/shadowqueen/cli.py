
import argparse,json,time
from .core import Event,Store,ShadowQueen
from .collector import load_events,follow_existing_jsonl,follow_live_jsonl,collect_basic_snapshot

def engine(s): return ShadowQueen(s.load_memory(),s.load_risk())

def handle(s,q,e,quiet=False):
    d=q.classify(e); s.record(e,d)
    if not quiet: print(json.dumps(d,sort_keys=True),flush=True)

def scan(args):
    s=Store(args.db); q=engine(s)
    for e in load_events(args.input): handle(s,q,e,args.quiet)
    if not args.quiet: print("STATS",json.dumps(s.stats(),sort_keys=True))
def stream(args):
    s=Store(args.db); q=engine(s)
    source=follow_live_jsonl(args.input,args.poll,args.stop_after) if args.live else follow_existing_jsonl(args.input)
    count=0
    for e in source:
        handle(s,q,e,args.quiet); count+=1
        if args.max_events and count>=args.max_events: break
    if not args.quiet: print("STREAM_STATS",json.dumps(s.stats(),sort_keys=True))
def collect(args):
    s=Store(args.db); q=engine(s)
    end=time.time()+args.duration
    while True:
        for e in collect_basic_snapshot(): handle(s,q,e,args.quiet)
        if args.duration<=0 or time.time()>=end: break
        time.sleep(args.interval)
    if not args.quiet: print("COLLECT_STATS",json.dumps(s.stats(),sort_keys=True))
def demo(args):
    s=Store(args.db); q=engine(s)
    for e in [Event("clean-1","agent_call",time.time(),phase="+1"),Event("shadow-1","agent_call",time.time(),phase="-1",parent_id="clean-1"),Event("peek-1","session",time.time(),layer="L5",features={"payload_read_attempt":True}),Event("bad-wiggle","io",time.time(),wiggle_sequence="++++"),Event("mem-1","memory",time.time(),features={"memory_import":True,"shadow_read_pass":False}),Event("child-shadow","agent_call",time.time(),parent_id="shadow-1",phase="0")]:
        handle(s,q,e,args.quiet)
    print("STATS",json.dumps(s.stats(),sort_keys=True))
def stats(args):
    s=Store(args.db); d=s.stats()
    if args.recent: d["recent"]=s.recent(args.recent)
    print(json.dumps(d,indent=2,sort_keys=True))
def main(argv=None):
    p=argparse.ArgumentParser(prog="shadowqueen"); p.add_argument("--db",default="shadowqueen.db"); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("scan"); a.add_argument("input"); a.add_argument("--quiet",action="store_true"); a.set_defaults(func=scan)
    a=sub.add_parser("stream"); a.add_argument("input"); a.add_argument("--live",action="store_true"); a.add_argument("--poll",type=float,default=0.25); a.add_argument("--stop-after",type=float,default=None); a.add_argument("--max-events",type=int,default=None); a.add_argument("--quiet",action="store_true"); a.set_defaults(func=stream)
    a=sub.add_parser("collect"); a.add_argument("--interval",type=float,default=2.0); a.add_argument("--duration",type=float,default=0.0); a.add_argument("--quiet",action="store_true"); a.set_defaults(func=collect)
    a=sub.add_parser("demo"); a.add_argument("--quiet",action="store_true"); a.set_defaults(func=demo)
    a=sub.add_parser("stats"); a.add_argument("--recent",type=int,default=0); a.set_defaults(func=stats)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
