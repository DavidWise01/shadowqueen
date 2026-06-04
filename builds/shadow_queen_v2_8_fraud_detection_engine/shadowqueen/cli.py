import argparse,json
from .core import Store,FraudEngine

def seed_demo(s):
    p1=s.add_node("person","root",{"name":"Root User","dob":"1981-06-21","domain":"carbon"})
    p2=s.add_node("person","root-copy",{"name":"Root User","dob":"1981-06-21","domain":"carbon"})
    p3=s.add_node("person","synthetic",{"name":"","domain":"carbon"})
    addr=s.add_node("address","addr-1",{"state":"MN"})
    for p in [p1,p2,p3]: s.add_edge(p,addr,"resides_at")
    for i in range(5):
        c=s.add_node("credential",f"C-{i}",{"type":"license"}); s.add_edge(p1,c,"holds")
    s.add_edge(p2,p2,"weird_self_loop")

def demo(args):
    s=Store(args.db,args.office); seed_demo(s); print(json.dumps(FraudEngine(s).analyze(),indent=2))
def analyze(args): print(json.dumps(FraudEngine(Store(args.db,args.office)).analyze(),indent=2))
def scores(args): print(json.dumps(Store(args.db,args.office).risk_scores(),indent=2))
def findings(args): print(json.dumps(Store(args.db,args.office).findings(),indent=2))
def audit(args): print(json.dumps(Store(args.db,args.office).audit(args.auditor),indent=2))
def stats(args): print(json.dumps(Store(args.db,args.office).stats(),indent=2))
def verify(args): print(json.dumps(Store(args.db,args.office).verify_ledger(),indent=2))
def evidence(args): print(json.dumps(Store(args.db,args.office).bundle(args.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="fraud.db"); p.add_argument("--office",default="north")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo); sub.add_parser("analyze").set_defaults(func=analyze); sub.add_parser("scores").set_defaults(func=scores); sub.add_parser("findings").set_defaults(func=findings)
    a=sub.add_parser("audit"); a.add_argument("--auditor",default="auditor"); a.set_defaults(func=audit)
    sub.add_parser("stats").set_defaults(func=stats); sub.add_parser("verify-ledger").set_defaults(func=verify)
    a=sub.add_parser("evidence"); a.add_argument("output"); a.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
