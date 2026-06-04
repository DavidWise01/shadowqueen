# Shadow Queen v5.9 — Reporting Engine

## Added
- audit reports
- workflow reports
- credential reports
- fraud reports
- authority reports
- federation health reports
- evidence records
- evidence packet generator
- report manifest
- hash receipts
- report bundle export

## Run
```bash
python selftest.py
python -m shadowqueen.cli demo
python -m shadowqueen.cli --db reports.db --node office:north status
python -m shadowqueen.cli --db reports.db --node office:north packet --subject release
python -m shadowqueen.cli --db reports.db --node office:north evidence reporting_evidence.zip
```

Reports are JSON-formal records in this prototype. The next phase can add actual PDF/DOCX rendering.
