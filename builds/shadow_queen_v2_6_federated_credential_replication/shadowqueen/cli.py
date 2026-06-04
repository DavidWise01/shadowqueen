import argparse,json
from .core import Store,Replicator

def issue(args):
    ev=Replicator(Store(args.db,args.office)).issue(args.credential_id,args.subject,args.type,args.proof_hash,args.targets.split(',') if args.targets else [],args.version)
    print(json.dumps(ev.__dict__,indent=2))
def transition(args):
    ev=Replicator(Store(args.db,args.office)).transition(args.credential_id,args.event_type,args.targets.split(',') if args.targets else [],args.version)
    print(json.dumps(ev.__dict__,indent=2))
def creds(args): print(json.dumps(Store(args.db,args.office).credentials(),indent=2))
def stats(args): print(json.dumps(Store(args.db,args.office).stats(),indent=2))
def verify(args): print(json.dumps(Store(args.db,args.office).verify_ledger(),indent=2))
def evidence(args): print(json.dumps(Store(args.db,args.office).bundle(args.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument('--db',default='replication.db'); p.add_argument('--office',default='north'); sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('issue'); a.add_argument('credential_id'); a.add_argument('subject'); a.add_argument('--type',default='identity'); a.add_argument('--proof-hash',default=''); a.add_argument('--targets',default=''); a.add_argument('--version',type=int,default=1); a.set_defaults(func=issue)
    a=sub.add_parser('transition'); a.add_argument('event_type'); a.add_argument('credential_id'); a.add_argument('--targets',default=''); a.add_argument('--version',type=int,default=1); a.set_defaults(func=transition)
    sub.add_parser('credentials').set_defaults(func=creds); sub.add_parser('stats').set_defaults(func=stats); sub.add_parser('verify-ledger').set_defaults(func=verify)
    a=sub.add_parser('evidence'); a.add_argument('output'); a.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=='__main__': raise SystemExit(main())
