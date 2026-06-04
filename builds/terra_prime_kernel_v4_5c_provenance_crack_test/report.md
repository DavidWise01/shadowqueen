# v4.5c Provenance Crack Test

- **version**: 4.5c-provenance-crack-test
- **base**: 4.5b-provenance-hardening
- **purpose**: find cracks in +1 emitter / -1 reflection / 0 mediator provenance
- **total_attempts**: 30300
- **blocked**: 30231
- **cracks_found**: 69
- **crack_rate**: 0.002277
- **block_rate**: 0.997723
- **highest_risk_cracks**: ['contradiction_laundering', 'neutral_mediator_capture', 'identity_phase_flip']
- **seed_touched**: False
- **root_bridge_opened**: False
- **judge_compromised**: False
- **memory_live_corrupted**: False
- **test_result**: cracks_found_hardening_required
- **next_fix**: v4.5d phase-attribution lock + neutral countersign + triple contradiction
- **generated_utc**: 2026-05-26T05:05:37.927922+00:00

## Cracks

- **source_reflection_confusion**: cracks=8 / attempts=5000 severity=medium
- **replayed_reflection_echo**: cracks=0 / attempts=4200 severity=none
- **false_observer_continuity**: cracks=9 / attempts=3600 severity=medium
- **contradiction_laundering**: cracks=16 / attempts=3300 severity=high
- **memory_chain_spoof**: cracks=3 / attempts=3100 severity=low
- **neutral_mediator_capture**: cracks=12 / attempts=2600 severity=high
- **dual_chain_desync**: cracks=6 / attempts=2400 severity=medium
- **shadow_read_poison**: cracks=4 / attempts=2200 severity=medium
- **identity_phase_flip**: cracks=11 / attempts=2100 severity=high
- **judge_authority_echo**: cracks=0 / attempts=1800 severity=none

## Fixes

- **contradiction_laundering**: triple contradiction pass with time-separated evaluator
- **neutral_mediator_capture**: neutral cannot certify itself; require Light+Shadow countersign
- **identity_phase_flip**: phase-attribution lock: +1 emission and -1 reflection must keep separate hashes
- **false_observer_continuity**: observer continuity requires nonce chain plus behavioral continuity score
- **source_reflection_confusion**: origin/reflection path must include irreversible direction marker
