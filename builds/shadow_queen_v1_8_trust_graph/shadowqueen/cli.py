
import argparse,json
from pathlib import Path
from .core import Store,IdentityProof,TrustEdge,TrustGraph

def load_graph(path):
    data=json.loads(Path(path).read_text())
    nodes=[IdentityProof.from_dict(x) for x in data.get("nodes",[])]
    edges=[TrustEdge.from_dict(x) for x in data.get("edges",[])]
    return nodes,edges

def ingest(args):
    s=Store(args.db); nodes,edges=load_graph(args.input)
    print(json.dumps(TrustGraph(s).ingest(nodes,edges),indent=2,sort_keys=True))

def stats(args): print(json.dumps(Store(args.db).stats(),indent=2,sort_keys=True))
def nodes(args): print(json.dumps(Store(args.db).nodes(),indent=2,sort_keys=True))
def edges(args): print(json.dumps(Store(args.db).edges(),indent=2,sort_keys=True))
def findings(args): print(json.dumps(Store(args.db).findings(),indent=2,sort_keys=True))
def lineage(args): print(json.dumps(TrustGraph(Store(args.db)).lineage(args.entity_id),indent=2,sort_keys=True))
def verify(args): print(json.dumps(Store(args.db).verify_ledger(),indent=2,sort_keys=True))
def evidence(args): print(json.dumps(Store(args.db).bundle(args.output),indent=2,sort_keys=True))

def main(argv=None):
    p=argparse.ArgumentParser(prog="shadowqueen-trust-graph")
    p.add_argument("--db",default="trust_graph.db")
    sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("ingest"); a.add_argument("input"); a.set_defaults(func=ingest)
    sub.add_parser("stats").set_defaults(func=stats)
    sub.add_parser("nodes").set_defaults(func=nodes)
    sub.add_parser("edges").set_defaults(func=edges)
    sub.add_parser("findings").set_defaults(func=findings)
    a=sub.add_parser("lineage"); a.add_argument("entity_id"); a.set_defaults(func=lineage)
    sub.add_parser("verify-ledger").set_defaults(func=verify)
    a=sub.add_parser("evidence"); a.add_argument("output"); a.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)

if __name__=="__main__": raise SystemExit(main())
