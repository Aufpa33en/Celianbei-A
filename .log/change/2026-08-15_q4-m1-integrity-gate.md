# Q4 M1 integrity gate

- Replaced a nearly tautological squared-error-share sum check.
- The gate now verifies the worst fold is out of range, predicts negative loss, and is unique.
- It also machine-checks that M1 remains worse than the constant baseline after removing that fold.
