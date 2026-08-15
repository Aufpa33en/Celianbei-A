# Q3/Q4 validation rerun contract

## Scope

- Add an explicit `--output-root` to the formal Q3 and Q4 validation entrypoints.
- Preserve the rule that an existing target directory is never overwritten.
- Make protocol tests fail when authoritative result directories are absent instead of silently skipping checks.

## Verification

- Python compilation passed for all changed Python files.
- `test_q3_full_protocol.py`, `test_q4_smoke.py`, and `test_q4_full_validation.py` passed against the current authoritative artifacts.
- Q4 was independently rerun with 5000 bootstrap samples into an isolated temporary output root. All 17 stable output files matched the authoritative tables after parsing; runtime, manifest, and the runtime-bearing report were excluded from deterministic comparison.
- Q3 `--help` and output routing were checked. Its full rerun is intentionally deferred to the later Q3 model-selection correction, where the expensive computation must be repeated anyway.

## Boundary

This change improves reproducibility and test failure semantics only. It does not claim that the current Q3 or Q4 algorithm choice is valid.
