
import argparse,json
from .core import RC
def run(a): print(json.dumps(RC(a.db,a.release).run_all(),indent=2))
def stats(a): print(json.dumps(RC(a.db,a.release).stats(),indent=2))
def verify(a): print(json.dumps(RC(a.db,a.release).verify_ledger(),indent=2))
def evidence(a): print(json.dumps(RC(a.db,a.release).bundle(a.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="rc.db"); p.add_argument("--release",default="shadow-queen-v4.0-rc1")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("run").set_defaults(func=run); sub.add_parser("stats").set_defaults(func=stats); sub.add_parser("verify-ledger").set_defaults(func=verify)
    e=sub.add_parser("evidence"); e.add_argument("output"); e.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
