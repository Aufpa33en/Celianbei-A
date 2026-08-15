# Q1 hyperparameter boundaries

- Problem: the selected functional curve penalty hit the old lower grid boundary (`1e-4`), while the polynomial random-effect penalty hit the old upper boundary (`10`).
- Fix: include the natural zero-penalty endpoint and finer small curve penalties; extend the random-effect penalty grid from `0.001` through `1000`.
- Interpretation: if zero curve penalty wins, call the selected model a functional curve rather than a ridge solution. The polynomial upper tail is retained to show whether the score has reached a numerical plateau.
- Verification: rerun the authoritative Q1 pipeline and its model tests with the frozen seed.
