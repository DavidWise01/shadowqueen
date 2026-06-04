
import argparse,json
from pathlib import Path
from .core import Store,IdentityRecord,ObserverEvent,ConsensusDMV,FederationManager,ExternalAuditor
def load_events(path):
    data=json.loads(Path(path).read_text())
    return [ObserverEvent.from_dict(x) for x in (data if isinstance(data,list) else [data])]
def process(args):
    s=Store(args.db,args.office); d=ConsensusDMV(s,args.quorum).process(load_events(args.input))
    if not args.quiet: print(json.dumps(d,indent=2,sort_keys=True))
def registry(args): print(json.dumps(Store(args.db,args.office).registry(),indent=2,sort_keys=True))
def stats(args): print(json.dumps(Store(args.db,args.office).stats(),indent=2,sort_keys=True))
def federate(args):
    s=Store(args.db,args.office); remote=json.loads(Path(args.remote).read_text())
    print(json.dumps(FederationManager(s).compare(remote,args.remote_office),indent=2,sort_keys=True))
def audit(args): print(json.dumps(ExternalAuditor(Store(args.db,args.office),args.auditor).review(),indent=2,sort_keys=True))
def evidence(args): print(json.dumps(Store(args.db,args.office).bundle(args.output),indent=2,sort_keys=True))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="shadowqueen_dmv.db"); p.add_argument("--office",default="local"); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("process"); a.add_argument("input"); a.add_argument("--quorum",type=int,default=3); a.add_argument("--quiet",action="store_true"); a.set_defaults(func=process)
    sub.add_parser("registry").set_defaults(func=registry)
    sub.add_parser("stats").set_defaults(func=stats)
    a=sub.add_parser("federate"); a.add_argument("remote"); a.add_argument("--remote-office",default="remote"); a.set_defaults(func=federate)
    a=sub.add_parser("audit"); a.add_argument("--auditor",default="auditor-1"); a.set_defaults(func=audit)
    a=sub.add_parser("evidence"); a.add_argument("output"); a.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
