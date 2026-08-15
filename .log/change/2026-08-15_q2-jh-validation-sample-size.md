# Q2 J+H validation sample size

- Problem: the paper said the J+H candidate was rejected, while its explicit-new-structure validation has only six strategies.
- Fix: emit one diagnostic row per held coordinate with training rows, test rows, fitted parameter count, and a residual-degree-of-freedom proxy.
- Boundary: each explicit-new-structure fold has five training strategies for three coefficients, leaving only two residual degrees of freedom. The current sample cannot validate the candidate; this is not proof that the whole model class is invalid.
