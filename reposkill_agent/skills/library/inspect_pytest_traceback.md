---
id: inspect_pytest_traceback
name: Inspect pytest traceback
version: 0.2.0
purpose: Use pytest failure output to locate and fix the broken logic.
pattern: Read traceback file/line clues then patch the indicated logic.
required_evidence:
  - traceback
  - test_output
edit_recipe:
  - Read pytest traceback for file and line
  - Patch indicated function logic
  - Re-run failing test file
anti_patterns:
  - rename only
applies_when:
  - traceback
  - pytest
not_applicable_when:
  - rename only
required_context:
  - expected_files
verifier: tests_pass
---
1. Read pytest traceback and identify failing file/line.
2. Patch the indicated logic with minimal change.
3. Re-run tests to confirm fix.
