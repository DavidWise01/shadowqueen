# Shadow Queen v5.8 — Notification System

## Added
- notification channels
- email-style local adapter
- SMS-style local adapter
- operator/dashboard adapter
- event subscriptions
- filter rules
- notification queue
- workflow hooks
- delivery logs
- failure logs
- retry failed queue
- evidence export

## Run
```bash
python selftest.py
python -m shadowqueen.cli demo
python -m shadowqueen.cli --db notifications.db --node office:north status
python -m shadowqueen.cli --db notifications.db --node office:north process
python -m shadowqueen.cli --db notifications.db --node office:north evidence notifications_evidence.zip
```

Note: email/SMS are local file adapters in this prototype. No external messages are sent.
