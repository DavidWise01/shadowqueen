# Aeonic Coherence Kernel v0.2

## Purpose

v0.2 adds an external validation / retrieval interface to v0.1.

Core rule:

```text
external evidence informs
external evidence warns
external evidence records provenance
external evidence does not control the resolver
```

## Base Kernel

v0.1 included:

- 11+1 core resolver
- truth validator
- weak shadow archive
- bridge mediator
- observer A trust audit
- observer B anomaly history
- hash-chain report ledger
- warning-only feedback

## v0.2 Additions

### External Validation Interface

Receives evidence packets:

- source id
- claim value
- confidence
- freshness
- relevance
- provenance

### Evidence Scorer

Produces:

- support
- contradiction
- uncertainty

### Evidence Observer

Read-only observer for external evidence.

Watches:

- conflict
- weak support
- uncertainty
- provenance pressure

### Retrieval Gate

Passes only weak signals into the bridge:

- support signal
- contradiction signal
- uncertainty signal
- warning signal

It cannot pass raw authority.

### Provenance Ledger

Extends the hash-chain ledger with evidence scores.

## Sovereignty Rule

External validation may affect:

- confidence
- warning
- bridge pressure
- provenance score

External validation may not:

- choose output
- overwrite self state
- erase shadow
- bypass bridge
- rewrite ledger

## Control Law v0.2

```text
core decides
truth validates
shadow preserves alternatives
bridge reconciles
observers audit
ledger remembers
warning dampens
evidence informs
retrieval gate filters
provenance records
```

## Target

Adaptive stability band:

```text
0.78–0.88
```
