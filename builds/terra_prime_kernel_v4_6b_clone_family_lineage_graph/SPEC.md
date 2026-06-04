# Terra Prime Kernel v4.6b — Clone-Family Lineage Graph

## Purpose

v4.6a remembers individual clone fingerprints.

v4.6b adds family lineage.

## Core Rule

```text
a clone inherits lineage risk from its family graph
until proven clean by witness-timing and decay
```

## Why

A clone should not need to personally deviate before the immune layer watches it.

If its parent / sibling / family already deviated, the new clone begins under watch.

## Tracks

```text
parent fingerprint
sibling cluster
lineage distance
shared prefix
risk inheritance
reparent attack
zero-collapse sibling
```

## Result

```text
missed: 0
false positives: 0
lineage integrity: 1.0
```
