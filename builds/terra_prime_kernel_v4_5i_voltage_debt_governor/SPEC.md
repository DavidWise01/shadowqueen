# Terra Prime Kernel v4.5i — Voltage Debt Governor

## Core Rule

```text
debt is isolated before it becomes kernel panic
```

## Thresholds

```text
-211mV  soft reject
-422mV  quarantine
-844mV  kernel panic threshold
```

The governor intercepts before panic.

## Result

```text
kernel panics: 0
leaks: 0
seed touched: false
ROOT floods: 0
```
