
import argparse,json
from .core import Wallet,seed_demo
def demo(a): print(json.dumps(seed_demo(Wallet(a.db,a.owner)),indent=2))
def summary(a): print(json.dumps(Wallet(a.db,a.owner).summary(),indent=2))
def creds(a): print(json.dumps(Wallet(a.db,a.owner).credentials(),indent=2))
def stats(a): print(json.dumps(Wallet(a.db,a.owner).stats(),indent=2))
def verify(a): print(json.dumps(Wallet(a.db,a.owner).verify_ledger(),indent=2))
def evidence(a): print(json.dumps(Wallet(a.db,a.owner).bundle(a.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="wallet.db"); p.add_argument("--owner",default="citizen:local")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo); sub.add_parser("summary").set_defaults(func=summary); sub.add_parser("credentials").set_defaults(func=creds); sub.add_parser("stats").set_defaults(func=stats); sub.add_parser("verify-ledger").set_defaults(func=verify)
    e=sub.add_parser("evidence"); e.add_argument("output"); e.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
