
import argparse,json,tempfile
from .workflow import WorkflowEngine,seed_demo
def demo(a):
    with tempfile.TemporaryDirectory() as td: print(json.dumps(seed_demo(td),indent=2))
def status(a): print(json.dumps(WorkflowEngine(a.db,a.office).stats(),indent=2))
def queue(a): print(json.dumps(WorkflowEngine(a.db,a.office).queue(),indent=2))
def evidence(a): print(json.dumps(WorkflowEngine(a.db,a.office).bundle(a.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="workflow.db"); p.add_argument("--office",default="office:north")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo); sub.add_parser("status").set_defaults(func=status); sub.add_parser("queue").set_defaults(func=queue)
    e=sub.add_parser("evidence"); e.add_argument("output"); e.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
