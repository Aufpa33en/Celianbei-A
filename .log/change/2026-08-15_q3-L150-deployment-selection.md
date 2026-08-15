# Q3 L=150 deployment selection correction

## Problem

The final test batteries always provide cycles 1-150, but the previous deployment freeze used a weighted score over L=50, 100, and 150. That objective selected `C_ridge` even though `P1_linear` had the lowest honest outer-LOBO error at the actual L=150 deployment information set. The multi-length robustness question and the final deployment question were therefore conflated.

## Correction

- Select the deployment family only from the six pre-specified candidates at L=150.
- Keep the 0.15/0.25/0.60 multi-length score as a labeled robustness sensitivity, not a deployment decision.
- Publish `deployment_candidate_comparison.csv` and require exactly one selected row to match `deployment_freeze.csv`.
- Keep C feature ablations as post-selection architecture diagnostics; do not add those data-informed variants to the current candidate set.
- Make paper figures read the frozen model from `final_model_settings.csv` instead of hard-coding `C_ridge`.

## Verification

- Reran 40-battery full validation, 5000 battery-level bootstrap repetitions, C ablation, deployment fitting, and nine-battery final prediction under `q3_full_v2`.
- `P1_linear` was frozen with L=150 strategy-equal RMSE 0.0006165 and worst-battery RMSE 0.0026354; second-place `C_ridge` had 0.0006690 and 0.0027855.
- Full validation passed 16/16 integrity checks; final prediction passed 9/9; 450 selected prediction rows and 2700 six-model audit rows were published.
- Q3 model, smoke, full-protocol, and paper-figure tests passed; all three Q3 figures were visually inspected.

## Boundary

The nested selector RMSE and multi-length score estimate different workflows and remain useful sensitivity evidence, but neither is the fixed P1 deployment error. The approximate intervals condition on the frozen P1 family and do not include model-selection uncertainty. T80 remains an unvalidated extrapolation scenario because no battery reaches 80% SOH in the observed data.
