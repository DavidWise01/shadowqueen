
import argparse,json
from pathlib import Path
from .core import Event,Store,ShadowQueen
def load(path):
    data=json.loads(Path(path).read_text())
    for item in (data if isinstance(data,list) else [data]): yield Event.from_dict(item)
def scan(args):
    s=Store(args.db); q=ShadowQueen()
    for e in load(args.input):
        d=q.classify(e); a=q.alerts.alert_for(e,d); s.record(e,d,a)
        if not args.quiet: print(json.dumps({"decision":d,"alert":a},sort_keys=True))
    if not args.quiet: print("STATS",json.dumps(s.stats(),sort_keys=True))
def stats(args):
    print(json.dumps(Store(args.db).stats(),indent=2,sort_keys=True))
def alerts(args):
    print(json.dumps(Store(args.db).alerts(args.limit,args.severity),indent=2,sort_keys=True))
def report(args):
    data=Store(args.db).export_report(args.output)
    print(json.dumps({"wrote":args.output,"alerts":len(data["alerts"]),"stats":data["stats"]},indent=2,sort_keys=True))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="shadowqueen.db"); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("scan"); a.add_argument("input"); a.add_argument("--quiet",action="store_true"); a.set_defaults(func=scan)
    sub.add_parser("stats").set_defaults(func=stats)
    a=sub.add_parser("alerts"); a.add_argument("--limit",type=int,default=50); a.add_argument("--severity"); a.set_defaults(func=alerts)
    a=sub.add_parser("report"); a.add_argument("output"); a.set_defaults(func=report)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
