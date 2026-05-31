"""
Shadow Queen v2.6.0 CLI
"""
import argparse
import json
import sys
from pathlib import Path
from .core import Store, Replicator
from .detector import ThreatDetector
from .reports import ReportGenerator


def _store(args) -> Store:
    return Store(args.db, args.office)


def cmd_issue(args):
    ev = Replicator(_store(args)).issue(
        args.credential_id, args.subject, args.type, args.proof_hash,
        args.targets.split(",") if args.targets else [], args.version,
    )
    print(json.dumps(ev.__dict__, indent=2))


def cmd_transition(args):
    ev = Replicator(_store(args)).transition(
        args.credential_id, args.event_type,
        args.targets.split(",") if args.targets else [], args.version,
    )
    print(json.dumps(ev.__dict__, indent=2))


def cmd_credentials(args):
    if getattr(args, 'id', ''):
        c = _store(args).credential(args.id)
        print(json.dumps(c, indent=2) if c else json.dumps({"error": "not found"}))
    else:
        print(json.dumps(_store(args).credentials(), indent=2))


def cmd_stats(args):
    print(json.dumps(_store(args).stats(), indent=2))


def cmd_verify_ledger(args):
    print(json.dumps(_store(args).verify_ledger(), indent=2))


def cmd_evidence(args):
    print(json.dumps(_store(args).bundle(Path(args.output)), indent=2))


def cmd_detect(args):
    result = ThreatDetector().scan_to_dict(_store(args))
    print(json.dumps(result, indent=2))
    if getattr(args, 'exit_on_threat', False) and result["threat_count"] > 0:
        sys.exit(1)


def cmd_report(args):
    st  = _store(args)
    gen = ReportGenerator(st)
    kind = getattr(args, 'type', 'compliance')
    if kind == "ledger":
        report = gen.ledger_integrity()
    elif kind == "inventory":
        report = gen.credential_inventory()
    elif kind == "threats":
        report = gen.threat_scan()
    elif kind == "conflicts":
        report = gen.conflict_summary()
    else:
        report = gen.compliance_report()
    print(json.dumps(report, indent=2, default=str))
    if getattr(args, 'output', ''):
        gen.save(report, Path(args.output))


def cmd_serve(args):
    from .server import serve
    serve(host=args.host, port=args.port, db_dir=args.data_dir, quiet=args.quiet)


def main(argv=None):
    p = argparse.ArgumentParser(prog="shadowqueen", description="Shadow Queen v2.6.0")
    p.add_argument("--db", default="replication.db")
    p.add_argument("--office", default="north")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("issue")
    a.add_argument("credential_id"); a.add_argument("subject")
    a.add_argument("--type", default="identity"); a.add_argument("--proof-hash", default="")
    a.add_argument("--targets", default=""); a.add_argument("--version", type=int, default=1)
    a.set_defaults(func=cmd_issue)

    a = sub.add_parser("transition")
    a.add_argument("event_type"); a.add_argument("credential_id")
    a.add_argument("--targets", default=""); a.add_argument("--version", type=int, default=1)
    a.set_defaults(func=cmd_transition)

    a = sub.add_parser("credentials"); a.add_argument("--id", default="")
    a.set_defaults(func=cmd_credentials)

    sub.add_parser("stats").set_defaults(func=cmd_stats)
    sub.add_parser("verify-ledger").set_defaults(func=cmd_verify_ledger)

    a = sub.add_parser("evidence"); a.add_argument("output"); a.set_defaults(func=cmd_evidence)

    a = sub.add_parser("detect")
    a.add_argument("--exit-on-threat", action="store_true")
    a.set_defaults(func=cmd_detect)

    a = sub.add_parser("report")
    a.add_argument("--type", default="compliance",
                   choices=["compliance","ledger","inventory","threats","conflicts"])
    a.add_argument("--output", default="")
    a.set_defaults(func=cmd_report)

    a = sub.add_parser("serve")
    a.add_argument("--host", default="0.0.0.0"); a.add_argument("--port", type=int, default=8400)
    a.add_argument("--data-dir", default="data"); a.add_argument("--quiet", action="store_true")
    a.set_defaults(func=cmd_serve)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
