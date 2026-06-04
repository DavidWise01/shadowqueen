
import argparse,json
from pathlib import Path
from .core import Store,IdentityNode,TrustEdge,FraudEngine
def load(path):
    d=json.loads(Path(path).read_text())
    return [IdentityNode.from_dict(x) for x in d.get("nodes",[])],[TrustEdge.from_dict(x) for x in d.get("edges",[])]
def ingest(args):
    s=Store(args.db); n,e=load(args.input)
    print(json.dumps(FraudEngine(s).load_graph(n,e),indent=2,sort_keys=True))
def stats(args): print(json.dumps(Store(args.db).stats(),indent=2,sort_keys=True))
def findings(args): print(json.dumps(Store(args.db).findings(),indent=2,sort_keys=True))
def verify(args): print(json.dumps(Store(args.db).verify_ledger(),indent=2,sort_keys=True))
def evidence(args): print(json.dumps(Store(args.db).bundle(args.output),indent=2,sort_keys=True))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="fraud_graph.db"); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("ingest"); a.add_argument("input"); a.set_defaults(func=ingest)
    sub.add_parser("stats").set_defaults(func=stats)
    sub.add_parser("findings").set_defaults(func=findings)
    sub.add_parser("verify-ledger").set_defaults(func=verify)
    a=sub.add_parser("evidence"); a.add_argument("output"); a.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
