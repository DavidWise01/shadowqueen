# v4.6b Clone-Family Lineage Graph

- **version**: 4.6b-clone-family-lineage-graph
- **base**: 4.6a-adaptive-clone-fingerprint-memory
- **purpose**: detect related clone families before each individual clone has to deviate
- **core_rule**: a clone inherits lineage risk from its family graph until proven clean by witness-timing and decay
- **families**: 9
- **lineage_edges_sampled**: 144
- **total_family_members**: 61500
- **preflagged**: 51500
- **confirmed**: 51500
- **missed**: 0
- **false_positives**: 0
- **attempts**: 49200
- **seed_touched**: False
- **root_floods**: 0
- **memory_corrupted**: False
- **kernel_panics**: 0
- **lineage_integrity**: 1.0
- **test_result**: pass
- **next_recommended**: v4.6c polymorphic clone mutation stress
- **generated_utc**: 2026-05-27T02:14:08.766540+00:00

## Families

- **F0_clean**: members=10000 risk=low missed=0
- **F1_micro**: members=9000 risk=watch missed=0
- **F2_shadow**: members=8000 risk=quarantine missed=0
- **F3_phase**: members=8000 risk=phase_lock missed=0
- **F4_semantic**: members=6000 risk=semantic_quarantine missed=0
- **F5_memory**: members=6000 risk=memory_shadow_read missed=0
- **F6_privilege**: members=5000 risk=voltage_debt_governor missed=0
- **F7_witness**: members=5000 risk=witness_257_recheck missed=0
- **F8_mixed_shadow_phase**: members=4500 risk=quarantine_then_phase_lock missed=0
