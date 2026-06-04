# Aeonic Coherence Kernel v0.3

## Purpose

v0.3 adds active retrieval adapters around the v0.2 external validation layer.

The kernel still follows the sovereignty rule:

```text
retrieval may fetch
evidence may score
observers may warn
ledger may remember
core still decides
```

## v0.3 Additions

### 1. Source Adapter Layer

A source adapter converts an external system into evidence packets.

Adapters are pluggable.

Example adapters:

- local memory adapter
- document adapter
- web/search adapter
- tool/API adapter
- human note adapter

Each adapter must output a normalized evidence packet.

---

### 2. Evidence Packet Schema

```json
{
  "source_id": "string",
  "source_type": "memory | document | web | tool | human | simulated",
  "claim": "string",
  "claim_value": "float",
  "confidence": "float",
  "freshness": "float",
  "relevance": "float",
  "provenance": "string",
  "retrieved_at": "string"
}
```

---

### 3. Source Ranking

Sources are ranked by:

```text
rank = confidence × freshness × relevance × provenance_weight
```

No source becomes absolute authority.

---

### 4. Adapter Observer

Observer C watches retrieval quality.

It detects:

- stale evidence
- low provenance
- source disagreement
- retrieval collapse
- excessive source dominance

---

### 5. Retrieval Budget

Retrieval is rate-limited.

Purpose:

- avoid over-querying
- avoid evidence flooding
- preserve core sovereignty

---

## Control Law v0.3

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
adapters fetch
source ranks constrain
```

## Forbidden Behavior

Adapters may not:

- overwrite core state
- choose output
- bypass retrieval gate
- bypass provenance ledger
- declare themselves final truth

## Target Stability

Target adaptive band remains:

```text
0.78–0.88
```
