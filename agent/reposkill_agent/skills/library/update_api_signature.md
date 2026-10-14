---
id: update_api_signature_and_callers
name: Update API signature and callers
version: 0.2.0
purpose: Propagate API signature updates to dependent call sites.
pattern: Change signature then update all callers and tests.
required_evidence:
  - api
  - expected_files
edit_recipe:
  - Update function signature with defaults if needed
  - Update all caller locations
  - Run tests
anti_patterns:
  - typo only
applies_when:
  - signature
  - argument
  - caller
  - api
not_applicable_when:
  - typo only
required_context:
  - expected_files
verifier: type_and_tests_pass
---
1. Update function or method signature.
2. Update all caller locations.
3. Verify tests and static checks.
