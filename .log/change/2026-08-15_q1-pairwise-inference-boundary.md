# Q1 pairwise inference boundary

- Problem: the paper reported zero Holm-confirmed SOH200 pairs without also exposing that some unadjusted battery-bootstrap intervals exclude zero.
- Fix: report both summaries, add a machine-readable `BootstrapCIExcludesZero` field, and state that neither result implies strategy equivalence or multiplicity-adjusted significance for the bootstrap intervals.
- Verification: rerun the authoritative Q1 pipeline with the frozen seed and check the generated tables, report, and Q1 model test.
