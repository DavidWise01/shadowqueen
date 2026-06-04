# v4.5j Silicon-Live Soak

- **version**: 4.5j-silicon-live-soak
- **base**: 4.5i-voltage-debt-governor
- **purpose**: long-running silicon IO with governor decay and safe source recovery
- **cycles**: 50000
- **sources**: ['clean', 'noisy', 'hostile', 'recovering']
- **accepted**: 35000
- **rejected**: 37000
- **quarantined**: 18942
- **recovered**: 219
- **debt_decay_events**: 27644
- **replay_blocks**: 2168
- **nonce_rotations**: 195
- **root_bridge_opens**: 35000
- **kernel_panics**: 0
- **seed_touches**: 0
- **root_floods**: 0
- **memory_corruptions**: 0
- **egress_loops**: 0
- **leaks**: 0
- **soak_result**: pass
- **next_recommended**: v4.5k adaptive IO rate governor
- **generated_utc**: 2026-05-26T22:38:35.187743+00:00

## Source Summary

- **clean**: accepted=18000 rejected=0 recovered=0 final_debt=0 quarantine=0
- **noisy**: accepted=9600 rejected=8400 recovered=131 final_debt=-104 quarantine=0
- **hostile**: accepted=0 rejected=18000 recovered=0 final_debt=-633 quarantine=257
- **recovering**: accepted=7400 rejected=10600 recovered=88 final_debt=-196 quarantine=0
