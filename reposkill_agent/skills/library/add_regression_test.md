---
id: add_regression_test_before_fix
name: Add regression test before fix
version: 0.2.0
purpose: Cover failing edge case with regression test then fix implementation.
pattern: Reproduce failing case in test, then fix production code.
required_evidence:
  - regression
  - expected_files
edit_recipe:
  - Add regression test for failing scenario
  - Fix implementation to satisfy test
  - Re-run full test suite
anti_patterns:
  - rename only
applies_when:
  - regression
  - edge case
not_applicable_when:
  - rename only
required_context:
  - expected_files
verifier: tests_pass
---
1. Add or update regression test for the failing scenario.
2. Fix implementation until tests pass.
3. Re-run full test suite.
