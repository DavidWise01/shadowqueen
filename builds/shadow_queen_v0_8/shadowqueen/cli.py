
import argparse,json
from pathlib import Path
from .core import Event,Store,ShadowQueen
def load(path):
    data=json.loads(Path(path).read_text())
    for item in (data if isinstance(data,list) else [data]): yield Event.from_dict(item)
def scan(args):
    s=Store(args.db); q=ShadowQueen(s)
    for e in load(args.input):
        d=q.classify(e,learn_mode=args.learn); s.record(e,d,learn=args.learn)
        if not args.quiet: print(json.dumps(d,sort_keys=True))
    if not args.quiet: print("STATS",json.dumps(s.stats(),sort_keys=True))
def stats(args): print(json.dumps(Store(args.db).stats(),indent=2,sort_keys=True))
def baselines(args): print(json.dumps(Store(args.db).baselines(args.limit),indent=2,sort_keys=True))
def alerts(args): print(json.dumps(Store(args.db).alerts(args.limit),indent=2,sort_keys=True))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="shadowqueen.db"); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("scan"); a.add_argument("input"); a.add_argument("--learn",action="store_true"); a.add_argument("--quiet",action="store_true"); a.set_defaults(func=scan)
    sub.add_parser("stats").set_defaults(func=stats)
    a=sub.add_parser("baselines"); a.add_argument("--limit",type=int,default=50); a.set_defaults(func=baselines)
    a=sub.add_parser("alerts"); a.add_argument("--limit",type=int,default=50); a.set_defaults(func=alerts)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
