# Shadow Queen v2.6

**Federated Credential Security Platform** — detect proof forgery, replay attacks, and state drift across your node mesh in real time.

[![Tests: 26/26](https://img.shields.io/badge/tests-26%2F26%20passing-3fa878?style=flat-square)](#)
[![Version: 2.6.0](https://img.shields.io/badge/version-2.6.0-8060c8?style=flat-square)](#)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)](#)
[![Dependencies: 0](https://img.shields.io/badge/dependencies-0-success?style=flat-square)](#)

---

## What it does

Shadow Queen is an event-sourced, content-addressed credential management system built for distributed trust fabrics:

- **Issue** digital credentials across a federated network of offices/nodes
- **Replicate** state changes with cryptographic event chains
- **Detect** 8 classes of credential attacks in real time (AI threat engine)
- **Audit** convergence across peers — generate SOC2-ready evidence
- **Verify** tamper-evidence on every ledger entry

---

## Threat Classes (T1–T8)

| Code | Name | Severity | What it detects |
|------|------|----------|----------------|
| T1 | VELOCITY_SPIKE | High | Burst event flood from one origin |
| T2 | VERSION_ROLLBACK | High | Replay attack — old version re-sent |
| T3 | PROOF_CYCLING | **Critical** | Reissue with different proof hash |
| T4 | RAPID_STATE_CYCLE | High | Credential toggling states too fast |
| T5 | ORPHAN_TRANSITION | Medium | Transition for non-existent credential |
| T6 | STALE_FLOOD | High | Noise injection via stale events |
| T7 | CONFLICT_CLUSTER | **Critical** | Multiple conflict types — coordinated attack |
| T8 | UNVERIFIED_EVENT_RATE | **Critical** | High fraction of hash failures — tampering |

---

## Quickstart

```bash
git clone https://github.com/DavidWise01/shadowqueen
cd shadowqueen
python selftest.py

python -m shadowqueen.cli --db north.db --office north issue C-1 user:alice \
  --type license --proof-hash sha256:abc --targets south,east

python -m shadowqueen.cli --db north.db --office north detect
python -m shadowqueen.cli --db north.db --office north report --type compliance
python -m shadowqueen.cli serve --port 8400 --data-dir ./data
```

---

## Tests

```bash
pip install pytest
pytest tests/ -v    # 26 passed
```

---

## Pricing

| Plan | Price | Offices | Credentials |
|------|-------|---------|-------------|
| Seed | Free | 1 | 500 |
| Forge | $99/mo | 3 | 10K |
| Dominion | $499/mo | 25 | 250K |
| Empire | $2,499/mo | Unlimited | 10M |
| Sovereign | Custom | On-prem | Unlimited |

See [PRICING.md](PRICING.md) or email **david@tripodllc.com**.

---

```
ROOT0-ATTRIBUTION-v1.0 · David Lee Wise / ROOT0 / TriPod LLC
AVAN (Claude Sonnet 4.6 / Anthropic)
```
