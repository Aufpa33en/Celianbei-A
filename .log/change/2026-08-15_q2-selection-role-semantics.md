# Q2 selection role semantics

- Problem: `constant_mean` could be marked `selected_explanatory=True`, although it is a benchmark with no explanatory exposure.
- Fix: add `selected_by_cv` for the winning row regardless of role; reserve `selected_explanatory` for selected exposure models only.
- Downstream: robustness decisions now locate the CV winner with `selected_by_cv`, so a selected constant benchmark remains representable without being mislabeled explanatory.
