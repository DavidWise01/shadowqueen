
import argparse,json
from .core import Store,PeerNode,P2PRuntime,P2PMessage
def register(args):
    s=Store(args.db,args.node); P2PRuntime(s).add_peer(PeerNode(args.peer,args.type,args.trust,args.status)); print(json.dumps(s.nodes(),indent=2,sort_keys=True))
def send(args):
    s=Store(args.db,args.node); msg=P2PRuntime(s).send(args.to,args.kind,json.loads(args.payload)); print(json.dumps(msg.__dict__,indent=2,sort_keys=True))
def receive(args):
    s=Store(args.db,args.node); print(json.dumps(s.receive(P2PMessage.from_dict(json.loads(args.message))),indent=2,sort_keys=True))
def stats(args): print(json.dumps(Store(args.db,args.node).stats(),indent=2,sort_keys=True))
def nodes(args): print(json.dumps(Store(args.db,args.node).nodes(),indent=2,sort_keys=True))
def inbox(args): print(json.dumps(Store(args.db,args.node).inbox(),indent=2,sort_keys=True))
def outbox(args): print(json.dumps(Store(args.db,args.node).outbox(),indent=2,sort_keys=True))
def conflicts(args): print(json.dumps(Store(args.db,args.node).conflicts(),indent=2,sort_keys=True))
def verify(args): print(json.dumps(Store(args.db,args.node).verify_ledger(),indent=2,sort_keys=True))
def trust(args): print(json.dumps(P2PRuntime(Store(args.db,args.node)).federated_trust_score(),indent=2,sort_keys=True))
def evidence(args): print(json.dumps(Store(args.db,args.node).bundle(args.output),indent=2,sort_keys=True))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="p2p.db"); p.add_argument("--node",default="queen"); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("register"); a.add_argument("peer"); a.add_argument("--type",default="office"); a.add_argument("--trust",type=float,default=.5); a.add_argument("--status",default="active"); a.set_defaults(func=register)
    a=sub.add_parser("send"); a.add_argument("to"); a.add_argument("kind"); a.add_argument("payload"); a.set_defaults(func=send)
    a=sub.add_parser("receive"); a.add_argument("message"); a.set_defaults(func=receive)
    for name,func in [("stats",stats),("nodes",nodes),("inbox",inbox),("outbox",outbox),("conflicts",conflicts),("verify-ledger",verify),("trust-score",trust)]:
        sub.add_parser(name).set_defaults(func=func)
    a=sub.add_parser("evidence"); a.add_argument("output"); a.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
