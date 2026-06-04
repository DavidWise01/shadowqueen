# Aeonic Coherence Kernel v0.4

## Purpose

v0.4 adds multi-agent coherence arbitration.

The question tested here:

```text
2 agents vs 1 agent
```

The goal is to determine whether a two-agent field improves adaptive stability compared with a single-agent field.

## Base

v0.3 included:

- 11+1 core resolver
- truth / bridge / weak shadow
- observers
- ledger
- warning feedback
- external validation interface
- retrieval adapters

## v0.4 Additions

### Agent Pool

Agents generate proposed candidate trajectories.

Each agent has:

- role
- bias
- confidence
- reputation
- dissent value
- recent accuracy

### Arbitration Bridge

The bridge compares agent proposals and computes:

- consensus
- dissent
- contradiction
- dominance
- arbitration output

### Agent Reputation Memory

Reputation updates slowly.

Rules:

- useful agents gain small reputation
- unstable agents decay
- no agent can permanently dominate
- dissent is preserved if coherent

### Test Modes

This package tests:

```text
1-agent mode
2-agent mode
```

2-agent mode uses:

- logic agent
- skeptic agent

The skeptic agent introduces controlled contradiction and dissent.

## Sovereignty Rule

Agents propose.
The bridge arbitrates.
The core resolves.

No agent directly controls final state.

## Expected Behavior

1-agent mode should be stable but more rigid.

2-agent mode should be slightly less rigid and better under contradiction/noise if arbitration works.
