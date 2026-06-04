
import argparse,json
from .core import Store,PeerNode,P2PRuntime
def register(args):
    s=Store(args.db,args.node); P2PRuntime(s).add_peer(PeerNode(args.peer,args.type,args.trust,args.status)); print(json.dumps(s.nodes(),indent=2))
def send(args):
    msg=P2PRuntime(Store(args.db,args.node)).send(args.to,args.kind,json.loads(args.payload),args.ttl); print(json.dumps(msg.__dict__,indent=2))
def stats(args): print(json.dumps(Store(args.db,args.node).stats(),indent=2))
def conflicts(args): print(json.dumps(Store(args.db,args.node).conflicts(),indent=2))
def verify(args): print(json.dumps(Store(args.db,args.node).verify_ledger(),indent=2))
def evidence(args): print(json.dumps(Store(args.db,args.node).bundle(args.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="p2p.db"); p.add_argument("--node",default="queen"); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("register"); a.add_argument("peer"); a.add_argument("--type",default="office"); a.add_argument("--trust",type=float,default=.5); a.add_argument("--status",default="active"); a.set_defaults(func=register)
    a=sub.add_parser("send"); a.add_argument("to"); a.add_argument("kind"); a.add_argument("payload"); a.add_argument("--ttl",type=int,default=300); a.set_defaults(func=send)
    sub.add_parser("stats").set_defaults(func=stats); sub.add_parser("conflicts").set_defaults(func=conflicts); sub.add_parser("verify-ledger").set_defaults(func=verify)
    a=sub.add_parser("evidence"); a.add_argument("output"); a.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
