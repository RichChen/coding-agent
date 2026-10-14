---
id: fix_import_module_error
name: Fix import or module error
version: 0.2.0
purpose: Resolve module import failures found in test output.
pattern: Repair missing or incorrect import paths shown in traceback.
required_evidence:
  - import
  - expected_files
edit_recipe:
  - Capture failing test traceback
  - Fix import path in target module
  - Re-run tests
anti_patterns:
  - rename API only
applies_when:
  - import
  - module
  - ModuleNotFoundError
not_applicable_when:
  - rename API only
required_context:
  - expected_files
verifier: tests_pass
---
1. Run failing tests and capture traceback.
2. Locate the missing/incorrect import path.
3. Update import statements or module path.
4. Re-run tests to verify fix.
