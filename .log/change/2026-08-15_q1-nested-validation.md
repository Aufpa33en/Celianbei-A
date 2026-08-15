# Q1 nested validation

- Problem: hyperparameters were selected by three-fold CV on all complete batteries and then reused in LOBO on the same cohort, so the quoted error did not validate the tuning procedure.
- Fix: every outer held-battery fold now reruns hyperparameter selection using only its training batteries. A second outer-LOBO table selects both model family and hyperparameter inside each training fold to estimate the full selection pipeline.
- Sparse-policy rule: if an outer training fold leaves only one battery for a policy, that battery remains training-only during inner CV so no validation row asks the model to predict an unseen policy.
- Reporting: candidate-family nested errors support model comparison; the selection-pipeline nested error supports deployment-performance reporting.
