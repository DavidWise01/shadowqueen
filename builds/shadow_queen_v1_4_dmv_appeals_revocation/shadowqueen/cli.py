
import argparse,json
from pathlib import Path
from .core import Store,ShadowQueenDMV,ObserverEvent
def load(path):
    data=json.loads(Path(path).read_text())
    return [ObserverEvent.from_dict(x) for x in (data if isinstance(data,list) else [data])]
def process(args):
    s=Store(args.db); d=ShadowQueenDMV(s,args.quorum).process(load(args.input))
    if not args.quiet: print(json.dumps(d,indent=2,sort_keys=True)); print("STATS",json.dumps(s.stats(),sort_keys=True))
def appeal(args): print(json.dumps(Store(args.db).create_appeal(args.appeal_id,args.person_id,args.reason),indent=2,sort_keys=True))
def review(args):
    s=Store(args.db); print(json.dumps(ShadowQueenDMV(s,args.quorum).appeal_review(args.appeal_id,args.person_id,load(args.input)),indent=2,sort_keys=True))
def revoke(args): print(json.dumps(Store(args.db).set_status(args.person_id,"revoked",args.reason),indent=2,sort_keys=True))
def stats(args): print(json.dumps(Store(args.db).stats(),indent=2,sort_keys=True))
def registry(args): print(json.dumps(Store(args.db).registry(),indent=2,sort_keys=True))
def appeals(args): print(json.dumps(Store(args.db).appeals(),indent=2,sort_keys=True))
def evidence(args): print(json.dumps(Store(args.db).evidence_bundle(args.output),indent=2,sort_keys=True))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="shadowqueen_dmv.db"); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("process"); a.add_argument("input"); a.add_argument("--quorum",type=int,default=3); a.add_argument("--quiet",action="store_true"); a.set_defaults(func=process)
    a=sub.add_parser("appeal"); a.add_argument("appeal_id"); a.add_argument("person_id"); a.add_argument("reason"); a.set_defaults(func=appeal)
    a=sub.add_parser("review"); a.add_argument("appeal_id"); a.add_argument("person_id"); a.add_argument("input"); a.add_argument("--quorum",type=int,default=3); a.set_defaults(func=review)
    a=sub.add_parser("revoke"); a.add_argument("person_id"); a.add_argument("reason"); a.set_defaults(func=revoke)
    sub.add_parser("stats").set_defaults(func=stats)
    sub.add_parser("registry").set_defaults(func=registry)
    sub.add_parser("appeals").set_defaults(func=appeals)
    a=sub.add_parser("evidence"); a.add_argument("output"); a.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
