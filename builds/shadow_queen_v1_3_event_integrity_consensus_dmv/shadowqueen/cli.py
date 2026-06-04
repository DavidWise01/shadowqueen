
import argparse,json
from pathlib import Path
from .core import Store,ShadowQueenDMV,ObserverEvent
def load(path):
    data=json.loads(Path(path).read_text())
    return [ObserverEvent.from_dict(x) for x in (data if isinstance(data,list) else [data])]
def process(args):
    s=Store(args.db); dmv=ShadowQueenDMV(s,args.quorum); decisions=dmv.process(load(args.input))
    if not args.quiet:
        print(json.dumps(decisions,indent=2,sort_keys=True)); print("STATS",json.dumps(s.stats(),sort_keys=True))
def stats(args): print(json.dumps(Store(args.db).stats(),indent=2,sort_keys=True))
def registry(args): print(json.dumps(Store(args.db).registry(),indent=2,sort_keys=True))
def main(argv=None):
    p=argparse.ArgumentParser(prog="shadowqueen-dmv"); p.add_argument("--db",default="shadowqueen_dmv.db"); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("process"); a.add_argument("input"); a.add_argument("--quorum",type=int,default=3); a.add_argument("--quiet",action="store_true"); a.set_defaults(func=process)
    sub.add_parser("stats").set_defaults(func=stats)
    sub.add_parser("registry").set_defaults(func=registry)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
