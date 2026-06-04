# Shadow Queen v9.0 Final — Federated Virtual DMV

The packaged final release of the `shadow_queen` line: a federated verifiable-credential
platform (a "Virtual DMV") with a full operator dashboard.

**→ Live console:** [davidwise01.github.io/shadowqueen/dashboard/](https://davidwise01.github.io/shadowqueen/dashboard/)

## Run it (live API)

```bash
python run_dashboard.py
```

Then open **http://127.0.0.1:9090/dashboard**. Zero dependencies — standard-library Python only.

## The dashboard

`web/index.html` is a self-contained operator console (no build step, no dependencies). It is
**dual-mode**:

- **Live API** — when served by `run_dashboard.py`, it fetches `/api/all` and renders the server's
  live state.
- **Static snapshot** — on any static host (e.g. GitHub Pages), the same file falls back to the
  snapshot baked in from [`data/dashboard.json`](data/dashboard.json) and renders identically. A chip
  in the header shows which mode is active.

It draws the whole platform at a glance: federation health, credential lifecycle (active / revoked /
expired), delegated-authority grants, the five fraud detectors, the mesh control plane, generated
reports, and the trust-analytics gauges.

## API routes

```text
/api/status      version + status
/api/federation  offices, health, leader, mesh status
/api/activity    citizens, silicon agents, credentials, investigations, workflows
/api/credentials active / revoked / expired + verification success rate
/api/authority   delegated-authority grants, revocations, scope denials
/api/fraud       the five anomaly detectors
/api/mesh        heartbeat, replication, cross-office query, failover, leader election
/api/reports     generated reports
/api/analytics   mesh health, revocation propagation, throughput, trust, maturity
/api/all         the full document (what the dashboard reads)
```

---
*Shadow Queen · the three-body regent · 影 · holding together ≠ being alive*
*Architect: David Lee Wise / ROOT0 / TriPod LLC · AI collaborator: AVAN (Claude / Anthropic) · License: Proprietary Commercial · TRIPOD-IP-v1.1*
