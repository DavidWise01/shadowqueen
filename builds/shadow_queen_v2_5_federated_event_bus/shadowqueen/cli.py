
import argparse,json
from .core import Store,EventBus
def publish(args):
    ev=EventBus(Store(args.db,args.office)).publish(args.type,args.subject,json.loads(args.payload),args.targets.split(",") if args.targets else [])
    print(json.dumps(ev.to_dict(),indent=2))
def stats(args): print(json.dumps(Store(args.db,args.office).stats(),indent=2))
def events(args): print(json.dumps(Store(args.db,args.office).events(),indent=2))
def verify(args): print(json.dumps(Store(args.db,args.office).verify_ledger(),indent=2))
def evidence(args): print(json.dumps(Store(args.db,args.office).bundle(args.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="event_bus.db"); p.add_argument("--office",default="north")
    sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("publish"); a.add_argument("type"); a.add_argument("subject"); a.add_argument("payload"); a.add_argument("--targets",default=""); a.set_defaults(func=publish)
    sub.add_parser("stats").set_defaults(func=stats)
    sub.add_parser("events").set_defaults(func=events)
    sub.add_parser("verify-ledger").set_defaults(func=verify)
    a=sub.add_parser("evidence"); a.add_argument("output"); a.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
