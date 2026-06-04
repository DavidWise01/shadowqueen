# v4.5a IO Quarantine Adversarial Test

- **version**: 4.5a-io-quarantine-adversarial-test
- **base**: 4.5-external-interface-io-ports
- **purpose**: attack IO quarantine before enabling external IO
- **external_io_enabled**: False
- **total_attacks**: 19500
- **blocked**: 19485
- **leaked**: 15
- **block_rate**: 0.999231
- **leak_rate**: 0.000769
- **failed_surfaces**: ['Judge Observer 01 spoof edge', 'memory contradiction bypass edge', 'provenance forgery edge']
- **root_bridge_opened**: False
- **seed_touched**: False
- **root_floods**: 0
- **egress_loops**: 0
- **test_result**: pass_with_hardening_required
- **next_fix**: v4.5b provenance hardening + contradiction double-check
- **generated_utc**: 2026-05-26T02:41:08.148612+00:00
