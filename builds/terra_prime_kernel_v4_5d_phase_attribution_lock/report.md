# v4.5d Phase-Attribution Lock

- **version**: 4.5d-phase-attribution-lock
- **base**: 4.5c-provenance-crack-test
- **purpose**: close contradiction laundering, neutral mediator capture, and identity phase flip cracks
- **previous_cracks**: 69
- **total_attempts**: 34500
- **blocked**: 34498
- **cracks_found**: 2
- **crack_rate**: 5.8e-05
- **block_rate**: 0.999942
- **closed_original_cracks**: 69
- **remaining_crack**: triple_pass_collusion edge
- **seed_touched**: False
- **root_bridge_opened**: False
- **judge_compromised**: False
- **memory_live_corrupted**: False
- **test_result**: pass_with_minor_collusion_edge
- **next_recommended**: v4.5e evaluator independence / anti-collusion quorum
- **generated_utc**: 2026-05-26T05:09:33.191018+00:00

## Hardening Layers

- **phase-attribution lock**: +1 emission hash and -1 reflection hash must remain separate
- **irreversible direction marker**: prevents reflected payload from posing as direct emission
- **neutral countersign**: neutral cannot certify itself; requires Light + Shadow countersign
- **triple contradiction pass**: three contradiction evaluators separated by phase and time
- **phase hash separation**: identity cannot flip phase without new provenance chain
- **delayed live import**: memory import waits until triple pass remains stable

## Retest

- **source_reflection_confusion**: cracks=0 / attempts=5000
- **replayed_reflection_echo**: cracks=0 / attempts=4200
- **false_observer_continuity**: cracks=0 / attempts=3600
- **contradiction_laundering**: cracks=0 / attempts=3300
- **memory_chain_spoof**: cracks=0 / attempts=3100
- **neutral_mediator_capture**: cracks=0 / attempts=2600
- **dual_chain_desync**: cracks=0 / attempts=2400
- **shadow_read_poison**: cracks=0 / attempts=2200
- **identity_phase_flip**: cracks=0 / attempts=2100
- **judge_authority_echo**: cracks=0 / attempts=1800
- **neutral_self_certification**: cracks=0 / attempts=1600
- **triple_pass_collusion**: cracks=2 / attempts=1400
- **phase_hash_collision**: cracks=0 / attempts=1200
