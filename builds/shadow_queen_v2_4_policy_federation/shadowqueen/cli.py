
import argparse,json
from pathlib import Path
from .core import Store
def export(args): print(json.dumps(Store(args.db,args.office).export_bundle(),indent=2))
def importb(args): print(json.dumps(Store(args.db,args.office).import_bundle(json.loads(Path(args.input).read_text())),indent=2))
def compare(args): print(json.dumps(Store(args.db,args.office).compare(args.remote),indent=2))
def override(args): print(json.dumps(Store(args.db,args.office).override(args.rule_id,args.remote,args.action,args.actor,args.reason),indent=2))
def audit(args): print(json.dumps(Store(args.db,args.office).audit(args.auditor),indent=2))
def rules(args): print(json.dumps(Store(args.db,args.office).list_rules(),indent=2))
def conflicts(args): print(json.dumps(Store(args.db,args.office).conflicts(),indent=2))
def stats(args): print(json.dumps(Store(args.db,args.office).stats(),indent=2))
def verify(args): print(json.dumps(Store(args.db,args.office).verify_ledger(),indent=2))
def evidence(args): print(json.dumps(Store(args.db,args.office).bundle_zip(args.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="policy_federation.db"); p.add_argument("--office",default="north"); sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("export").set_defaults(func=export)
    a=sub.add_parser("import"); a.add_argument("input"); a.set_defaults(func=importb)
    a=sub.add_parser("compare"); a.add_argument("remote"); a.set_defaults(func=compare)
    a=sub.add_parser("override"); a.add_argument("rule_id"); a.add_argument("remote"); a.add_argument("action",choices=["accept_remote","reject_remote","defer"]); a.add_argument("--actor",default="queen"); a.add_argument("--reason",default="manual override"); a.set_defaults(func=override)
    a=sub.add_parser("audit"); a.add_argument("--auditor",default="auditor"); a.set_defaults(func=audit)
    sub.add_parser("rules").set_defaults(func=rules); sub.add_parser("conflicts").set_defaults(func=conflicts); sub.add_parser("stats").set_defaults(func=stats); sub.add_parser("verify-ledger").set_defaults(func=verify)
    a=sub.add_parser("evidence"); a.add_argument("output"); a.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
