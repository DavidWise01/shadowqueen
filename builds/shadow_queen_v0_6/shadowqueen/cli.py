
import argparse,json
from pathlib import Path
from .core import Event, Store, ShadowQueen
def load(path):
    data=json.loads(Path(path).read_text())
    for item in (data if isinstance(data,list) else [data]): yield Event.from_dict(item)
def scan(args):
    s=Store(args.db); q=ShadowQueen()
    for e in load(args.input):
        d=q.classify(e); s.record(e,d)
        if not args.quiet: print(json.dumps(d,sort_keys=True))
    if not args.quiet: print("STATS",json.dumps(s.stats(),sort_keys=True))
def stats(args):
    s=Store(args.db); d=s.stats()
    if args.recent: d["recent"]=s.recent(args.recent)
    print(json.dumps(d,indent=2,sort_keys=True))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="shadowqueen.db"); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("scan"); a.add_argument("input"); a.add_argument("--quiet",action="store_true"); a.set_defaults(func=scan)
    a=sub.add_parser("stats"); a.add_argument("--recent",type=int,default=0); a.set_defaults(func=stats)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
