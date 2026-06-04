
import argparse,json
from .core import Store,ShadowQueen
from .collectors import load_events,process_snapshot,file_snapshot,network_snapshot
def engine(s): return ShadowQueen(s.load_memory(),s.load_risk())
def handle(s,q,e,quiet=False):
    d=q.classify(e); s.record(e,d)
    if not quiet: print(json.dumps(d,sort_keys=True))
def scan(args):
    s=Store(args.db); q=engine(s)
    for e in load_events(args.input): handle(s,q,e,args.quiet)
    if not args.quiet: print("STATS",json.dumps(s.stats(),sort_keys=True))
def collect(args):
    s=Store(args.db); q=engine(s); events=[]
    if args.process: events+=process_snapshot(args.limit)
    if args.network: events+=network_snapshot(args.limit)
    if args.files: events+=file_snapshot(args.files,args.recursive,args.limit)
    if not events: events+=process_snapshot(args.limit)
    for e in events: handle(s,q,e,args.quiet)
    if not args.quiet: print("STATS",json.dumps(s.stats(),sort_keys=True))
def stats(args):
    s=Store(args.db); d=s.stats()
    if args.recent: d["recent"]=s.recent(args.recent)
    print(json.dumps(d,indent=2,sort_keys=True))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="shadowqueen.db"); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("scan"); a.add_argument("input"); a.add_argument("--quiet",action="store_true"); a.set_defaults(func=scan)
    a=sub.add_parser("collect"); a.add_argument("--process",action="store_true"); a.add_argument("--network",action="store_true"); a.add_argument("--files"); a.add_argument("--recursive",action="store_true"); a.add_argument("--limit",type=int,default=128); a.add_argument("--quiet",action="store_true"); a.set_defaults(func=collect)
    a=sub.add_parser("stats"); a.add_argument("--recent",type=int,default=0); a.set_defaults(func=stats)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
