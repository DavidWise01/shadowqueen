
import json,hashlib
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class HardeningKit:
    def __init__(self,root="."):
        self.root=Path(root)
    def exists(self,p): return (self.root/p).exists()
    def run_all(self):
        required=[
            "config/default.json","security/security_review.json","migrations/001_init.sql",
            "docs/ARCHITECTURE.md","docs/RUNBOOK.md","release/manifest.json",
            "release/api_contracts.json","packaging/pyproject.template.toml"
        ]
        missing=[p for p in required if not self.exists(p)]
        cfg=json.loads((self.root/"config/default.json").read_text())
        sec=json.loads((self.root/"security/security_review.json").read_text())
        api=json.loads((self.root/"release/api_contracts.json").read_text())
        manifest=json.loads((self.root/"release/manifest.json").read_text())
        sql=(self.root/"migrations/001_init.sql").read_text()
        checks={
            "files":{"ok":not missing,"missing":missing},
            "config":{"ok":all(k in cfg for k in ["environment","database","security","logging","federation"])},
            "security":{"ok":all(v=="pass" for k,v in sec.items() if k!="notes")},
            "api_contracts":{"ok":all(k in api for k in ["identity","credential","wallet","authority","investigation","analytics","operator"])},
            "migrations":{"ok":all(x in sql for x in ["CREATE TABLE","ledger","modules","release_state"])},
            "manifest":{"ok":all(k in manifest for k in ["name","version","status","modules","artifact_hashes"])}
        }
        ok=all(v["ok"] for v in checks.values())
        report={"status":"PASS" if ok else "FAIL","checks":checks,"config_hash":digest(cfg),"manifest_hash":digest(manifest)}
        (self.root/"release/hardening_report.json").write_text(json.dumps(report,indent=2))
        return report
