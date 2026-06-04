
import argparse,json,tempfile
from .real_crypto import RealCryptoNode,seed_demo
def demo(a):
    with tempfile.TemporaryDirectory() as td: print(json.dumps(seed_demo(td),indent=2))
def status(a): print(json.dumps(RealCryptoNode(a.db,a.node,a.key_dir).stats(),indent=2))
def evidence(a): print(json.dumps(RealCryptoNode(a.db,a.node,a.key_dir).bundle(a.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="real_crypto.db"); p.add_argument("--node",default="office:north"); p.add_argument("--key-dir",default="keys")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo); sub.add_parser("status").set_defaults(func=status)
    e=sub.add_parser("evidence"); e.add_argument("output"); e.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
