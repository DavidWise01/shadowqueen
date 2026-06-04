
import argparse,json
from .core import TrustStore, seed_demo

def demo(args):
    s=TrustStore(args.db,args.office); seed_demo(s); print(json.dumps(s.compute_all(),indent=2))
def subject(args): print(json.dumps(TrustStore(args.db,args.office).add_subject(args.subject,args.type,args.base,json.loads(args.metadata)),indent=2))
def signal(args): print(json.dumps(TrustStore(args.db,args.office).add_signal(args.subject,args.signal,args.source,args.weight,args.confidence,json.loads(args.details)),indent=2))
def compute(args): print(json.dumps(TrustStore(args.db,args.office).compute_all(),indent=2))
def scores(args): print(json.dumps(TrustStore(args.db,args.office).scores(),indent=2))
def audit(args): print(json.dumps(TrustStore(args.db,args.office).audit(args.auditor),indent=2))
def stats(args): print(json.dumps(TrustStore(args.db,args.office).stats(),indent=2))
def verify(args): print(json.dumps(TrustStore(args.db,args.office).verify_ledger(),indent=2))
def evidence(args): print(json.dumps(TrustStore(args.db,args.office).bundle(args.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument('--db',default='trust.db'); p.add_argument('--office',default='north')
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('demo').set_defaults(func=demo)
    a=sub.add_parser('subject'); a.add_argument('subject'); a.add_argument('type'); a.add_argument('--base',type=float,default=50); a.add_argument('--metadata',default='{}'); a.set_defaults(func=subject)
    a=sub.add_parser('signal'); a.add_argument('subject'); a.add_argument('signal'); a.add_argument('--source',default='local'); a.add_argument('--weight',type=float,default=0); a.add_argument('--confidence',type=float,default=1); a.add_argument('--details',default='{}'); a.set_defaults(func=signal)
    sub.add_parser('compute').set_defaults(func=compute); sub.add_parser('scores').set_defaults(func=scores)
    a=sub.add_parser('audit'); a.add_argument('--auditor',default='auditor'); a.set_defaults(func=audit)
    sub.add_parser('stats').set_defaults(func=stats); sub.add_parser('verify-ledger').set_defaults(func=verify)
    a=sub.add_parser('evidence'); a.add_argument('output'); a.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=='__main__': raise SystemExit(main())
