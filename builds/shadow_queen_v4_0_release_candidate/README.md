# Shadow Queen v4.0 — Release Candidate RC1

## Purpose
v4.0 RC proves that the existing federation survives integration, failure, disagreement, corruption, revocation, delegation, and recovery.

## RC Suites
- federation integration tests
- chaos tests
- recovery validation
- governance validation
- release audit matrices

## Generated Matrices
- capability matrix
- trust matrix
- authority matrix
- risk matrix
- federation health report

## Run
```bash
python selftest.py
python -m shadowqueen.cli --db rc.db run
python -m shadowqueen.cli --db rc.db stats
python -m shadowqueen.cli --db rc.db verify-ledger
python -m shadowqueen.cli --db rc.db evidence rc_evidence.zip
```
