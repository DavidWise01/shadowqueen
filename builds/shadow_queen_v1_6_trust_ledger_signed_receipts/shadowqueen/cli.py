
import argparse,json
from pathlib import Path
from .core import Store,IdentityRecord,ObserverEvent,ConsensusDMV,FederationManager,ExternalAuditor
def load_events(path):
    data=json.loads(Path(path).read_text())
    return [ObserverEvent.from_dict(x) for x in (data if isinstance(data,list) else [data])]
def process(args): print(json.dumps(ConsensusDMV(Store(args.db,args.office),args.quorum).process(load_events(args.input)),indent=2,sort_keys=True))
def registry(args): print(json.dumps(Store(args.db,args.office).registry(),indent=2,sort_keys=True))
def stats(args): print(json.dumps(Store(args.db,args.office).stats(),indent=2,sort_keys=True))
def federate(args): print(json.dumps(FederationManager(Store(args.db,args.office)).compare(json.loads(Path(args.remote).read_text()),args.remote_office),indent=2,sort_keys=True))
def audit(args): print(json.dumps(ExternalAuditor(Store(args.db,args.office),args.auditor).review(),indent=2,sort_keys=True))
def verify(args): print(json.dumps(Store(args.db,args.office).verify_ledger(),indent=2,sort_keys=True))
def evidence(args): print(json.dumps(Store(args.db,args.office).bundle(args.output),indent=2,sort_keys=True))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="shadowqueen_dmv.db"); p.add_argument("--office",default="local"); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("process"); a.add_argument("input"); a.add_argument("--quorum",type=int,default=3); a.set_defaults(func=process)
    sub.add_parser("registry").set_defaults(func=registry); sub.add_parser("stats").set_defaults(func=stats); sub.add_parser("verify-ledger").set_defaults(func=verify)
    a=sub.add_parser("federate"); a.add_argument("remote"); a.add_argument("--remote-office",default="remote"); a.set_defaults(func=federate)
    a=sub.add_parser("audit"); a.add_argument("--auditor",default="auditor-1"); a.set_defaults(func=audit)
    a=sub.add_parser("evidence"); a.add_argument("output"); a.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
