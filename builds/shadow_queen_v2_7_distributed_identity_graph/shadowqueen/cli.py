
import argparse,json
from .core import Store
def identity(args):
    print(json.dumps({"event_id":Store(args.db,args.office).add_node("person",args.key,json.loads(args.attrs),args.targets.split(",") if args.targets else [])},indent=2))
def link(args):
    print(json.dumps({"event_id":Store(args.db,args.office).add_edge(args.src,args.type,args.key,args.rel,json.loads(args.attrs),args.targets.split(",") if args.targets else [])},indent=2))
def nodes(args): print(json.dumps(Store(args.db,args.office).nodes(),indent=2))
def edges(args): print(json.dumps(Store(args.db,args.office).edges(),indent=2))
def scan(args): print(json.dumps(Store(args.db,args.office).duplicate_scan(),indent=2))
def stats(args): print(json.dumps(Store(args.db,args.office).stats(),indent=2))
def verify(args): print(json.dumps(Store(args.db,args.office).verify_ledger(),indent=2))
def evidence(args): print(json.dumps(Store(args.db,args.office).bundle(args.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="graph.db"); p.add_argument("--office",default="north")
    sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("identity"); a.add_argument("key"); a.add_argument("attrs"); a.add_argument("--targets",default=""); a.set_defaults(func=identity)
    a=sub.add_parser("link"); a.add_argument("src"); a.add_argument("type"); a.add_argument("key"); a.add_argument("rel"); a.add_argument("attrs"); a.add_argument("--targets",default=""); a.set_defaults(func=link)
    sub.add_parser("nodes").set_defaults(func=nodes); sub.add_parser("edges").set_defaults(func=edges); sub.add_parser("duplicate-scan").set_defaults(func=scan)
    sub.add_parser("stats").set_defaults(func=stats); sub.add_parser("verify-ledger").set_defaults(func=verify)
    a=sub.add_parser("evidence"); a.add_argument("output"); a.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
